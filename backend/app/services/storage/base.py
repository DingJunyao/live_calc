from typing import Protocol


class StorageBackend(Protocol):
    """图片存储后端统一契约。

    DB 只存 key（相对路径），url_for 动态拼 URL。
    具体 backend 实现见 local.py / s3.py（后续 task）。
    """

    def put(self, key: str, data: bytes, content_type: str) -> str:
        """存储，返回 key。"""
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
