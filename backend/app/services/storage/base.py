from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    """图片存储后端统一契约。

    DB 只存 key（相对路径），url_for 动态拼 URL。
    具体 backend 实现见 local.py / s3.py。
    """

    def put(self, key: str, data: bytes, content_type: str) -> str:
        """存储，返回最终存储的 key（入参不变时与入参相同），便于调用方链式拿 key 存 DB。"""
        ...

    def get(self, key: str) -> bytes:
        """读取。"""
        ...

    def delete(self, key: str) -> None:
        """删除。"""
        ...

    def exists(self, key: str) -> bool:
        """存在性。"""
        ...

    def url_for(self, key: str) -> str:
        """对外可访问 URL。"""
        ...
