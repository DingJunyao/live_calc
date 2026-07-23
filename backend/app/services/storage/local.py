from pathlib import Path
from urllib.parse import quote


class LocalBackend:
    """本地文件系统后端。

    落 <root>/images/<key>（key 为相对路径，如 recipes/xxx.jpg），
    url_for 返 <base_url>/images/<key>。

    与 StorageBackend Protocol 结构性兼容（@runtime_checkable isinstance 可验证）。

    安全：_path 对 key 做路径穿越防御，解析后路径必须仍在 images_dir 内，
    否则抛 ValueError；exists 对非法 key 返 False（不抛）。
    """

    _IMAGES_SUBDIR = "images"

    def __init__(self, root: Path, base_url: str = "/api/v1/static") -> None:
        self.root = Path(root)
        self.images_dir = self.root / self._IMAGES_SUBDIR
        self.images_dir.mkdir(parents=True, exist_ok=True)
        # 预算一次 resolved，避免每次 _path 都 resolve images_dir
        self._images_dir_resolved = self.images_dir.resolve()
        self.base_url = base_url.rstrip("/")

    def _path(self, key: str) -> Path:
        """key -> 本地绝对路径，含路径穿越防御。

        解析后路径必须仍在 images_dir 内，否则抛 ValueError。
        """
        path = (self.images_dir / key).resolve()
        if not path.is_relative_to(self._images_dir_resolved):
            raise ValueError(f"key escapes images_dir: {key!r}")
        return path

    def put(self, key: str, data: bytes, content_type: str) -> str:
        """存储，返回最终存储的 key（与入参相同）。

        content_type 参数本 backend 不消费（文件系统不存 MIME），
        为满足 StorageBackend Protocol 签名保留。
        """
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def get(self, key: str) -> bytes:
        """读取。key 不存在时抛 FileNotFoundError（Pythonic，调用方可 try/except）。"""
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def exists(self, key: str) -> bool:
        """存在性。对非法 key（路径穿越）返 False，不抛。"""
        try:
            path = self._path(key)
        except ValueError:
            return False
        return path.exists()

    def file_size(self, key: str) -> int:
        """返回文件大小（bytes）。key 不存在时抛 FileNotFoundError。"""
        path = self._path(key)
        if not path.exists():
            raise FileNotFoundError(key)
        return path.stat().st_size

    def list(self, prefix: str = "") -> list[tuple[str, int]]:
        """列出给定 prefix 下的所有 key 及大小（递归）。prefix 为空时从 images 根目录列起。"""
        scan_dir = self.images_dir / prefix if prefix else self.images_dir
        if not scan_dir.exists():
            return []
        keys: list[tuple[str, int]] = []
        for fp in sorted(scan_dir.rglob("*")):
            if fp.is_file():
                rel = fp.relative_to(self.images_dir).as_posix()
                keys.append((rel, fp.stat().st_size))
        return keys

    def url_for(self, key: str) -> str:
        """对外可访问 URL。key 经 quote 编码以兼容空格/中文/特殊字符。

        注意：url_for 不调 _path、不做安全校验，只拼字符串。
        """
        return f"{self.base_url}/{self._IMAGES_SUBDIR}/{quote(key)}"
