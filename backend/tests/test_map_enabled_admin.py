"""管理员地图配置端点 map_enabled 总开关测试。"""
from conftest import TestingSessionLocal, engine
from app.core.database import Base
from app.models.map_config import MapConfiguration


def _ensure_map_config_row():
    """确保内存库有一行配置（默认 map_enabled=True）。"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        if not db.query(MapConfiguration).first():
            db.add(MapConfiguration(
                map_enabled=True,
                available_maps=['amap', 'baidu', 'tencent', 'tianditu', 'osm'],
                default_map='amap',
                map_api_keys={},
                geocoding={},
            ))
            db.commit()
        else:
            # 重置为启用，避免受前序测试残留影响
            cfg = db.query(MapConfiguration).first()
            cfg.map_enabled = True
            db.commit()
    finally:
        db.close()


def test_get_map_config_returns_map_enabled(as_admin):
    from starlette.testclient import TestClient
    from app.main import app

    _ensure_map_config_row()
    client = TestClient(app)
    resp = client.get("/api/v1/admin/map-config")
    assert resp.status_code == 200
    data = resp.json()
    assert "map_enabled" in data
    assert data["map_enabled"] is True


def test_update_map_config_can_disable_map(as_admin):
    from starlette.testclient import TestClient
    from app.main import app

    _ensure_map_config_row()
    client = TestClient(app)
    # 先读回当前完整配置
    current = client.get("/api/v1/admin/map-config").json()
    current["map_enabled"] = False
    resp = client.put("/api/v1/admin/map-config", json=current)
    assert resp.status_code == 200
    assert resp.json()["map_enabled"] is False
    # 再读确认持久化
    again = client.get("/api/v1/admin/map-config").json()
    assert again["map_enabled"] is False
    # 还原，避免污染后续测试
    current["map_enabled"] = True
    client.put("/api/v1/admin/map-config", json=current)
