from app.services.storage.base import StorageBackend
from app.config import settings


def test_storage_backend_protocol_methods():
    """Protocol 必须声明 put/get/delete/exists/url_for 五个方法签名"""
    methods = [m for m in dir(StorageBackend) if not m.startswith("_")]
    for required in ("put", "get", "delete", "exists", "url_for"):
        assert required in methods, f"StorageBackend 缺方法 {required}"


def test_settings_has_storage_config():
    assert hasattr(settings, "storage_backend")
    assert settings.storage_backend in ("local", "s3")
    assert hasattr(settings, "s3_endpoint")
    assert hasattr(settings, "s3_bucket")
