"""导入 API 路由。"""
import os
import threading

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.core.security import get_current_user
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
    content = file.read()
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
                import_db, file_path, current_user_id,
                is_admin,
                progress_callback=progress_callback,
            )
        finally:
            import_db.close()

    task_id = start_background_import(
        db, "upload_import", current_user.id, _do_import,
    )
    return {"task_id": task_id}


@router.post("/data/import-from-repo")
def trigger_repo_import(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """手动触发从 git 仓库导入（仅管理员）。"""
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(403, detail="仅管理员可操作")

    task_id = start_background_import(
        db, "git_import", current_user.id,
        import_from_git_repo, db, current_user.id,
    )
    return {"task_id": task_id}


@router.post("/data/import-from-local")
def trigger_local_import(
    local_path: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """从本地目录导入（仅管理员）。"""
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(403, detail="仅管理员可操作")

    if not os.path.isdir(local_path):
        raise HTTPException(400, detail=f"目录不存在: {local_path}")

    task_id = start_background_import(
        db, "local_import", current_user.id,
        import_from_local_dir, db, local_path, current_user.id,
    )
    return {"task_id": task_id}


# ---- 任务状态查询 ----

@router.get("/task/{task_id}")
def get_task_status(
    task_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """查询导入任务状态。"""
    task = db.query(ImportTask).filter(
        ImportTask.id == task_id,
        ImportTask.user_id == current_user.id,
    ).first()
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
        from app.services.translate.registry import get_translator, find_provider_section
        prov_cfg = find_provider_section(config_dict, provider)
        if not prov_cfg:
            return None

        import asyncio
        translator = get_translator(provider, prov_cfg, timeout=120)

        def _call(prompt: str) -> str:
            """同步调用 translator 的 translate_batch。"""
            result_list = asyncio.run(
                translator.translate_batch([prompt])
            )
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


def _run_ai_inference(task_id: int, inference_type: str, force: bool,
                       provider: str, db_session_factory):
    """后台运行 AI 推测。"""
    db = db_session_factory()
    try:
        task = db.query(ImportTask).get(task_id)
        if not task:
            return
        task.status = "running"
        task.progress = {"stage": "初始化", "current": 0, "total": 0, "message": "准备 AI 推测..."}
        db.commit()

        ai_caller = _create_ai_caller(provider, db)
        inferrer = AIInferrer(db)
        if ai_caller:
            inferrer.set_ai_caller(ai_caller)

        def progress_callback(stage: str, current: int, total: int, message: str = ""):
            try:
                t = db.query(ImportTask).get(task_id)
                if t:
                    t.progress = {"stage": stage, "current": current, "total": total, "message": message}
                    db.commit()
            except Exception:
                pass

        if inference_type == "quantities":
            result = inferrer.infer_fuzzy_quantities(force=force, progress_callback=progress_callback)
        elif inference_type == "densities":
            result = inferrer.infer_densities(force=force, progress_callback=progress_callback)
        else:
            raise ValueError(f"Unknown inference type: {inference_type}")

        task = db.query(ImportTask).get(task_id)
        if task:
            task.status = "success"
            task.progress = {"stage": "完成", "current": 1, "total": 1, "message": "推测完成"}
            task.stats = result.stats if hasattr(result, 'stats') else {}
            if hasattr(result, 'errors') and result.errors:
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
def infer_fuzzy_quantities(
    force: bool = False,
    provider: str = Query("claude_code", description="AI 提供方名称"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """触发模糊量推测。

    需要先在 AI 配置页启用至少一个 AI 后端。
    通过 provider 参数指定使用的 AI 提供方。
    """
    task = ImportTask(task_type="ai_quantities", status="pending", user_id=current_user.id)
    db.add(task)
    db.commit()
    db.refresh(task)

    thread = threading.Thread(
        target=_run_ai_inference,
        args=(task.id, "quantities", force, provider, SessionLocal),
        daemon=True,
    )
    thread.start()

    return {"task_id": task.id}


@router.post("/ai-infer/densities")
def infer_densities(
    force: bool = False,
    provider: str = Query("claude_code", description="AI 提供方名称"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """触发密度推测。

    需要先在 AI 配置页启用至少一个 AI 后端。
    通过 provider 参数指定使用的 AI 提供方。
    """
    task = ImportTask(task_type="ai_densities", status="pending", user_id=current_user.id)
    db.add(task)
    db.commit()
    db.refresh(task)

    thread = threading.Thread(
        target=_run_ai_inference,
        args=(task.id, "densities", force, provider, SessionLocal),
        daemon=True,
    )
    thread.start()

    return {"task_id": task.id}
