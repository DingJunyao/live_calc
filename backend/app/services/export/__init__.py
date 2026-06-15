"""数据导出包入口。"""
from sqlalchemy.orm import Session

from .packaging import build_export_zip


def export_data(db: Session, user, scope: str) -> tuple[bytes, dict]:
    """导出当前用户可见数据为 zip。返回 (zip_bytes, manifest)。"""
    if scope not in ("full", "mine"):
        scope = "full"
    return build_export_zip(db, user, scope)
