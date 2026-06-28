// 智能研究助手 — 前端交互

// ====== 工具函数 ======

function escapeHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ====== 快捷键 ======

document.getElementById('topicInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) startResearch();
});

// ====== 提交研究 ======

async function startResearch() {
    const topic = document.getElementById('topicInput').value.trim();
    if (topic.length < 4) return showError('请输入至少4个字的研究主题');

    // 重置 UI
    document.getElementById('progressWrap').style.display = 'block';
    document.getElementById('reportArea').style.display = 'none';
    document.getElementById('reportArea').innerHTML = '';
    hideError();
    document.getElementById('progressFill').style.width = '0%';
    document.getElementById('stepText').textContent = '提交中…';
    document.getElementById('statusTag').className = 'tag tag-running';
    document.getElementById('statusTag').textContent = '分析中';

    try {
        const resp = await fetch('/api/research', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || '请求失败');
        }
        subscribeProgress((await resp.json()).task_id);
    } catch (e) {
        showError(e.message);
    }
}

// ====== SSE 进度订阅 ======

function subscribeProgress(taskId) {
    const bar = document.getElementById('progressFill');
    const step = document.getElementById('stepText');
    const tag = document.getElementById('statusTag');
    const es = new EventSource(`/api/sse/${taskId}`);

    es.addEventListener('status', (e) => {
        const d = JSON.parse(e.data);
        bar.style.width = `${(d.progress || 0) * 100}%`;
        step.textContent = d.current_step || '';

        if (d.status === 'done') {
            tag.className = 'tag tag-done';
            tag.textContent = '✅ 完成';
            es.close();
            renderReport(taskId);
        } else if (d.status === 'failed') {
            tag.className = 'tag tag-failed';
            tag.textContent = '❌ 失败';
            es.close();
            showError(d.error || '分析失败，请重试');
        }
    });

    es.addEventListener('error', () => {
        es.close();
        if (tag.textContent !== '✅ 完成') {
            tag.className = 'tag tag-failed';
            tag.textContent = '❌ 连接断开';
        }
    });
}

// ====== 渲染报告 ======

async function renderReport(taskId) {
    const area = document.getElementById('reportArea');
    try {
        const resp = await fetch(`/api/reports/${taskId}/content`);
        if (!resp.ok) throw new Error('报告加载失败');
        const r = await resp.json();

        let html = '<h2>📄 研究报告</h2>';
        if (r.summary) html += `<p><strong>摘要：</strong>${escapeHtml(r.summary)}</p>`;
        html += '<hr>';
        html += mdToHtml(r.content || '*暂无内容*');

        area.innerHTML = html;
        area.style.display = 'block';
        refreshReports();
    } catch (e) {
        showError('报告加载失败: ' + e.message);
    }
}

// ====== Markdown → HTML ======

function mdToHtml(md) {
    if (!md) return '<p>暂无内容</p>';

    // XSS 防护：先转义所有 HTML
    let h = escapeHtml(md);

    // 标题
    h = h.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
    h = h.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    h = h.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    h = h.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // 粗体 / 斜体
    h = h.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    h = h.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // 链接
    h = h.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

    // 分割线
    h = h.replace(/^---$/gm, '<hr>');

    // 有序列表（加 data-ol 标记供分组识别）
    h = h.replace(/^(\d+)\. (.+)$/gm, '<li data-ol>$2</li>');
    // 无序列表
    h = h.replace(/^[-*] (.+)$/gm, '<li>$1</li>');
    // 列表分组：有序 → <ol>，无序 → <ul>
    h = h.replace(/((?:<li(?: data-ol)?>.*<\/li>\n?)+)/g, (m) =>
        m.includes('data-ol') ? `<ol>${m.replace(/ data-ol/g, '')}</ol>` : `<ul>${m}</ul>`
    );

    // 表格
    h = h.replace(/^\|(.+)\|$/gm, (line) => {
        const cells = line.split('|').filter(c => c.trim()).map(c => c.trim());
        if (/^[-: ]+$/.test(cells[0] || '')) return ''; // 分隔行
        return '<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>';
    });
    h = h.replace(/((?:<tr>.*<\/tr>\n?)+)/g, (match) => {
        const rows = match.match(/<tr>.*?<\/tr>/g);
        if (!rows || rows.length < 2) return `<table>${match}</table>`;
        const thead = `<thead>${rows[0].replace(/<td>/g, '<th>').replace(/<\/td>/g, '</th>')}</thead>`;
        const tbody = `<tbody>${rows.slice(1).join('')}</tbody>`;
        return `<table>${thead}${tbody}</table>`;
    });

    // 段落：双换行 → </p><p>
    h = h.replace(/\n\n/g, '</p><p>');
    h = '<p>' + h + '</p>';

    // 清理：去掉块级元素外的多余 <p>
    const blocks = /<p>(<(?:h[1-4]|table|ul|ol|hr|blockquote))/g;
    const ends = /(<\/\s*(?:h[1-4]|table|ul|ol|hr|blockquote)>)<\/p>/g;
    h = h.replace(blocks, '$1').replace(ends, '$1');
    h = h.replace(/<p>\s*<\/p>/g, '');

    return h;
}

// ====== 错误 ======

function showError(msg) {
    const el = document.getElementById('errorBox');
    el.innerHTML = '⚠️ ' + msg;
    el.style.display = 'block';
}
function hideError() {
    document.getElementById('errorBox').style.display = 'none';
}

// ====== 历史报告 ======

async function refreshReports() {
    const tbody = document.getElementById('reportsBody');
    try {
        const resp = await fetch('/api/reports');
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();

        if (!data.items || !data.items.length) {
            tbody.innerHTML = '<tr><td class="empty" colspan="3">暂无报告</td></tr>';
            return;
        }

        tbody.innerHTML = data.items.map(r => {
            const date = (r.created_at || '').slice(0, 10);
            const label = escapeHtml((r.topic || r.stock_name || '').slice(0, 50));
            const summary = escapeHtml((r.summary || '').slice(0, 60));
            return `<tr><td>${label}</td><td>${summary || '—'}</td><td>${date}</td></tr>`;
        }).join('');
    } catch (e) {
        console.error('加载历史报告失败:', e);
        tbody.innerHTML = `<tr><td class="empty" colspan="3" style="color:var(--danger)">加载失败: ${escapeHtml(e.message)}</td></tr>`;
    }
}

refreshReports();
