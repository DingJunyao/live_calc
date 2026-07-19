"""地图关闭时常用地点写接口拦截、读接口保留测试。"""
from conftest import TestingSessionLocal, engine, NonAdminFakeUser
from app.core.database import Base
from app.models.map_config import MapConfiguration
from app.models.user_place import UserPlace


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


def _seed_place(db):
    """建一条该用户的常用地点用于 update/delete/default 测试。"""
    p = UserPlace(
        user_id=NonAdminFakeUser.id, name="测试地点", kind="custom",
        latitude=30.0, longitude=120.0, is_default=False, sort_order=0,
        view_radius_km=5,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p.id


def _cleanup_places(db):
    db.query(UserPlace).filter(UserPlace.user_id == NonAdminFakeUser.id).delete()
    db.commit()


PAYLOAD = {
    "name": "新地点", "kind": "custom",
    "latitude": 31.0, "longitude": 121.0,
    "address": "某地", "view_radius_km": 5,
}


def test_create_blocked_when_map_disabled(as_non_admin):
    from starlette.testclient import TestClient
    from app.main import app

    _set_map_enabled(False)
    client = TestClient(app)
    resp = client.post("/api/v1/places", json=PAYLOAD)
    assert resp.status_code == 403
    _set_map_enabled(True)


def test_update_blocked_when_map_disabled(as_non_admin):
    from starlette.testclient import TestClient
    from app.main import app

    _set_map_enabled(True)
    db = TestingSessionLocal()
    try:
        pid = _seed_place(db)
    finally:
        db.close()

    _set_map_enabled(False)
    client = TestClient(app)
    resp = client.put(f"/api/v1/places/{pid}", json=PAYLOAD)
    assert resp.status_code == 403

    _set_map_enabled(True)
    db = TestingSessionLocal()
    try:
        _cleanup_places(db)
    finally:
        db.close()


def test_delete_blocked_when_map_disabled(as_non_admin):
    from starlette.testclient import TestClient
    from app.main import app

    _set_map_enabled(True)
    db = TestingSessionLocal()
    try:
        pid = _seed_place(db)
    finally:
        db.close()

    _set_map_enabled(False)
    client = TestClient(app)
    resp = client.delete(f"/api/v1/places/{pid}")
    assert resp.status_code == 403

    _set_map_enabled(True)
    db = TestingSessionLocal()
    try:
        _cleanup_places(db)
    finally:
        db.close()


def test_set_default_blocked_when_map_disabled(as_non_admin):
    from starlette.testclient import TestClient
    from app.main import app

    _set_map_enabled(True)
    db = TestingSessionLocal()
    try:
        pid = _seed_place(db)
    finally:
        db.close()

    _set_map_enabled(False)
    client = TestClient(app)
    resp = client.put(f"/api/v1/places/{pid}/default")
    assert resp.status_code == 403

    _set_map_enabled(True)
    db = TestingSessionLocal()
    try:
        _cleanup_places(db)
    finally:
        db.close()


def test_list_still_works_when_map_disabled(as_non_admin):
    """读接口不拦：地图关闭时仍可读取已有地点（数据保留）。"""
    from starlette.testclient import TestClient
    from app.main import app

    _set_map_enabled(True)
    db = TestingSessionLocal()
    try:
        _seed_place(db)
    finally:
        db.close()

    _set_map_enabled(False)
    client = TestClient(app)
    resp = client.get("/api/v1/places")
    assert resp.status_code == 200

    _set_map_enabled(True)
    db = TestingSessionLocal()
    try:
        _cleanup_places(db)
    finally:
        db.close()
