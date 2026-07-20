from pathlib import Path

import pytest

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


def test_path_traversal_rejected(tmp_path):
    """路径穿越 key 在 put/get/delete 抛 ValueError，exists 返 False。"""
    backend = LocalBackend(root=tmp_path, base_url="/api/v1/static")
    malicious_keys = [
        "../foo",
        "../../etc/passwd",
        "a/../../b",
        "../",  # 裸父目录
    ]
    for key in malicious_keys:
        assert backend.exists(key) is False, f"exists({key!r}) 应 False"
        with pytest.raises(ValueError):
            backend.put(key, b"x", "image/png")
        with pytest.raises(ValueError):
            backend.get(key)
        with pytest.raises(ValueError):
            backend.delete(key)
    # 验证实际未落到 images_dir 之外（put 全被拦）
    assert not (tmp_path.parent / "foo").exists()
    assert not (tmp_path / ".." / "etc").exists()


def test_put_overwrites_existing(tmp_path):
    """同 key 二次 put 新数据应覆盖，get 返新数据。"""
    backend = LocalBackend(root=tmp_path, base_url="/api/v1/static")
    key = "recipes/abc.png"
    backend.put(key, b"old-data", "image/png")
    backend.put(key, b"new-data", "image/png")
    assert backend.get(key) == b"new-data"
