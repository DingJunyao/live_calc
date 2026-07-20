"""双向图片迁移：local↔S3（Task 9 补双向核心，本文件先建任务骨架）。

Task 8：start_migrate_task 建 ImportTask + 起后台线程跑 _run_migrate_task（占位）。
Task 9：补 _migrate_to_s3_core / _migrate_from_s3_core / _run_migrate_task 真实现。
"""
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


def start_migrate_task(db, direction: str, s3_config: Optional[dict], user_id: int) -> int:
    """建 ImportTask（task_type=storage_migrate）+ 起后台线程。返 task_id。

    Task 8 占位：后台跑 _run_migrate_task（当前占位返空 stats）。
    Task 9 补真正的双向迁移核心。
    """
    from app.services.importer.api_service import start_background_import
    task_id = start_background_import(
        db, task_type="storage_migrate", user_id=user_id,
        import_func=_run_migrate_task, direction=direction, s3_config=s3_config,
    )
    return task_id


def _run_migrate_task(db, direction: str = "to_s3", s3_config: Optional[dict] = None,
                      progress_callback: Optional[Callable] = None):
    """后台线程执行体。Task 8 占位（返空 stats），Task 9 补真正双向迁移逻辑。"""
    from app.services.importer.models import ImportResult
    logger.warning("_run_migrate_task 占位实现（Task 9 补双向迁移核心），direction=%s", direction)
    result = ImportResult()
    result.stats = {"direction": direction, "uploaded": 0, "skipped": 0, "failed": 0, "total": 0}
    result.errors = []
    return result
