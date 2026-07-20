"""按 settings 切换 StorageBackend 的工厂。

入口：`get_storage()` 返回单例（lru_cache）；`reset_storage()` 给测试重置缓存。

设计要点：
- 单例：避免每请求新建 boto3 client（S3Backend 构造含 boto3.client 调用，代价不低）。
- M3 懒加载（Task 3 reviewer 指出）：S3Backend 的 `import boto3` 在 s3.py 顶层，
  若 factory 模块顶层 `from .s3 import S3Backend`，则 local-only 部署也会付 boto3 import
  成本（数百毫秒）。故 S3Backend import 置于 `if settings.bootstrap_storage_backend == "s3"` 分支内
  （函数内导入=懒加载），local 模式永不 import s3.py / boto3。
- _STATIC_ROOT：对齐 main.py:551 的 `Path(__file__).parent.parent / "static"` = backend/static。
  本模块在 backend/app/services/storage/factory.py，
  Path(__file__).resolve().parents[3] = backend/，故 parents[3] / "static" = backend/static。
"""
from functools import lru_cache
from pathlib import Path

from app.config import settings
from app.services.storage.base import StorageBackend
from app.services.storage.local import LocalBackend

_STATIC_ROOT = Path(__file__).resolve().parents[3] / "static"


@lru_cache(maxsize=1)
def _build() -> StorageBackend:
    if settings.bootstrap_storage_backend == "s3":
        # 懒加载：local-only 部署不付 boto3 import 成本（Task 3 review M3）
        from app.services.storage.s3 import S3Backend

        return S3Backend(
            endpoint=settings.bootstrap_s3_endpoint,
            bucket=settings.bootstrap_s3_bucket,
            access_key=settings.bootstrap_s3_access_key,
            secret_key=settings.bootstrap_s3_secret_key,
            region=settings.bootstrap_s3_region,
            url_style=settings.bootstrap_s3_url_style,
        )
    base_url = settings.bootstrap_storage_base_url or "/api/v1/static"
    return LocalBackend(root=_STATIC_ROOT, base_url=base_url)


def get_storage() -> StorageBackend:
    """返回当前配置下的 StorageBackend 单例。

    单例由 lru_cache 保证；切换 backend 需重启进程，或测试调 reset_storage()。
    """
    return _build()


def reset_storage() -> None:
    """测试用：重置单例缓存，使下一轮 settings mock 生效。"""
    _build.cache_clear()
