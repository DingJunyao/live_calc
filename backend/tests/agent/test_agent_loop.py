"""Task 4b：run_agent_loop 多轮编排 + 写操作提取/执行/审批 + 回流的单测。

用 FakeMultiTurnRunner（按 run 调用次数返回不同事件序列）+ 内存 SQLite +
独立 create_engine 建临时表（验证 SQL 真执行）。
"""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.agent_approval import AgentApproval
from app.models.agent_message import AgentMessage
from app.models.agent_session import AgentSession
from app.services.agent import session_runner
from app.services.agent.runner import AgentEvent


# --------------------------------------------------------------------------- #
# FakeMultiTurnRunner：按 run 调用次数返回不同事件序列。
# --------------------------------------------------------------------------- #
class FakeMultiTurnRunner:
    """假 AgentRunner：每次 run() 按调用序号返回对应轮的事件列表。

    tracks["prompts"] / tracks["resumes"] 记录每次调用入参，便于断言回流 prompt
    与 resume_session_id。
    """

    def __init__(
        self,
        turns: "list[list[AgentEvent]]",
        last_sids: "list[str | None] | None" = None,
    ):
        self._turns = list(turns)
        n = len(self._turns)
        self._last_sids = (
            list(last_sids) if last_sids else [f"sid-{i+1}" for i in range(n)]
        )
        self._call_count = 0
        self.tracks: dict = {"prompts": [], "resumes": []}

    @property
    def last_session_id(self) -> "str | None":
        # 返回最近一次 run 的 last_sid。
        idx = min(self._call_count, len(self._last_sids)) - 1
        if idx < 0:
            return None
        return self._last_sids[idx]

    def run(
        self, prompt: str, *, resume_session_id: "str | None" = None
    ) -> "Iterator[AgentEvent]":
        self._call_count += 1
        self.tracks["prompts"].append(prompt)
        self.tracks["resumes"].append(resume_session_id)
        idx = self._call_count - 1
        if idx >= len(self._turns):
            # 超出预设轮数：返回 done（兜底，防无限）。
            yield AgentEvent(kind="done")
            return
        for ev in self._turns[idx]:
            yield ev


# --------------------------------------------------------------------------- #
# 内存库 fixture（含一个临时表 t，用于验证 SQL 真执行）。
# 用 monkeypatch 替换 app.core.database.SessionLocal，让 session_runner 与
# 测试断言共享同一内存库。
# --------------------------------------------------------------------------- #
@pytest.fixture()
def mem_db(monkeypatch):
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    # 额外建一张临时表 t（非 ORM 托管），验证 UPDATE/DELETE 真执行。
    with eng.connect() as conn:
        conn.execute(text("CREATE TABLE t (id INTEGER PRIMARY KEY, x INTEGER)"))
        conn.execute(text("INSERT INTO t (id, x) VALUES (1, 100), (2, 200), (3, 300)"))
        conn.commit()
    TestSession = sessionmaker(bind=eng, autoflush=False, autocommit=False)

    import app.core.database as dbmod

    monkeypatch.setattr(dbmod, "SessionLocal", TestSession)
    yield TestSession
    eng.dispose()


@pytest.fixture(autouse=True)
def _reset_pending_approvals():
    # 每个 test 前/后清理 _pending_approvals，防测试间污染。
    with session_runner._pending_lock:
        session_runner._pending_approvals.clear()
    yield
    with session_runner._pending_lock:
        session_runner._pending_approvals.clear()


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


def _session(TestSession, sid: int) -> AgentSession:
    db = TestSession()
    try:
        return db.query(AgentSession).get(sid)
    finally:
        db.close()


def _approvals(TestSession, sid: int) -> "list[AgentApproval]":
    db = TestSession()
    try:
        return (
            db.query(AgentApproval)
            .filter(AgentApproval.session_id == sid)
            .order_by(AgentApproval.id.asc())
            .all()
        )
    finally:
        db.close()


def _rows(TestSession):
    db = TestSession()
    try:
        rows = db.execute(text("SELECT id, x FROM t ORDER BY id")).fetchall()
        return {r[0]: r[1] for r in rows}
    finally:
        db.close()


def _new_loop():
    return asyncio.new_event_loop()


# --------------------------------------------------------------------------- #
# 测试
# --------------------------------------------------------------------------- #
def test_safe_sql_auto_executed_and_loop_completes(mem_db):
    """第 1 轮：assistant 文本含 safe UPDATE；第 2 轮：说「完成」无 SQL。

    断言：跑 2 轮；UPDATE 真执行（表数据变化）；AgentApproval(auto_executed)；
    session.success；回流 prompt 含执行结果。
    """
    sid = _make_session(mem_db)
    turn1 = [
        AgentEvent(
            kind="text_delta",
            text="我来更新一行：\n```sql\nUPDATE t SET x=999 WHERE id=1 AND x=100\n```\n",
        ),
        AgentEvent(kind="done", cost_usd=0.01),
    ]
    turn2 = [
        AgentEvent(kind="text_delta", text="已完成。"),
        AgentEvent(kind="done", cost_usd=0.005),
    ]
    runner = FakeMultiTurnRunner([turn1, turn2])
    loop = _new_loop()

    session_runner.run_agent_loop(sid, runner, "请更新", loop)

    # 跑了 2 轮。
    assert runner._call_count == 2
    # 第 2 轮是 resume 第 1 轮的 sid。
    assert runner.tracks["resumes"][0] is None
    assert runner.tracks["resumes"][1] == "sid-1"
    # 回流 prompt 含执行结果。
    assert "影响" in runner.tracks["prompts"][1]
    assert (
        "999" in runner.tracks["prompts"][1] or "UPDATE" in runner.tracks["prompts"][1]
    )

    # UPDATE 真执行。
    assert _rows(mem_db)[1] == 999

    # AgentApproval(auto_executed)。
    aps = _approvals(mem_db, sid)
    assert len(aps) == 1
    assert aps[0].status == "auto_executed"
    assert aps[0].affected_estimate == 1
    assert "UPDATE" in aps[0].sql

    # session.success。
    s = _session(mem_db, sid)
    assert s.status == "success"
    # cost 累加：0.01 + 0.005。
    assert s.cost_usd is not None
    assert abs(float(s.cost_usd) - 0.015) < 1e-6


def test_dangerous_sql_approved_executed(mem_db):
    """第 1 轮：dangerous DELETE → agent_loop 写 pending + 阻塞。
    测试线程调 wake_approval(approved=True) → loop 继续。
    第 2 轮：无 SQL 完成。

    断言：DELETE 真执行；AgentApproval.status=approved；session.success。
    """
    sid = _make_session(mem_db)
    turn1 = [
        AgentEvent(kind="text_delta", text="删除全部：\n```sql\nDELETE FROM t\n```\n"),
        AgentEvent(kind="done"),
    ]
    turn2 = [
        AgentEvent(kind="text_delta", text="完成。"),
        AgentEvent(kind="done"),
    ]
    runner = FakeMultiTurnRunner([turn1, turn2])
    loop = _new_loop()

    # 后台线程跑 loop。
    t = threading.Thread(
        target=session_runner.run_agent_loop,
        args=(sid, runner, "请删除", loop),
        daemon=True,
    )
    t.start()

    # 轮询等 AgentApproval(pending) 出现。
    approval_id = None
    deadline = time.time() + 10
    while time.time() < deadline:
        aps = _approvals(mem_db, sid)
        if aps:
            approval_id = aps[0].id
            break
        time.sleep(0.02)
    assert approval_id is not None, "timeout waiting for pending approval"

    # 调 wake_approval 批准。
    ok = session_runner.wake_approval(approval_id, approved=True, user_id=42)
    assert ok is True

    t.join(timeout=10)
    assert not t.is_alive(), "agent_loop 线程未退出"

    # DELETE 真执行（表空）。
    assert _rows(mem_db) == {}

    aps = _approvals(mem_db, sid)
    assert len(aps) == 1
    assert aps[0].status == "approved"
    assert aps[0].decided_by == 42
    assert aps[0].decided_at is not None
    assert aps[0].affected_estimate == 3

    assert _session(mem_db, sid).status == "success"


def test_dangerous_sql_rejected_not_executed(mem_db):
    """dangerous SQL 被拒：不执行；回流 prompt 含「已拒绝」；继续 loop 到完成。"""
    sid = _make_session(mem_db)
    turn1 = [
        AgentEvent(kind="text_delta", text="删除：\n```sql\nDELETE FROM t\n```\n"),
        AgentEvent(kind="done"),
    ]
    turn2 = [
        AgentEvent(kind="text_delta", text="好的，已完成。"),
        AgentEvent(kind="done"),
    ]
    runner = FakeMultiTurnRunner([turn1, turn2])
    loop = _new_loop()

    t = threading.Thread(
        target=session_runner.run_agent_loop,
        args=(sid, runner, "请删除", loop),
        daemon=True,
    )
    t.start()

    approval_id = None
    deadline = time.time() + 10
    while time.time() < deadline:
        aps = _approvals(mem_db, sid)
        if aps:
            approval_id = aps[0].id
            break
        time.sleep(0.02)
    assert approval_id is not None

    ok = session_runner.wake_approval(approval_id, approved=False, user_id=7)
    assert ok is True

    t.join(timeout=10)
    assert not t.is_alive()

    # 未执行：表数据保留。
    rows = _rows(mem_db)
    assert rows == {1: 100, 2: 200, 3: 300}

    aps = _approvals(mem_db, sid)
    assert aps[0].status == "rejected"
    assert aps[0].decided_by == 7

    # 回流 prompt 含「拒绝」。
    assert "拒绝" in runner.tracks["prompts"][1]

    assert _session(mem_db, sid).status == "success"


def test_max_turns_terminates(mem_db):
    """每轮都输出 SQL（永远不完成）→ max_turns 后终止，session 不卡死。"""
    sid = _make_session(mem_db)
    # 4 轮都含 safe UPDATE（无完成轮）。
    one_turn = [
        AgentEvent(
            kind="text_delta", text="```sql\nUPDATE t SET x=1 WHERE id=1\n```\n"
        ),
        AgentEvent(kind="done"),
    ]
    runner = FakeMultiTurnRunner([one_turn, one_turn, one_turn, one_turn])
    loop = _new_loop()

    session_runner.run_agent_loop(sid, runner, "请反复更新", loop, max_turns=3)

    assert runner._call_count == 3
    s = _session(mem_db, sid)
    # 达 max_turns：置 success + 附说明。
    assert s.status == "success"
    assert "max_turns" in (s.error or "")


def test_error_terminates_loop(mem_db):
    """某轮 Runner 产 error → session.failed，循环终止。"""
    sid = _make_session(mem_db)
    turn1 = [
        AgentEvent(
            kind="text_delta",
            text="我先试试：\n```sql\nUPDATE t SET x=1 WHERE id=1\n```\n",
        ),
        AgentEvent(kind="error", error="CLI 崩溃", is_error=True),
    ]
    runner = FakeMultiTurnRunner([turn1])
    loop = _new_loop()

    session_runner.run_agent_loop(sid, runner, "请更新", loop)

    assert runner._call_count == 1
    s = _session(mem_db, sid)
    assert s.status == "failed"
    # safe SQL 在 error 前已被处理（_consume_events 消费完所有事件才返回，但 SQL
    # 处理在 _consume_events 返回后；error 终态时直接终止，SQL 不处理）。
    # 因此 UPDATE 不应执行。
    assert _rows(mem_db)[1] == 100
    assert _approvals(mem_db, sid) == []


def test_wake_approval_returns_false_for_unknown(mem_db):
    """wake_approval 对不存在/已决策的 approval 返回 False。"""
    sid = _make_session(mem_db)
    # 不存在的 id。
    assert session_runner.wake_approval(99999, approved=True, user_id=1) is False

    # 已决策的 approval。
    db = mem_db()
    try:
        ap = AgentApproval(session_id=sid, sql="DELETE FROM t", status="approved")
        db.add(ap)
        db.commit()
        db.refresh(ap)
        ap_id = ap.id
    finally:
        db.close()

    assert session_runner.wake_approval(ap_id, approved=False, user_id=1) is False


def test_resume_prompt_contains_all_items(mem_db):
    """多 SQL 同轮：回流 prompt 含每条结果摘要。"""
    sid = _make_session(mem_db)
    turn1 = [
        AgentEvent(
            kind="text_delta",
            text=(
                "我更新两行：\n"
                "```sql\nUPDATE t SET x=10 WHERE id=1\n```\n"
                "再更新：\n"
                "```sql\nUPDATE t SET x=20 WHERE id=2\n```\n"
            ),
        ),
        AgentEvent(kind="done"),
    ]
    turn2 = [AgentEvent(kind="text_delta", text="完成"), AgentEvent(kind="done")]
    runner = FakeMultiTurnRunner([turn1, turn2])
    loop = _new_loop()

    session_runner.run_agent_loop(sid, runner, "请更新", loop)

    resume_prompt = runner.tracks["prompts"][1]
    # 含两条摘要。
    assert resume_prompt.count("影响") == 2
    aps = _approvals(mem_db, sid)
    assert len(aps) == 2
    assert all(a.status == "auto_executed" for a in aps)
    assert _rows(mem_db) == {1: 10, 2: 20, 3: 300}


# --------------------------------------------------------------------------- #
# C10：审批竞态死锁回归测试
# --------------------------------------------------------------------------- #
def _patch_sse_recorder(monkeypatch):
    """patch session_runner._emit_sse，记录所有推送的 payload 到 list。"""
    events: "list[dict]" = []

    def _fake(session_id, main_loop, payload):
        events.append(dict(payload))

    monkeypatch.setattr(session_runner, "_emit_sse", _fake)
    return events


def test_c10_event_registered_before_sse(mem_db, monkeypatch):
    """C10：Event 入 _pending_approvals 必须在 SSE approval_needed 推送之前。

    通过在 _emit_sse 内部断言 dict 已含 approval_id 来验证时序。
    """
    sse_events = _patch_sse_recorder(monkeypatch)

    # 包装 _emit_sse 的 fake，在 approval_needed 推送时验证 dict 已含 approval_id。
    checked: "list[int]" = []
    real_fake = session_runner._emit_sse  # 上面 patch 的 _fake（已被绑定）

    def _fake_with_check(session_id, main_loop, payload):
        if payload.get("kind") == "approval_needed":
            aid = payload.get("approval_id")
            with session_runner._pending_lock:
                has = aid in session_runner._pending_approvals
            if has:
                checked.append(aid)
        real_fake(session_id, main_loop, payload)

    monkeypatch.setattr(session_runner, "_emit_sse", _fake_with_check)

    sid = _make_session(mem_db)
    turn1 = [
        AgentEvent(kind="text_delta", text="删除：\n```sql\nDELETE FROM t\n```\n"),
        AgentEvent(kind="done"),
    ]
    turn2 = [AgentEvent(kind="text_delta", text="完成"), AgentEvent(kind="done")]
    runner = FakeMultiTurnRunner([turn1, turn2])
    loop = _new_loop()

    t = threading.Thread(
        target=session_runner.run_agent_loop,
        args=(sid, runner, "请删除", loop),
        daemon=True,
    )
    t.start()

    approval_id = None
    deadline = time.time() + 10
    while time.time() < deadline:
        aps = _approvals(mem_db, sid)
        if aps:
            approval_id = aps[0].id
            break
        time.sleep(0.02)
    assert approval_id is not None

    ok = session_runner.wake_approval(approval_id, approved=True, user_id=1)
    assert ok is True
    t.join(timeout=10)
    assert not t.is_alive(), "agent_loop 死锁未退出（C10 回归）"

    # 时序断言：approval_needed 推送时 dict 已含 approval_id。
    assert approval_id in checked, "Event 未在 SSE 推送前注册入 _pending_approvals"
    # approval_needed 确实被推送了。
    assert any(e.get("kind") == "approval_needed" for e in sse_events)


def test_c10_wake_in_race_window_no_deadlock(mem_db, monkeypatch):
    """C10 极端竞态：在 Event 注册完成、SSE 推送前的窗口内提前调 wake_approval。

    用 pre_sse_hook（注册后、SSE 前）立即 wake → 断言 loop 不死锁，能正常唤醒。
    """
    _patch_sse_recorder(monkeypatch)

    sid = _make_session(mem_db)
    turn1 = [
        AgentEvent(kind="text_delta", text="删除：\n```sql\nDELETE FROM t\n```\n"),
        AgentEvent(kind="done"),
    ]
    turn2 = [AgentEvent(kind="text_delta", text="完成"), AgentEvent(kind="done")]
    runner = FakeMultiTurnRunner([turn1, turn2])
    loop = _new_loop()

    # 通过 monkeypatch 把 pre_sse_hook 注入 _handle_dangerous_sql。
    real_handler = session_runner._handle_dangerous_sql

    def _hooked_handle(*args, **kwargs):
        # 在 SSE 前调 wake_approval：此时 AgentApproval 已 commit 为 pending，
        # Event 已注册（_handle_dangerous_sql 内部在调 pre_sse_hook 后才推 SSE）。
        fired: "list[bool]" = []

        def hook(approval_id):
            ok = session_runner.wake_approval(approval_id, approved=True, user_id=99)
            fired.append(ok)

        kwargs["pre_sse_hook"] = hook
        result = real_handler(*args, **kwargs)
        # hook 应已触发并返回 True（找到 pending + 写决策 + set Event）。
        assert fired == [True], "pre_sse_hook 中的 wake_approval 应成功"
        return result

    monkeypatch.setattr(session_runner, "_handle_dangerous_sql", _hooked_handle)

    t = threading.Thread(
        target=session_runner.run_agent_loop,
        args=(sid, runner, "请删除", loop),
        daemon=True,
    )
    t.start()
    t.join(timeout=10)
    assert not t.is_alive(), "C10：SSE 前 wake 导致死锁"

    # DELETE 真执行（wake 成功唤醒并 approved）。
    assert _rows(mem_db) == {}
    aps = _approvals(mem_db, sid)
    assert len(aps) == 1
    assert aps[0].status == "approved"
    assert aps[0].decided_by == 99
    assert _session(mem_db, sid).status == "success"


# --------------------------------------------------------------------------- #
# C12：审批超时语义回归测试
# --------------------------------------------------------------------------- #
def test_c12_approval_timeout_marks_failed(mem_db, monkeypatch):
    """C12：审批超时（不 wake）→ session.failed + SSE sql_timeout + SQL 未执行 +
    loop 不进下一轮重试。"""
    sse_events = _patch_sse_recorder(monkeypatch)

    sid = _make_session(mem_db)
    turn1 = [
        AgentEvent(kind="text_delta", text="删除：\n```sql\nDELETE FROM t\n```\n"),
        AgentEvent(kind="done"),
    ]
    # 故意只给 1 轮（超时后 loop 应 failed 终止，不该进第 2 轮）。
    runner = FakeMultiTurnRunner([turn1])
    loop = _new_loop()

    t = threading.Thread(
        target=session_runner.run_agent_loop,
        args=(sid, runner, "请删除", loop),
        kwargs={"approval_timeout": 0.3},
        daemon=True,
    )
    t.start()
    t.join(timeout=10)
    assert not t.is_alive(), "超时分支未退出"

    # session.failed。
    s = _session(mem_db, sid)
    assert s.status == "failed"
    assert "超时" in (s.error or "")

    # SSE 推了 sql_timeout（而非 sql_rejected）。
    kinds = [e.get("kind") for e in sse_events]
    assert "sql_timeout" in kinds
    assert "sql_rejected" not in kinds

    # SQL 未执行：表数据保留。
    assert _rows(mem_db) == {1: 100, 2: 200, 3: 300}

    # loop 未进下一轮重试同条 SQL（只跑了 1 轮）。
    assert runner._call_count == 1

    # AgentApproval 仍为 pending（未被 wake 改写）。
    aps = _approvals(mem_db, sid)
    assert len(aps) == 1
    assert aps[0].status == "pending"


# --------------------------------------------------------------------------- #
# D15：safe SQL rowcount 阈值护栏回归测试
# --------------------------------------------------------------------------- #
def test_d15_safe_sql_exceeds_threshold_rolls_back_and_escalates(mem_db, monkeypatch):
    """D15：safe UPDATE（带 WHERE 但恒真条件，静态判 safe）影响行数 > 阈值 →
    回滚该 SQL + 转 dangerous 审批（pending）。"""
    _patch_sse_recorder(monkeypatch)

    # 先把 t 表扩到 200 行（id 4..203），让 UPDATE ... WHERE id>0 影响超过阈值。
    # 加上原始 3 行，共 203 行。
    db = mem_db()
    try:
        for i in range(4, 204):
            db.execute(text(f"INSERT INTO t (id, x) VALUES ({i}, {i * 10})"))
        db.commit()
    finally:
        db.close()
    total_rows = 203

    sid = _make_session(mem_db)
    # UPDATE t SET x=0 WHERE id>0：静态 safe（有 WHERE）+ 运行时影响 200 行。
    turn1 = [
        AgentEvent(
            kind="text_delta",
            text="批量更新：\n```sql\nUPDATE t SET x=0 WHERE id>0\n```\n",
        ),
        AgentEvent(kind="done"),
    ]
    turn2 = [AgentEvent(kind="text_delta", text="完成"), AgentEvent(kind="done")]
    runner = FakeMultiTurnRunner([turn1, turn2])
    loop = _new_loop()

    t = threading.Thread(
        target=session_runner.run_agent_loop,
        args=(sid, runner, "请更新", loop),
        kwargs={"safe_row_threshold": 100},
        daemon=True,
    )
    t.start()

    # 应出现 pending 审批（escalated）。
    approval_id = None
    deadline = time.time() + 10
    while time.time() < deadline:
        aps = _approvals(mem_db, sid)
        if aps and aps[0].status == "pending":
            approval_id = aps[0].id
            break
        time.sleep(0.02)
    assert approval_id is not None, "超阈值 SQL 未转 pending 审批"

    # 关键：回滚生效——表数据未被修改（仍为原值）。
    db = mem_db()
    try:
        changed = db.execute(text("SELECT COUNT(*) FROM t WHERE x=0")).scalar()
    finally:
        db.close()
    assert changed == 0, "超阈值 SQL 未被回滚（D15 失效）"

    # danger_reason 含「超阈值」。
    aps = _approvals(mem_db, sid)
    assert aps[0].danger_reason is not None
    assert "超阈值" in aps[0].danger_reason

    # 批准 → 真执行（这次走 approved 路径，应改 200 行）。
    ok = session_runner.wake_approval(approval_id, approved=True, user_id=5)
    assert ok is True
    t.join(timeout=10)
    assert not t.is_alive()

    aps = _approvals(mem_db, sid)
    assert aps[0].status == "approved"
    assert aps[0].affected_estimate == total_rows
    assert _session(mem_db, sid).status == "success"

    db = mem_db()
    try:
        zero_count = db.execute(text("SELECT COUNT(*) FROM t WHERE x=0")).scalar()
    finally:
        db.close()
    assert zero_count == total_rows


def test_d15_safe_sql_under_threshold_executes(mem_db):
    """D15：safe UPDATE 影响行数 <= 阈值 → 正常 auto_executed。"""
    sid = _make_session(mem_db)
    turn1 = [
        AgentEvent(
            kind="text_delta",
            text="更新：\n```sql\nUPDATE t SET x=0 WHERE id>0\n```\n",
        ),
        AgentEvent(kind="done"),
    ]
    turn2 = [AgentEvent(kind="text_delta", text="完成"), AgentEvent(kind="done")]
    runner = FakeMultiTurnRunner([turn1, turn2])
    loop = _new_loop()

    # t 表只有 3 行（fixture 默认），阈值设 10：3 <= 10 应正常执行。
    session_runner.run_agent_loop(sid, runner, "请更新", loop, safe_row_threshold=10)

    # 3 行全被更新为 0。
    assert _rows(mem_db) == {1: 0, 2: 0, 3: 0}
    aps = _approvals(mem_db, sid)
    assert len(aps) == 1
    assert aps[0].status == "auto_executed"
    assert aps[0].affected_estimate == 3
    assert _session(mem_db, sid).status == "success"


# --------------------------------------------------------------------------- #
# Task 4：unattended（无人值守）模式
# --------------------------------------------------------------------------- #
def test_unattended_dangerous_sql_auto_skipped(mem_db):
    """unattended=True：dangerous SQL 不挂审批，自动跳过 + 记录，session 不进 awaiting_approval。"""
    sid = _make_session(mem_db, task_type="infer_densities")
    runner = FakeMultiTurnRunner(
        [
            [
                AgentEvent(
                    kind="text_delta",
                    text="```sql\nDELETE FROM t;\n```\n",
                ),
                AgentEvent(kind="done"),
            ],
            [AgentEvent(kind="done")],  # 第二轮：无 SQL → 完成
        ]
    )
    main_loop = _new_loop()
    session_runner.run_agent_loop(
        sid,
        runner,
        "初始指令",
        main_loop,
        unattended=True,
        max_turns=4,
    )
    s = _session(mem_db, sid)
    assert s.status == "success"  # 未卡 awaiting_approval，未 failed
    db = mem_db()
    try:
        assert db.execute(text("SELECT COUNT(*) FROM t")).scalar() == 3  # 数据未删
    finally:
        db.close()


def test_unattended_safe_sql_still_executed(mem_db):
    """unattended=True：safe SQL 照常执行。"""
    sid = _make_session(mem_db, task_type="infer_densities")
    runner = FakeMultiTurnRunner(
        [
            [
                AgentEvent(
                    kind="text_delta",
                    text="```sql\nUPDATE t SET x=999 WHERE id=1;\n```\n",
                ),
                AgentEvent(kind="done"),
            ],
            [AgentEvent(kind="done")],
        ]
    )
    main_loop = _new_loop()
    session_runner.run_agent_loop(
        sid,
        runner,
        "初始指令",
        main_loop,
        unattended=True,
        max_turns=4,
    )
    db = mem_db()
    try:
        assert db.execute(text("SELECT x FROM t WHERE id=1")).scalar() == 999
    finally:
        db.close()
