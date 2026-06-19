"""session_runner 单测：AgentEvent 流 -> AgentMessage 落库 + stream_bridge 推送。"""
from __future__ import annotations

import asyncio
from typing import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.agent_message import AgentMessage
from app.models.agent_session import AgentSession
from app.services.agent import session_runner, stream_bridge
from app.services.agent.runner import AgentEvent


# --------------------------------------------------------------------------- #
# 测试用假 Runner：按预设序列产出 AgentEvent。
# --------------------------------------------------------------------------- #
class FakeRunner:
    """假 AgentRunner，按 events 列表逐条 yield，last_session_id 可设。"""

    def __init__(self, events: list[AgentEvent], last_sid: str | None = "fake-sid-xyz"):
        self._events = list(events)
        self._last_sid = last_sid

    @property
    def last_session_id(self) -> "str | None":
        return self._last_sid

    def run(
        self, prompt: str, *, resume_session_id: "str | None" = None
    ) -> Iterator[AgentEvent]:
        for ev in self._events:
            yield ev


# --------------------------------------------------------------------------- #
# 内存库 fixture（替换 app.core.database.SessionLocal）
# --------------------------------------------------------------------------- #
@pytest.fixture()
def mem_db(monkeypatch):
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    TestSession = sessionmaker(bind=eng, autoflush=False, autocommit=False)

    # session_runner 内部 `from app.core.database import SessionLocal`，
    # 替换该模块属性即可。
    import app.core.database as dbmod

    monkeypatch.setattr(dbmod, "SessionLocal", TestSession)
    yield TestSession
    eng.dispose()


@pytest.fixture(autouse=True)
def _clear_subscribers():
    with stream_bridge._lock:
        stream_bridge._subscribers.clear()
    yield
    with stream_bridge._lock:
        stream_bridge._subscribers.clear()


def _make_session(TestSession, **kw) -> int:
    db = TestSession()
    try:
        s = AgentSession(status="pending", **kw)
        db.add(s)
        db.commit()
        db.refresh(s)
        return s.id
    finally:
        db.close()


def _messages(TestSession, sid: int) -> list[AgentMessage]:
    db = TestSession()
    try:
        return (
            db.query(AgentMessage)
            .filter(AgentMessage.session_id == sid)
            .order_by(AgentMessage.seq.asc())
            .all()
        )
    finally:
        db.close()


def _session(TestSession, sid: int) -> AgentSession:
    db = TestSession()
    try:
        return db.query(AgentSession).get(sid)
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# 测试
# --------------------------------------------------------------------------- #
def test_text_delta_aggregated_and_tool_events_persisted(mem_db):
    sid = _make_session(mem_db)
    events = [
        AgentEvent(kind="text_delta", text="Hello "),
        AgentEvent(kind="text_delta", text="world"),
        AgentEvent(
            kind="tool_use",
            tool_name="mcp__fake_db__db_read",
            tool_input={"sql": "SELECT 1"},
            tool_use_id="tu_1",
        ),
        AgentEvent(
            kind="tool_result",
            tool_use_id="tu_1",
            tool_result="| col |\n|----|\n| 1 |",
        ),
        AgentEvent(kind="done", cost_usd=0.0123),
    ]
    runner = FakeRunner(events)
    loop = asyncio.new_event_loop()

    last_sid = session_runner.run_session(sid, runner, "test prompt", loop)

    msgs = _messages(mem_db, sid)
    sess = _session(mem_db, sid)

    # last_session_id 记录。
    assert last_sid == "fake-sid-xyz"
    assert sess.claude_session_id == "fake-sid-xyz"
    assert sess.status == "success"

    # 消息结构：
    #   seq1: assistant "Hello world"   (两条 text_delta 聚合)
    #   seq2: tool tool_use
    #   seq3: tool tool_result
    assert len(msgs) == 3
    assert msgs[0].role == "assistant"
    assert msgs[0].content == "Hello world"
    assert msgs[0].seq == 1

    assert msgs[1].role == "tool"
    assert msgs[1].tool_name == "mcp__fake_db__db_read"
    assert msgs[1].tool_input == {"sql": "SELECT 1"}
    assert msgs[1].tool_use_id == "tu_1"
    assert msgs[1].seq == 2

    assert msgs[2].role == "tool"
    assert msgs[2].tool_result is not None
    # C-11/C-12: tool_result 统一写入规整后的值（字符串），不再包
    # {"value":..., "is_error":...} 也不再有 dict/str 分叉。
    assert msgs[2].tool_result == "| col |\n|----|\n| 1 |"
    assert msgs[2].tool_use_id == "tu_1"
    assert msgs[2].seq == 3

    # seq 单调递增。
    seqs = [m.seq for m in msgs]
    assert seqs == sorted(seqs)
    assert len(set(seqs)) == len(seqs)


def test_text_delta_flushed_on_done_without_tool(mem_db):
    """纯文本（无 tool_use）时，done 触发 flush。"""
    sid = _make_session(mem_db)
    events = [
        AgentEvent(kind="text_delta", text="abc"),
        AgentEvent(kind="text_delta", text="def"),
        AgentEvent(kind="done"),
    ]
    runner = FakeRunner(events)
    loop = asyncio.new_event_loop()
    session_runner.run_session(sid, runner, "p", loop)

    msgs = _messages(mem_db, sid)
    assert len(msgs) == 1
    assert msgs[0].content == "abcdef"
    assert _session(mem_db, sid).status == "success"


def test_stream_bridge_receives_events(mem_db):
    sid = _make_session(mem_db)
    events = [
        AgentEvent(kind="text_delta", text="x"),
        AgentEvent(kind="tool_use", tool_name="T", tool_use_id="t1"),
        AgentEvent(kind="done"),
    ]
    runner = FakeRunner(events)
    loop = asyncio.new_event_loop()

    async def scenario():
        q = await stream_bridge.subscribe(sid)
        # 在同一线程同步跑 run_session（run_session 不进 loop），但用此 loop
        # 做 call_soon_threadsafe。run_session 是同步函数，这里直接调。
        session_runner.run_session(sid, runner, "p", loop)
        # 让 call_soon_threadsafe 回调执行。
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        items = []
        while not q.empty():
            items.append(q.get_nowait())
        return items

    items = loop.run_until_complete(scenario())
    kinds = [e["kind"] for e in items]
    assert "text_delta" in kinds
    assert "tool_use" in kinds
    assert "done" in kinds


def test_error_path_marks_failed_and_persists_error_message(mem_db):
    sid = _make_session(mem_db)
    events = [
        AgentEvent(kind="text_delta", text="partial "),
        AgentEvent(kind="error", error="boom", is_error=True),
    ]
    runner = FakeRunner(events, last_sid="err-sid")
    loop = asyncio.new_event_loop()
    session_runner.run_session(sid, runner, "p", loop)

    sess = _session(mem_db, sid)
    assert sess.status == "failed"

    msgs = _messages(mem_db, sid)
    # seq1: assistant "partial "（flush）
    # seq2: assistant error content "boom"
    assert len(msgs) == 2
    assert msgs[0].content == "partial "
    assert msgs[1].role == "assistant"
    assert msgs[1].content == "boom"


def test_on_event_callback_invoked(mem_db):
    sid = _make_session(mem_db)
    events = [
        AgentEvent(kind="text_delta", text="a"),
        AgentEvent(kind="done"),
    ]
    seen: list[str] = []
    runner = FakeRunner(events)
    loop = asyncio.new_event_loop()
    session_runner.run_session(
        sid, runner, "p", loop, on_event=lambda ev: seen.append(ev.kind)
    )
    assert seen == ["text_delta", "done"]


def test_resume_session_id_forwarded(mem_db):
    sid = _make_session(mem_db)
    captured: dict = {}

    class ProbeRunner:
        @property
        def last_session_id(self):
            return "new-sid"

        def run(self, prompt, *, resume_session_id=None):
            captured["prompt"] = prompt
            captured["resume"] = resume_session_id
            yield AgentEvent(kind="done")

    loop = asyncio.new_event_loop()
    session_runner.run_session(
        sid, ProbeRunner(), "the prompt", loop, resume_session_id="resume-123"
    )
    assert captured["prompt"] == "the prompt"
    assert captured["resume"] == "resume-123"


def test_exception_in_runner_marks_failed(mem_db):
    sid = _make_session(mem_db)

    class BoomRunner:
        @property
        def last_session_id(self):
            return None

        def run(self, prompt, *, resume_session_id=None):
            yield AgentEvent(kind="text_delta", text="x")
            raise RuntimeError("kaboom")

    loop = asyncio.new_event_loop()
    session_runner.run_session(sid, BoomRunner(), "p", loop)

    sess = _session(mem_db, sid)
    assert sess.status == "failed"
    assert "kaboom" in (sess.error or "")


def test_done_is_error_marks_failed(mem_db):
    """C-15: done.is_error=True（预算超限等 CLI 终态错误）必须置 failed。"""
    sid = _make_session(mem_db)
    events = [
        AgentEvent(kind="text_delta", text="partial"),
        AgentEvent(
            kind="done",
            is_error=True,
            error="预算超限",
            cost_usd=0.5,
        ),
    ]
    runner = FakeRunner(events, last_sid="err-done-sid")
    loop = asyncio.new_event_loop()
    session_runner.run_session(sid, runner, "p", loop)

    sess = _session(mem_db, sid)
    assert sess.status == "failed"
    assert "预算超限" in (sess.error or "")
    # cost_usd 仍应写入（C-9/C-13）。
    assert sess.cost_usd is not None
    assert float(sess.cost_usd) == 0.5


def test_done_normal_marks_success_and_writes_cost(mem_db):
    """C-9/C-13: 正常 done 写 success + cost_usd 落库。"""
    sid = _make_session(mem_db)
    events = [
        AgentEvent(kind="text_delta", text="ok"),
        AgentEvent(kind="done", cost_usd=0.0123),
    ]
    runner = FakeRunner(events)
    loop = asyncio.new_event_loop()
    session_runner.run_session(sid, runner, "p", loop)

    sess = _session(mem_db, sid)
    assert sess.status == "success"
    assert sess.cost_usd is not None
    assert float(sess.cost_usd) == 0.0123


def test_tool_result_unified_write_str_and_dict(mem_db):
    """C-11/C-12: tool_result 统一写入规整后的值——字符串/对象都直接存，
    不再包 ``{"value":..., "is_error":...}``，不再 dict/str 分叉。"""
    sid = _make_session(mem_db)
    events = [
        AgentEvent(
            kind="tool_use",
            tool_name="T1",
            tool_use_id="tu_a",
            tool_input={"x": 1},
        ),
        AgentEvent(
            kind="tool_result",
            tool_use_id="tu_a",
            tool_result="字符串结果",
        ),
        AgentEvent(
            kind="tool_use",
            tool_name="T2",
            tool_use_id="tu_b",
            tool_input={"y": 2},
        ),
        AgentEvent(
            kind="tool_result",
            tool_use_id="tu_b",
            tool_result={"already": "dict"},
        ),
        AgentEvent(kind="done"),
    ]
    runner = FakeRunner(events)
    loop = asyncio.new_event_loop()
    session_runner.run_session(sid, runner, "p", loop)

    msgs = _messages(mem_db, sid)
    # seq1: tool_use T1；seq2: tool_result 字符串；seq3: tool_use T2；seq4: tool_result dict
    assert len(msgs) == 4
    assert msgs[0].tool_use_id == "tu_a"
    assert msgs[0].tool_name == "T1"
    assert msgs[1].tool_use_id == "tu_a"
    assert msgs[1].tool_result == "字符串结果"
    assert msgs[2].tool_use_id == "tu_b"
    assert msgs[2].tool_name == "T2"
    assert msgs[3].tool_use_id == "tu_b"
    assert msgs[3].tool_result == {"already": "dict"}


def test_tool_use_id_pairing(mem_db):
    """D: tool_use 与 tool_result 的 AgentMessage 都有正确的 tool_use_id。"""
    sid = _make_session(mem_db)
    events = [
        AgentEvent(kind="tool_use", tool_name="A", tool_use_id="tu_1", tool_input={}),
        AgentEvent(kind="tool_use", tool_name="B", tool_use_id="tu_2", tool_input={}),
        AgentEvent(kind="tool_result", tool_use_id="tu_2", tool_result="r2"),
        AgentEvent(kind="tool_result", tool_use_id="tu_1", tool_result="r1"),
        AgentEvent(kind="done"),
    ]
    runner = FakeRunner(events)
    loop = asyncio.new_event_loop()
    session_runner.run_session(sid, runner, "p", loop)

    msgs = _messages(mem_db, sid)
    # 按 tool_use_id 配对（不依赖 seq 顺序）。
    by_id: dict[str, list[AgentMessage]] = {}
    for m in msgs:
        if m.tool_use_id:
            by_id.setdefault(m.tool_use_id, []).append(m)
    assert len(by_id["tu_1"]) == 2
    assert len(by_id["tu_2"]) == 2
    # 每个 id 下恰好一个 tool_use（有 tool_name）和一个 tool_result。
    for tid in ("tu_1", "tu_2"):
        names = [m.tool_name for m in by_id[tid] if m.tool_name]
        results = [m.tool_result for m in by_id[tid] if m.tool_result is not None]
        assert len(names) == 1
        assert len(results) == 1
    r1 = next(m.tool_result for m in by_id["tu_1"] if m.tool_result is not None)
    r2 = next(m.tool_result for m in by_id["tu_2"] if m.tool_result is not None)
    assert r1 == "r1"
    assert r2 == "r2"
