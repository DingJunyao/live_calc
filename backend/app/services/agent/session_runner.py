"""session_runner - 事件聚合落库 + SSE 推送（Task 4a）+ 多轮写操作 loop（Task 4b）。

后台线程入口：

- ``run_session``（4a）：跑**一轮** ``AgentRunner``，把产出的 ``AgentEvent`` 流聚合
  落成 ``AgentMessage``（独立 Session），同时通过 ``stream_bridge.publish_sync`` 推
  SSE 订阅者。
- ``run_agent_loop``（4b）：多轮编排。每轮调 ``_consume_events``（与 ``run_session``
  共用）→ 提取 ```sql``` 块 → safe 自动执行 / dangerous 阻塞等审批 →
  构造下一轮 prompt（执行结果摘要）→ ``runner.run(prompt, resume_session_id=...)``
  续跑。
- ``wake_approval``（4b）：API 端点（Task 5）调用，写审批决策并唤醒阻塞在
  ``_pending_approvals[approval_id]`` 上的 ``run_agent_loop``。

关键复用：4a 的事件 → AgentMessage 落库 + stream_bridge 推送逻辑抽成
``_consume_events``，4a 的 ``run_session`` 与 4b 的 ``run_agent_loop`` 共用它，避免重复。
"""

from __future__ import annotations

import asyncio
import logging
import re
import threading
import time
from datetime import datetime
from typing import Callable, Iterator

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.models.agent_approval import AgentApproval
from app.models.agent_message import AgentMessage
from app.models.agent_session import AgentSession
from app.services.agent import stream_bridge
from app.services.agent.claude_code_runner import ClaudeCodeRunner
from app.services.agent.runner import AgentEvent, AgentRunner
from app.services.agent.sql_extractor import extract_sqls
from app.services.agent.sql_guard import SqlVerdict, classify_sql

logger = logging.getLogger("app.agent.session_runner")

__all__ = [
    "run_session",
    "run_agent_loop",
    "wake_approval",
]

# approval_id -> threading.Event，run_agent_loop 阻塞等审批用。
# wake_approval 写决策后 set 对应 Event 唤醒 loop。
_pending_approvals: "dict[int, threading.Event]" = {}
_pending_lock = threading.Lock()

# session_id -> ClaudeCodeRunner，用于从外部终止正在运行的 Runner。
# cancel_session 通过此 dict 获取 Runner 实例并调用 .cancel()。
_running_runners: "dict[int, ClaudeCodeRunner]" = {}
_running_runners_lock = threading.Lock()


def register_runner(session_id: int, runner: ClaudeCodeRunner) -> None:
    """注册正在运行的 Runner，供 cancel 操作定位。"""
    with _running_runners_lock:
        _running_runners[session_id] = runner


def unregister_runner(session_id: int) -> None:
    """取消注册 Runner（cancel 或自然结束）。"""
    with _running_runners_lock:
        _running_runners.pop(session_id, None)


def cancel_session(session_id: int) -> bool:
    """从外部取消正在运行的 Agent 会话。

    1. 通过 _running_runners 定位并终止 Runner 子进程。
    2. 更新 AgentSession.status 为 'cancelled'。

    Returns:
        True 表示找到了 Runner 或 DB 行并已处理；
        False 表示会话不存在或已终态。
    """
    # 终止子进程。
    with _running_runners_lock:
        runner = _running_runners.get(session_id)
    if runner is not None:
        try:
            runner.cancel()
        except Exception:
            pass

    # 更新 DB status。
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        sess = db.query(AgentSession).get(session_id)
        if sess is None:
            return False
        if sess.status not in ("pending", "running", "awaiting_approval"):
            return False
        sess.status = "cancelled"
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


def _event_to_dict(ev: AgentEvent) -> dict:
    """把 AgentEvent 转成 JSON 可序列化的 dict，供 stream_bridge 推送。

    字段与 AgentEvent 一一对应，None/空值保留以保持结构稳定。
    """
    return {
        "kind": ev.kind,
        "text": ev.text,
        "tool_name": ev.tool_name,
        "tool_input": ev.tool_input,
        "tool_use_id": ev.tool_use_id,
        "tool_result": ev.tool_result,
        "is_error": ev.is_error,
        "crash": ev.crash,
        "cost_usd": ev.cost_usd,
        "permission_denials": ev.permission_denials,
        "error": ev.error,
    }


# --------------------------------------------------------------------------- #
# _consume_events：4a/4b 共用——事件 → AgentMessage 落库 + 推 stream_bridge
#                  + 聚合 assistant 文本。
# --------------------------------------------------------------------------- #
def _consume_events(
    runner_iter: "Iterator[AgentEvent]",
    session_id: int,
    db,
    main_loop: asyncio.AbstractEventLoop,
    *,
    seq_counter: "list[int]",
    on_event: "Callable[[AgentEvent], None] | None" = None,
) -> "tuple[str, bool, bool, float | None, str | None, str | None]":
    """消费一轮 Runner 事件流：落 AgentMessage + 推 stream_bridge + 聚合文本。

    本函数 **不** 改 AgentSession.status（由调用方根据返回值决定），但会维护
    assistant 文本缓冲落 ``AgentMessage``（含 error 兜底落 assistant 消息）。

    Args:
        runner_iter: ``runner.run(...)`` 返回的迭代器。
        session_id: AgentSession.id。
        db: SQLAlchemy Session（调用方负责生命周期）。
        main_loop: 主事件循环（asyncio），跨线程推 stream_bridge 用。
        seq_counter: 单元素 list，持久化消息 seq 自增计数（跨多轮复用，保证整
            个 session 的 seq 单调）。``[起始值]``。
        on_event: 可选回调，每条事件落库+推送后调用。

    Returns:
        tuple ``(turn_text, is_error, had_done, cost_usd, done_error, last_session_id, crashed)``:
            - turn_text: 本轮所有 text_delta 聚合成的完整 assistant 文本。
            - is_error: 本轮是否以 error 或 done.is_error 终态（True 则调用方应中止）。
            - had_done: 是否收到 done 事件。
            - cost_usd: done 事件携带的成本（done.is_error 也保留），无则 None。
            - done_error: done.is_error 时的 error 文本（用于写 session.error），
                无则 None。error 事件场景由 error 分支已落 assistant 消息，
                调用方可用 ``_last_assistant_error`` 取回。
            - last_session_id: 未在此函数捕获（由调用方从 runner 读取）—— 占位 None。
            - crashed: error 事件是否标记了 crash（CLI 自身崩溃，可重试）。
                用于 ``run_agent_loop`` 区分崩溃重试 vs 逻辑错误终止。
    """
    asst_buf: list[str] = []
    # turn_text_parts：累积本轮所有 text_delta（不被 flush 清空），供 4b 提取 SQL。
    # 与 asst_buf 解耦——asst_buf 仅用于按工具调用边界切分 AgentMessage。
    turn_text_parts: list[str] = []
    is_error = False
    had_done = False
    crashed = False
    cost_usd: float | None = None
    done_error: "str | None" = None

    def _next_seq() -> int:
        seq_counter[0] += 1
        return seq_counter[0]

    def _flush_asst() -> None:
        if not asst_buf:
            return
        content = "".join(asst_buf)
        asst_buf.clear()
        msg = AgentMessage(
            session_id=session_id,
            seq=_next_seq(),
            role="assistant",
            content=content,
        )
        db.add(msg)
        db.commit()

    def _emit(ev: AgentEvent, event_dict: "dict | None" = None) -> None:
        payload = event_dict if event_dict is not None else _event_to_dict(ev)
        try:
            stream_bridge.publish_sync(session_id, payload, main_loop)
        except Exception:  # noqa: BLE001
            logger.exception("stream_bridge.publish_sync failed")
        if on_event is not None:
            try:
                on_event(ev)
            except Exception:  # noqa: BLE001
                logger.exception("on_event callback raised")

    for ev in runner_iter:
        if ev.kind == "text_delta":
            asst_buf.append(ev.text)
            turn_text_parts.append(ev.text)
            _emit(ev)

        elif ev.kind == "tool_use":
            _flush_asst()
            msg = AgentMessage(
                session_id=session_id,
                seq=_next_seq(),
                role="tool",
                tool_name=ev.tool_name,
                tool_use_id=ev.tool_use_id or None,
                tool_input=dict(ev.tool_input) if ev.tool_input else {},
            )
            db.add(msg)
            db.commit()
            # C1：tool_use 带 seq，供 SSE 客户端在重连去重时使用。
            _emit(ev, {**_event_to_dict(ev), "seq": msg.seq})

        elif ev.kind == "tool_result":
            msg = AgentMessage(
                session_id=session_id,
                seq=_next_seq(),
                role="tool",
                tool_use_id=ev.tool_use_id or None,
                tool_result=ev.tool_result,
            )
            db.add(msg)
            db.commit()
            # C1：tool_result 带 seq，供 SSE 客户端在重连去重时使用。
            _emit(ev, {**_event_to_dict(ev), "seq": msg.seq})

        elif ev.kind == "done":
            _flush_asst()
            if ev.cost_usd is not None:
                cost_usd = ev.cost_usd
            had_done = True
            if ev.is_error:
                is_error = True
                done_error = ev.error or "Agent 终态 is_error"
            _emit(ev)

        elif ev.kind == "error":
            _flush_asst()
            err_msg = AgentMessage(
                session_id=session_id,
                seq=_next_seq(),
                role="assistant",
                content=ev.error or "(unknown error)",
            )
            db.add(err_msg)
            db.commit()
            _emit(ev)
            is_error = True
            crashed = bool(ev.crash)
            # error 即终态：直接结束消费。
            break

        else:
            _emit(ev)

    turn_text = "".join(turn_text_parts)
    _flush_asst()
    return turn_text, is_error, had_done, cost_usd, done_error, None, crashed


def run_session(
    session_id: int,
    runner: AgentRunner,
    prompt: str,
    main_loop: asyncio.AbstractEventLoop,
    *,
    resume_session_id: "str | None" = None,
    on_event: "Callable[[AgentEvent], None] | None" = None,
) -> "str | None":
    """后台线程入口：跑一轮 Runner，事件聚合落 AgentMessage + 推 stream_bridge。

    Args:
        session_id: AgentSession.id（调用方先建好行）。
        runner: AgentRunner 实例（如 ClaudeCodeRunner）。
        prompt: 用户指令。
        main_loop: 主事件循环（asyncio.get_event_loop()），用于跨线程推送。
        resume_session_id: 若提供，传给 runner.run 续跑。
        on_event: 可选回调，每条事件落库+推送后调用。

    Returns:
        str | None: runner.last_session_id（供 4b 回流用）。
    """
    from app.core.database import SessionLocal

    db = SessionLocal()
    seq_counter = [0]
    last_cost_usd: float | None = None

    try:
        sess = db.query(AgentSession).get(session_id)
        if sess is None:
            raise ValueError(f"AgentSession {session_id} 不存在")
        sess.status = "running"
        db.commit()

        turn_text, is_error, had_done, cost_usd, done_error, _, _crashed = _consume_events(
            runner.run(prompt, resume_session_id=resume_session_id),
            session_id,
            db,
            main_loop,
            seq_counter=seq_counter,
            on_event=on_event,
        )
        if cost_usd is not None:
            last_cost_usd = cost_usd

        last_claude_sid: str | None
        try:
            last_claude_sid = runner.last_session_id
        except Exception:  # noqa: BLE001
            last_claude_sid = None

        # 收尾：根据 error/done.is_error 决定终态。
        sess = db.query(AgentSession).get(session_id)
        if sess is not None:
            sess.claude_session_id = last_claude_sid or sess.claude_session_id
            if last_cost_usd is not None:
                sess.cost_usd = last_cost_usd
            if is_error:
                sess.status = "failed"
                # done.is_error 优先用 done_error；error 事件走 _last_assistant_error
                # （_consume_events 的 error 分支已落 assistant 消息）。
                if done_error:
                    sess.error = done_error
                else:
                    sess.error = _last_assistant_error(db, session_id) or sess.error
            elif had_done:
                sess.status = "success"
            else:
                sess.status = "success"
            db.commit()

        return last_claude_sid

    except Exception as exc:  # noqa: BLE001
        logger.exception("run_session 异常")
        try:
            sess = db.query(AgentSession).get(session_id)
            if sess is not None:
                sess.status = "failed"
                sess.error = f"{type(exc).__name__}: {exc}"
                db.commit()
            err_ev = AgentEvent(
                kind="error", error=f"{type(exc).__name__}: {exc}", is_error=True
            )
            try:
                stream_bridge.publish_sync(
                    session_id, _event_to_dict(err_ev), main_loop
                )
            except Exception:  # noqa: BLE001
                logger.exception("publish_sync failed in except")
        except Exception:  # noqa: BLE001
            pass
        try:
            return runner.last_session_id
        except Exception:  # noqa: BLE001
            return None
    finally:
        db.close()


def _last_assistant_error(db, session_id: int) -> "str | None":
    """取本 session 最新一条 assistant 消息 content（error 分支已落此消息）。"""
    msg = (
        db.query(AgentMessage)
        .filter(AgentMessage.session_id == session_id)
        .filter(AgentMessage.role == "assistant")
        .order_by(AgentMessage.seq.desc())
        .first()
    )
    if msg is None:
        return None
    return msg.content


# --------------------------------------------------------------------------- #
# Task 4b：多轮 agent_loop + 写操作提取/执行/审批 + 回流
# --------------------------------------------------------------------------- #

# 数据库中的布尔列名列表，用于 normalize_booleans 将 Agent 生成的 = 1/= 0
# 转换为 = true/= false（兼容 PostgreSQL）。
_BOOLEAN_COLUMNS: set[str] = {
    "is_active", "is_default", "is_verified", "ai_inferred",
    "is_admin", "is_common", "is_si_base", "is_bidirectional",
    "is_optional", "is_favorite", "is_primary", "is_imported",
    "is_merged", "is_open", "email_verified", "is_primary",
}


def _find_matching_paren(text: str, start: int) -> int:
    """找到从 start 开始的匹配括号位置（start 指向 '('），处理嵌套。"""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                return i
    return -1


def _normalize_booleans(sql: str) -> str:
    """将 Agent 生成的 SQL 中布尔列比较从 ``= 1``/``= 0`` 转为 ``= true``/``= false``。

    SQLite 把 BOOLEAN 存为 0/1 整数，PostgreSQL 需要真正的 BOOLEAN 语义。
    Agent 按 SQLite 习惯生成 ``WHERE is_active = 1``，在 PostgreSQL 上会报
    ``UndefinedFunction: 操作符不存在: boolean = integer``。

    此函数作为**兜底安全网**（搭配模板中已添加的提示），在 SQL 执行前自动转换。
    仅当列名匹配已知布尔列时替换，避免误伤普通整数列。
    """
    cols = "|".join(sorted(_BOOLEAN_COLUMNS, key=len, reverse=True))
    # WHERE/AND/OR/ON/HAVING 等语境下的布尔比较
    sql = re.sub(
        rf"\b({cols})\s*=\s*1\b",
        r"\1 = true",
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(
        rf"\b({cols})\s*=\s*0\b",
        r"\1 = false",
        sql,
        flags=re.IGNORECASE,
    )

    # INSERT 语句：用括号匹配解析（支持子查询等嵌套括号）
    result_parts: list[str] = []
    pos = 0
    while pos < len(sql):
        # 查找 INSERT INTO
        insert_match = re.match(
            r"INSERT\s+INTO\s+(\w+)\s*\(", sql[pos:], re.IGNORECASE,
        )
        if not insert_match:
            result_parts.append(sql[pos:])
            break

        # 保留 INSERT INTO table 前缀
        prefix_end = pos + insert_match.end() - 1  # 指向 '('
        # 找列名列表的匹配括号
        cols_end = _find_matching_paren(sql, prefix_end)
        if cols_end < 0:
            result_parts.append(sql[pos:])
            break

        cols_str = sql[prefix_end + 1:cols_end]
        after_cols = sql[cols_end + 1:].lstrip()
        # 检查是否以 VALUES 开头
        vals_match = re.match(r"VALUES\s*\(", after_cols, re.IGNORECASE)
        if not vals_match:
            result_parts.append(sql[pos:cols_end + 1])
            pos = cols_end + 1
            continue

        vals_start = cols_end + 1 + (len(after_cols) - len(after_cols.lstrip())) + vals_match.end() - 1
        vals_end = _find_matching_paren(sql, vals_start)
        if vals_end < 0:
            result_parts.append(sql[pos:cols_end + 1])
            pos = cols_end + 1
            continue

        vals_str = sql[vals_start + 1:vals_end]

        # 检查列名中是否有布尔列
        col_names = [c.strip() for c in cols_str.split(",")]
        bool_indices = {i for i, c in enumerate(col_names)
                        if c.strip().lower() in _BOOLEAN_COLUMNS}
        if not bool_indices:
            result_parts.append(sql[pos:vals_end + 1])
            pos = vals_end + 1
            continue

        # 解析 VALUES，用逗号分割时考虑括号嵌套和引号
        val_items = _split_values(vals_str)
        changed = False
        for i in bool_indices:
            if i < len(val_items):
                v = val_items[i].strip()
                if v == "0":
                    val_items[i] = " false"
                    changed = True
                elif v == "1":
                    val_items[i] = " true"
                    changed = True
        if not changed:
            result_parts.append(sql[pos:vals_end + 1])
            pos = vals_end + 1
            continue

        # 拼回 INSERT（原语句的 ; 会在 pos 跳跃时被跳过，不重复追加）
        result_parts.append(f"INSERT INTO {insert_match.group(1)} ({cols_str}) VALUES ({','.join(val_items)})")
        # 跳过分号（如果有），避免在结尾追加剩余文本时重复
        pos = vals_end + 1
        if pos < len(sql) and sql[pos] == ";":
            pos += 1

    return "".join(result_parts)


def _split_values(vals_str: str) -> list[str]:
    """分割 VALUES 括号中的值列表，支持子查询嵌套和引号字符串。

    例如 ``'ingredient', 2, (SELECT id FROM units WHERE abbreviation = 'g'), 'agent', 0``
    """
    result: list[str] = []
    current: list[str] = []
    in_quote = False
    quote_char = ""
    paren_depth = 0
    for ch in vals_str:
        if in_quote:
            current.append(ch)
            if ch == quote_char:
                in_quote = False
        elif ch in ("'", '"'):
            current.append(ch)
            in_quote = True
            quote_char = ch
        elif ch == '(':
            current.append(ch)
            paren_depth += 1
        elif ch == ')':
            current.append(ch)
            paren_depth -= 1
        elif ch == "," and paren_depth == 0:
            # 只在顶层逗号处分割
            result.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        result.append("".join(current))
    return result


def _execute_sql(db, sql: str) -> "tuple[int | None, str | None]":
    """在**独立 Session** 上执行一条 SQL（已通过审批或 safe 判定）。

    用独立 ``SessionLocal()`` 而非 loop 的 db Session，原因：
    - 避免污染 loop 的读 Session；
    - 使 D15 rowcount 护栏能在超阈值时仅 rollback 这一条 SQL，而不影响 loop 之前
      已 commit 的写。

    Args:
        db: 保留入参兼容（现不再使用，传 None 也行），实际由独立 Session 执行。
        sql: 要执行的 SQL 文本。

    Returns:
        (affected_rows, error_msg)：affected_rows 为 rowcount 或 None（异常时），
        error_msg 非 None 表示执行失败。
    """
    from app.core.database import SessionLocal

    del db  # 不再使用 loop 的 db Session，避免污染 + rollback 撤销已 commit 的写。
    # 兼容 PostgreSQL：将 Agent 生成的 SQL 中布尔列比较从 = 1/= 0 转为 = true/= false
    sql = _normalize_booleans(sql)
    sess = SessionLocal()
    try:
        result = sess.execute(text(sql))
        sess.commit()
        return result.rowcount, None
    except SQLAlchemyError as e:
        sess.rollback()
        return None, f"{type(e).__name__}: {e}"
    except Exception as e:  # noqa: BLE001
        try:
            sess.rollback()
        except Exception:  # noqa: BLE001
            pass
        return None, f"{type(e).__name__}: {e}"
    finally:
        sess.close()


def _execute_safe_with_threshold(
    sql: str, threshold: int
) -> "tuple[int | None, str | None, bool]":
    """safe SQL 的执行 + rowcount 护栏（D15）。

    流程（用独立 Session 的事务）：
      1. execute → 得 rowcount。
      2. 若 rowcount > threshold：rollback（不提交该 SQL）→ 返回 ``(rowcount,
         None, escalated=True)``，由调用方转 dangerous 审批。
      3. 否则 commit → 返回 ``(rowcount, None, escalated=False)``。
      4. 异常：rollback → 返回 ``(None, errmsg, False)``。

    用独立 ``SessionLocal()``：rollback 只回滚这一条 SQL 的事务，不影响 loop 的 db
    Session（loop 的 db 是另一个实例，已 commit 的写不受影响）。

    注意：SQLAlchemy 的 ``result.rowcount`` 在 commit 前即可读，且未 commit 时其它
    Session 看不到该写（事务隔离），因此 rollback 可安全撤销。

    Returns:
        (affected_rows, error_msg, escalated)。
    """
    from app.core.database import SessionLocal

    sess = SessionLocal()
    try:
        result = sess.execute(text(sql))
        rowcount = result.rowcount
        if rowcount is not None and rowcount > threshold:
            # 超阈值：回滚这条 SQL（事务未提交，其它 Session 看不到写）。
            sess.rollback()
            return rowcount, None, True
        sess.commit()
        return rowcount, None, False
    except SQLAlchemyError as e:
        sess.rollback()
        return None, f"{type(e).__name__}: {e}", False
    except Exception as e:  # noqa: BLE001
        try:
            sess.rollback()
        except Exception:  # noqa: BLE001
            pass
        return None, f"{type(e).__name__}: {e}", False
    finally:
        sess.close()


def _emit_sse(
    session_id: int,
    main_loop: asyncio.AbstractEventLoop,
    payload: dict,
) -> None:
    """推一条 synthesized 事件给 stream_bridge，吞异常。"""
    try:
        stream_bridge.publish_sync(session_id, payload, main_loop)
    except Exception:  # noqa: BLE001
        logger.exception("publish_sync failed in agent_loop")


def _build_resume_prompt(items: list[str]) -> str:
    """把「执行结果摘要」条目拼成下一轮 user prompt。"""
    if not items:
        return "本轮无待执行写操作，请确认任务完成或继续。"
    body = "\n".join(items)
    return (
        "已处理以下数据库写操作：\n"
        f"{body}\n\n"
        "请基于上述结果继续，或确认任务已完成。"
    )


def run_agent_loop(
    session_id: int,
    runner: AgentRunner,
    initial_prompt: str,
    main_loop: asyncio.AbstractEventLoop,
    *,
    max_turns: int = 10,
    db_session_factory=None,
    approval_timeout: float = 3600.0,
    safe_row_threshold: int = 100,
    resume_session_id: "str | None" = None,
    unattended: bool = False,
    max_crash_retries: int = 5,
) -> None:
    """后台线程入口：多轮 Runner + 写操作提取/执行/审批 + 回流。

    循环（每轮）：
      1. 跑一轮 Runner（首轮用 initial_prompt + resume_session_id（插话用），
         后续用上一轮的执行结果摘要 + 本轮捕获的 claude_session_id）。
      2. 捕获本轮 assistant 文本（``_consume_events`` 聚合 text_delta）。
      3. error / done.is_error → session.failed，终止。
         **例外**：若 error 来自 CLI 自身崩溃（``AgentEvent.crash=True``），
         且 ``crash_retries_left > 0``，则退避重试同一轮（不消耗 turn 配额）。
      4. ``sqls = extract_sqls(turn_text)``：
         - 无 SQL → session.success，终止（Agent 表示完成）。
         - 有 SQL → 逐条 classify_sql：safe 自动执行；dangerous 写 AgentApproval
           (pending) + 阻塞等 ``wake_approval``。
      5. 构造下一轮 prompt（执行结果摘要），回到步骤 1。

    终止条件：无 SQL（完成）/ max_turns / error / done.is_error / 审批超时。

    Args:
        resume_session_id: 首轮 resume 的 claude session id（插话场景：在已终态
            会话上起新轮，``initial_prompt`` 作为 user 消息，``--resume`` 续跑）。
            首次创建的会话不传（默认 None）。
        approval_timeout: 单条 dangerous SQL 审批等待秒数；超时则 session.failed，
            SSE 推 ``sql_timeout``，不再重试同条 SQL（语义与 rejected 区分）。
        safe_row_threshold: safe SQL 运行时影响行数护栏；超阈值则回滚该 SQL 并转
            dangerous 审批（防止 ``UPDATE ... WHERE 1=1`` 类恒真条件全表更新）。
        unattended: 无人值守模式（默认 False）。为 True 时，dangerous SQL **不** 阻塞
            等审批——不写 pending AgentApproval、不进 awaiting_approval、不调
            ``_handle_dangerous_sql``，改为记 warning + 推 ``sql_skipped`` SSE +
            摘要标注「已跳过」。safe SQL 行为不变（照常执行 + D15 护栏）。
            老路径（导入后处理等用户不在线的场景）应传 True，dangerous 兜底跳过。
        max_crash_retries: CLI 自身崩溃（非逻辑/超时错误）的最大重试次数（默认 5）。
            每次重试间有指数退避延迟（2s→4s→8s，上限 30s）。
            崩溃不消耗 ``max_turns`` 配额。
    """
    if db_session_factory is None:
        from app.core.database import SessionLocal as db_session_factory  # type: ignore[assignment]

    db = db_session_factory()
    register_runner(session_id, runner)
    seq_counter = [0]
    # resume 锚分流：
    # - uses_db_pk_resume=True（LangChainRunner）：锚恒为 str(session_id)，
    #   因为 _load_history 按 AgentMessage.session_id（= AgentSession DB PK）查历史。
    #   首轮即设值 → claude_session_id 非 NULL → post_message 插话不再 409；
    #   每轮 resume 都能恢复历史。
    # - 否则（ClaudeCodeRunner）：首轮用入参 resume_session_id（插话场景），
    #   后续轮用 runner.last_session_id（CLI 捕获的 claude session id）。
    uses_db_pk = bool(getattr(runner, "uses_db_pk_resume", False))
    current_sid: "str | None" = str(session_id) if uses_db_pk else resume_session_id
    next_prompt = initial_prompt

    try:
        sess = db.query(AgentSession).get(session_id)
        if sess is None:
            raise ValueError(f"AgentSession {session_id} 不存在")
        sess.status = "running"
        db.commit()

        crash_retries_left = max_crash_retries
        turn_idx = 0
        while turn_idx < max_turns:
            turn_idx += 1

            turn_text, is_error, had_done, cost_usd, done_error, _, _crashed = _consume_events(
                runner.run(next_prompt, resume_session_id=current_sid),
                session_id,
                db,
                main_loop,
                seq_counter=seq_counter,
            )

            # 累计 cost。
            if cost_usd is not None:
                s = db.query(AgentSession).get(session_id)
                if s is not None:
                    prev = float(s.cost_usd) if s.cost_usd is not None else 0.0
                    s.cost_usd = prev + cost_usd
                    db.commit()

            # 捕获 last_session_id（下一轮 resume 用）。
            # uses_db_pk_resume=True（LangChainRunner）路径：锚恒为 str(session_id)，
            # 与 runner.last_session_id（仅 echo 入参，首轮为 None）无关。
            try:
                if uses_db_pk:
                    current_sid = str(session_id)
                else:
                    current_sid = runner.last_session_id
            except Exception:  # noqa: BLE001
                current_sid = None
            s = db.query(AgentSession).get(session_id)
            if s is not None and current_sid:
                s.claude_session_id = current_sid
                db.commit()

            # 取消检查：若外部调用了 cancel_session，DB 状态已变，立即终止。
            s = db.query(AgentSession).get(session_id)
            if s is not None and s.status == "cancelled":
                s.error = "用户取消了会话"
                db.commit()
                return

            # 终态错误：CLI 崩溃可重试，其他错误直接终止。
            if is_error:
                if _crashed and crash_retries_left > 0:
                    crash_retries_left -= 1
                    # 指数退避：2s → 4s → 8s（上限 30s）
                    delay = min(2 ** (max_crash_retries - crash_retries_left), 30)
                    logger.warning(
                        "CLI 崩溃（turn %d/%d），%d 次重试剩余，%ds 后退避重试…",
                        turn_idx, max_turns, crash_retries_left, delay,
                    )
                    _emit_sse(
                        session_id,
                        main_loop,
                        {
                            "kind": "crash_retry",
                            "turn": turn_idx,
                            "retries_left": crash_retries_left,
                            "delay_s": delay,
                            "error": done_error or _last_assistant_error(db, session_id) or "",
                        },
                    )
                    time.sleep(delay)
                    turn_idx -= 1  # 崩溃不消耗 turn 配额
                    # 重置 current_sid：崩溃后 resume 可能失败，下次用 None 起新会话
                    # （保留上次成功轮的 sid 供 resume 尝试，若失败 CLI 会起新会话）
                    continue

                s = db.query(AgentSession).get(session_id)
                if s is not None:
                    s.status = "failed"
                    if done_error:
                        s.error = done_error
                    else:
                        s.error = _last_assistant_error(db, session_id) or s.error
                    db.commit()
                return

            # 提取 SQL。
            sqls = extract_sqls(turn_text)
            if not sqls:
                # Agent 表示完成。
                s = db.query(AgentSession).get(session_id)
                if s is not None:
                    s.status = "success"
                    db.commit()
                return

            # 逐条处理。
            summary_items: list[str] = []
            session_failed = False
            for i, sql in enumerate(sqls, start=1):
                verdict = classify_sql(sql, lenient=True)
                if not verdict.dangerous:
                    item, escalated = _handle_safe_sql(
                        db,
                        session_id,
                        main_loop,
                        i,
                        sql,
                        safe_row_threshold=safe_row_threshold,
                        approval_timeout=approval_timeout,
                        unattended=unattended,
                    )
                    summary_items.append(item)
                    if escalated:
                        # safe 转 dangerous 审批——阻塞等 / 超时分支。
                        s_after = db.query(AgentSession).get(session_id)
                        if s_after is not None and s_after.status == "failed":
                            session_failed = True
                            break
                else:
                    if unattended:
                        # 无人值守：dangerous SQL 不挂审批、不阻塞——记日志 + 推
                        # sql_skipped SSE + 摘要标注「已跳过」。session 仍 running。
                        logger.warning(
                            "unattended 模式跳过 dangerous SQL: %s", sql[:120]
                        )
                        _emit_sse(
                            session_id,
                            main_loop,
                            {
                                "kind": "sql_skipped",
                                "sql": sql,
                                "danger_reason": verdict.reason,
                            },
                        )
                        preview = sql if len(sql) <= 80 else sql[:77] + "..."
                        summary_items.append(
                            f"{i}. {preview} → 已跳过（无人值守，{verdict.reason}）"
                        )
                    else:
                        summary_items.append(
                            _handle_dangerous_sql(
                                db,
                                session_id,
                                main_loop,
                                i,
                                sql,
                                verdict,
                                approval_timeout=approval_timeout,
                            )
                        )
                        # 超时 / 拒绝 / 异常分支可能将 session 置 failed——若 failed 则终止。
                        s_after = db.query(AgentSession).get(session_id)
                        if s_after is not None and s_after.status == "failed":
                            session_failed = True
                            break

            if session_failed:
                return

            # 再次检查取消。
            s = db.query(AgentSession).get(session_id)
            if s is not None and s.status == "cancelled":
                s.error = "用户取消了会话"
                db.commit()
                return

            next_prompt = _build_resume_prompt(summary_items)

        # 达到 max_turns：保守置 success 并附说明。
        s = db.query(AgentSession).get(session_id)
        if s is not None:
            s.status = "success"
            s.error = f"达到 max_turns={max_turns} 上限，循环终止"
            db.commit()

    except Exception as exc:  # noqa: BLE001
        logger.exception("run_agent_loop 异常")
        try:
            s = db.query(AgentSession).get(session_id)
            if s is not None:
                s.status = "failed"
                s.error = f"{type(exc).__name__}: {exc}"
                db.commit()
        except Exception:  # noqa: BLE001
            pass
    finally:
        unregister_runner(session_id)
        # 清理可能残留的 pending approval Event（loop 异常退出兜底）。
        db.close()


def _handle_safe_sql(
    db,
    session_id: int,
    main_loop: asyncio.AbstractEventLoop,
    index: int,
    sql: str,
    *,
    safe_row_threshold: int = 100,
    approval_timeout: float = 3600.0,
    unattended: bool = False,
) -> "tuple[str, bool]":
    """safe SQL：执行 + 运行时 rowcount 护栏（D15）。

    - err 非 None：执行失败 → 写 auto_executed AgentApproval（带 error）+ 推 SSE，
      返回 ``(失败摘要, escalated=False)``。
    - rowcount <= safe_row_threshold：正常提交 → 写 auto_executed AgentApproval +
      推 SSE，返回 ``(摘要, escalated=False)``。
    - rowcount > safe_row_threshold：**回滚该 SQL**（见 ``_execute_safe_with_threshold``
      事务未提交即 rollback，不影响 loop 的 db）→ 转 ``_handle_dangerous_sql`` 走审批
      （danger_reason="影响行数超阈值 {n}"）。返回 ``(审批摘要, escalated=True)``。
      若 ``unattended=True``：转 dangerous 后不挂审批——记 warning + 推
      ``sql_skipped`` SSE + 摘要标注「已跳过」，返回 ``(跳过摘要, escalated=True)``
      （escalated 仍 True 以保持返回值语义一致，但 session 不会变 failed——unattended
      分支永不阻塞）。

    返回 ``(摘要条目, escalated)``。``escalated=True`` 时调用方需检查 session.status
    是否因审批超时变为 failed（unattended 分支永不置 failed）。
    """
    affected, err, escalated = _execute_safe_with_threshold(sql, safe_row_threshold)

    if escalated:
        # 超阈值 → 转 dangerous 审批。danger_reason 用运行时实测 rowcount。
        verdict = SqlVerdict(
            dangerous=True,
            reason=f"影响行数超阈值 {affected}（> {safe_row_threshold}）",
        )
        if unattended:
            # 无人值守：超阈值 SQL 也不挂审批——跳过。
            logger.warning("unattended 模式跳过超阈值 SQL: %s", sql[:120])
            _emit_sse(
                session_id,
                main_loop,
                {
                    "kind": "sql_skipped",
                    "sql": sql,
                    "danger_reason": verdict.reason,
                },
            )
            preview = sql if len(sql) <= 80 else sql[:77] + "..."
            return (
                f"{index}. {preview} → 已跳过（无人值守，{verdict.reason}）",
                True,
            )
        summary = _handle_dangerous_sql(
            db,
            session_id,
            main_loop,
            index,
            sql,
            verdict,
            approval_timeout=approval_timeout,
        )
        return summary, True

    # 正常路径：写 auto_executed + 推 SSE。
    ap = AgentApproval(
        session_id=session_id,
        sql=sql,
        affected_estimate=affected,
        status="auto_executed",
    )
    db.add(ap)
    db.commit()
    db.refresh(ap)

    _emit_sse(
        session_id,
        main_loop,
        {
            "kind": "sql_executed",
            "approval_id": ap.id,
            "sql": sql,
            "affected": affected,
            "status": "auto_executed",
            "error": err,
            "auto": True,
        },
    )

    preview = sql if len(sql) <= 80 else sql[:77] + "..."
    if err is not None:
        return (
            f"{index}. [执行失败] {preview} → 错误：{err}（source=agent, auto）",
            False,
        )
    return f"{index}. {preview} → 影响 {affected} 行（source=agent, auto）", False


def _handle_dangerous_sql(
    db,
    session_id: int,
    main_loop: asyncio.AbstractEventLoop,
    index: int,
    sql: str,
    verdict: SqlVerdict,
    *,
    approval_timeout: float = 3600.0,
    pre_sse_hook: "Callable[[int], None] | None" = None,
) -> str:
    """dangerous SQL：写 pending AgentApproval + 阻塞等 wake_approval。

    C10 时序（修复审批竞态死锁）：
      1. commit pending AgentApproval（拿到 approval_id）。
      2. **在 SSE 推送之前**将 threading.Event 注册入 ``_pending_approvals``。
         （wake_approval 只能由前端收到 SSE 后触发，dict 在 SSE 前写入就能保证
         wake 时 dict 必有 Event，避免「wake 查到 pending→写 approved→dict.get 返
         None 不 set→return True」的竞态死锁。）
      3. 标 session awaiting_approval + commit。
      4. 推 SSE approval_needed。
      5. ev.wait(timeout=approval_timeout)。
      6. 无论是否唤醒，清理 dict。

    C12 超时语义：
      - wait 返回 False（超时）：session.failed + SSE 推 ``sql_timeout``，返回
        「审批超时」摘要。loop 检测到 failed 终止，不重试同条 SQL。
      - wait 返回 True（被唤醒）：重查决策。
        - approved → 执行（独立 Session）+ SSE sql_executed，恢复 running。
        - rejected → 不执行 + SSE sql_rejected，恢复 running。

    Args:
        pre_sse_hook: 可选测试钩子，在 Event 注册完成、SSE 推送**之前**调用，
            传入 approval_id。用于竞态回归测试（在 SSE 前提前调 wake_approval）。
    """
    ap = AgentApproval(
        session_id=session_id,
        sql=sql,
        danger_reason=verdict.reason,
        status="pending",
    )
    db.add(ap)
    db.commit()
    db.refresh(ap)
    approval_id = ap.id

    # C10：Event 注册提前到 SSE 之前。
    ev = threading.Event()
    with _pending_lock:
        _pending_approvals[approval_id] = ev

    # 测试钩子：在 SSE 前注入（模拟 wake 在 SSE 后、Event 注册前的极端竞态）。
    if pre_sse_hook is not None:
        try:
            pre_sse_hook(approval_id)
        except Exception:  # noqa: BLE001
            logger.exception("pre_sse_hook raised")

    # 标记 session awaiting_approval。
    s = db.query(AgentSession).get(session_id)
    if s is not None:
        s.status = "awaiting_approval"
        db.commit()

    _emit_sse(
        session_id,
        main_loop,
        {
            "kind": "approval_needed",
            "approval_id": approval_id,
            "sql": sql,
            "danger_reason": verdict.reason,
        },
    )

    # 阻塞等审批（C12 可配超时）。
    got = ev.wait(timeout=approval_timeout)
    # 无论是否唤醒，清理 dict。
    with _pending_lock:
        _pending_approvals.pop(approval_id, None)

    preview = sql if len(sql) <= 80 else sql[:77] + "..."

    if not got:
        # C12：超时分支——异常终态，不重试。
        logger.warning("审批 %d 超时（%ss）", approval_id, approval_timeout)
        _emit_sse(
            session_id,
            main_loop,
            {
                "kind": "sql_timeout",
                "approval_id": approval_id,
                "sql": sql,
            },
        )
        s = db.query(AgentSession).get(session_id)
        if s is not None and s.status != "failed":
            s.status = "failed"
            s.error = f"审批 {approval_id} 超时未响应"
            db.commit()
        return f"{index}. {preview} → 审批超时（未执行）"

    # 唤醒：重查审批结果（wake_approval 在独立 Session 提交决策；expire_all 避开缓存）。
    db.expire_all()
    ap = db.query(AgentApproval).get(approval_id)
    if ap is None:
        return f"{index}. [异常] {preview} → 审批记录丢失"

    if ap.status == "approved":
        affected, err = _execute_sql(db, sql)
        ap.affected_estimate = affected
        db.commit()
        _emit_sse(
            session_id,
            main_loop,
            {
                "kind": "sql_executed",
                "approval_id": approval_id,
                "sql": sql,
                "affected": affected,
                "status": "approved",
                "error": err,
                "auto": False,
            },
        )
        # 恢复 running。
        s = db.query(AgentSession).get(session_id)
        if s is not None and s.status == "awaiting_approval":
            s.status = "running"
            db.commit()
        if err is not None:
            return (
                f"{index}. [执行失败] {preview} → 错误：{err}（source=agent, approved）"
            )
        return (
            f"{index}. {preview} → 已执行 影响 {affected} 行（source=agent, approved）"
        )

    # rejected（或其它非 approved 终态）。
    _emit_sse(
        session_id,
        main_loop,
        {
            "kind": "sql_rejected",
            "approval_id": approval_id,
            "sql": sql,
            "status": "rejected",
        },
    )
    s = db.query(AgentSession).get(session_id)
    if s is not None and s.status == "awaiting_approval":
        s.status = "running"
        db.commit()
    return f"{index}. {preview} → 已拒绝（未执行）"


def wake_approval(approval_id: int, approved: bool, user_id: int) -> bool:
    """API 端点（Task 5）调用：写审批决策 + 唤醒阻塞的 agent_loop。

    Args:
        approval_id: AgentApproval.id。
        approved: True=批准并执行，False=拒绝。
        user_id: 决策者 user_id。

    Returns:
        True 表示找到 pending 审批并已写决策 + 唤醒；
        False 表示审批不存在 / 已决策 / 无阻塞 loop。
    """
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        ap = db.query(AgentApproval).get(approval_id)
        if ap is None or ap.status != "pending":
            return False
        ap.status = "approved" if approved else "rejected"
        ap.decided_by = user_id
        ap.decided_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()

    with _pending_lock:
        ev = _pending_approvals.get(approval_id)
    if ev is not None:
        ev.set()
    return True
