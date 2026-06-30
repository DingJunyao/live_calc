"""实体单位覆盖/密度执行器 apply/revert 单元测试。

直接用 db_session 内存库测执行器，不经 API 层。

注意：db_session 是模块级共享内存库（见 conftest.py，StaticPool 单例），
不同测试间有数据残留。各测试用独立的大 entity_id（770011/770012/770013）隔离，
避免被前测或其他测试模块残留污染，但保持测试逻辑不变。
"""
import pytest
from types import SimpleNamespace

from app.services.proposals.executors.entity_unit_override import EntityUnitOverrideExecutor
from app.services.proposals.executors.entity_density import EntityDensityExecutor
from app.models.entity_unit_override import EntityUnitOverride
from app.models.entity_density import EntityDensity


def _proposal(action, payload, entity_id=None):
    return SimpleNamespace(
        action=action, payload=payload, entity_id=entity_id,
        snapshot=None, revert_payload=None,
    )


def test_override_create_apply_revert(db_session):
    ex = EntityUnitOverrideExecutor()
    p = _proposal("create", {
        "entity_type": "ingredient", "entity_id": 770011, "unit_name": "盒",
        "weight_per_unit": 55, "is_active": True,
    })
    result = ex.apply(db_session, p)
    db_session.commit()
    created = db_session.query(EntityUnitOverride).filter_by(
        entity_type="ingredient", entity_id=770011, unit_name="盒").first()
    assert created is not None and created.is_active in (True, 1)
    assert result.revert_payload["delete_id"] == created.id
    # revert（按 apply 返回的 revert_payload）
    p.revert_payload = result.revert_payload
    ex.revert(db_session, p)
    db_session.commit()
    assert db_session.query(EntityUnitOverride).filter_by(id=created.id).first() is None


def test_override_delete_soft_then_revert(db_session):
    ex = EntityUnitOverrideExecutor()
    o = EntityUnitOverride(entity_type="ingredient", entity_id=770011,
                           unit_name="盒", is_active=True)
    db_session.add(o)
    db_session.commit()
    db_session.refresh(o)
    p = _proposal("delete", {}, entity_id=o.id)
    result = ex.apply(db_session, p)
    db_session.commit()
    db_session.refresh(o)
    assert o.is_active in (False, 0)  # 软删
    # revert 复活
    p.revert_payload = result.revert_payload
    p.snapshot = result.snapshot
    ex.revert(db_session, p)
    db_session.commit()
    db_session.refresh(o)
    assert o.is_active in (True, 1)


def test_override_create_duplicate_rejected(db_session):
    from fastapi import HTTPException
    ex = EntityUnitOverrideExecutor()
    db_session.add(EntityUnitOverride(
        entity_type="ingredient", entity_id=770012, unit_name="盒", is_active=True))
    db_session.commit()
    p = _proposal("create", {
        "entity_type": "ingredient", "entity_id": 770012, "unit_name": "盒", "is_active": True,
    })
    with pytest.raises(HTTPException) as exc_info:
        ex.validate(db_session, p)
    assert exc_info.value.status_code == 400


def test_density_delete_soft_then_revert(db_session):
    ex = EntityDensityExecutor()
    d = EntityDensity(entity_type="ingredient", entity_id=770013,
                      density=780, is_active=True)
    db_session.add(d)
    db_session.commit()
    db_session.refresh(d)
    p = _proposal("delete", {}, entity_id=d.id)
    result = ex.apply(db_session, p)
    db_session.commit()
    db_session.refresh(d)
    assert d.is_active in (False, 0)
    p.revert_payload = result.revert_payload
    p.snapshot = result.snapshot
    ex.revert(db_session, p)
    db_session.commit()
    db_session.refresh(d)
    assert d.is_active in (True, 1)


def test_executors_registered_manual(db_session):
    from app.services.proposals.bootstrap import register_all
    from app.services.proposals.registry import ExecutorRegistry
    register_all()
    assert ExecutorRegistry.get("entity_unit_override") is not None
    assert ExecutorRegistry.get("entity_density") is not None
    assert ExecutorRegistry.policy_for("entity_unit_override", "create") == "manual"
    assert ExecutorRegistry.policy_for("entity_density", "delete") == "manual"


def test_density_create_duplicate_rejected(db_session):
    from fastapi import HTTPException
    ex = EntityDensityExecutor()
    db_session.add(EntityDensity(
        entity_type="ingredient", entity_id=770014, density=780, condition=None, is_active=True))
    db_session.commit()
    p = _proposal("create", {
        "entity_type": "ingredient", "entity_id": 770014, "density": 900, "condition": None,
    })
    with pytest.raises(HTTPException) as exc_info:
        ex.validate(db_session, p)
    assert exc_info.value.status_code == 400


def test_downstream_filter_excludes_soft_deleted(db_session):
    """软删的覆盖不应被换算服务读到（防幽灵数据）。"""
    from app.services.unit_conversion_service import UnitConversionService
    live = EntityUnitOverride(entity_type="ingredient", entity_id=9991,
                              unit_name="X", weight_per_unit=10, is_active=True)
    dead = EntityUnitOverride(entity_type="ingredient", entity_id=9991,
                              unit_name="X", weight_per_unit=99, is_active=False)
    db_session.add_all([live, dead])
    db_session.commit()
    ucs = UnitConversionService(db_session)
    found = ucs.get_entity_override("ingredient", 9991, "X")
    assert found is not None
    assert float(found.weight_per_unit) == 10.0  # 活跃值，非软删的 99


def test_downstream_density_filter_excludes_soft_deleted(db_session):
    """软删的密度（高 confidence）不应被 get_density 读到。"""
    from app.services.unit_conversion_service import UnitConversionService
    db_session.add(EntityDensity(entity_type="ingredient", entity_id=9992,
                                 density=1234, confidence=0.99, is_active=False))
    db_session.add(EntityDensity(entity_type="ingredient", entity_id=9992,
                                 density=780, confidence=0.5, is_active=True))
    db_session.commit()
    ucs = UnitConversionService(db_session)
    assert float(ucs.get_density("ingredient", 9992)) == 780.0

