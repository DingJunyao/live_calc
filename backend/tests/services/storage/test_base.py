from app.services.storage.base import StorageBackend
from app.config import settings


class _DummyBackend:
    """满足 StorageBackend 协议的最小实现，仅用于 isinstance 结构性验证。"""

    def put(self, key: str, data: bytes, content_type: str) -> str:
        return key

    def get(self, key: str) -> bytes:
        return b""

    def delete(self, key: str) -> None:
        pass

    def exists(self, key: str) -> bool:
        return True

    def url_for(self, key: str) -> str:
        return ""


def test_storage_backend_protocol_runtime_checkable():
    """@runtime_checkable + isinstance 结构性验证：满足签名的小 dummy 应被识别为 StorageBackend。"""
    assert isinstance(_DummyBackend(), StorageBackend)


def test_settings_has_storage_config():
    assert hasattr(settings, "storage_backend")
    assert settings.storage_backend in ("local", "s3")
    assert hasattr(settings, "s3_endpoint")
    assert hasattr(settings, "s3_bucket")
