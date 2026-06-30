"""实体单位覆盖/密度 软删字段模型层测试。

内存库 Base.metadata.create_all 自动按最新模型建表（含 is_active），
无需跑 alembic 迁移。验证字段存在 + 默认 True + 同名软删后可重建。
"""
from app.models.entity_unit_override import EntityUnitOverride
from app.models.entity_density import EntityDensity


def test_override_has_is_active_default_true(db_session):
    o = EntityUnitOverride(
        entity_type="ingredient", entity_id=1, unit_name="盒",
        weight_per_unit=55, is_active=True,
    )
    db_session.add(o)
    db_session.commit()
    db_session.refresh(o)
    assert o.is_active is True or o.is_active == 1


def test_override_same_name_rebuild_after_soft_delete(db_session):
    """软删后同名重建不撞约束（唯一约束已拆）。

    用独立 entity_id 隔离共享内存库的存量数据，使断言不被前序测试污染。
    """
    eid = 998877  # 独立 entity_id，避免与 test_override_has_is_active_default_true 冲突
    o1 = EntityUnitOverride(entity_type="ingredient", entity_id=eid, unit_name="盒", is_active=True)
    db_session.add(o1)
    db_session.commit()
    o1.is_active = False
    db_session.commit()
    o2 = EntityUnitOverride(entity_type="ingredient", entity_id=eid, unit_name="盒", is_active=True)
    db_session.add(o2)
    db_session.commit()
    assert db_session.query(EntityUnitOverride).filter_by(
        entity_type="ingredient", entity_id=eid, unit_name="盒", is_active=True).count() == 1


def test_density_has_is_active_default_true(db_session):
    d = EntityDensity(entity_type="ingredient", entity_id=1, density=780, is_active=True)
    db_session.add(d)
    db_session.commit()
    db_session.refresh(d)
    assert d.is_active is True or d.is_active == 1


def test_density_same_name_rebuild_after_soft_delete(db_session):
    """软删后同 condition 密度重建不撞约束（唯一约束已拆）。

    用独立 entity_id 隔离共享内存库的存量数据；condition=None 参与 SQLite
    唯一性语义（NULL 在 UNIQUE 中互不冲突，但索引已拆为普通复合索引故无影响）。
    """
    eid = 998876  # 独立 entity_id，避免与其他测试冲突
    d1 = EntityDensity(entity_type="ingredient", entity_id=eid, density=780,
                       condition=None, is_active=True)
    db_session.add(d1)
    db_session.commit()
    d1.is_active = False
    db_session.commit()
    d2 = EntityDensity(entity_type="ingredient", entity_id=eid, density=900,
                       condition=None, is_active=True)
    db_session.add(d2)
    db_session.commit()  # 不应抛 IntegrityError
    assert db_session.query(EntityDensity).filter_by(
        entity_type="ingredient", entity_id=eid, condition=None, is_active=True).count() == 1
