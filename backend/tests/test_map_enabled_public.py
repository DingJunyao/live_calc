"""公开地图配置端点 map_enabled 下发测试。"""
from conftest import TestingSessionLocal, engine
from app.core.database import Base
from app.models.map_config import MapConfiguration


def _set_map_enabled(value: bool):
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        cfg = db.query(MapConfiguration).first()
        if not cfg:
            cfg = MapConfiguration(
                available_maps=['amap'], default_map='amap',
                map_api_keys={}, geocoding={},
            )
            db.add(cfg)
        cfg.map_enabled = value
        db.commit()
    finally:
        db.close()


def test_public_map_config_contains_map_enabled(as_non_admin):
    from starlette.testclient import TestClient
    from app.main import app

    _set_map_enabled(True)
    client = TestClient(app)
    resp = client.get("/api/v1/merchants/map-config")
    assert resp.status_code == 200
    assert resp.json().get("map_enabled") is True


def test_public_map_config_default_includes_map_enabled(as_non_admin):
    """测试无配置时的默认分支也包含 map_enabled"""
    from starlette.testclient import TestClient
    from app.main import app

    # 确保没有配置
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        db.query(MapConfiguration).delete()
        db.commit()
    finally:
        db.close()

    client = TestClient(app)
    resp = client.get("/api/v1/merchants/map-config")
    assert resp.status_code == 200
    # 默认分支应该包含 map_enabled 且为 True
    assert resp.json().get("map_enabled") is True


def test_public_map_config_reflects_disabled(as_non_admin):
    from starlette.testclient import TestClient
    from app.main import app

    _set_map_enabled(False)
    client = TestClient(app)
    resp = client.get("/api/v1/merchants/map-config")
    assert resp.status_code == 200
    assert resp.json().get("map_enabled") is False
    # 还原
    _set_map_enabled(True)
