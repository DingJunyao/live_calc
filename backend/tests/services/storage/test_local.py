from pathlib import Path

from app.services.storage.base import StorageBackend
from app.services.storage.local import LocalBackend


def test_put_get_roundtrip(tmp_path):
    backend = LocalBackend(root=tmp_path, base_url="/api/v1/static")
    key = backend.put("recipes/abc.png", b"\x89PNG data", "image/png")
    assert key == "recipes/abc.png"
    assert backend.get(key) == b"\x89PNG data"
    assert backend.exists(key) is True
    assert (tmp_path / "images" / "recipes" / "abc.png").exists()


def test_url_for_local(tmp_path):
    backend = LocalBackend(root=tmp_path, base_url="/api/v1/static")
    assert backend.url_for("recipes/abc.png") == "/api/v1/static/images/recipes/abc.png"


def test_url_for_strips_trailing_slash(tmp_path):
    """base_url 带末尾斜杠时也应拼出单斜杠，避免 //images//。"""
    backend = LocalBackend(root=tmp_path, base_url="/api/v1/static/")
    assert backend.url_for("recipes/abc.png") == "/api/v1/static/images/recipes/abc.png"


def test_delete(tmp_path):
    backend = LocalBackend(root=tmp_path, base_url="/api/v1/static")
    backend.put("avatars/x.jpg", b"data", "image/jpeg")
    backend.delete("avatars/x.jpg")
    assert backend.exists("avatars/x.jpg") is False


def test_delete_missing_is_noop(tmp_path):
    """删不存在的 key 不应抛错。"""
    backend = LocalBackend(root=tmp_path, base_url="/api/v1/static")
    backend.delete("never/existed.png")  # 不抛


def test_put_creates_subdirs(tmp_path):
    backend = LocalBackend(root=tmp_path, base_url="/api/v1/static")
    backend.put("recipes/sub/deep.png", b"x", "image/png")
    assert backend.exists("recipes/sub/deep.png")


def test_local_satisfies_protocol(tmp_path):
    """LocalBackend 满足 StorageBackend Protocol（@runtime_checkable isinstance 验证）。"""
    assert isinstance(LocalBackend(root=tmp_path), StorageBackend)


def test_init_creates_images_dir(tmp_path):
    """初始化时自动创建 <root>/images 目录。"""
    root = tmp_path / "nested" / "store"
    assert not root.exists()
    backend = LocalBackend(root=root)
    assert (root / "images").is_dir()
    # 二次初始化幂等（目录已存在不报错）
    LocalBackend(root=root)
