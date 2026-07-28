import io
import zipfile
import json

from app.core.database import SessionLocal
from app.models.user import User
from app.services.export import export_data


def _testuser(db):
    return db.query(User).filter(User.username == "testuser").first()


def test_export_data_full_returns_valid_zip():
    db = SessionLocal()
    try:
        user = _testuser(db)
        assert user is not None, "db 缺 testuser"
        zip_bytes, manifest = export_data(db, user, "full")
        assert isinstance(zip_bytes, (bytes, bytearray))
        assert len(zip_bytes) > 0
        assert manifest["scope"] == "full"
        assert "counts" in manifest
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
        names = zf.namelist()
        assert "manifest.json" in names
        assert "ingredients.json" in names
        assert "units.json" in names
        # manifest 可被 json 解析
        json.loads(zf.read("manifest.json"))
    finally:
        db.close()


def test_export_data_mine_returns_valid_zip():
    db = SessionLocal()
    try:
        user = _testuser(db)
        assert user is not None
        zip_bytes, manifest = export_data(db, user, "mine")
        assert manifest["scope"] == "mine"
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
        # mine 模式菜谱数应等于 recipes/ 下文件数
        recipe_files = [n for n in zf.namelist() if n.startswith("recipes/") and n.endswith(".json")]
        assert len(recipe_files) == manifest["counts"].get("recipes", 0)
    finally:
        db.close()


# ==================== 以下为 Task 1 新增测试 ====================
from unittest.mock import patch, MagicMock
from app.services.export.packaging import _download_remote_images


def test_download_remote_images_success_and_paths():
    """成功下载：返回 {url: (rel, tmp_path)}，rel 为 images/<basename>。"""
    urls = ["https://cdn.example.com/livecalc/abc.jpg?imageslim"]
    with patch("app.services.export.packaging.requests.get") as mock_get:
        mock_get.return_value = MagicMock(content=b"\x89PNG fake", raise_for_status=lambda: None)
        downloaded, failed, tmpdir = _download_remote_images(urls, is_admin=False)
    assert failed == 0
    assert len(downloaded) == 1
    rel, tmp_path = downloaded[urls[0]]
    assert rel == "images/abc.jpg"
    import os
    assert os.path.exists(tmp_path)


def test_download_remote_images_admin_strips_query():
    """管理员：下载 URL 去 query（下原图）。"""
    urls = ["https://cdn.example.com/x/keep.png?imageslim"]
    with patch("app.services.export.packaging.requests.get") as mock_get:
        mock_get.return_value = MagicMock(content=b"img", raise_for_status=lambda: None)
        _download_remote_images(urls, is_admin=True)
    called_url = mock_get.call_args[0][0]
    assert called_url == "https://cdn.example.com/x/keep.png"
    assert "?imageslim" not in called_url


def test_download_remote_images_non_admin_keeps_query():
    """普通用户：URL 原样（含瘦身 query）。"""
    urls = ["https://cdn.example.com/x/keep.png?imageslim"]
    with patch("app.services.export.packaging.requests.get") as mock_get:
        mock_get.return_value = MagicMock(content=b"img", raise_for_status=lambda: None)
        _download_remote_images(urls, is_admin=False)
    called_url = mock_get.call_args[0][0]
    assert called_url == "https://cdn.example.com/x/keep.png?imageslim"


def test_download_remote_images_failure_counted():
    """下载失败：计入 failed，不抛异常。"""
    urls = ["https://cdn.example.com/a.jpg", "https://cdn.example.com/b.jpg"]
    def fake_get(url, timeout=None):
        if "b.jpg" in url:
            raise Exception("network error")
        return MagicMock(content=b"ok", raise_for_status=lambda: None)
    with patch("app.services.export.packaging.requests.get", side_effect=fake_get):
        downloaded, failed, tmpdir = _download_remote_images(urls, is_admin=True)
    assert failed == 1
    assert len(downloaded) == 1  # a.jpg 成功


def test_download_remote_images_dedup_basenames():
    """同名 basename 去重：第二个加 _2。"""
    urls = ["https://cdn.example.com/dup.jpg", "https://cdn.example.com/other/dup.jpg"]
    with patch("app.services.export.packaging.requests.get") as mock_get:
        mock_get.return_value = MagicMock(content=b"x", raise_for_status=lambda: None)
        downloaded, failed, tmpdir = _download_remote_images(urls, is_admin=True)
    rels = {v[0] for v in downloaded.values()}
    assert "images/dup.jpg" in rels
    assert "images/dup_2.jpg" in rels


# ==================== Task 2 新增测试 ====================
from app.services.export.packaging import _collect_image_files


def _fake_user(admin: bool):
    u = MagicMock()
    u.is_admin = admin
    return u


def test_collect_image_files_rewrites_remote_and_packs(monkeypatch):
    """外链图下载成功：JSON 改写为相对路径，图文件收集打包。"""
    recipes = [{"images": ["https://cdn.example.com/r1/foo.jpg?imageslim"]}]
    products = [{"image_url": "https://cdn.example.com/p1/bar.png"}]
    monkeypatch.setattr(
        "app.services.export.packaging._download_remote_images",
        lambda urls, is_admin: (
            {
                "https://cdn.example.com/r1/foo.jpg?imageslim": ("images/foo.jpg", "/tmp/_/foo.jpg"),
                "https://cdn.example.com/p1/bar.png": ("images/bar.png", "/tmp/_/bar.png"),
            },
            0,
            "/tmp/_dummy",
        ),
    )
    manifest = {}
    files, tmpdir = _collect_image_files(manifest, recipes, products, user=_fake_user(admin=False))
    assert recipes[0]["images"] == ["images/foo.jpg"]
    assert products[0]["image_url"] == "images/bar.png"
    rels = [f[0] for f in files]
    assert "images/foo.jpg" in rels
    assert "images/bar.png" in rels
    assert manifest["image_summary"]["downloaded"] == 2
    assert manifest["image_summary"]["failed"] == 0


def test_collect_image_files_failed_keeps_remote(monkeypatch):
    """下载失败：JSON 保留外链 URL，计入 failed，不打包该图。"""
    recipes = [{"images": ["https://cdn.example.com/missing.jpg"]}]
    monkeypatch.setattr(
        "app.services.export.packaging._download_remote_images",
        lambda urls, is_admin: ({}, 1, "/tmp/_dummy"),
    )
    manifest = {}
    files, tmpdir = _collect_image_files(manifest, recipes, [], user=_fake_user(admin=True))
    assert recipes[0]["images"] == ["https://cdn.example.com/missing.jpg"]  # 保留外链
    assert manifest["image_summary"]["failed"] == 1
    assert manifest["image_summary"]["downloaded"] == 0
    assert all("missing.jpg" not in f[0] for f in files)


def test_collect_image_files_admin_flag_passed(monkeypatch):
    """user.is_admin 透传给 _download_remote_images。"""
    captured = {}
    def fake_dl(urls, is_admin):
        captured["is_admin"] = is_admin
        return {}, 0, "/tmp/_dummy"
    monkeypatch.setattr("app.services.export.packaging._download_remote_images", fake_dl)
    _collect_image_files({}, [{"images": ["https://x/y.jpg"]}], [], user=_fake_user(admin=True))
    assert captured["is_admin"] is True


def test_collect_image_files_storage_key_from_s3(monkeypatch, tmp_path):
    """storage key 图（本地缺失）：storage.get 读 S3 打包到原 key，JSON 不改写。"""
    recipes = [{"images": ["recipes/foo/bar.png"]}]
    monkeypatch.setattr(
        "app.services.export.packaging._download_remote_images",
        lambda urls, is_admin: ({}, 0, str(tmp_path)),
    )
    fake_storage = MagicMock()
    fake_storage.get.return_value = b"\x89PNG s3 bytes"
    monkeypatch.setattr("app.services.export.packaging.get_storage", lambda: fake_storage)
    manifest = {}
    files, tmpdir = _collect_image_files(manifest, recipes, [], user=_fake_user(admin=True))
    assert recipes[0]["images"] == ["images/recipes/foo/bar.png"]  # JSON 改写到 images/
    assert "images/recipes/foo/bar.png" in [f[0] for f in files]   # 打包到 images/<key>
    fake_storage.get.assert_called_once_with("recipes/foo/bar.png")  # S3 仍按原 key 读
    assert manifest["image_summary"]["s3_downloaded"] == 1


def test_collect_image_files_storage_key_missing_s3(monkeypatch, tmp_path):
    """storage key 图 S3 也没有：计 s3_missing，不打包。"""
    recipes = [{"images": ["recipes/missing.png"]}]
    monkeypatch.setattr(
        "app.services.export.packaging._download_remote_images",
        lambda urls, is_admin: ({}, 0, str(tmp_path)),
    )
    fake_storage = MagicMock()
    fake_storage.get.side_effect = FileNotFoundError("not in s3")
    monkeypatch.setattr("app.services.export.packaging.get_storage", lambda: fake_storage)
    manifest = {}
    files, tmpdir = _collect_image_files(manifest, recipes, [], user=_fake_user(admin=False))
    assert recipes[0]["images"] == ["recipes/missing.png"]  # 失败保留原 key 不改写
    assert manifest["image_summary"]["s3_missing"] == 1
    assert all("missing.png" not in f[0] for f in files)
