from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.models.image_tracking import ImageTracking


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
