# backend/app/services/usda/index_manager.py
"""USDA 搜索索引全局单例：启动加载，数据变更后重建。"""
from threading import Lock
from sqlalchemy.orm import Session
from app.services.usda.search import UsdaSearchIndex

_index: UsdaSearchIndex | None = None
_lock = Lock()


def get_usda_index() -> UsdaSearchIndex:
    global _index
    if _index is None:
        raise RuntimeError("USDA 索引未初始化（应在应用启动时加载）")
    return _index


def build_usda_index(db: Session) -> UsdaSearchIndex:
    """构建并缓存索引。启动时与数据变更后调用。"""
    global _index
    with _lock:
        _index = UsdaSearchIndex.build(db)
    return _index
