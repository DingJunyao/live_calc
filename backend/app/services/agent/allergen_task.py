"""过敏原分组 AI 匹配任务触发器

自动启动 Agent 搜索数据库中属于某过敏原分组的原料，并写入 allergen_group_ingredients 表。

复用 ``run_agent_loop(unattended=True)``——Agent 自主「查原料 → SQL INSERT → 复核」，
sql_guard 自动执行 safe SQL（写回 ``allergen_group_ingredients.is_ai_matched=true``）。
"""

from __future__ import annotations

import asyncio
import logging
import threading

from sqlalchemy.orm import Session

from app.config import settings
from app.models.agent_session import AgentSession
from app.services.agent import runner_factory, session_runner
from app.services.agent.task_templates import get_template

logger = logging.getLogger("allergen_agent")

_TASK_TYPE = "allergen_match"


def trigger_allergen_match(
    db: Session,
    group_id: int,
    group_name: str,
    admin_id: int,
    main_loop: asyncio.AbstractEventLoop,
) -> int:
    """触发过敏原 AI 匹配任务。

    Args:
        db: SQLAlchemy Session（用于建 AgentSession 记录）。
        group_id: 过敏原分组 ID。
        group_name: 过敏原分组名称。
        admin_id: 操作人 user_id。
        main_loop: 主事件循环（用于跨线程 SSE 推送）。

    Returns:
        agent_session_id
    """
    tpl = get_template(_TASK_TYPE)
    prompt = tpl["prompt"].format(
        group_name=group_name, group_id=group_id, admin_id=admin_id
    )

    # 创建 AgentSession
    sess = AgentSession(
        task_type=_TASK_TYPE,
        title=f"过敏原匹配: {group_name}",
        status="pending",
        runner_type="claude_code",
        initial_prompt=prompt,
        user_id=admin_id,
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    session_id = sess.id

    # 异步启动 Agent 运行（后台线程）
    db_url = settings.database_url

    def _run_in_thread() -> None:
        try:
            runner = runner_factory.build_runner(
                _TASK_TYPE,
                db_url,
                provider="claude_code",
                idle_timeout=settings.agent_idle_timeout,
                total_timeout=settings.agent_total_timeout,
            )
            session_runner.run_agent_loop(
                session_id,
                runner,
                prompt,
                main_loop,
                db_session_factory=_get_session_factory(),
                unattended=True,
                safe_row_threshold=50000,
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "过敏原匹配 Agent 异常 session=%s", session_id
            )
            _mark_session_failed(session_id)

    threading.Thread(target=_run_in_thread, daemon=True).start()

    return session_id


def _get_session_factory():
    """返回 run_agent_loop 的 db_session_factory（懒求值 SessionLocal）。"""
    from app.core.database import SessionLocal

    return SessionLocal


def _mark_session_failed(session_id: int) -> None:
    """后台线程异常兜底：把 AgentSession 置 failed。"""
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        s = db.query(AgentSession).get(session_id)
        if s is not None and s.status not in ("success", "failed"):
            s.status = "failed"
            s.error = "allergen_match 后台线程启动失败（见日志）"
            db.commit()
    except Exception:  # noqa: BLE001
        logger.exception("兜底置 failed 失败 session=%s", session_id)
    finally:
        db.close()
