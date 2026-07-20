"""Task 4: 工厂按 config 切换 backend。

覆盖三场景：
- storage_backend='local' → LocalBackend
- storage_backend='s3'    → S3Backend
- 单例（lru_cache）：get_storage() is get_storage()
- reset_storage() 清缓存
- M3 懒加载：local 模式下 sys.modules 不含 app.services.storage.s3
"""
import sys
from unittest.mock import patch

import pytest


def test_factory_local_by_default():
    from app.services.storage import get_storage, reset_storage
    from app.services.storage.local import LocalBackend

    reset_storage()
    with patch("app.services.storage.factory.settings") as s:
        s.storage_backend = "local"
        s.storage_base_url = "/api/v1/static"
        b = get_storage()
        assert isinstance(b, LocalBackend)


def test_factory_singleton():
    from app.services.storage import get_storage, reset_storage

    reset_storage()
    with patch("app.services.storage.factory.settings") as s:
        s.storage_backend = "local"
        s.storage_base_url = "/api/v1/static"
        assert get_storage() is get_storage()


def test_factory_reset_clears_singleton():
    from app.services.storage import get_storage, reset_storage

    reset_storage()
    with patch("app.services.storage.factory.settings") as s:
        s.storage_backend = "local"
        s.storage_base_url = "/api/v1/static"
        first = get_storage()
        reset_storage()
        second = get_storage()
        assert first is not second


def test_factory_s3():
    pytest.importorskip("boto3")
    from app.services.storage import get_storage, reset_storage
    from app.services.storage.s3 import S3Backend

    reset_storage()
    with patch("app.services.storage.factory.settings") as s:
        s.storage_backend = "s3"
        s.s3_endpoint = "https://oss.example.com"
        s.s3_bucket = "live"
        s.s3_access_key = "ak"
        s.s3_secret_key = "sk"
        s.s3_region = "cn"
        s.s3_url_style = "path"
        b = get_storage()
        assert isinstance(b, S3Backend)
        assert b.bucket == "live"
        assert b.url_style == "path"


def test_factory_s3_virtual_url_style():
    pytest.importorskip("boto3")
    from app.services.storage import get_storage, reset_storage
    from app.services.storage.s3 import S3Backend

    reset_storage()
    with patch("app.services.storage.factory.settings") as s:
        s.storage_backend = "s3"
        s.s3_endpoint = "https://oss-cn-beijing.aliyuncs.com"
        s.s3_bucket = "live"
        s.s3_access_key = "ak"
        s.s3_secret_key = "sk"
        s.s3_region = "cn"
        s.s3_url_style = "virtual"
        b = get_storage()
        assert isinstance(b, S3Backend)
        assert b.url_style == "virtual"


def test_factory_local_lazy_import():
    """M3：local 模式永不 import s3.py / boto3。

    local-only 部署不应付 boto3 import 成本（数百毫秒）。
    """
    from app.services.storage import get_storage, reset_storage

    reset_storage()
    # 确保起始状态干净
    sys.modules.pop("app.services.storage.s3", None)

    with patch("app.services.storage.factory.settings") as s:
        s.storage_backend = "local"
        s.storage_base_url = "/api/v1/static"
        get_storage()

    assert "app.services.storage.s3" not in sys.modules, (
        "local 模式不应 import s3.py（M3 懒加载未生效）"
    )
