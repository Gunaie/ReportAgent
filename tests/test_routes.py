"""API 路由测试 — 研究/任务/报告/对话 端点。"""

import pytest
from fastapi.testclient import TestClient
from src.api.app import app


@pytest.fixture
def client():
    """TestClient（上下文管理器确保 lifespan 执行）。"""
    with TestClient(app) as c:
        yield c


class TestResearchEndpoint:
    """POST /api/research — 提交研究任务。"""

    def test_valid_topic_returns_task_id(self, client):
        """合法主题 → 返回 task_id 和 pending 状态。"""
        resp = client.post("/api/research", json={"topic": "新能源汽车电池技术分析"})
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data
        assert data["status"] == "pending"
        assert len(data["task_id"]) == 36  # UUID

    def test_topic_too_short_rejected(self, client):
        """主题过短 → 422。"""
        resp = client.post("/api/research", json={"topic": "ab"})
        assert resp.status_code == 422

    def test_empty_topic_rejected(self, client):
        """空主题 → 422。"""
        resp = client.post("/api/research", json={"topic": ""})
        assert resp.status_code == 422

    def test_empty_topic_via_whitespace_rejected(self, client):
        """纯空白主题 → 422（validator 清理后 <4 字符）。"""
        resp = client.post("/api/research", json={"topic": "   "})
        assert resp.status_code == 422


class TestTaskEndpoint:
    """GET /api/task/{task_id} — 查询任务状态。"""

    def test_valid_task_returns_status(self, client):
        """已存在的任务 → 返回状态。"""
        # 先创建
        resp = client.post("/api/research", json={"topic": "测试任务查询"})
        task_id = resp.json()["task_id"]

        # 查询
        resp = client.get(f"/api/task/{task_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == task_id
        assert data["status"] in ("pending", "running", "clarifying", "done", "failed")

    def test_nonexistent_task_returns_404(self, client):
        """不存在的任务 → 404。"""
        resp = client.get("/api/task/nonexistent-id-12345")
        assert resp.status_code == 404

    def test_task_response_has_required_fields(self, client):
        """响应包含所有必需字段。"""
        resp = client.post("/api/research", json={"topic": "字段完整性测试"})
        task_id = resp.json()["task_id"]

        resp = client.get(f"/api/task/{task_id}")
        data = resp.json()

        required = ["task_id", "status", "progress", "current_step", "error", "result"]
        for field in required:
            assert field in data, f"Missing field: {field}"


class TestReportsEndpoint:
    """GET /api/reports — 历史报告列表。"""

    def test_list_reports_returns_paginated(self, client):
        """返回分页结构。"""
        resp = client.get("/api/reports")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "page" in data
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_list_reports_items_have_required_fields(self, client):
        """每条报告包含必需字段。"""
        resp = client.get("/api/reports")
        data = resp.json()
        if data["items"]:
            item = data["items"][0]
            for field in ["id", "task_id", "topic", "summary", "created_at"]:
                assert field in item, f"Missing: {field}"


class TestReportContentEndpoint:
    """GET /api/reports/{task_id}/content — 报告 Markdown 全文。"""

    def test_nonexistent_report_returns_404(self, client):
        """不存在的报告 → 404。"""
        resp = client.get("/api/reports/nonexistent-id/content")
        assert resp.status_code == 404


class TestConversationEndpoint:
    """GET /api/conversation/{task_id} — 对话历史。"""

    def test_conversation_returns_structure(self, client):
        """返回对话历史结构。"""
        resp = client.post("/api/research", json={"topic": "对话历史测试主题"})
        task_id = resp.json()["task_id"]

        resp = client.get(f"/api/conversation/{task_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == task_id
        assert "messages" in data
        assert isinstance(data["messages"], list)
        # 至少有用户输入的那条
        assert len(data["messages"]) >= 1

    def test_conversation_messages_have_role_content(self, client):
        """每条消息含 role/content/time。"""
        resp = client.post("/api/research", json={"topic": "消息字段测试"})
        task_id = resp.json()["task_id"]

        resp = client.get(f"/api/conversation/{task_id}")
        for msg in resp.json()["messages"]:
            assert "role" in msg
            assert "content" in msg
            assert msg["role"] in ("user", "assistant")


class TestContinueEndpoint:
    """POST /api/research/continue — 继续对话。"""

    def test_continue_wrong_status_rejected(self, client):
        """非 clarifying 状态的任务 → 400。"""
        resp = client.post("/api/research", json={"topic": "继续对话拒绝测试"})
        task_id = resp.json()["task_id"]

        # 任务刚创建是 pending，不是 clarifying
        resp = client.post("/api/research/continue", json={
            "task_id": task_id, "user_reply": "补充信息"
        })
        assert resp.status_code == 400

    def test_continue_nonexistent_task_returns_404(self, client):
        """不存在的任务 → 404。"""
        resp = client.post("/api/research/continue", json={
            "task_id": "nonexistent-12345", "user_reply": "test"
        })
        assert resp.status_code == 404

    def test_continue_short_reply_rejected(self, client):
        """回复过短 → 422。"""
        resp = client.post("/api/research/continue", json={
            "task_id": "some-id", "user_reply": "x"
        })
        assert resp.status_code == 422


class TestHealthEndpoint:
    """GET /health — 健康检查。"""

    def test_health_returns_ok(self, client):
        """返回 healthy。"""
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"
        assert resp.json()["service"] == "智能研究助手"
