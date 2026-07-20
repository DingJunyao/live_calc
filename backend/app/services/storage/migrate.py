"""双向图片迁移：local↔S3（Task 9 补双向核心，本文件先建任务骨架）。

Task 8：start_migrate_task 建 ImportTask + 起后台线程跑 _run_migrate_task（占位）。
Task 9：补 _migrate_to_s3_core / _migrate_from_s3_core / _run_migrate_task 真实现。
"""
import logging
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# 定位 static/images 目录（从 backend/app/services/storage/migrate.py 上 3 级到 backend，再到 static/images）
_STATIC_ROOT = Path(__file__).resolve().parents[3] / "static"
IMAGES_DIR = _STATIC_ROOT / "images"


def _migrate_to_s3_core(s3_backend, images_dir: Path,
                        progress_callback=None) -> tuple[int, int, int]:
    """local→S3。walk images_dir 所有文件 → s3.put。幂等：S3 已存在跳过。"""
    import mimetypes
    files = sorted(f for f in images_dir.rglob("*") if f.is_file())
    uploaded = skipped = failed = 0
    for i, fp in enumerate(files):
        key = fp.relative_to(images_dir).as_posix()
        try:
            if s3_backend.exists(key):
                skipped += 1
            else:
                mime, _ = mimetypes.guess_type(str(fp))
                s3_backend.put(key, fp.read_bytes(), mime or "application/octet-stream")
                uploaded += 1
        except Exception as e:
            failed += 1
            logger.warning("to_s3 失败 %s: %s", key, e)
        if progress_callback:
            progress_callback("迁移到 S3", i + 1, len(files), key)
    return uploaded, skipped, failed


def _migrate_from_s3_core(s3_backend, images_dir: Path,
                          progress_callback=None) -> tuple[int, int, int]:
    """S3→local。list_objects_v2 分页 → get → 落本地。幂等：本地已存在跳过（不覆盖）。"""
    uploaded = skipped = failed = 0
    continuation = None
    all_keys = []
    while True:
        kwargs = {"Bucket": s3_backend.bucket}
        if continuation:
            kwargs["ContinuationToken"] = continuation
        resp = s3_backend.client.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []):
            all_keys.append(obj["Key"])
        if resp.get("IsTruncated") and resp.get("NextContinuationToken"):
            continuation = resp["NextContinuationToken"]
        else:
            break

    for i, key in enumerate(all_keys):
        try:
            dest = images_dir / key
            if dest.exists():
                skipped += 1
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(s3_backend.get(key))
                uploaded += 1
        except Exception as e:
            failed += 1
            logger.warning("to_local 失败 %s: %s", key, e)
        if progress_callback:
            progress_callback("迁移到本地", i + 1, len(all_keys), key)
    return uploaded, skipped, failed


def _build_s3_from_config(s3_config):
    """建 S3Backend：to_s3 用向导填的 s3_config；to_local 用 effective（当前生效）。"""
    from app.services.storage.s3 import S3Backend
    if s3_config:
        return S3Backend(
            endpoint=s3_config["s3_endpoint"], bucket=s3_config["s3_bucket"],
            access_key=s3_config["s3_access_key"], secret_key=s3_config["s3_secret_key"],
            region=s3_config.get("s3_region", ""), url_style=s3_config.get("s3_url_style", "path"),
        )
    # to_local：当前 effective S3 配置
    from app.services.storage.effective import load_effective_storage_config
    cfg = load_effective_storage_config()
    return S3Backend(endpoint=cfg.s3_endpoint, bucket=cfg.s3_bucket,
                     access_key=cfg.s3_access_key, secret_key=cfg.s3_secret_key,
                     region=cfg.s3_region, url_style=cfg.s3_url_style)


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
    """后台线程执行体（Task 8 占位 → Task 9 真实现）。"""
    from app.services.importer.models import ImportResult
    s3_backend = _build_s3_from_config(s3_config if direction == "to_s3" else None)
    if direction == "to_s3":
        uploaded, skipped, failed = _migrate_to_s3_core(s3_backend, IMAGES_DIR, progress_callback)
    else:
        uploaded, skipped, failed = _migrate_from_s3_core(s3_backend, IMAGES_DIR, progress_callback)
    result = ImportResult()
    result.stats = {"direction": direction, "uploaded": uploaded,
                    "skipped": skipped, "failed": failed,
                    "total": uploaded + skipped + failed}
    result.errors = [] if failed == 0 else [f"{failed} 张图片迁移失败"]
    return result
