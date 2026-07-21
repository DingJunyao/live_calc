"""按 effective 配置（DB → .env → 默认）切换 StorageBackend 的工厂。

入口：`get_storage()` 返回单例（lru_cache）；`reset_storage()` 写 DB 后清缓存热生效。

设计要点：
- 单例：避免每请求新建 boto3 client（S3Backend 构造含 boto3.client 调用，代价不低）。
- 懒加载：S3Backend 的 `import boto3` 在 s3.py 顶层，若 factory 模块顶层
  `from .s3 import S3Backend`，则 local-only 部署也会付 boto3 import 成本（数百毫秒）。
  故 S3Backend import 置于 `if cfg.backend == "s3"` 分支内（函数内导入=懒加载），
  local 模式永不 import s3.py / boto3。
- _STATIC_ROOT：对齐 main.py:551 的 `Path(__file__).parent.parent / "static"` = backend/static。
  本模块在 backend/app/services/storage/factory.py，
  Path(__file__).resolve().parents[3] = backend/，故 parents[3] / "static" = backend/static。
- 配置优先级：DB（storage_configurations 表）→ .env(BOOTSTRAP_*) → 代码默认，
  由 load_effective_storage_config 实现。
"""
from functools import lru_cache
from pathlib import Path

from app.services.storage.base import StorageBackend
from app.services.storage.local import LocalBackend
from app.services.storage.effective import load_effective_storage_config

_STATIC_ROOT = Path(__file__).resolve().parents[3] / "static"


@lru_cache(maxsize=1)
def _build() -> StorageBackend:
    cfg = load_effective_storage_config()
    if cfg.backend == "s3":
        from app.services.storage.s3 import S3Backend   # 懒加载 boto3

        return S3Backend(
            endpoint=cfg.s3_endpoint, bucket=cfg.s3_bucket,
            access_key=cfg.s3_access_key, secret_key=cfg.s3_secret_key,
            region=cfg.s3_region, url_style=cfg.s3_url_style,
            base_path=cfg.s3_base_path or "", custom_domain=cfg.s3_custom_domain or "",
            url_suffix=cfg.s3_url_suffix or "",
        )
    return LocalBackend(root=_STATIC_ROOT,
                        base_url=cfg.storage_base_url or "/api/v1/static")


def get_storage() -> StorageBackend:
    """返回当前配置下的 StorageBackend 单例。

    单例由 lru_cache 保证；切换 backend 需重启进程，或测试调 reset_storage()。
    """
    return _build()


def reset_storage() -> None:
    """写 DB 配置后调，清 lru_cache 重建（热生效）。"""
    _build.cache_clear()
