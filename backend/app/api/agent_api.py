"""Agent 任务台 API 路由（Task 5）。

端点总览：
- ``POST /agent/sessions`` - 建会话 + 后台线程跑 run_agent_loop。
- ``GET  /agent/sessions`` - 列会话（管理员看全部，普通用户看自己的）。
- ``GET  /agent/sessions/{sid}`` - 会话详情（session + messages + pending_approvals）。
- ``GET  /agent/sessions/{sid}/stream`` - SSE：历史回放 + 实时 queue + 终态兜底。
- ``POST /agent/sessions/{sid}/messages`` - 插话：在已终态会话上起 resume 新轮。
- ``POST /agent/approvals/{aid}`` - 审批决策：wake_approval。

鉴权对齐 import_api 风格：建会话/插话/审批仅管理员；list/get 自己的会话普通
用户也能看。

跨线程 main_loop：async 端点用 ``asyncio.get_event_loop()`` 捕获，传给后台线程，
后台线程用 ``loop.call_soon_threadsafe`` 经 stream_bridge 推送事件给订阅者 queue。
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from datetime import datetime
from typing import Any, AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.security import get_current_user, resolve_user_from_token
from app.models.agent_approval import AgentApproval
from app.models.agent_message import AgentMessage
from app.models.agent_session import AgentSession
from app.schemas.agent import (
    AgentApprovalOut,
    AgentMessageOut,
    AgentSessionOut,
    ApprovalDecisionIn,
    CreateSessionIn,
    PostMessageIn,
    SessionDetailOut,
)
from app.services.agent import runner_factory, session_runner, stream_bridge
from app.services.agent.session_runner import cancel_session, _pending_approvals
from app.services.agent.task_templates import get_template, list_task_types

logger = logging.getLogger("app.api.agent")

# 最终挂载前缀由 main.py 的 include_router(prefix="/api/v1/agent") 决定，
# 路径为 /api/v1/agent/sessions 等。
router = APIRouter()


# --------------------------------------------------------------------------- #
# 鉴权
# --------------------------------------------------------------------------- #
def _require_admin(user) -> None:
    """管理员校验，对齐 import_api.trigger_repo_import 风格。"""
    if not getattr(user, "is_admin", False):
        raise HTTPException(status_code=403, detail="仅管理员可操作")


# --------------------------------------------------------------------------- #
# task_type -> 模板解析（Task 6 接入 task_templates）
# --------------------------------------------------------------------------- #
# 已知 task_type 命中 TASK_TEMPLATES（见 services/agent/task_templates.py），
# 用模板的 title/prompt；未知 task_type 直接 400 拒绝（避免任意 prompt 注入）。
def _resolve_template(task_type: str) -> dict:
    """根据 task_type 解析模板，未命中抛 KeyError（由调用方转 400）。"""
    return get_template(task_type)


# --------------------------------------------------------------------------- #
# 端点
# --------------------------------------------------------------------------- #
@router.get("/task-types")
def get_task_types(current_user=Depends(get_current_user)):
    """列出可用任务类型（前端按钮列表用）。

    - 任意已登录用户可访问（仅返回静态模板清单，无敏感数据）。
    - 返回 ``[{task_type, title}]``。
    """
    return list_task_types()


@router.post("/sessions")
async def create_session(
    body: CreateSessionIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """建会话 + 起后台 run_agent_loop 线程。

    - 仅管理员。
    - task_type 必须命中 ``TASK_TEMPLATES``（见 task_templates）；未知 → 400。
    - 后台线程独立 Session（run_agent_loop 内部 ``SessionLocal()``）。
    - main_loop 在 async 端点捕获（``asyncio.get_event_loop()``），传给后台线程
      跨线程推 stream_bridge。
    """
    _require_admin(current_user)

    try:
        tpl = _resolve_template(body.task_type)
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"未知任务类型: {body.task_type}（可用类型见 GET /api/v1/agent/task-types）",
        )
    initial_prompt = tpl["prompt"]

    # 预查询兜底原料列表，直接注入 prompt，防止 Agent 跳过
    if body.task_type in ("infer_quantities", "fill_piece_weight"):
        try:
            sdb = SessionLocal()
            try:
                from sqlalchemy import text as _text
                orphans = sdb.execute(_text(
                    "SELECT i.id, i.name FROM ingredients i"
                    " WHERE i.is_active = true AND i.piece_weight IS NULL"
                    " AND (i.name LIKE '%个' OR i.name LIKE '%只' OR i.name LIKE '%条'"
                    " OR i.name LIKE '%根' OR i.name LIKE '%颗' OR i.name LIKE '%粒'"
                    " OR i.name LIKE '%瓣' OR i.name LIKE '%片' OR i.name LIKE '%块'"
                    " OR i.name LIKE '%段' OR i.name LIKE '%朵' OR i.name LIKE '%把'"
                    " OR i.name LIKE '%头' OR i.name LIKE '%尾' OR i.name LIKE '%腿'"
                    " OR i.name LIKE '%翅' OR i.name LIKE '%爪' OR i.name LIKE '%叶'"
                    " OR i.name LIKE '%张' OR i.name LIKE '%串' OR i.name LIKE '%卷')"
                    " ORDER BY i.name"
                )).fetchall()
                if orphans:
                    lines = [f"  - id={row[0]}, name={row[1]}" for row in orphans]
                    initial_prompt += (
                        "\n\n# ⚠️ 强制任务：以下原料缺少 piece_weight，必须全部估值\n"
                        "这些原料未出现在上述查询 1/2 中，但名称明确指示它们是计数型食材"
                        "（个/只/条/根/腿/翅等），必须在本次会话中为**每一条**输出 UPDATE：\n"
                        + "\n".join(lines)
                        + "\n\n**不得跳过任何一条。每条都必须出现在 UPDATE 的 WHERE id IN (...) 中。**\n"
                    )
            finally:
                sdb.close()
        except Exception:
            logger.warning("预查询兜底原料失败，使用模板默认提示", exc_info=True)

    if body.force:
        # 按任务类型生成具体的 SQL 修改规则（prepend 在模板之前，比 append 醒目）。
        _force_rules: dict[str, str] = {
            "fill_piece_weight": (
                "【补单位质量 · 必须修改】\n"
                "- 摸底：不移除 `weight_per_unit IS NULL OR = 100` 条件（仍以脏数据为目标）\n"
                "- UPDATE：移除 `AND weight_per_unit = <原值>` 守卫——对所有行重新估值\n"
            ),
            "infer_quantities": (
                "【推测模糊量 · 必须修改】\n"
                "- 摸底：移除 `AND (i.piece_weight IS NULL OR i.piece_weight = 100)`\n"
                "- 摸底：移除 `(ri.quantity IS NULL AND ri.quantity_range IS NULL)` 筛选\n"
                "- UPDATE：移除 `AND (piece_weight IS NULL OR piece_weight = 100)` 守卫\n"
                "- UPDATE：移除 `AND (quantity_range IS NULL OR json_extract(...))` 守卫\n"
                "- 复核：移除 `AND ri.ai_inferred = 0`\n"
            ),
            "infer_densities": (
                "【推断密度 · 必须修改】\n"
                "- 摸底：移除 `AND ed.id IS NULL` 条件——查询全部原料\n"
                "- 已有密度记录的用 UPDATE（不能用 INSERT，WHERE NOT EXISTS 会阻止）：\n"
                "  ```sql\n"
                "  UPDATE entity_densities SET density = <新值>,\n"
                "    source = 'agent', updated_at = datetime('now')\n"
                "  WHERE entity_type = 'ingredient' AND entity_id = <id>\n"
                "    AND condition IS NULL;\n"
                "  ```\n"
                "- 无密度记录的仍用 INSERT（带 WHERE NOT EXISTS 守卫）\n"
            ),
            "usda_translate": (
                "【USDA 食材翻译 · 必须修改】\n"
                "- 模板 SQL 中的 `WHERE translate_status = 'pending'` 条件保留\n"
                "  （强制模式下已重置状态为 pending）\n"
                "- 对已有译文的也要重新翻译\n"
            ),
            "unmapped_nutrient_translate": (
                "【营养素翻译 · 必须修改】\n"
                "- 模板 SQL 中的 `WHERE name_zh IS NULL` 条件保留\n"
                "  （强制模式下已清空译文）\n"
                "- 对已有译文的也要重新翻译\n"
            ),
        }
        rules = _force_rules.get(body.task_type, "- 移除摸底/UPDATE 中所有 `IS NULL`、`= 'pending'` 等守卫条件\n")
        initial_prompt = (
            "# ⚠️ 强制重推模式 — SQL 修改规则\n\n"
            "本次为**强制重推**。请对**所有**符合条件的条目（包括已处理过的）"
            "重新推理并输出修正 SQL。已有值的条目也要重新估值。\n\n"
            + rules
            + "\n即：只保留 `WHERE id IN (...)` 定位目标行，"
            "移除所有「原值为空/已处理」的守卫条件。\n\n"
            + initial_prompt
        )
    title = tpl["title"]
    sess = AgentSession(
        task_type=body.task_type,
        title=title,
        status="pending",
        runner_type=body.provider,
        initial_prompt=initial_prompt,
        user_id=current_user.id,
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    session_id = sess.id

    # 捕获主事件循环（async 端点运行在主 loop），传给后台线程跨线程推送。
    main_loop = asyncio.get_running_loop()
    db_url = _settings_db_url()
    settings = _settings()

    def _launch() -> None:
        try:
            runner = runner_factory.build_runner(
                body.task_type, db_url, provider=body.provider,
                idle_timeout=settings.agent_idle_timeout,
                total_timeout=settings.agent_total_timeout,
            )
            session_runner.run_agent_loop(
                session_id,
                runner,
                initial_prompt,
                main_loop,
                db_session_factory=SessionLocal,
                approval_timeout=settings.agent_approval_timeout,
                safe_row_threshold=50000,
            )
        except Exception:  # noqa: BLE001 - 后台线程异常兜底
            logger.exception("agent 后台线程异常 session_id=%s", session_id)
            # 兜底置 failed（run_agent_loop 自身异常已会置 failed，此处防 build_runner 失败等）。
            try:
                sdb = SessionLocal()
                try:
                    s = sdb.query(AgentSession).get(session_id)
                    if s is not None and s.status not in ("success", "failed"):
                        s.status = "failed"
                        s.error = "后台线程启动失败（见日志）"
                        sdb.commit()
                finally:
                    sdb.close()
            except Exception:  # noqa: BLE001
                logger.exception("兜底置 failed 失败")

    threading.Thread(target=_launch, daemon=True).start()

    return {"session_id": session_id, "status": sess.status}


@router.get("/sessions")
def list_sessions(
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """列会话。管理员看全部；普通用户只看自己的。"""
    query = db.query(AgentSession)
    if not getattr(current_user, "is_admin", False):
        query = query.filter(AgentSession.user_id == current_user.id)
    sessions = query.order_by(AgentSession.id.desc()).limit(limit).all()
    return [_session_to_out(s).model_dump(mode="json") for s in sessions]


@router.get("/sessions/{sid}")
def get_session(
    sid: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """会话详情：session + messages + pending_approvals。"""
    sess = _get_session_or_404(db, sid, current_user)
    messages = (
        db.query(AgentMessage)
        .filter(AgentMessage.session_id == sid)
        .order_by(AgentMessage.seq.asc())
        .all()
    )
    pending = (
        db.query(AgentApproval)
        .filter(AgentApproval.session_id == sid, AgentApproval.status == "pending")
        .order_by(AgentApproval.id.asc())
        .all()
    )
    detail = SessionDetailOut(
        session=_session_to_out(sess),
        messages=[_message_to_out(m) for m in messages],
        pending_approvals=[_approval_to_out(a) for a in pending],
    )
    return detail.model_dump(mode="json")


@router.get("/sessions/{sid}/stream")
async def stream_session(
    sid: int,
    request: Request,
    token: "Optional[str]" = Query(
        default=None,
        description="JWT access token；浏览器原生 EventSource 无法带 Authorization "
        "header，故用 query 参数。生产建议使用短时效 token 或改用 "
        "fetch + ReadableStream，避免 query token 进入 access log 泄漏。",
    ),
    db: Session = Depends(get_db),
):
    """SSE 流：1) **先 subscribe 实时 queue**（C1：防止回放期间实时事件被丢）；
    2) 回放历史 AgentMessage（按 seq）；3) 从 queue 消费实时事件，对带 ``seq``
    的 tool_use/tool_result 事件按 ``seq <= max_seq_seen`` 去重（重连/历史回放
    已发过的不再重复）；4) 终态兜底（B-5）：周期查 session.status，终态发
    synthesized done 关流。

    鉴权（C2）：浏览器原生 ``EventSource`` 无法设自定义 header，故本端点改用
    **query token**：``?token=<jwt>``。``_auth_user_from_token`` 复用
    ``resolve_user_from_token``（与 HTTPBearer 同一套校验逻辑）。
    其它写端点仍用 header 鉴权（axios/fetch 能带 header）。

    心跳（I1）：queue 空超时分支每 ~15s 发一行 SSE 注释 ``: ping\\n\\n``（浏览器
    忽略，仅保活 TCP），防 nginx/CDN 超时断连。
    """
    # C2：query token 鉴权。
    current_user = _auth_user_from_token(token, db)
    sess = _get_session_or_404(db, sid, current_user)

    # 已终态：回放历史 + synthesized done。
    # 仍 running/awaiting_approval：回放历史 + 续实时 queue。
    is_terminal = sess.status in ("success", "failed", "cancelled")

    async def event_gen() -> AsyncGenerator[bytes, None]:
        q: "Optional[Any]" = None
        max_seq_seen = 0
        try:
            if not is_terminal:
                # C1：**先 subscribe**，确保回放期间产生的事件进入 queue，不丢。
                q = await stream_bridge.subscribe(sid)

            # 1) 回放历史 AgentMessage（按 seq）。
            db_replay = SessionLocal()
            try:
                history = (
                    db_replay.query(AgentMessage)
                    .filter(AgentMessage.session_id == sid)
                    .order_by(AgentMessage.seq.asc())
                    .all()
                )
                for m in history:
                    payload = {
                        "kind": "history",
                        "role": m.role,
                        "seq": m.seq,
                        "content": m.content,
                        "tool_name": m.tool_name,
                        "tool_use_id": m.tool_use_id,
                        "tool_input": m.tool_input,
                        "tool_result": m.tool_result,
                    }
                    yield _format_sse(payload)
                    if m.seq is not None and m.seq > max_seq_seen:
                        max_seq_seen = m.seq
                    if await _client_disconnected(request):
                        return
            finally:
                db_replay.close()

            # 已终态：发 synthesized done 后关流。
            if is_terminal:
                yield _format_sse(
                    {
                        "kind": "done",
                        "synthesized": True,
                        "status": sess.status,
                    }
                )
                return

            # synthesized marker：历史回放结束、转入实时。
            yield _format_sse({"kind": "history_end", "status": sess.status})

            tick = 0
            idle_ticks = 0  # 连续空超时计数，用于心跳（I1）。
            terminal_status: "Optional[str]" = None
            while True:
                if await _client_disconnected(request):
                    return
                try:
                    evt = await asyncio.wait_for(q.get(), timeout=1.0)
                    idle_ticks = 0
                except asyncio.TimeoutError:
                    idle_ticks += 1
                    # I1：每 ~15s（15 次空超时）发心跳注释行保活。
                    if idle_ticks % 15 == 0:
                        yield _HEARTBEAT_SSE
                    # 周期性查 session.status，终态兜底。
                    tick += 1
                    if tick % 2 == 0:
                        tstatus = _peek_session_status(sid)
                        if tstatus in ("success", "failed", "cancelled"):
                            terminal_status = tstatus
                            break
                    continue
                evt_kind = evt.get("kind") if isinstance(evt, dict) else None
                # C1：tool_use/tool_result 带 seq，重连后去重——回放已发过的跳过。
                if evt_kind in ("tool_use", "tool_result"):
                    eseq = evt.get("seq")
                    if isinstance(eseq, int) and eseq <= max_seq_seen:
                        continue
                    if isinstance(eseq, int) and eseq > max_seq_seen:
                        max_seq_seen = eseq
                yield _format_sse(evt)
                # done / error 终态事件：关流。
                if evt_kind in ("done", "error"):
                    return

            # 终态兜底（B-5）：发 synthesized done。
            if terminal_status is not None:
                yield _format_sse(
                    {
                        "kind": "done",
                        "synthesized": True,
                        "status": terminal_status,
                    }
                )
        finally:
            if q is not None:
                try:
                    await stream_bridge.unsubscribe(sid, q)
                except Exception:  # noqa: BLE001
                    logger.exception("unsubscribe failed sid=%s", sid)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # nginx 关缓冲
            "Connection": "keep-alive",
        },
    )


@router.post("/sessions/{sid}/messages")
async def post_message(
    sid: int,
    body: PostMessageIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """插话：在已终态会话上起 resume 新轮。

    - 仅管理员。
    - session.status 必须是终态（success/failed/cancelled）；运行中 → 409。
    - 用 claude_session_id 作 resume_session_id，body.text 作下一轮 user prompt。
    """
    _require_admin(current_user)
    sess = _get_session_or_404(db, sid, current_user)

    if sess.status not in ("success", "failed", "cancelled"):
        raise HTTPException(
            status_code=409,
            detail="会话仍在运行，无法插话（请在轮次结束后再追加）",
        )

    if not sess.claude_session_id:
        raise HTTPException(
            status_code=409,
            detail="会话缺少 claude_session_id，无法 resume",
        )

    main_loop = asyncio.get_running_loop()
    db_url = _settings_db_url()
    settings = _settings()
    resume_sid = sess.claude_session_id
    user_text = body.text
    task_type = sess.task_type or "followup"
    # 复用原 session 的 runner_type 作为 provider（与 create_session 对齐）。
    # 历史数据可能 runner_type 为 NULL，回退默认 claude_code。
    provider = sess.runner_type or "claude_code"

    def _launch() -> None:
        try:
            runner = runner_factory.build_runner(
                task_type, db_url, provider=provider,
                idle_timeout=settings.agent_idle_timeout,
                total_timeout=settings.agent_total_timeout,
            )
            session_runner.run_agent_loop(
                sid,
                runner,
                user_text,
                main_loop,
                db_session_factory=SessionLocal,
                resume_session_id=resume_sid,
                approval_timeout=settings.agent_approval_timeout,
                safe_row_threshold=50000,
            )
        except Exception:  # noqa: BLE001
            logger.exception("agent 插话线程异常 session_id=%s", sid)
            try:
                sdb = SessionLocal()
                try:
                    s = sdb.query(AgentSession).get(sid)
                    if s is not None and s.status not in ("success", "failed"):
                        s.status = "failed"
                        s.error = "插话后台线程启动失败（见日志）"
                        sdb.commit()
                finally:
                    sdb.close()
            except Exception:  # noqa: BLE001
                logger.exception("兜底置 failed 失败")

    threading.Thread(target=_launch, daemon=True).start()

    return {"session_id": sid, "resumed": True}


@router.post("/sessions/{sid}/cancel")
async def cancel_agent_session(
    sid: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """取消正在运行的 Agent 会话（仅管理员）。

    - 只有 pending / running / awaiting_approval 状态可取消。
    - 会终止正在运行的 Claude Code CLI 子进程。
    - 取消后会话保留在列表上，status 变为 cancelled。
    """
    _require_admin(current_user)
    sess = _get_session_or_404(db, sid, current_user)

    if sess.status not in ("pending", "running", "awaiting_approval"):
        raise HTTPException(
            status_code=409,
            detail=f"会话状态为 {sess.status}，不可取消",
        )

    ok = cancel_session(sid)
    if not ok:
        raise HTTPException(status_code=500, detail="取消失败")

    return {"status": "cancelled"}


@router.post("/approvals/{aid}")
def decide_approval(
    aid: int,
    body: ApprovalDecisionIn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """审批决策：调 wake_approval。

    wake_approval 返回 False（审批不存在/已决策）→ 404。
    """
    _require_admin(current_user)

    # 先校验存在性，给出更友好的错误。
    ap = db.query(AgentApproval).get(aid)
    if ap is None:
        raise HTTPException(status_code=404, detail="审批记录不存在")
    if ap.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"审批已决策（status={ap.status}），不能重复操作",
        )

    ok = session_runner.wake_approval(aid, body.approved, current_user.id)
    if not ok:
        # 竞态：被并发决策了。
        raise HTTPException(
            status_code=409,
            detail="审批已被处理或无阻塞 loop",
        )
    return {"ok": True, "approved": body.approved}


# --------------------------------------------------------------------------- #
# 内部辅助
# --------------------------------------------------------------------------- #
# I1：SSE 心跳注释行（浏览器忽略，仅保活 TCP）。每次空超时 ~1s，15 次 ~15s 发一次。
_HEARTBEAT_SSE = b": ping\n\n"


def _auth_user_from_token(token: "Optional[str]", db: Session):
    """C2：用 query token 鉴权拿 User（复用 ``resolve_user_from_token``）。

    浏览器原生 ``EventSource`` 无法设 ``Authorization`` header，故 SSE 端点改用
    query token。此函数把 query token 交给与 HTTPBearer 同源的校验逻辑
    （``resolve_user_from_token``），失败（空/无效/非 access/用户不存在）→ 抛
    401/404。

    Args:
        token: query 参数 ``token`` 的值（可能为 None）。
        db: 未使用（保留入参一致性；``resolve_user_from_token`` 内部自取 db）。

    Returns:
        User 对象。

    Raises:
        HTTPException: 401 / 404。
    """
    del db  # resolve_user_from_token 内部自取 db。
    return resolve_user_from_token(token)


def _settings_db_url() -> str:
    from app.config import settings

    return settings.database_url


def _settings():
    from app.config import get_settings

    return get_settings()


def _get_session_or_404(db: Session, sid: int, current_user) -> AgentSession:
    sess = db.query(AgentSession).get(sid)
    if sess is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    # 管理员看全部；普通用户只看自己的。
    if not getattr(current_user, "is_admin", False) and sess.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    return sess


def _session_to_out(s: AgentSession) -> AgentSessionOut:
    cost = float(s.cost_usd) if s.cost_usd is not None else None
    return AgentSessionOut(
        id=s.id,
        task_type=s.task_type,
        title=s.title,
        status=s.status,
        runner_type=s.runner_type,
        user_id=s.user_id,
        claude_session_id=s.claude_session_id,
        cost_usd=cost,
        error=s.error,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _message_to_out(m: AgentMessage) -> AgentMessageOut:
    return AgentMessageOut(
        id=m.id,
        session_id=m.session_id,
        seq=m.seq,
        role=m.role,
        content=m.content,
        tool_name=m.tool_name,
        tool_use_id=m.tool_use_id,
        tool_input=m.tool_input,
        tool_result=m.tool_result,
        created_at=m.created_at,
    )


def _approval_to_out(a: AgentApproval) -> AgentApprovalOut:
    return AgentApprovalOut(
        id=a.id,
        session_id=a.session_id,
        sql=a.sql,
        danger_reason=a.danger_reason,
        affected_estimate=a.affected_estimate,
        status=a.status,
        decided_by=a.decided_by,
        decided_at=a.decided_at,
        created_at=a.created_at,
    )


def _peek_session_status(sid: int) -> "Optional[str]":
    """查 session.status（独立 Session，避免干扰请求 db）。"""
    sdb = SessionLocal()
    try:
        s = sdb.query(AgentSession).get(sid)
        return s.status if s is not None else None
    finally:
        sdb.close()


async def _client_disconnected(request: Request) -> bool:
    """检测客户端是否断开连接。"""
    try:
        disconnected = await request.is_disconnected()
    except Exception:  # noqa: BLE001
        return False
    return disconnected


def _format_sse(payload: Any) -> bytes:
    """格式化一条 SSE 事件（``event: message\\ndata: {json}\\n\\n``）。"""
    data = json.dumps(payload, ensure_ascii=False, default=_json_default)
    return f"event: message\ndata: {data}\n\n".encode("utf-8")


def _json_default(o: Any) -> Any:
    """json.dumps 默认序列化器：处理 datetime / Decimal。"""
    if isinstance(o, datetime):
        return o.isoformat()
    try:
        return float(o)
    except (TypeError, ValueError):
        return str(o)
