# backend/app/services/translate/task.py
"""USDA 食材翻译任务（Task 7 引擎替换）。

老路径改造的第一项：把「分批串行 ``translate_batch``」替换为
「``LangChainRunner`` + ``run_agent_loop(unattended=True)``」——Agent 自主
「查 pending 食材 → 翻译 → 写 ````sql```` UPDATE → 复核」，sql_guard 自动执行
safe SQL（写回 ``usda_foods.description_zh`` + ``translate_status='done'``）。

两条记录并存：
- ``UsdaTask(task_type='translate')``：USDA 维护页任务轮询用（前端已有）。
- ``AgentSession(task_type='usda_translate', title='[后台] ...')``：复用
  ``run_agent_loop`` 全套（事件聚合 + SQL 提取/执行 + SSE），对话可在任务台
  回看（前端靠 title ``[后台]`` 前缀区分，暂不特殊过滤）。

async/同步桥接：``TranslateTask.run`` 保持 ``async``（调用方 ``usda_admin`` 在
async BackgroundTask 里 ``await`` 它）；内部用 ``asyncio.to_thread`` 把同步的
``run_agent_loop``（设计为后台线程入口）放工作线程跑，不阻塞 event loop。
"""
import asyncio
import logging
import threading

from sqlalchemy.orm import Session

from app.config import settings
from app.models.agent_session import AgentSession
from app.models.usda import UsdaFood, UsdaTask
from app.services.agent import runner_factory, session_runner
from app.services.agent.task_templates import get_template

logger = logging.getLogger(__name__)

# USDA 食材翻译对应的 task_template 键（见 services/agent/task_templates.py）。
_TASK_TYPE = "usda_translate"


class TranslateTask:
    """USDA 食材翻译任务。

    Args:
        db: SQLAlchemy Session（调用方负责生命周期；用于建 UsdaTask /
            AgentSession 与统计）。
    """

    def __init__(self, db: Session):
        self.db = db

    async def run(
        self,
        provider: str,
        config_dict: dict,
        batch_size: int = 50,
        cancel_event: "threading.Event | None" = None,
        force: bool = False,
    ) -> dict:
        """跑 USDA 食材翻译（Agent 自主批量）。

        Args:
            provider: ``"openai"`` / ``"anthropic"`` / ``"claude_code"``。
            config_dict: 翻译配置（保留向后兼容，当前 Agent 路径由
                ``runner_factory`` 自行从 ``TranslationConfig`` 读取）。
            batch_size: 保留入参兼容，Agent 路径下由 prompt 内「每批 50 条」约定。
            cancel_event: 保留入参兼容（Agent 路径下 dangerous SQL 自动跳过，
                unattended 模式不阻塞）。
            force: 强制重翻——先把 done/error 重置 pending，prompt 加强制前缀。

        Returns:
            ``{"translated": int, "total": int}``：total 为本次待翻译条数
            （force 时为全表非 pending 外的条数，否则为 pending 条数）；
            translated 为 Agent 执行后 done 行的净增量。
        """
        del config_dict  # Agent 路径由 runner_factory 自取 TranslationConfig

        # 1. UsdaTask 进度载体（前端 USDA 维护页已有轮询逻辑）。
        usda_task = UsdaTask(task_type="translate", status="running", provider=provider)
        self.db.add(usda_task)
        self.db.commit()
        self.db.refresh(usda_task)

        # 2. force 重翻：把 done/error 重置 pending（保留老 force 语义）。
        if force:
            self.db.query(UsdaFood).filter(
                UsdaFood.translate_status.in_(["done", "error"]),
            ).update({UsdaFood.translate_status: "pending"}, synchronize_session=False)
            self.db.commit()

        total = (
            self.db.query(UsdaFood)
            .filter(UsdaFood.translate_status == "pending")
            .count()
        )
        # 翻译前 done 行数，用于算净增量。
        done_before = (
            self.db.query(UsdaFood).filter(UsdaFood.translate_status == "done").count()
        )

        usda_task.progress = {"done": 0, "total": total}
        self.db.commit()

        # 3. 渲染 usda_translate 模板 prompt + force 前缀。
        tpl = get_template(_TASK_TYPE)
        initial_prompt = tpl["prompt"]
        if force:
            initial_prompt = (
                "# 强制重翻\n"
                "本次为强制重翻所有条目（含已 done/error）。"
                "忽略已有译文，对所有 `usda_foods` 行重新翻译并输出 UPDATE。\n\n"
                + initial_prompt
            )

        # 4. 建 [后台] AgentSession（拿真实 session_id 传给 run_agent_loop，
        #    复用全套事件聚合 + SQL 提取/执行 + SSE）。
        sess = AgentSession(
            task_type=_TASK_TYPE,
            title=f"[后台] {tpl['title']}",
            status="pending",
            runner_type=provider,
            initial_prompt=initial_prompt,
            user_id=None,
        )
        self.db.add(sess)
        self.db.commit()
        self.db.refresh(sess)
        session_id = sess.id

        # 4b. cancel_event → cancel_session 桥接：外部取消 ImportTask 时真正停掉 Agent。
        if cancel_event is not None:

            def _watch_cancel(_sid: int = session_id) -> None:
                cancel_event.wait()
                from app.services.agent.session_runner import cancel_session

                cancel_session(_sid)

            threading.Thread(target=_watch_cancel, daemon=True).start()

        # 5. 构造 Runner + 后台跑 run_agent_loop（unattended：dangerous 自动跳过）。
        db_url = settings.database_url
        main_loop = asyncio.get_running_loop()

        def _run_in_thread() -> None:
            try:
                runner = runner_factory.build_runner(
                    _TASK_TYPE, db_url, provider=provider
                )
                session_runner.run_agent_loop(
                    session_id,
                    runner,
                    initial_prompt,
                    main_loop,
                    db_session_factory=session_runner_db_factory(),
                    unattended=True,
                )
            except Exception:  # noqa: BLE001
                logger.exception(
                    "TranslateTask run_agent_loop 异常 session=%s", session_id
                )
                _mark_session_failed(session_id)

        # 桥接：run_agent_loop 是同步线程入口，放工作线程不阻塞 event loop。
        await asyncio.to_thread(_run_in_thread)

        # 6. 统计净增量 + 更新 UsdaTask 进度。
        self.db.expire_all()
        done_after = (
            self.db.query(UsdaFood).filter(UsdaFood.translate_status == "done").count()
        )
        translated = max(done_after - done_before, 0)

        usda_task = self.db.query(UsdaTask).get(usda_task.id)
        if usda_task is not None:
            usda_task.status = "success"
            usda_task.progress = {"done": translated, "total": total}
            self.db.commit()

        return {"translated": translated, "total": total, "agent_session_id": session_id}


def session_runner_db_factory():
    """返回 run_agent_loop 的 db_session_factory（懒求值 SessionLocal）。

    封一层函数避免在模块加载期强绑定 ``app.core.database.SessionLocal``——
    便于测试 monkeypatch 替换内存库（monkeypatch 生效在 run 调用时）。
    """
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
            s.error = "TranslateTask 后台线程启动失败（见日志）"
            db.commit()
    except Exception:  # noqa: BLE001
        logger.exception("兜底置 failed 失败 session=%s", session_id)
    finally:
        db.close()
