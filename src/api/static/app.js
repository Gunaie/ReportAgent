// 智能研究助手 — 对话式交互

let _currentTaskId = null;
let _busy = false;

const chat = document.getElementById('chatBox');
const input = document.getElementById('msgInput');
const sendBtn = document.getElementById('sendBtn');
const errEl = document.getElementById('inputError');

// ====== 快捷键 ======

input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) sendMessage();
});

// 模板快速填充
document.getElementById('tplBar').addEventListener('click', (e) => {
    if (e.target.classList.contains('tpl-chip')) {
        const tpl = e.target.dataset.tpl;
        input.value = `分析${tpl}行业的发展趋势、竞争格局和风险`;
        input.focus();
    }
});

// ====== 发送消息 ======

async function sendMessage() {
    if (_busy) return;
    const text = input.value.trim();
    if (!text) return;

    if (text.length < 4) {
        showError('请输入至少4个字的研究主题');
        return;
    }

    _busy = true;
    hideError();
    sendBtn.disabled = true;

    // 判断是首次研究还是继续对话
    if (_currentTaskId && _isClarifying()) {
        await continueResearch(text);
    } else {
        await startResearch(text);
    }

    input.value = '';
    _busy = false;
    sendBtn.disabled = false;
    input.focus();
}

function _isClarifying() {
    const last = lastProgressMsg();
    return last && last.querySelector('.tag-clarifying');
}

// ====== 首次研究 ======

async function startResearch(topic) {
    addBubble('user', topic);

    try {
        const resp = await fetch('/api/research', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic }),
        });
        if (!resp.ok) {
            const e = await resp.json();
            throw new Error(e.detail || '请求失败');
        }
        const { task_id } = await resp.json();
        _currentTaskId = task_id;
        subscribeSSE(task_id);
    } catch (e) {
        addBubble('assistant', '❌ ' + e.message);
    }
}

// ====== 继续对话 ======

async function continueResearch(reply) {
    addBubble('user', reply);

    try {
        const resp = await fetch('/api/research/continue', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: _currentTaskId, user_reply: reply }),
        });
        if (!resp.ok) {
            const e = await resp.json();
            throw new Error(e.detail || '请求失败');
        }
        subscribeSSE(_currentTaskId);
    } catch (e) {
        addBubble('assistant', '❌ ' + e.message);
    }
}

// ====== SSE 订阅 ======

function subscribeSSE(taskId) {
    // 清理旧进度
    removeProgress();

    const es = new EventSource(`/api/sse/${taskId}`);
    let done = false;

    es.addEventListener('status', (e) => {
        if (done) return;
        const d = JSON.parse(e.data);
        updateProgress(d);

        if (d.status === 'clarifying') {
            done = true;
            es.close();
            removeProgress();
            const q = d.result?.clarify_question || '请补充更多信息';
            addBubble('assistant', '🔍 ' + q);
            // 显示提示
            const tip = addElement('div', 'progress-msg');
            tip.innerHTML = '<span style="color:var(--accent)">👆 请回复补充信息后发送</span>';
            chat.appendChild(tip);
            scrollDown();
            _busy = false;
            sendBtn.disabled = false;
            input.focus();
        } else if (d.status === 'done') {
            done = true;
            es.close();
            removeProgress();
            renderReport(taskId);
        } else if (d.status === 'failed') {
            done = true;
            es.close();
            removeProgress();
            addBubble('assistant', '❌ 分析失败: ' + (d.error || '未知错误'));
        }
    });

    es.addEventListener('error', () => {
        if (!done) {
            es.close();
            removeProgress();
            addBubble('assistant', '❌ 连接断开，请重试');
        }
    });
}

// ====== 报告渲染 ======

async function renderReport(taskId) {
    try {
        const resp = await fetch(`/api/reports/${taskId}/content`);
        if (!resp.ok) throw new Error('报告加载失败');
        const r = await resp.json();

        let html = '<div class="report">';
        if (r.summary) html += `<p><strong>📝 摘要：</strong>${escapeHtml(r.summary)}</p>`;
        html += '<hr>';
        html += mdToHtml(r.content || '*暂无内容*');
        // 导出按钮
        html += `<div style="margin-top:20px;display:flex;gap:8px;flex-wrap:wrap">
            <a href="/api/reports/${taskId}/export?format=pdf" download class="export-btn pdf">📄 下载 PDF</a>
            <a href="/api/reports/${taskId}/export?format=docx" download class="export-btn docx">📝 下载 Word</a>
        </div>`;
        html += '</div>';

        const bubble = addBubble('assistant', '', 'report');
        bubble.innerHTML = html;
        _currentTaskId = null;
        refreshHistory();
    } catch (e) {
        addBubble('assistant', '❌ 报告加载失败: ' + e.message);
    }
}

// ====== 进度条 ======

function updateProgress(d) {
    let el = lastProgressMsg();
    if (!el) {
        el = addElement('div', 'progress-msg');
        chat.appendChild(el);
    }
    const pct = Math.round((d.progress || 0) * 100);
    const step = d.current_step || '';
    const status = d.status;
    const tagClass = status === 'running' ? 'tag-running' : status === 'done' ? 'tag-done' : status === 'failed' ? 'tag-failed' : status === 'clarifying' ? 'tag-clarifying' : '';
    el.innerHTML = `<span>${step}</span><span class="tag ${tagClass}">${status}</span>
        <div class="bar"><div class="fill" style="width:${pct}%"></div></div>`;
    scrollDown();
}

function lastProgressMsg() {
    const list = chat.querySelectorAll('.progress-msg');
    return list.length ? list[list.length - 1] : null;
}

function removeProgress() {
    chat.querySelectorAll('.progress-msg').forEach(e => e.remove());
}

// ====== 对话气泡 ======

function addBubble(role, text, extraClass) {
    const div = addElement('div', `msg ${role}`);
    const avatar = addElement('div', 'avatar');
    avatar.textContent = role === 'user' ? '👤' : '🤖';
    const bubble = addElement('div', `bubble ${extraClass || ''}`);
    if (text) bubble.innerHTML = text.replace(/\n/g, '<br>');
    div.appendChild(avatar);
    div.appendChild(bubble);
    chat.appendChild(div);
    scrollDown();
    return bubble;
}

function addElement(tag, className) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    return el;
}

function scrollDown() {
    requestAnimationFrame(() => { chat.scrollTop = chat.scrollHeight; });
}

// ====== 工具 ======

function escapeHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function showError(msg) {
    errEl.textContent = msg;
    errEl.style.display = 'block';
}
function hideError() {
    errEl.style.display = 'none';
}

// ====== Markdown → HTML ======

function mdToHtml(md) {
    if (!md) return '<p>暂无内容</p>';
    let h = escapeHtml(md);

    h = h.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
    h = h.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    h = h.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    h = h.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    h = h.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    h = h.replace(/\*(.+?)\*/g, '<em>$1</em>');
    h = h.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    h = h.replace(/^---$/gm, '<hr>');
    h = h.replace(/^(\d+)\. (.+)$/gm, '<li data-ol>$2</li>');
    h = h.replace(/^[-*] (.+)$/gm, '<li>$1</li>');
    h = h.replace(/((?:<li(?: data-ol)?>.*<\/li>\n?)+)/g, (m) =>
        m.includes('data-ol') ? `<ol>${m.replace(/ data-ol/g, '')}</ol>` : `<ul>${m}</ul>`
    );
    h = h.replace(/^\|(.+)\|$/gm, (line) => {
        const cells = line.split('|').filter(c => c.trim()).map(c => c.trim());
        if (/^[-: ]+$/.test(cells[0] || '')) return '';
        return '<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>';
    });
    h = h.replace(/((?:<tr>.*<\/tr>\n?)+)/g, (match) => {
        const rows = match.match(/<tr>.*?<\/tr>/g);
        if (!rows || rows.length < 2) return `<table>${match}</table>`;
        const thead = `<thead>${rows[0].replace(/<td>/g, '<th>').replace(/<\/td>/g, '</th>')}</thead>`;
        const tbody = `<tbody>${rows.slice(1).join('')}</tbody>`;
        return `<table>${thead}${tbody}</table>`;
    });

    h = h.replace(/\n\n/g, '</p><p>');
    h = '<p>' + h + '</p>';
    const blocks = /<p>(<(?:h[1-4]|table|ul|ol|hr|blockquote))/g;
    const ends = /(<\/\s*(?:h[1-4]|table|ul|ol|hr|blockquote)>)<\/p>/g;
    h = h.replace(blocks, '$1').replace(ends, '$1');
    h = h.replace(/<p>\s*<\/p>/g, '');
    return h;
}

// ====== 历史报告侧边栏 ======

async function refreshHistory() {
    // 轻量刷新 — 后台同步，不阻塞
    try {
        const resp = await fetch('/api/reports?size=5');
        if (!resp.ok) return;
        // 后台静默更新，不影响 UI
    } catch (e) { /* ignore */ }
}
