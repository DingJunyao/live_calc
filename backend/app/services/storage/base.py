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

    def file_size(self, key: str) -> int:
        """返回给定 key 的文件大小（bytes）。key 不存在时抛 FileNotFoundError。"""
        ...

    def list(self, prefix: str = "") -> list[str]:
        """列出给定 prefix 下的所有 key（递归）。prefix 为空时从根目录列全部。"""
        ...
