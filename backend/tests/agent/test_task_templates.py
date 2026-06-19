"""task_templates 单元测试 + create_session 集成测试（Task 6）。"""
from __future__ import annotations

import time
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models.agent_session import AgentSession
from app.models.user import User
from app.services.agent import runner_factory, session_runner, stream_bridge
from app.services.agent.runner import AgentEvent
from app.services.agent.task_templates import (
    TASK_TEMPLATES,
    get_template,
    list_task_types,
)


# --------------------------------------------------------------------------- #
# task_templates 纯单元测试
# --------------------------------------------------------------------------- #
def test_get_template_fill_piece_weight_shape():
    """get_template('fill_piece_weight') 返回含 title/prompt/allowed_tools。"""
    tpl = get_template("fill_piece_weight")
    assert tpl["title"]  # 非空
    assert isinstance(tpl["prompt"], str) and tpl["prompt"].strip()
    assert isinstance(tpl["allowed_tools"], list) and tpl["allowed_tools"]
    # allowed_tools 对齐 controlled_db MCP 只读三件套。
    assert "mcp__controlled_db__db_read" in tpl["allowed_tools"]
    assert "mcp__controlled_db__describe" in tpl["allowed_tools"]
    assert "mcp__controlled_db__list_tables" in tpl["allowed_tools"]


def test_fill_piece_weight_prompt_contains_required_constraints():
    """prompt 含方案 B + 历史守卫模式关键约束。"""
    prompt = get_template("fill_piece_weight")["prompt"]

    # 目标表/字段。
    assert "entity_unit_overrides" in prompt
    assert "weight_per_unit" in prompt

    # 方案 B：无写工具 + ```sql``` 输出。
    assert "只读" in prompt or "没有任何写工具" in prompt
    assert "```sql```" in prompt.replace(" ", "") or "```sql```" in prompt

    # 历史守卫：WHERE + AND 原值 + source=agent。
    assert "WHERE id IN" in prompt or "WHERE id in" in prompt
    assert "AND weight_per_unit" in prompt
    assert "source = 'agent'" in prompt or "source='agent'" in prompt


def test_get_template_unknown_raises_key_error():
    """未知 task_type 抛 KeyError。"""
    with pytest.raises(KeyError):
        get_template("does_not_exist")


def test_list_task_types_contains_fill_piece_weight():
    """list_task_types() 返回 [{task_type, title}] 且含 fill_piece_weight。"""
    items = list_task_types()
    assert isinstance(items, list) and items
    keys = [it["task_type"] for it in items]
    assert "fill_piece_weight" in keys
    the = next(it for it in items if it["task_type"] == "fill_piece_weight")
    assert the["title"]  # 非空 title
    # 每项只含 task_type / title 两键。
    assert set(the.keys()) == {"task_type", "title"}


def test_list_task_types_matches_registry_keys():
    """list_task_types 的 task_type 集合与 TASK_TEMPLATES 键一致。"""
    assert {it["task_type"] for it in list_task_types()} == set(TASK_TEMPLATES.keys())


# --------------------------------------------------------------------------- #
# create_session 集成测试：模板 prompt 注入 + 未知 400 + task-types 端点
# --------------------------------------------------------------------------- #
@pytest.fixture()
def _mem_env(monkeypatch):
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    TestSession = sessionmaker(bind=eng, autoflush=False, autocommit=False)

    import app.core.database as dbmod

    monkeypatch.setattr(dbmod, "SessionLocal", TestSession)
    monkeypatch.setattr("app.api.agent_api.SessionLocal", TestSession, raising=False)

    db = TestSession()
    try:
        admin = User(
            username="admin", email="a@t.com", password_hash="x", is_admin=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        admin_id = admin.id
    finally:
        db.close()

    class _U:
        def __init__(self, uid, is_admin):
            self.id = uid
            self.is_admin = is_admin

    def _admin_user():
        return _U(admin_id, True)

    def _get_db():
        s = TestSession()
        try:
            yield s
        finally:
            s.close()

    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_current_user] = _admin_user

    with stream_bridge._lock:
        stream_bridge._subscribers.clear()

    yield {"Session": TestSession, "admin_id": admin_id}

    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)
    with stream_bridge._lock:
        stream_bridge._subscribers.clear()
    eng.dispose()


class _FakeRunner:
    def __init__(self, events):
        self._events = list(events)

    @property
    def last_session_id(self):
        return "fake-sid"

    def run(self, prompt, *, resume_session_id=None) -> Iterator[AgentEvent]:
        for ev in self._events:
            yield ev


def _patch_loop_capture_prompt(mem_env, monkeypatch) -> list[dict]:
    calls: list[dict] = []

    def _fake(session_id, runner, initial_prompt, main_loop, **kwargs):
        calls.append({"initial_prompt": initial_prompt})
        db = mem_env["Session"]()
        try:
            s = db.query(AgentSession).get(session_id)
            if s is not None:
                s.status = "success"
                s.claude_session_id = "fake-sid"
                db.commit()
        finally:
            db.close()

    monkeypatch.setattr(session_runner, "run_agent_loop", _fake)
    return calls


def test_create_session_injects_template_prompt(_mem_env, monkeypatch):
    """建 fill_piece_weight 会话：initial_prompt == 模板 prompt。"""
    calls = _patch_loop_capture_prompt(_mem_env, monkeypatch)

    with TestClient(app) as c:
        resp = c.post(
            "/api/v1/agent/sessions", json={"task_type": "fill_piece_weight"}
        )
        assert resp.status_code == 200, resp.text
        sid = resp.json()["session_id"]

        # 等后台线程调用 fake loop。
        deadline = time.time() + 3.0
        while time.time() < deadline and not calls:
            time.sleep(0.01)

    assert len(calls) == 1, f"calls={calls}"
    expected = get_template("fill_piece_weight")["prompt"]
    assert calls[0]["initial_prompt"] == expected

    # title 也应来自模板。
    db = _mem_env["Session"]()
    try:
        s = db.query(AgentSession).get(sid)
        assert s.title == get_template("fill_piece_weight")["title"]
    finally:
        db.close()


def test_task_types_endpoint(_mem_env):
    """GET /api/v1/agent/task-types 返回 list_task_types() 结果。"""
    with TestClient(app) as c:
        resp = c.get("/api/v1/agent/task-types")
        assert resp.status_code == 200
        data = resp.json()
        keys = [it["task_type"] for it in data]
        assert "fill_piece_weight" in keys
        assert data == list_task_types()


def test_create_session_unknown_task_type_400_via_api(_mem_env):
    """API 层：未知 task_type → 400 + 中文 detail。"""
    with TestClient(app) as c:
        resp = c.post(
            "/api/v1/agent/sessions", json={"task_type": "nope"}
        )
        assert resp.status_code == 400
        assert "未知任务类型" in resp.json()["detail"]
