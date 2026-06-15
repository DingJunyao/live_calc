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
