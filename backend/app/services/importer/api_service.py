"""导入 API 编排服务——协调输入源、格式检测、导入器和 AI 后处理。"""
import logging
import os
import tempfile
import threading
from typing import Optional

logger = logging.getLogger("app.importer.api_service")

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.import_task import ImportTask
from app.services.importer.models import FileCollection, FormatType, ImportResult
from app.services.importer.sources.local_fs import LocalDirSource, UploadArchiveSource
from app.services.importer.sources.git_repo import GitRepoSource
from app.services.importer.detectors.format_detector import FormatDetector
from app.services.importer.importers.howtocook import HowToCookImporter
from app.services.importer.importers.export import ExportImporter


def start_background_import(db: Session, task_type: str, user_id: int,
                             import_func, *args) -> int:
    """创建任务记录并启动后台导入线程。返回 task_id。"""
    task = ImportTask(task_type=task_type, status="pending", user_id=user_id)
    db.add(task)
    db.commit()
    db.refresh(task)
    task_id = task.id

    # 在新线程中执行导入
    thread = threading.Thread(
        target=_run_import_task,
        args=(task_id, import_func, *args),
        daemon=True,
    )
    thread.start()

    return task_id


def make_progress_callback(task_id: int):
    """创建进度回调函数，用于更新数据库中的任务进度。

    返回形如 (stage, current, total, message="", counts=None) -> bool 的回调：
    - counts 非 None 时，其键值合并进 progress（供迁移实时展示 已上传/跳过/失败）。
    - 返回值表示任务是否已被取消（task.status == "cancelled"），
      供支持取消的后台循环（如图片迁移）在循环中检查并 break。
    """
    from app.core.database import SessionLocal as _SessionLocal

    def progress_callback(stage: str, current: int, total: int,
                          message: str = "", counts: dict = None):
        try:
            cb_db = _SessionLocal()
            try:
                t = cb_db.query(ImportTask).get(task_id)
                if t:
                    progress = {
                        "stage": stage,
                        "current": current,
                        "total": total,
                        "message": message,
                    }
                    if counts:
                        progress.update(counts)
                    t.progress = progress
                    cb_db.commit()
                    return t.status == "cancelled"
            finally:
                cb_db.close()
        except Exception:
            pass
        return False

    return progress_callback


def _run_import_task(task_id: int, import_func, *args):
    """在后台线程中导入，更新任务进度。"""
    from app.core.database import SessionLocal as _SessionLocal
    db = _SessionLocal()
    try:
        task = db.query(ImportTask).get(task_id)
        if not task:
            return
        task.status = "running"
        task.progress = {
            "stage": "初始化",
            "current": 0,
            "total": 0,
            "message": "正在准备导入…",
        }
        db.commit()

        progress_callback = make_progress_callback(task_id)

        # 将 args 中来自外层请求的 Session 替换为线程本地会话
        new_args = tuple(
            db if isinstance(arg, Session) else arg
            for arg in args
        )

        result = import_func(*new_args, progress_callback=progress_callback)

        task = db.query(ImportTask).get(task_id)
        if task:
            # 若运行中被取消（cancel 端点置 status=cancelled），保留 cancelled，
            # 不覆盖为 success/failed；stats 仍记部分统计，前端可见「取消时已迁移多少」
            was_cancelled = task.status == "cancelled"
            has_errors = (
                hasattr(result, 'errors') and result.errors
            )
            if was_cancelled:
                task.status = "cancelled"
                task.progress = {"stage": "已取消", "current": 1, "total": 1,
                                 "message": "任务已取消"}
            else:
                task.status = "failed" if has_errors else "success"
                task.progress = {"stage": "完成", "current": 1, "total": 1,
                                 "message": "导入完成"}
            stats = dict(result.stats) if hasattr(result, 'stats') else {}
            if hasattr(result, 'skipped') and result.skipped:
                stats["skipped"] = result.skipped
            task.stats = stats
            task.error = (None if was_cancelled
                          else ("\n".join(result.errors) if has_errors else None))
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


def import_from_git_repo(db: Session, user_id: int,
                          progress_callback=None) -> ImportResult:
    """从 git 仓库导入（启动时或管理员触发）。"""
    logger.info("=== 开始从 Git 仓库导入 ===")
    source = GitRepoSource()
    collection = source.collect_files()
    fmt = FormatDetector.detect(collection)
    logger.info("格式检测结果: %s", fmt.value)

    if fmt == FormatType.HOWTOCOOK_JSON:
        importer = HowToCookImporter(db, user_id=user_id)
    elif fmt == FormatType.EXPORT:
        importer = ExportImporter(db, user_id=user_id, is_admin=True)
    else:
        raise ValueError(f"无法识别的数据格式: {fmt}")

    result = importer.import_all(collection)
    collection.cleanup_temp()
    logger.info("=== Git 仓库导入完成: %s ===", result.stats)
    return result


def import_from_local_dir(db: Session, local_path: str,
                           user_id: int,
                           progress_callback=None) -> ImportResult:
    """从本地目录导入。

    自动检测数据子目录（如 out/），兼容指向仓库根目录和直接指向
    数据目录两种路径。
    """
    for subdir in ("out", "data", "recipes"):
        candidate = os.path.join(local_path, subdir)
        if os.path.isdir(candidate) and os.path.isfile(
            os.path.join(candidate, "ingredients.json")):
            local_path = candidate
            break

    source = LocalDirSource(local_path)
    collection = source.collect_files()
    fmt = FormatDetector.detect(collection)

    if fmt == FormatType.HOWTOCOOK_JSON:
        importer = HowToCookImporter(db, user_id=user_id)
    elif fmt == FormatType.EXPORT:
        importer = ExportImporter(db, user_id=user_id, is_admin=True)
    else:
        raise ValueError(f"无法识别的数据格式: {fmt}")

    return importer.import_all(collection, progress_callback=progress_callback)


def import_from_upload(db: Session, file: UploadFile,
                        user_id: int, is_admin: bool,
                        progress_callback=None) -> ImportResult:
    """从上传的压缩包导入。"""
    suffix = os.path.splitext(file.filename or "upload.zip")[1] or ".zip"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    collection = None
    try:
        content = file.read()
        tmp.write(content)
        tmp.close()

        source = UploadArchiveSource(tmp.name)
        collection = source.collect_files()
        fmt = FormatDetector.detect(collection)

        if fmt == FormatType.HOWTOCOOK_JSON and not is_admin:
            raise PermissionError("仅管理员可导入 HowToCook 格式数据")

        if fmt == FormatType.HOWTOCOOK_JSON:
            importer = HowToCookImporter(db, user_id=user_id)
        elif fmt == FormatType.EXPORT:
            importer = ExportImporter(db, user_id=user_id, is_admin=is_admin)
        else:
            raise ValueError("无法识别的数据格式，支持 HowToCook_json 和系统导出格式")

        result = importer.import_all(collection, progress_callback=progress_callback)
        return result
    finally:
        if collection:
            try:
                collection.cleanup_temp()
            except Exception:
                pass
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)


def import_from_upload_path(db: Session, file_path: str, user_id: int,
                              is_admin: bool, progress_callback=None) -> ImportResult:
    """从已保存的 ZIP 文件路径导入。"""
    source = UploadArchiveSource(file_path)
    collection = source.collect_files()
    fmt = FormatDetector.detect(collection)

    if fmt == FormatType.HOWTOCOOK_JSON and not is_admin:
        raise PermissionError("仅管理员可导入 HowToCook 格式数据")

    if fmt == FormatType.HOWTOCOOK_JSON:
        importer = HowToCookImporter(db, user_id=user_id)
    elif fmt == FormatType.EXPORT:
        importer = ExportImporter(db, user_id=user_id, is_admin=is_admin)
    else:
        raise ValueError("无法识别的数据格式")

    result = importer.import_all(collection)
    collection.cleanup_temp()
    if os.path.exists(file_path):
        os.unlink(file_path)
    return result
