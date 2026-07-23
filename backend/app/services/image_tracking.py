import logging

from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.models.image_tracking import ImageTracking

logger = logging.getLogger("app.services.image_tracking")


def update_image_refs(
    db: Session,
    old_keys: set[str],
    new_keys: set[str],
    file_sizes: dict[str, int] | None = None,
) -> None:
    """批量更新引用计数和最后使用时间。

    对比 old_keys 和 new_keys 的差集，决定引用增减。
    - added = new - old: ref_count +1，不存在则创建（ref_count=1）
    - removed = old - new: ref_count -1，减后为 0 时记 last_used_at = now()
    - 从 0 正数（扫描重建场景）：清 NULL last_used_at

    file_sizes: 可选，新建行时填充 file_size（仅在扫描等场景提供）
    """
    now = datetime.now(timezone.utc)
    added = new_keys - old_keys
    removed = old_keys - new_keys

    if not added and not removed:
        return

    # 获取现有记录
    all_keys = added | removed
    existing = {
        row.key: row
        for row in db.query(ImageTracking).filter(ImageTracking.key.in_(all_keys)).all()
    }

    for key in added:
        if key in existing:
            existing[key].ref_count += 1
            # ref_count 从 0 变正数  清 last_used_at（又开始用了）
            if existing[key].ref_count == 1 and existing[key].last_used_at is not None:
                existing[key].last_used_at = None
        else:
            row = ImageTracking(
                key=key,
                ref_count=1,
                file_size=file_sizes.get(key, 0) if file_sizes else 0,
            )
            db.add(row)

    for key in removed:
        if key in existing:
            existing[key].ref_count -= 1
            if existing[key].ref_count <= 0:
                existing[key].ref_count = 0
                # 仅在 last_used_at 为 NULL 时记（已有精确时间的不覆盖）
                if existing[key].last_used_at is None:
                    existing[key].last_used_at = now


def scan_all_images(db) -> dict:
    """扫描存储后端，全量重建 image_tracking 表。

    每次系统启动时自动执行一次（lifespan 内调相同逻辑），
    也支持管理员手动调用刷新。失败不阻断启动。
    """
    from app.services.storage import get_storage
    from app.models.image_tracking import ImageTracking
    from datetime import datetime, timezone

    storage = get_storage()
    now = datetime.now(timezone.utc)

    # 1. 遍历 storage 文件（list 已带回大小，无需逐 key head_object）
    all_keys_with_size: dict[str, int] = {}
    for key, size in storage.list(""):
        if key.startswith("recipes/") or key.startswith("avatars/"):
            all_keys_with_size[key] = size

    # 2. 收集引用源，构建 {key → ref_count}
    from app.api.admin import _collect_used_image_keys
    used_keys = _collect_used_image_keys(db)
    ref_count_map: dict[str, int] = {}
    for key in used_keys:
        ref_count_map[key] = ref_count_map.get(key, 0) + 1

    # 3. 获取现有记录
    existing_rows = {
        row.key: row
        for row in db.query(ImageTracking).all()
    }

    # 4. 合并写入
    all_scan_keys = set(all_keys_with_size.keys()) | used_keys
    for key in all_scan_keys:
        new_ref_count = ref_count_map.get(key, 0)
        file_size = all_keys_with_size.get(key, 0)

        if key in existing_rows:
            row = existing_rows[key]
            old_ref_count = row.ref_count
            row.ref_count = new_ref_count
            if file_size > 0:
                row.file_size = file_size
            if old_ref_count > 0 and new_ref_count == 0 and row.last_used_at is None:
                row.last_used_at = now
            elif old_ref_count == 0 and new_ref_count > 0:
                row.last_used_at = None
        else:
            row = ImageTracking(
                key=key,
                ref_count=new_ref_count,
                file_size=file_size,
                last_used_at=None,  # 新行无历史，last_used_at 恒为 None
            )
            db.add(row)

    db.commit()

    # 5. 清理残留行：存在于 image_tracking 但不在 storage 也不被引用的行
    orphaned = db.query(ImageTracking).filter(
        ~ImageTracking.key.in_(all_scan_keys)
    ).all()
    for row in orphaned:
        db.delete(row)
    if orphaned:
        logger.info(f"cleaned {len(orphaned)} orphaned tracking rows")
    if orphaned:
        db.commit()

    # 6. 统计
    all_rows = db.query(ImageTracking).all()
    used_images = sum(1 for r in all_rows if r.ref_count > 0)
    unused_images = sum(1 for r in all_rows if r.ref_count == 0)
    used_size = sum(r.file_size for r in all_rows if r.ref_count > 0)
    unused_size = sum(r.file_size for r in all_rows if r.ref_count == 0)

    stats = {
        "total_images": len(all_rows),
        "used_images": used_images,
        "unused_images": unused_images,
        "used_size": used_size,
        "unused_size": unused_size,
    }
    logger.info(f"image tracking scan complete: {stats}")
    return stats
