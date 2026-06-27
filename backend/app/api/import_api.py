"""导入 API 路由。"""

import asyncio
import os
import threading

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.core.database import get_db, SessionLocal
from app.core.security import get_current_admin_user, get_current_user
from app.models.import_task import ImportTask
from app.models.usda import TranslationConfig
from app.services.importer.api_service import (
    import_from_git_repo,
    import_from_local_dir,
    import_from_upload_path,
    start_background_import,
)
from app.services.importer.ai_inference.inferrer import AIInferrer

router = APIRouter()


# ---- 数据导入端点 ----


@router.post("/data/upload")
def upload_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """上传压缩包导入数据。

    管理员可上传 HowToCook_json 格式和系统导出格式。
    普通用户仅可上传系统导出格式。
    """
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(400, detail="仅支持 ZIP 格式的压缩包")

    # 保存上传文件到临时路径
    import tempfile as _tmpfile

    suffix = os.path.splitext(file.filename or "upload.zip")[1] or ".zip"
    tmp = _tmpfile.NamedTemporaryFile(delete=False, suffix=suffix)
    content = file.file.read()
    tmp.write(content)
    tmp.close()

    current_user_id = current_user.id
    is_admin = getattr(current_user, "is_admin", False)
    file_path = tmp.name

    # 使用闭包包装导入函数，在后台线程中用独立会话执行
    def _do_import(progress_callback=None):
        from app.core.database import SessionLocal as _SessionLocal

        import_db = _SessionLocal()
        try:
            return import_from_upload_path(
                import_db,
                file_path,
                current_user_id,
                is_admin,
                progress_callback=progress_callback,
            )
        finally:
            import_db.close()

    task_id = start_background_import(
        db,
        "upload_import",
        current_user.id,
        _do_import,
    )
    return {"task_id": task_id}


@router.post("/data/import-from-repo")
def trigger_repo_import(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin_user),
):
    """手动触发从 git 仓库导入（仅管理员）。"""
    task_id = start_background_import(
        db,
        "git_import",
        current_user.id,
        import_from_git_repo,
        db,
        current_user.id,
    )
    return {"task_id": task_id}


@router.post("/data/import-from-local")
def trigger_local_import(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin_user),
):
    """从本地目录导入（仅管理员）。

    导入目录取自 .env 的 DATA_LOCAL_PATH（settings.data_local_path），
    与启动时的首次初始化导入共用同一来源，不在页面上手填。
    """
    local_path = settings.data_local_path
    if not local_path:
        raise HTTPException(
            400,
            detail="未在 .env 配置 DATA_LOCAL_PATH，请在 backend/.env 设置",
        )
    if not os.path.isdir(local_path):
        raise HTTPException(400, detail=f"目录不存在: {local_path}")

    task_id = start_background_import(
        db,
        "local_import",
        current_user.id,
        import_from_local_dir,
        db,
        local_path,
        current_user.id,
    )
    return {"task_id": task_id}


@router.get("/data/local-path-config")
def get_local_path_config(
    current_user=Depends(get_current_admin_user),
):
    """返回 .env 中 DATA_LOCAL_PATH 的配置情况（仅管理员）。

    供前端只读展示当前会导入哪个目录，不在此处校验目录是否存在
    （目录存在性校验交给导入端点负责）。
    """
    path = settings.data_local_path
    return {"configured": bool(path), "path": path}


# ---- 任务状态查询 ----


@router.get("/task/{task_id}")
def get_task_status(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """查询导入任务状态。"""
    task = (
        db.query(ImportTask)
        .filter(
            ImportTask.id == task_id,
            ImportTask.user_id == current_user.id,
        )
        .first()
    )
    if not task:
        # 管理员可以查看所有任务
        if getattr(current_user, "is_admin", False):
            task = db.query(ImportTask).get(task_id)
        if not task:
            raise HTTPException(404, detail="任务不存在")
    return task.to_dict()


@router.get("/tasks")
def list_tasks(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取最近的导入任务列表（用于页面刷新恢复）。"""
    query = db.query(ImportTask)

    if not getattr(current_user, "is_admin", False):
        query = query.filter(ImportTask.user_id == current_user.id)

    tasks = query.order_by(ImportTask.id.desc()).limit(limit).all()
    return [t.to_dict() for t in tasks]


@router.post("/task/{task_id}/cancel")
def cancel_import_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """取消正在运行的导入/AI 推测任务。

    - 只有 pending / running 状态可取消。
    - 取消后任务保留在列表上，status 变为 cancelled。
    - 实际的后台线程会继续运行（daemon thread），但状态已标记。
    """
    task = db.query(ImportTask).filter(ImportTask.id == task_id).first()
    if not task:
        raise HTTPException(404, detail="任务不存在")

    if task.status not in ("pending", "running"):
        raise HTTPException(
            status_code=409,
            detail=f"任务状态为 {task.status}，不可取消",
        )

    # 如果该 ImportTask 关联了 Agent 会话，一并取消 Agent（推测模糊量/密度/翻译等）。
    if task.stats and task.stats.get("agent_session_id"):
        from app.services.agent.session_runner import cancel_session

        cancel_session(task.stats["agent_session_id"])

    task.status = "cancelled"
    db.commit()
    return {"status": "cancelled"}


# ---- AI 后处理端点 ----


def _create_ai_caller(provider: str, db: Session):
    """根据 provider 名称创建 AI 调用函数。

    从 TranslationConfig 中读取该 provider 的配置并构造 Translator，
    返回一个同步的 callable(prompt: str) -> str。
    如果 provider 不可用则返回 None。
    """
    try:
        cfg_record = db.query(TranslationConfig).first()
        if not cfg_record:
            return None
        config_dict = cfg_record.to_dict()

        # 在 ai 和 machine 两区中查找 provider 配置
        from app.services.translate.registry import (
            get_translator,
            find_provider_section,
        )

        prov_cfg = find_provider_section(config_dict, provider)
        if not prov_cfg:
            return None

        import asyncio

        translator = get_translator(provider, prov_cfg, timeout=120)

        def _call(prompt: str) -> str:
            """同步调用 translator 的 translate_batch。"""
            result_list = asyncio.run(translator.translate_batch([prompt]))
            return result_list[0] if result_list else ""

        # 快速健康检查
        try:
            test = _call("回复一个词：ok")
            if not test:
                return None
        except Exception:
            return None

        return _call
    except Exception:
        return None


def _run_ai_inference(
    task_id: int, inference_type: str, force: bool, provider: str, db_session_factory,
    main_loop: "asyncio.AbstractEventLoop | None" = None,
):
    """后台运行 AI 推测。"""
    db = db_session_factory()
    try:
        task = db.query(ImportTask).get(task_id)
        if not task:
            return
        task.status = "running"
        task.progress = {
            "stage": "初始化",
            "current": 0,
            "total": 0,
            "message": "准备 AI 推测...",
        }
        db.commit()

        ai_caller = _create_ai_caller(provider, db)
        inferrer = AIInferrer(db, provider=provider, main_loop=main_loop)
        if ai_caller:
            inferrer.set_ai_caller(ai_caller)

        def progress_callback(
            stage: str,
            current: int,
            total: int,
            message: str = "",
            agent_session_id: "int | None" = None,
        ):
            try:
                t = db.query(ImportTask).get(task_id)
                if t:
                    t.progress = {
                        "stage": stage,
                        "current": current,
                        "total": total,
                        "message": message,
                    }
                    # 即时把 agent_session_id 写进 stats，供前端任务进行中点击跳转任务台对话
                    # （不等任务完成——完成时 task.stats = result.stats 会覆盖，但 result.stats
                    # 也含 agent_session_id，故全程可见）。
                    if agent_session_id is not None:
                        prev = dict(t.stats or {})
                        prev["agent_session_id"] = agent_session_id
                        t.stats = prev
                    db.commit()
            except Exception:
                pass

        if inference_type == "quantities":
            result = inferrer.infer_fuzzy_quantities(
                force=force, progress_callback=progress_callback
            )
        elif inference_type == "densities":
            result = inferrer.infer_densities(
                force=force, progress_callback=progress_callback
            )
        else:
            raise ValueError(f"Unknown inference type: {inference_type}")

        task = db.query(ImportTask).get(task_id)
        if task:
            task.status = "success"
            task.progress = {
                "stage": "完成",
                "current": 1,
                "total": 1,
                "message": "推测完成",
            }
            task.stats = result.stats if hasattr(result, "stats") else {}
            if hasattr(result, "errors") and result.errors:
                task.error = "\n".join(result.errors)
            db.commit()
    except Exception as e:
        try:
            task = db.query(ImportTask).get(task_id)
            if task:
                task.status = "failed"
                task.error = str(e)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.post("/ai-infer/quantities")
async def infer_fuzzy_quantities(
    force: bool = False,
    provider: str = Query("claude_code", description="AI 提供方名称"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """触发模糊量推测。

    需要先在 AI 配置页启用至少一个 AI 后端。
    通过 provider 参数指定使用的 AI 提供方。
    """
    task = ImportTask(
        task_type="ai_quantities", status="pending", user_id=current_user.id
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    main_loop = asyncio.get_running_loop()
    thread = threading.Thread(
        target=_run_ai_inference,
        args=(task.id, "quantities", force, provider, SessionLocal, main_loop),
        daemon=True,
    )
    thread.start()

    return {"task_id": task.id}


@router.post("/ai-infer/densities")
async def infer_densities(
    force: bool = False,
    provider: str = Query("claude_code", description="AI 提供方名称"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """触发密度推测。

    需要先在 AI 配置页启用至少一个 AI 后端。
    通过 provider 参数指定使用的 AI 提供方。
    """
    task = ImportTask(
        task_type="ai_densities", status="pending", user_id=current_user.id
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    main_loop = asyncio.get_running_loop()
    thread = threading.Thread(
        target=_run_ai_inference,
        args=(task.id, "densities", force, provider, SessionLocal, main_loop),
        daemon=True,
    )
    thread.start()

    return {"task_id": task.id}


# ---- USDA 翻译任务（带 ImportTask 跟踪） ----


def _run_translate_task(
    task_id: int,
    translate_type: str,
    provider: str,
    db_session_factory,
    force: bool = False,
):
    """后台运行 USDA 翻译任务（食材名或营养素），带 ImportTask 进度跟踪。

    在独立线程中运行翻译，同时轮询 UsdaTask 进度同步到 ImportTask，
    并在轮询中检查 ImportTask 是否被取消。
    """
    db = db_session_factory()
    try:
        task = db.query(ImportTask).get(task_id)
        if not task:
            return
        if task.status == "cancelled":
            return

        task.status = "running"
        task.progress = {
            "stage": "翻译中",
            "current": 0,
            "total": 0,
            "message": f"使用 {provider} 翻译...",
        }
        db.commit()

        from app.models.usda import TranslationConfig

        cfg_record = db.query(TranslationConfig).first()
        config_dict = cfg_record.to_dict() if cfg_record else {}
        # 在关闭 db 前捕获 task.created_at（之后 task 对象 detached 无法安全访问）。
        _task_created_at = task.created_at
        db.close()  # 关闭当前 db，翻译和轮询用独立 Session

        # 在独立线程中运行翻译，拿到结果。
        result_box: list = [None]
        error_box: list = [None]
        import threading as _threading

        barrier = _threading.Event()
        cancel_event = _threading.Event()

        def _translate_worker():
            """在新 Session 中执行翻译（可被 cancel_event 中断）。"""
            wdb = db_session_factory()
            try:

                async def _do():
                    if translate_type == "foods":
                        from app.services.translate.task import TranslateTask

                        return await TranslateTask(wdb).run(
                            provider=provider,
                            config_dict=config_dict,
                            cancel_event=cancel_event,
                            force=force,
                        )
                    else:
                        from app.services.translate.nutrient_task import (
                            TranslateNutrientsTask,
                        )

                        return await TranslateNutrientsTask(wdb).run(
                            provider=provider,
                            config_dict=config_dict,
                            cancel_event=cancel_event,
                            force=force,
                        )

                r = asyncio.run(_do())
                result_box[0] = r
            except Exception as e:
                error_box[0] = e
            finally:
                wdb.close()
                barrier.set()

        t = _threading.Thread(target=_translate_worker, daemon=True)
        t.start()

        # 主线程：轮询 UsdaTask 进度 + 检查取消 + 即时暴露 agent_session_id
        poll_db = db_session_factory()
        _reported_agent_sid = False
        try:
            while not barrier.is_set():
                cancelled = barrier.wait(timeout=2)
                if cancelled:
                    # 超时未 set，继续轮询
                    pass

                # 同步 UsdaTask 进度 → ImportTask
                try:
                    sync_db = db_session_factory()
                    try:
                        from app.models.usda import UsdaTask

                        ut = (
                            sync_db.query(UsdaTask)
                            .filter(
                                UsdaTask.task_type
                                == (
                                    "translate"
                                    if translate_type == "foods"
                                    else "translate_nutrients"
                                ),
                                UsdaTask.status == "running",
                            )
                            .order_by(UsdaTask.id.desc())
                            .first()
                        )
                        if ut and ut.progress:
                            p = ut.progress
                            done = p.get("done", 0)
                            total = p.get("total", 0) or 1
                            sync_import = sync_db.query(ImportTask).get(task_id)
                            if sync_import:
                                sync_import.progress = {
                                    "stage": "翻译中",
                                    "current": done,
                                    "total": total,
                                    "message": f"Agent 翻译中（{total} 条待处理）",
                                }
                                sync_db.commit()

                        # 即时把 agent_session_id 暴露到 ImportTask.stats（前端任务列表据此跳转任务台）。
                        if not _reported_agent_sid:
                            from app.models.agent_session import AgentSession

                            agent_task_type = (
                                "usda_translate" if translate_type == "foods"
                                else "unmapped_nutrient_translate"
                            )
                            agent_sess = (
                                sync_db.query(AgentSession)
                                .filter(
                                    AgentSession.task_type == agent_task_type,
                                    AgentSession.created_at >= _task_created_at,
                                )
                                .order_by(AgentSession.id.asc())
                                .first()
                            )
                            if agent_sess:
                                sync_import = sync_db.query(ImportTask).get(task_id)
                                if sync_import:
                                    prev = dict(sync_import.stats or {})
                                    prev["agent_session_id"] = agent_sess.id
                                    sync_import.stats = prev
                                    _reported_agent_sid = True
                                    sync_db.commit()
                    finally:
                        sync_db.close()
                except Exception:
                    pass

                # 检查取消：信号翻译线程停止 + 不再更新进度
                try:
                    check_db = db_session_factory()
                    try:
                        check_task = check_db.query(ImportTask).get(task_id)
                        if check_task and check_task.status == "cancelled":
                            cancel_event.set()
                            return
                    finally:
                        check_db.close()
                except Exception:
                    pass

                if barrier.is_set():
                    break
        finally:
            poll_db.close()

        # 翻译完成，更新 ImportTask
        final_db = db_session_factory()
        try:
            final_task = final_db.query(ImportTask).get(task_id)
            if final_task is None:
                return
            if final_task.status == "cancelled":
                return  # 取消优先，不改状态
            if error_box[0] is not None:
                final_task.status = "failed"
                final_task.error = str(error_box[0])
            else:
                final_task.status = "success"
                final_task.progress = {
                    "stage": "完成",
                    "current": 1,
                    "total": 1,
                    "message": "翻译完成",
                }
                final_task.stats = (
                    result_box[0] if isinstance(result_box[0], dict) else {}
                )
            final_db.commit()
        finally:
            final_db.close()
    except Exception as e:
        try:
            exc_db = db_session_factory()
            try:
                exc_task = exc_db.query(ImportTask).get(task_id)
                if exc_task and exc_task.status != "cancelled":
                    exc_task.status = "failed"
                    exc_task.error = str(e)
                    exc_db.commit()
            finally:
                exc_db.close()
        except Exception:
            pass
    finally:
        try:
            db.close()
        except Exception:
            pass


@router.post("/translate/foods")
def translate_foods(
    provider: str = Query("claude_code", description="翻译后端名称"),
    force: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """触发 USDA 食材名翻译（带 ImportTask 跟踪）。"""
    task = ImportTask(
        task_type="usda_translate", status="pending", user_id=current_user.id
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    thread = threading.Thread(
        target=_run_translate_task,
        args=(task.id, "foods", provider, SessionLocal),
        kwargs={"force": force},
        daemon=True,
    )
    thread.start()

    return {"task_id": task.id}


@router.post("/translate/nutrients")
def translate_nutrients(
    provider: str = Query("claude_code", description="AI 翻译后端名称"),
    force: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """触发 USDA 营养素翻译（带 ImportTask 跟踪）。"""
    task = ImportTask(
        task_type="nutrient_translate", status="pending", user_id=current_user.id
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    thread = threading.Thread(
        target=_run_translate_task,
        args=(task.id, "nutrients", provider, SessionLocal),
        kwargs={"force": force},
        daemon=True,
    )
    thread.start()

    return {"task_id": task.id}
