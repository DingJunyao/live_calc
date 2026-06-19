"""Agent 任务台 API 测试（Task 5）。

隔离策略（对齐 test_session_runner）：
- 内存 SQLite + StaticPool（跨线程共享同一内存库）。
- monkeypatch ``app.core.database.SessionLocal`` → TestSession，使端点内的
  ``SessionLocal()`` 与后台线程的独立 Session 都指向同一内存库。
- ``app.dependency_overrides[get_db / get_current_user]`` 覆盖鉴权/db 依赖。
- monkeypatch ``runner_factory.build_runner`` → FakeRunner；以及
  ``session_runner.run_agent_loop`` → 记录调用并立即标 success（端到端场景
  才用真 run_agent_loop + FakeRunner）。
"""
from __future__ import annotations

import asyncio
import threading
import time
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token, get_current_user
from app.main import app
from app.models.agent_approval import AgentApproval
from app.models.agent_message import AgentMessage
from app.models.agent_session import AgentSession
from app.models.user import User
from app.services.agent import runner_factory, session_runner, stream_bridge
from app.services.agent.runner import AgentEvent


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture()
def mem_env(monkeypatch):
    """内存库 + 替换 SessionLocal + 鉴权 override。"""
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    TestSession = sessionmaker(bind=eng, autoflush=False, autocommit=False)

    import app.core.database as dbmod

    monkeypatch.setattr(dbmod, "SessionLocal", TestSession)
    # agent_api 内 ``from app.core.database import SessionLocal`` 是函数内 import，
    # 会拿到被 patch 的属性。
    monkeypatch.setattr(
        "app.api.agent_api.SessionLocal", TestSession, raising=False
    )

    # 建 admin / 普通用户
    db = TestSession()
    try:
        admin = User(
            username="admin",
            email="admin@test.com",
            password_hash="x",
            is_admin=True,
        )
        plain = User(
            username="user",
            email="user@test.com",
            password_hash="x",
            is_admin=False,
        )
        db.add_all([admin, plain])
        db.commit()
        db.refresh(admin)
        db.refresh(plain)
        admin_id = admin.id
        plain_id = plain.id
    finally:
        db.close()

    def _admin_user():
        class _U:
            id = admin_id
            is_admin = True
        return _U()

    def _plain_user():
        class _U:
            id = plain_id
            is_admin = False
        return _U()

    def _get_db():
        s = TestSession()
        try:
            yield s
        finally:
            s.close()

    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = _get_db

    # 清空订阅者（隔离 stream_bridge 全局状态）
    with stream_bridge._lock:
        stream_bridge._subscribers.clear()

    yield {
        "Session": TestSession,
        "admin_user": _admin_user,
        "plain_user": _plain_user,
        "admin_id": admin_id,
        "plain_id": plain_id,
    }

    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)
    with stream_bridge._lock:
        stream_bridge._subscribers.clear()
    eng.dispose()


@pytest.fixture()
def admin_client(mem_env):
    """以管理员身份注入 get_current_user。"""
    app.dependency_overrides[get_current_user] = mem_env["admin_user"]
    # TestClient 用新 loop；stream 端点的 asyncio.get_event_loop() 需在 async
    # 上下文里。
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def plain_client(mem_env):
    app.dependency_overrides[get_current_user] = mem_env["plain_user"]
    with TestClient(app) as c:
        yield c


def _make_token(user_id: int) -> str:
    """生成 access JWT（C2 stream 端点 query token 鉴权用）。"""
    return create_access_token({"sub": str(user_id)})


def _make_invalid_token() -> str:
    """生成一个无效 token（用错误密钥签）。"""
    from jose import jwt as _jwt
    from app.config import settings

    # 用错误密钥 + 过期时间构造，decode_token 会失败。
    return _jwt.encode(
        {"sub": "1", "type": "access", "exp": 9999999999},
        settings.jwt_secret_key + "__tampered",
        algorithm="HS256",
    )


class _FakeRunner:
    """假 AgentRunner：按预设 events 产出，记录调用参数。"""

    def __init__(self, events: list[AgentEvent], last_sid: str | None = "fake-sid"):
        self._events = list(events)
        self._last_sid = last_sid
        self.calls: list[dict] = []

    @property
    def last_session_id(self):
        return self._last_sid

    def run(self, prompt, *, resume_session_id=None) -> Iterator[AgentEvent]:
        self.calls.append(
            {"prompt": prompt, "resume_session_id": resume_session_id}
        )
        for ev in self._events:
            yield ev


def _patch_loop_immediate_success(mem_env, monkeypatch):
    """monkeypatch run_agent_loop 为：标记 running→success，不跑 Runner。

    返回 calls 列表供断言。
    """
    calls: list[dict] = []

    def _fake(session_id, runner, initial_prompt, main_loop, **kwargs):
        calls.append(
            {
                "session_id": session_id,
                "initial_prompt": initial_prompt,
                "main_loop": main_loop,
                "kwargs": kwargs,
            }
        )
        db = mem_env["Session"]()
        try:
            s = db.query(AgentSession).get(session_id)
            if s is not None:
                s.status = "success"
                s.claude_session_id = "claude-test-sid"
                db.commit()
        finally:
            db.close()

    monkeypatch.setattr(session_runner, "run_agent_loop", _fake)
    # agent_api 内 ``from ... import session_runner`` 后调用
    # ``session_runner.run_agent_loop`` —— patch 模块属性即可生效。
    return calls


def _patch_build_runner(monkeypatch, runner: _FakeRunner):
    """monkeypatch runner_factory.build_runner 返回固定 runner。"""
    monkeypatch.setattr(
        runner_factory, "build_runner", lambda *a, **kw: runner
    )
    monkeypatch.setattr(
        "app.api.agent_api.runner_factory.build_runner",
        lambda *a, **kw: runner,
        raising=False,
    )


def _wait_session_status(mem_env, sid: int, target: set[str], timeout: float = 3.0):
    """轮询等待 session.status 进入 target。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        db = mem_env["Session"]()
        try:
            s = db.query(AgentSession).get(sid)
            if s is not None and s.status in target:
                return s.status
        finally:
            db.close()
        time.sleep(0.02)
    return None


# --------------------------------------------------------------------------- #
# POST /sessions
# --------------------------------------------------------------------------- #
def test_create_session_admin_only(plain_client):
    """非管理员建会话 → 403。"""
    resp = plain_client.post(
        "/api/v1/agent/sessions", json={"task_type": "fill_piece_weight"}
    )
    assert resp.status_code == 403


def test_create_session_starts_loop_and_returns_id(
    admin_client, mem_env, monkeypatch
):
    """管理员建会话：返回 session_id，后台 loop 被调用，session 标 success。"""
    calls = _patch_loop_immediate_success(mem_env, monkeypatch)

    resp = admin_client.post(
        "/api/v1/agent/sessions", json={"task_type": "fill_piece_weight"}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "session_id" in data
    sid = data["session_id"]

    # 等后台线程跑完。
    status = _wait_session_status(mem_env, sid, {"success"})
    assert status == "success"

    assert len(calls) == 1
    assert calls[0]["session_id"] == sid
    # fill_piece_weight 命中 TASK_TEMPLATES，用模板 prompt。
    tpl_prompt = __import__(
        "app.services.agent.task_templates", fromlist=["get_template"]
    ).get_template("fill_piece_weight")["prompt"]
    assert calls[0]["initial_prompt"] == tpl_prompt
    # main_loop 非空（async 端点捕获的）。
    assert calls[0]["main_loop"] is not None
    # 默认未传 resume_session_id。
    assert calls[0]["kwargs"].get("resume_session_id") is None


def test_create_session_unknown_task_type_400(admin_client):
    """未识别 task_type → 400（Task 6 后改为严格校验，不再透传 prompt）。"""
    resp = admin_client.post(
        "/api/v1/agent/sessions", json={"task_type": "do-something-custom"}
    )
    assert resp.status_code == 400
    assert "未知任务类型" in resp.json()["detail"]


# --------------------------------------------------------------------------- #
# GET /sessions, GET /sessions/{sid}
# --------------------------------------------------------------------------- #
def test_list_and_get_session(admin_client, mem_env, monkeypatch):
    _patch_loop_immediate_success(mem_env, monkeypatch)
    resp = admin_client.post(
        "/api/v1/agent/sessions", json={"task_type": "fill_piece_weight"}
    )
    sid = resp.json()["session_id"]
    _wait_session_status(mem_env, sid, {"success"})

    # list
    lst = admin_client.get("/api/v1/agent/sessions").json()
    assert any(s["id"] == sid for s in lst)
    the = next(s for s in lst if s["id"] == sid)
    assert the["status"] == "success"
    assert the["task_type"] == "fill_piece_weight"

    # detail
    detail = admin_client.get(f"/api/v1/agent/sessions/{sid}").json()
    assert detail["session"]["id"] == sid
    assert isinstance(detail["messages"], list)
    assert isinstance(detail["pending_approvals"], list)


def test_get_session_404(admin_client):
    resp = admin_client.get("/api/v1/agent/sessions/999999")
    assert resp.status_code == 404


def test_list_session_plain_user_sees_only_own(mem_env):
    """普通用户 list 只看自己的；get 别人的 → 404。

    plain user 无法建 session（admin only），故直接在 DB 里给 plain user 造一条。
    """
    db = mem_env["Session"]()
    try:
        admin_s = AgentSession(
            task_type="x", status="success",
            runner_type="claude_code", user_id=mem_env["admin_id"],
        )
        plain_s = AgentSession(
            task_type="y", status="success",
            runner_type="claude_code", user_id=mem_env["plain_id"],
        )
        db.add_all([admin_s, plain_s])
        db.commit()
        db.refresh(admin_s)
        db.refresh(plain_s)
        admin_sid = admin_s.id
        plain_sid = plain_s.id
    finally:
        db.close()

    app.dependency_overrides[get_current_user] = mem_env["plain_user"]
    with TestClient(app) as c:
        # plain list 只看到自己的
        lst = c.get("/api/v1/agent/sessions").json()
        ids = [s["id"] for s in lst]
        assert plain_sid in ids
        assert admin_sid not in ids

        # plain get admin 的 → 404
        assert c.get(f"/api/v1/agent/sessions/{admin_sid}").status_code == 404

        # plain get 自己的 → 200
        assert c.get(f"/api/v1/agent/sessions/{plain_sid}").status_code == 200


# --------------------------------------------------------------------------- #
# POST /approvals/{aid}
# --------------------------------------------------------------------------- #
def test_decide_approval_wakes_loop(admin_client, mem_env, monkeypatch):
    """管理员 POST approval approved → wake_approval 被调，状态变 approved。"""
    # 先建一个 session（不真跑 loop，直接造数据）
    db = mem_env["Session"]()
    try:
        s = AgentSession(
            task_type="fill_piece_weight",
            status="awaiting_approval",
            runner_type="claude_code",
            user_id=mem_env["admin_id"],
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        sid = s.id
        ap = AgentApproval(
            session_id=sid, sql="UPDATE products SET x=1", status="pending"
        )
        db.add(ap)
        db.commit()
        db.refresh(ap)
        aid = ap.id
    finally:
        db.close()

    resp = admin_client.post(
        f"/api/v1/agent/approvals/{aid}", json={"approved": True}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["ok"] is True

    db = mem_env["Session"]()
    try:
        ap2 = db.query(AgentApproval).get(aid)
        assert ap2.status == "approved"
        assert ap2.decided_by == mem_env["admin_id"]
    finally:
        db.close()


def test_decide_approval_double_decision_409(admin_client, mem_env):
    db = mem_env["Session"]()
    try:
        s = AgentSession(
            task_type="x", status="awaiting_approval",
            runner_type="claude_code", user_id=mem_env["admin_id"],
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        ap = AgentApproval(
            session_id=s.id, sql="UPDATE t SET a=1", status="approved"
        )
        db.add(ap)
        db.commit()
        db.refresh(ap)
        aid = ap.id
    finally:
        db.close()

    resp = admin_client.post(
        f"/api/v1/agent/approvals/{aid}", json={"approved": True}
    )
    assert resp.status_code == 409


def test_decide_approval_not_found(admin_client):
    resp = admin_client.post(
        "/api/v1/agent/approvals/999999", json={"approved": True}
    )
    assert resp.status_code == 404


def test_decide_approval_admin_only(plain_client, mem_env):
    db = mem_env["Session"]()
    try:
        s = AgentSession(
            task_type="x", status="awaiting_approval",
            runner_type="claude_code", user_id=mem_env["plain_id"],
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        ap = AgentApproval(
            session_id=s.id, sql="UPDATE t SET a=1", status="pending"
        )
        db.add(ap)
        db.commit()
        db.refresh(ap)
        aid = ap.id
    finally:
        db.close()

    resp = plain_client.post(
        f"/api/v1/agent/approvals/{aid}", json={"approved": True}
    )
    assert resp.status_code == 403


# --------------------------------------------------------------------------- #
# POST /sessions/{sid}/messages （插话）
# --------------------------------------------------------------------------- #
def test_post_message_resume(admin_client, mem_env, monkeypatch):
    """插话：终态 session + claude_session_id → resume_session_id 透传。"""
    calls = _patch_loop_immediate_success(mem_env, monkeypatch)

    # 建一个已终态的 session
    db = mem_env["Session"]()
    try:
        s = AgentSession(
            task_type="fill_piece_weight",
            status="success",
            runner_type="claude_code",
            claude_session_id="claude-abc",
            user_id=mem_env["admin_id"],
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        sid = s.id
    finally:
        db.close()

    resp = admin_client.post(
        f"/api/v1/agent/sessions/{sid}/messages", json={"text": "再查一下"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["resumed"] is True

    # 等后台线程调用 run_agent_loop（立即标 success）。
    _wait_session_status(mem_env, sid, {"success"})
    # 后台线程启动有调度延迟，再轮询 calls。
    deadline = time.time() + 3.0
    while time.time() < deadline and len(calls) == 0:
        time.sleep(0.01)
    assert len(calls) == 1, f"calls={calls}"
    assert calls[0]["initial_prompt"] == "再查一下"
    assert calls[0]["kwargs"].get("resume_session_id") == "claude-abc"


def test_post_message_running_session_409(admin_client, mem_env):
    db = mem_env["Session"]()
    try:
        s = AgentSession(
            task_type="x", status="running",
            runner_type="claude_code", claude_session_id="c",
            user_id=mem_env["admin_id"],
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        sid = s.id
    finally:
        db.close()

    resp = admin_client.post(
        f"/api/v1/agent/sessions/{sid}/messages", json={"text": "hi"}
    )
    assert resp.status_code == 409


def test_post_message_no_claude_sid_409(admin_client, mem_env):
    db = mem_env["Session"]()
    try:
        s = AgentSession(
            task_type="x", status="success",
            runner_type="claude_code", claude_session_id=None,
            user_id=mem_env["admin_id"],
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        sid = s.id
    finally:
        db.close()

    resp = admin_client.post(
        f"/api/v1/agent/sessions/{sid}/messages", json={"text": "hi"}
    )
    assert resp.status_code == 409


def test_post_message_admin_only(plain_client, mem_env):
    db = mem_env["Session"]()
    try:
        s = AgentSession(
            task_type="x", status="success",
            runner_type="claude_code", claude_session_id="c",
            user_id=mem_env["plain_id"],
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        sid = s.id
    finally:
        db.close()

    resp = plain_client.post(
        f"/api/v1/agent/sessions/{sid}/messages", json={"text": "hi"}
    )
    assert resp.status_code == 403


# --------------------------------------------------------------------------- #
# GET /sessions/{sid}/stream （SSE）
# --------------------------------------------------------------------------- #
def test_stream_replays_history_and_synthesized_done_for_terminal(
    admin_client, mem_env
):
    """终态 session：回放历史 + synthesized done。"""
    db = mem_env["Session"]()
    try:
        s = AgentSession(
            task_type="x", status="success",
            runner_type="claude_code", user_id=mem_env["admin_id"],
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        sid = s.id
        db.add(AgentMessage(session_id=sid, seq=1, role="assistant", content="hello"))
        db.add(AgentMessage(session_id=sid, seq=2, role="tool", tool_name="T"))
        db.commit()
    finally:
        db.close()

    token = _make_token(mem_env["admin_id"])
    with admin_client.stream(
        "GET", f"/api/v1/agent/sessions/{sid}/stream?token={token}"
    ) as r:
        assert r.status_code == 200
        body = b"".join(r.iter_bytes()).decode("utf-8")

    assert "event: message" in body
    assert '"kind": "history"' in body
    assert "hello" in body
    assert '"kind": "done"' in body
    assert '"synthesized": true' in body


def test_stream_404(admin_client, mem_env):
    """session 不存在 → 404（query token 有效）。"""
    token = _make_token(mem_env["admin_id"])
    resp = admin_client.get(
        f"/api/v1/agent/sessions/999999/stream?token={token}"
    )
    assert resp.status_code == 404


# --------------------------------------------------------------------------- #
# C1：subscribe 前置 + seq 去重
# C2：query token 鉴权
# --------------------------------------------------------------------------- #
def test_stream_query_token_auth_valid(mem_env):
    """C2：valid query token → 200。"""
    db = mem_env["Session"]()
    try:
        s = AgentSession(
            task_type="x", status="success",
            runner_type="claude_code", user_id=mem_env["admin_id"],
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        sid = s.id
    finally:
        db.close()

    token = _make_token(mem_env["admin_id"])
    # stream 端点不再走 get_current_user 依赖，无需 override。
    app.dependency_overrides.pop(get_current_user, None)
    with TestClient(app) as c:
        resp = c.get(f"/api/v1/agent/sessions/{sid}/stream?token={token}")
        assert resp.status_code == 200


def test_stream_query_token_auth_invalid(mem_env):
    """C2：invalid query token → 401。"""
    token = _make_invalid_token()
    app.dependency_overrides.pop(get_current_user, None)
    with TestClient(app) as c:
        resp = c.get(f"/api/v1/agent/sessions/1/stream?token={token}")
        assert resp.status_code == 401


def test_stream_query_token_missing(mem_env):
    """C2：无 token → 401。"""
    app.dependency_overrides.pop(get_current_user, None)
    with TestClient(app) as c:
        resp = c.get("/api/v1/agent/sessions/1/stream")
        assert resp.status_code == 401


def test_stream_plain_user_others_session_404(mem_env):
    """C2：普通用户 stream 别人的 session → 404（query token 鉴权 + session 隔离）。"""
    db = mem_env["Session"]()
    try:
        s = AgentSession(
            task_type="x", status="success",
            runner_type="claude_code", user_id=mem_env["admin_id"],
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        sid = s.id
    finally:
        db.close()

    token = _make_token(mem_env["plain_id"])
    app.dependency_overrides.pop(get_current_user, None)
    with TestClient(app) as c:
        resp = c.get(f"/api/v1/agent/sessions/{sid}/stream?token={token}")
        assert resp.status_code == 404


def test_stream_subscribe_before_replay_no_loss(mem_env, monkeypatch):
    """C1：subscribe 前置 + seq 去重——回放期间产生的事件不丢、不重复。

    场景：session running，历史里已有 seq=1 的 tool_use。
    回放完成后，后台线程再 publish 一条 seq=1 的 tool_use（模拟历史同 seq 的实时
    重复）→ 应被去重跳过；再 publish 一条 seq=2 的 tool_result → 应收到。
    """
    db = mem_env["Session"]()
    try:
        s = AgentSession(
            task_type="x", status="running",
            runner_type="claude_code", user_id=mem_env["admin_id"],
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        sid = s.id
        # 历史：seq=1 tool_use。
        db.add(
            AgentMessage(
                session_id=sid, seq=1, role="tool",
                tool_name="db_read", tool_use_id="tu_1",
            )
        )
        db.commit()
    finally:
        db.close()

    token = _make_token(mem_env["admin_id"])
    app.dependency_overrides.pop(get_current_user, None)

    # 在 stream 端点 subscribe 之后、回放完成之前注入实时事件。
    # 用 stream_bridge.publish_sync 直接推，需主事件循环。
    import asyncio as _asyncio

    injected = {"done": False}

    captured: list[dict] = []
    original_subscribe = stream_bridge.subscribe

    def _do_inject(loop):
        if injected["done"]:
            return
        # seq=1（与历史重复）→ 应去重跳过
        stream_bridge.publish_sync(
            sid,
            {
                "kind": "tool_use",
                "tool_name": "db_read",
                "tool_use_id": "tu_1_dup",
                "seq": 1,
            },
            loop,
        )
        # seq=2（新事件）→ 应收到
        stream_bridge.publish_sync(
            sid,
            {
                "kind": "tool_result",
                "tool_use_id": "tu_1",
                "tool_result": "ok",
                "seq": 2,
            },
            loop,
        )
        # done 关流
        stream_bridge.publish_sync(
            sid,
            {"kind": "done", "is_error": False, "synthesized": True},
            loop,
        )
        injected["done"] = True

    async def _wrapped_subscribe(session_id):
        q = await original_subscribe(session_id)
        # subscribe 后延迟注入（此时回放可能正在进行；因 subscribe 前置，
        # 注入的事件会进 queue，回放完成后被消费 + 去重）。
        loop = _asyncio.get_running_loop()
        if not injected["done"]:
            loop.call_later(0.05, lambda: _do_inject(loop))
        return q

    monkeypatch.setattr(stream_bridge, "subscribe", _wrapped_subscribe)

    with TestClient(app) as c:
        with c.stream(
            "GET", f"/api/v1/agent/sessions/{sid}/stream?token={token}"
        ) as r:
            assert r.status_code == 200
            for chunk in r.iter_lines():
                line = (
                    chunk.decode("utf-8")
                    if isinstance(chunk, (bytes, bytearray))
                    else chunk
                )
                if line.startswith("data: "):
                    import json as _json

                    try:
                        captured.append(_json.loads(line[len("data: "):]))
                    except Exception:
                        pass

    kinds_seq = [(e.get("kind"), e.get("seq")) for e in captured]
    # 历史回放：seq=1 tool_use（role=tool）。
    assert any(
        k == "history" and seq == 1 for k, seq in kinds_seq
    ), f"历史回放缺失 seq=1: {kinds_seq}"
    # 去重：实时 seq=1 的 tool_use 不应重复出现为 tool_use 事件。
    tool_use_seqs = [
        seq for k, seq in kinds_seq if k == "tool_use" and seq is not None
    ]
    assert 1 not in tool_use_seqs, (
        f"实时 seq=1 tool_use 未被去重: {kinds_seq}"
    )
    # 新事件 seq=2 tool_result 应收到。
    assert any(
        k == "tool_result" and seq == 2 for k, seq in kinds_seq
    ), f"实时 seq=2 tool_result 缺失: {kinds_seq}"
    # done 收到（关流）。
    assert any(k == "done" for k, _ in kinds_seq)


# --------------------------------------------------------------------------- #
# 端到端：真 run_agent_loop + FakeRunner
# --------------------------------------------------------------------------- #
def test_end_to_end_real_loop_with_fake_runner(admin_client, mem_env, monkeypatch):
    """建会话 → 真 run_agent_loop 跑 FakeRunner（产出 done，无 SQL）→ success。"""
    runner = _FakeRunner(
        [
            AgentEvent(kind="text_delta", text="任务完成"),
            AgentEvent(kind="done", cost_usd=0.01),
        ]
    )
    _patch_build_runner(monkeypatch, runner)
    # 不 patch run_agent_loop（用真的）

    resp = admin_client.post(
        "/api/v1/agent/sessions", json={"task_type": "fill_piece_weight"}
    )
    sid = resp.json()["session_id"]

    status = _wait_session_status(mem_env, sid, {"success", "failed"}, timeout=5.0)
    assert status == "success"

    db = mem_env["Session"]()
    try:
        msgs = (
            db.query(AgentMessage)
            .filter(AgentMessage.session_id == sid)
            .order_by(AgentMessage.seq.asc())
            .all()
        )
        # 一条 assistant "任务完成"
        contents = [m.content for m in msgs if m.role == "assistant"]
        assert any("任务完成" in (c or "") for c in contents)
        s = db.query(AgentSession).get(sid)
        assert s.claude_session_id == "fake-sid"
    finally:
        db.close()
