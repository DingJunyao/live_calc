"""存储配置三层合并：DB → .env(BOOTSTRAP_*) → 代码默认，逐字段判定 source。"""
import logging
from dataclasses import dataclass, field
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)

# 代码默认值
_DEFAULTS = {
    "backend": "local",
    "storage_base_url": "",
    "s3_endpoint": "", "s3_access_key": "", "s3_secret_key": "",
    "s3_bucket": "", "s3_region": "", "s3_url_style": "path",
}

# DB 字段名 → settings 字段名
_ENV_MAP = {
    "backend": "bootstrap_storage_backend",
    "storage_base_url": "bootstrap_storage_base_url",
    "s3_endpoint": "bootstrap_s3_endpoint",
    "s3_access_key": "bootstrap_s3_access_key",
    "s3_secret_key": "bootstrap_s3_secret_key",
    "s3_bucket": "bootstrap_s3_bucket",
    "s3_region": "bootstrap_s3_region",
    "s3_url_style": "bootstrap_s3_url_style",
}


@dataclass
class StorageEffectiveConfig:
    backend: str
    storage_base_url: Optional[str]
    s3_endpoint: Optional[str]
    s3_access_key: Optional[str]
    s3_secret_key: Optional[str]
    s3_bucket: Optional[str]
    s3_region: Optional[str]
    s3_url_style: str
    sources: dict = field(default_factory=dict)   # 字段名 → db/env/default


def _is_truthy(val) -> bool:
    """判断配置值是否有效（非 None / 非空串 / 非纯空白）。"""
    if val is None:
        return False
    if isinstance(val, str):
        return val.strip() != ""
    return True


def _query_db_row():
    """读 storage_configurations 单行；无表/异常返 None（不阻断启动，但记日志）。"""
    try:
        from app.core.database import SessionLocal
        from app.models.storage_configuration import StorageConfiguration
        db = SessionLocal()
        try:
            return db.query(StorageConfiguration).first()
        finally:
            db.close()
    except Exception as e:
        logger.warning("读取 storage_configurations 失败，回落 .env/默认配置: %s", e)
        return None


def load_effective_storage_config() -> StorageEffectiveConfig:
    """逐字段三层合并 DB→.env→默认，返回带 source 标注的配置。"""
    row = _query_db_row()
    resolved = {}
    sources = {}
    for fname, env_name in _ENV_MAP.items():
        db_val = getattr(row, fname, None) if row else None
        if _is_truthy(db_val):
            resolved[fname] = db_val
            sources[fname] = "db"
            continue
        env_val = getattr(settings, env_name, None)
        if _is_truthy(env_val):
            resolved[fname] = env_val
            sources[fname] = "env"
            continue
        resolved[fname] = _DEFAULTS[fname]
        sources[fname] = "default"
    return StorageEffectiveConfig(
        backend=resolved["backend"],
        storage_base_url=resolved["storage_base_url"],
        s3_endpoint=resolved["s3_endpoint"],
        s3_access_key=resolved["s3_access_key"],
        s3_secret_key=resolved["s3_secret_key"],
        s3_bucket=resolved["s3_bucket"],
        s3_region=resolved["s3_region"],
        s3_url_style=resolved["s3_url_style"],
        sources=sources,
    )
