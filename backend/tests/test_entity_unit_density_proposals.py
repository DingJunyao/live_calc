"""实体单位覆盖/密度 端点分流集成测试。

管理员直写即时生效；普通用户全 manual 待审（列表不出现待定值）。
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.proposals.bootstrap import register_all

client = TestClient(app)


@pytest.fixture(autouse=True)
def _setup():
    """TestClient 不触发 main.py lifespan，需显式注册执行器。"""
    register_all()
    previous = dict(app.dependency_overrides)
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)


def _ingredient(db_session):
    from app.models.nutrition import Ingredient
    ing = Ingredient(name="测试食材_xyz", is_active=True)
    db_session.add(ing)
    db_session.commit()
    db_session.refresh(ing)
    return ing.id


def test_admin_create_override_applied(db_session, as_admin):
    ing_id = _ingredient(db_session)
    resp = client.post(
        f"/api/v1/entities/ingredient/{ing_id}/units",
        json={"unit_name": "盒", "weight_per_unit": 55},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] != 0  # 管理员即时生效，返回真实 id
    assert body["unit_name"] == "盒"


def test_non_admin_create_override_pending(db_session, as_non_admin):
    ing_id = _ingredient(db_session)
    resp = client.post(
        f"/api/v1/entities/ingredient/{ing_id}/units",
        json={"unit_name": "盒", "weight_per_unit": 55},
    )
    assert resp.status_code == 201
    assert resp.json()["id"] == 0  # 占位骨架，待审
    lst = client.get(f"/api/v1/entities/ingredient/{ing_id}/units").json()
    assert all(u["unit_name"] != "盒" for u in lst)


def test_non_admin_delete_override_pending(db_session, as_non_admin):
    """已存在的覆盖，普通用户提交删除提议（待审，不立即删）。

    用 db_session 直接建数据（绕过 API，避免一个用例切两个身份）；
    db_session 与 as_non_admin 的 client 共享同一内存库（TestingSessionLocal + StaticPool）。
    """
    from app.models.entity_unit_override import EntityUnitOverride
    ing_id = _ingredient(db_session)
    o = EntityUnitOverride(entity_type="ingredient", entity_id=ing_id,
                           unit_name="袋", weight_per_unit=30, is_active=True)
    db_session.add(o)
    db_session.commit()
    db_session.refresh(o)
    oid = o.id
    resp = client.delete(f"/api/v1/entities/ingredient/{ing_id}/units/{oid}")
    assert resp.status_code == 200
    assert "已提交" in resp.json()["message"]
    lst = client.get(f"/api/v1/entities/ingredient/{ing_id}/units").json()
    assert any(u["id"] == oid for u in lst)


def test_non_admin_create_density_pending(db_session, as_non_admin):
    ing_id = _ingredient(db_session)
    resp = client.post(
        f"/api/v1/entities/ingredient/{ing_id}/density",
        json={"density": 780, "source": "估测"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == 0  # 占位，待审
    lst = client.get(f"/api/v1/entities/ingredient/{ing_id}/density").json()
    assert all(not (float(d["density"]) == 780.0) for d in lst)


def test_admin_update_override_with_decimal(db_session, as_admin):
    """管理员直写 update 带 Numeric 字段（weight_per_unit）不应崩 snapshot JSON 序列化。"""
    from app.models.entity_unit_override import EntityUnitOverride
    ing_id = _ingredient(db_session)
    o = EntityUnitOverride(entity_type="ingredient", entity_id=ing_id,
                           unit_name="盒", weight_per_unit=50, is_active=True)
    db_session.add(o)
    db_session.commit()
    db_session.refresh(o)
    resp = client.put(
        f"/api/v1/entities/ingredient/{ing_id}/units/{o.id}",
        json={"weight_per_unit": 55.5},
    )
    assert resp.status_code == 200
    assert float(resp.json()["weight_per_unit"]) == 55.5


def test_admin_delete_override_with_decimal(db_session, as_admin):
    """管理员直写 delete 含 Numeric 列的行不应崩 snapshot JSON 序列化。"""
    from app.models.entity_unit_override import EntityUnitOverride
    ing_id = _ingredient(db_session)
    o = EntityUnitOverride(entity_type="ingredient", entity_id=ing_id,
                           unit_name="盒", weight_per_unit=55.5, is_active=True)
    db_session.add(o)
    db_session.commit()
    db_session.refresh(o)
    resp = client.delete(f"/api/v1/entities/ingredient/{ing_id}/units/{o.id}")
    assert resp.status_code == 200
    # 软删：列表不再含该单位
    lst = client.get(f"/api/v1/entities/ingredient/{ing_id}/units").json()
    assert all(u["id"] != o.id for u in lst)
