"""过敏原 seed 服务测试。"""
import pytest

from app.models.blacklist_group import BlacklistGroup, BlacklistGroupIngredient
from app.models.nutrition import Ingredient
from app.services.allergen_seed import (
    ALLERGEN_GROUPS,
    _create_groups,
    ensure_allergen_groups,
)


def _clean_blacklist(db):
    """清空 BlacklistGroup 及映射，隔离测试。"""
    db.query(BlacklistGroupIngredient).delete()
    db.query(BlacklistGroup).delete()
    db.commit()


@pytest.fixture()
def clean_db(db_session):
    """每个测试前后清空黑名单分组表（db_session 是共享内存库，须自隔离）。"""
    _clean_blacklist(db_session)
    yield db_session
    _clean_blacklist(db_session)


def _add_ingredients(db):
    """预置若干原料供名称匹配（名字取自 ALLERGEN_GROUPS 真实成员）。"""
    for name in ["鸡蛋", "花生", "牛奶"]:
        db.add(Ingredient(name=name, is_active=True))
    db.commit()


def test_ensure_creates_groups_when_empty(clean_db):
    db = clean_db
    _add_ingredients(db)

    ensure_allergen_groups(db)

    assert db.query(BlacklistGroup).count() == len(ALLERGEN_GROUPS)
    assert db.query(BlacklistGroupIngredient).count() >= 3


def test_ensure_skips_when_already_populated(clean_db):
    db = clean_db
    db.add(BlacklistGroup(name="占位组", display_order=99, is_active=True))
    db.commit()

    ensure_allergen_groups(db)

    assert db.query(BlacklistGroup).count() == 1


def test_ensure_idempotent_on_double_call(clean_db):
    db = clean_db
    _add_ingredients(db)

    ensure_allergen_groups(db)
    first_groups = db.query(BlacklistGroup).count()
    first_maps = db.query(BlacklistGroupIngredient).count()

    ensure_allergen_groups(db)

    assert db.query(BlacklistGroup).count() == first_groups
    assert db.query(BlacklistGroupIngredient).count() == first_maps


def test_create_groups_handles_missing_ingredient(clean_db):
    """_create_groups 对缺失原料容错：计入 not_found、不抛错。

    共享内存库可能有残留原料，但 ALLERGEN_GROUPS 名字远多于测试预置，
    必有未命中项；只断言容错行为，不断言具体匹配数。
    """
    db = clean_db

    created, mappings, not_found = _create_groups(db)

    assert created == len(ALLERGEN_GROUPS)
    assert len(not_found) >= 1
