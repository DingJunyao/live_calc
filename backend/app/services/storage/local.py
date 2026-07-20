from pathlib import Path


class LocalBackend:
    """本地文件系统后端。

    落 <root>/images/<key>（key 为相对路径，如 recipes/xxx.jpg），
    url_for 返 <base_url>/images/<key>。

    与 StorageBackend Protocol 结构性兼容（@runtime_checkable isinstance 可验证）。
    """

    def __init__(self, root: Path, base_url: str = "/api/v1/static") -> None:
        self.root = Path(root)
        self.images_dir = self.root / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = base_url.rstrip("/")

    def _path(self, key: str) -> Path:
        return self.images_dir / key

    def put(self, key: str, data: bytes, content_type: str) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def url_for(self, key: str) -> str:
        return f"{self.base_url}/images/{key}"
