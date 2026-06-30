"""USDA 匹配接入审核框架测试。"""
import pytest
from types import SimpleNamespace
from fastapi.testclient import TestClient
from app.main import app
from app.services.proposals.bootstrap import register_all

client = TestClient(app)


@pytest.fixture(autouse=True)
def _setup():
    register_all()
    previous = dict(app.dependency_overrides)
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)


def _proposal(action, payload, entity_id=None):
    return SimpleNamespace(action=action, payload=payload, entity_id=entity_id,
                           snapshot=None, revert_payload=None, proposer_id=1)


def test_submit_policy_override_auto(db_session):
    """policy_override='auto_approve' 覆盖 registry manual，立即 apply。"""
    from app.services.proposals import service as proposal_service
    from app.services.proposals.executors.unit import UnitExecutor
    from app.services.proposals.registry import ExecutorRegistry
    from app.models.unit import Unit
    from tests.conftest import NonAdminFakeUser
    # unit.create 默认 auto_approve，临时改成 manual 测 override
    ExecutorRegistry.set_policy("unit", "create", "manual")
    try:
        proposer = NonAdminFakeUser()
        # policy_override auto → 立即 apply
        p = proposal_service.submit(
            db_session, entity_type="unit", entity_id=None, action="create",
            payload={"name": "override_unit_xyz", "abbreviation": "ou_xyz", "unit_type": "count", "is_active": True},
            proposer=proposer, policy_override="auto_approve",
        )
        db_session.commit()
        assert p.status == "applied"  # override auto，立即生效
    finally:
        ExecutorRegistry.set_policy("unit", "create", "auto_approve")  # reset


def test_submit_policy_override_none_uses_registry(db_session):
    """policy_override=None 走 registry 默认（unit.create=auto_approve）。"""
    from app.services.proposals import service as proposal_service
    from tests.conftest import NonAdminFakeUser
    proposer = NonAdminFakeUser()
    p = proposal_service.submit(
        db_session, entity_type="unit", entity_id=None, action="create",
        payload={"name": "no_override_xyz", "abbreviation": "no_xyz", "unit_type": "count", "is_active": True},
        proposer=proposer, policy_override=None,
    )
    db_session.commit()
    assert p.status == "applied"  # registry 默认 auto_approve


def test_submit_policy_override_manual(db_session):
    """policy_override='manual' 覆盖 registry auto，pending 待审。"""
    from app.services.proposals import service as proposal_service
    from app.services.proposals.registry import ExecutorRegistry
    from tests.conftest import NonAdminFakeUser
    proposer = NonAdminFakeUser()
    p = proposal_service.submit(
        db_session, entity_type="unit", entity_id=None, action="create",
        payload={"name": "manual_override_xyz", "abbreviation": "mo_xyz", "unit_type": "count", "is_active": True},
        proposer=proposer, policy_override="manual",
    )
    db_session.commit()
    assert p.status == "pending"  # override manual，待审


# ---------------------------------------------------------------------------
# USDA 匹配执行器：替换语义（apply 替换 + revert 还原）单测
# ---------------------------------------------------------------------------

def _make_ingredient(db_session, name="usda_test_ing"):
    from app.models.nutrition import Ingredient
    ing = Ingredient(name=name, is_active=True)
    db_session.add(ing)
    db_session.commit()
    db_session.refresh(ing)
    return ing.id


def _make_product(db_session, ingredient_id, name="usda_test_prod"):
    from app.models.product_entity import Product
    prod = Product(name=name, ingredient_id=ingredient_id, is_active=True)
    db_session.add(prod)
    db_session.commit()
    db_session.refresh(prod)
    return prod.id


def _make_usda_food(db_session, fdc_id=999111):
    """建最小 UsdaFood + 一条 UsdaFoodNutrient，供 match_ingredient/match_product 用。"""
    from app.models.usda import UsdaFood, UsdaFoodNutrient
    food = UsdaFood(
        fdc_id=fdc_id,
        data_type="foundation",
        description="Test Food",
        description_zh="测试食材",
    )
    db_session.add(food)
    db_session.commit()
    db_session.refresh(food)
    # 蛋白质：核心营养素，_build_nutrition_json 会进 core_nutrients，NRV 有标准
    nut = UsdaFoodNutrient(
        fdc_id=fdc_id,
        nutrient_no="203",
        name="Protein",
        name_zh="蛋白质",
        amount=25.0,
        unit_name="g",
    )
    db_session.add(nut)
    db_session.commit()
    return fdc_id


def test_ingredient_match_apply_reverts(db_session):
    """USDA 原料匹配：apply 替换 NutritionData，revert 还原旧数据。"""
    from app.services.proposals.executors.usda_ingredient_match import UsdaIngredientMatchExecutor
    from app.models.nutrition_data import NutritionData

    ing_id = _make_ingredient(db_session, name="match_ing")
    # 预置一条旧 NutritionData（自定义，验证标志 + 营养内容可被还原）
    db_session.add(NutritionData(
        ingredient_id=ing_id, source="custom", is_verified=True,
        nutrients={"core_nutrients": {"蛋白质": {"value": 10, "unit": "g", "key": "protein"}}},
        reference_amount=100.0, reference_unit="g",
    ))
    db_session.commit()

    fdc_id = _make_usda_food(db_session)

    ex = UsdaIngredientMatchExecutor()
    p = _proposal("create", {"fdc_id": fdc_id}, entity_id=ing_id)
    result = ex.apply(db_session, p)
    db_session.commit()

    # apply 后：旧数据被清空，只剩 USDA 的（usda_id=fdc_id）
    rows = db_session.query(NutritionData).filter(
        NutritionData.ingredient_id == ing_id).all()
    assert len(rows) == 1
    assert rows[0].usda_id == str(fdc_id)
    assert rows[0].source == "usda_manual_match"
    assert rows[0].is_verified is True

    # revert 还原旧数据
    p.revert_payload = result.revert_payload
    p.snapshot = result.snapshot
    ex.revert(db_session, p)
    db_session.commit()

    rows = db_session.query(NutritionData).filter(
        NutritionData.ingredient_id == ing_id).all()
    # USDA 行被删，旧行被插回
    assert all(r.usda_id != str(fdc_id) for r in rows)
    assert any(r.nutrients.get("core_nutrients", {}).get("蛋白质", {}).get("value") == 10
               for r in rows), "旧营养数据应被还原"


def test_ingredient_match_validate_missing_fdc(db_session):
    """validate：缺 fdc_id / entity_id → 400。"""
    from app.services.proposals.executors.usda_ingredient_match import UsdaIngredientMatchExecutor
    from fastapi import HTTPException

    ex = UsdaIngredientMatchExecutor()
    # 缺 fdc_id
    p_no_fdc = _proposal("create", {}, entity_id=1)
    with pytest.raises(HTTPException) as ei:
        ex.validate(db_session, p_no_fdc)
    assert ei.value.status_code == 400
    # 缺 entity_id
    p_no_eid = _proposal("create", {"fdc_id": 999}, entity_id=None)
    with pytest.raises(HTTPException) as ei:
        ex.validate(db_session, p_no_eid)
    assert ei.value.status_code == 400


def test_ingredient_match_validate_not_found(db_session):
    """validate：原料不存在 → 404。"""
    from app.services.proposals.executors.usda_ingredient_match import UsdaIngredientMatchExecutor
    from fastapi import HTTPException

    ex = UsdaIngredientMatchExecutor()
    p = _proposal("create", {"fdc_id": 999111}, entity_id=999999)
    with pytest.raises(HTTPException) as ei:
        ex.validate(db_session, p)
    assert ei.value.status_code == 404


def test_product_match_apply_reverts(db_session):
    """USDA 商品匹配：apply 覆盖 custom_nutrition_data，revert 还原旧值。"""
    from app.services.proposals.executors.usda_product_match import UsdaProductMatchExecutor
    from app.models.product_entity import Product

    ing_id = _make_ingredient(db_session, name="prod_match_ing")
    prod_id = _make_product(db_session, ing_id, name="prod_match")
    # 预置旧 custom_nutrition_data
    old_cnd = {"core_nutrients": {"蛋白质": {"value": 5, "unit": "g"}},
               "source": "custom"}
    db_session.query(Product).filter(Product.id == prod_id).update(
        {"custom_nutrition_data": old_cnd})
    db_session.commit()

    fdc_id = _make_usda_food(db_session, fdc_id=999222)

    ex = UsdaProductMatchExecutor()
    p = _proposal("create", {"fdc_id": fdc_id}, entity_id=prod_id)
    result = ex.apply(db_session, p)
    db_session.commit()

    # apply 后：custom_nutrition_data 被 USDA 数据覆盖
    prod = db_session.query(Product).get(prod_id)
    assert prod.custom_nutrition_data is not None
    assert prod.custom_nutrition_data.get("source") == "usda_manual_match"
    assert prod.custom_nutrition_data.get("usda_id") == str(fdc_id)
    core = prod.custom_nutrition_data.get("core_nutrients", {})
    assert core.get("蛋白质", {}).get("value") == 25.0

    # revert 还原旧值
    p.revert_payload = result.revert_payload
    p.snapshot = result.snapshot
    ex.revert(db_session, p)
    db_session.commit()

    prod = db_session.query(Product).get(prod_id)
    assert prod.custom_nutrition_data == old_cnd


def test_product_match_revert_from_none(db_session):
    """apply 前无 custom_nutrition_data（None），revert 还原回 None。"""
    from app.services.proposals.executors.usda_product_match import UsdaProductMatchExecutor
    from app.models.product_entity import Product

    ing_id = _make_ingredient(db_session, name="prod_none_ing")
    prod_id = _make_product(db_session, ing_id, name="prod_none")
    # 不预置 custom_nutrition_data（默认 None）
    fdc_id = _make_usda_food(db_session, fdc_id=999333)

    ex = UsdaProductMatchExecutor()
    p = _proposal("create", {"fdc_id": fdc_id}, entity_id=prod_id)
    result = ex.apply(db_session, p)
    db_session.commit()
    assert result.snapshot["old_custom_nutrition_data"] is None

    prod = db_session.query(Product).get(prod_id)
    assert prod.custom_nutrition_data is not None  # 已被 USDA 覆盖

    p.revert_payload = result.revert_payload
    p.snapshot = result.snapshot
    ex.revert(db_session, p)
    db_session.commit()

    prod = db_session.query(Product).get(prod_id)
    assert prod.custom_nutrition_data is None  # 还原回 None


def test_executors_registered():
    """两执行器已在 registry 注册。"""
    from app.services.proposals.registry import ExecutorRegistry
    assert ExecutorRegistry.get("usda_ingredient_match") is not None
    assert ExecutorRegistry.get("usda_product_match") is not None


# ---------------------------------------------------------------------------
# 端点分流集成测试：管理员直写 / 普通用户（有数据→manual，无数据→auto 补空）
# ---------------------------------------------------------------------------

def test_admin_match_ingredient_applied(db_session, as_admin):
    """管理员 USDA 原料匹配即时生效。"""
    ing_id = _make_ingredient(db_session, name="adm_match_ing")
    fdc_id = _make_usda_food(db_session, fdc_id=999555)
    resp = client.post(f"/api/v1/usda/match/ingredient/{ing_id}", json={"fdc_id": fdc_id})
    assert resp.status_code == 200
    assert "管理员直写" in resp.json()["message"]
    from app.models.nutrition_data import NutritionData
    nd = db_session.query(NutritionData).filter(NutritionData.ingredient_id == ing_id).first()
    assert nd is not None and nd.usda_id == str(fdc_id)


def test_non_admin_match_ingredient_no_data_auto(db_session, as_non_admin):
    """普通用户匹配无数据的原料→补空 auto 立即生效。"""
    ing_id = _make_ingredient(db_session, name="empty_match_ing")  # 无 NutritionData
    fdc_id = _make_usda_food(db_session, fdc_id=999666)
    resp = client.post(f"/api/v1/usda/match/ingredient/{ing_id}", json={"fdc_id": fdc_id})
    assert resp.status_code == 200
    assert "补空自动通过" in resp.json()["message"]
    from app.models.nutrition_data import NutritionData
    nd = db_session.query(NutritionData).filter(NutritionData.ingredient_id == ing_id).first()
    assert nd is not None  # 自动通过，已写入


def test_non_admin_match_ingredient_has_data_manual(db_session, as_non_admin):
    """普通用户匹配有数据的原料→manual 待审（不立即覆盖）。"""
    from app.models.nutrition_data import NutritionData
    ing_id = _make_ingredient(db_session, name="hasdata_match_ing")
    db_session.add(NutritionData(ingredient_id=ing_id, source="custom", is_verified=True,
                                 nutrients={"protein": 5}, reference_amount=100.0, reference_unit="g"))
    db_session.commit()
    fdc_id = _make_usda_food(db_session, fdc_id=999777)
    resp = client.post(f"/api/v1/usda/match/ingredient/{ing_id}", json={"fdc_id": fdc_id})
    assert resp.status_code == 200
    assert "待管理员审核" in resp.json()["message"]
    # 数据未变（仍是旧的 custom，非 USDA）
    nd = db_session.query(NutritionData).filter(NutritionData.ingredient_id == ing_id).first()
    assert nd.source == "custom"


def test_non_admin_match_product_auto(db_session, as_non_admin):
    """普通用户匹配商品（无 custom_nutrition_data）→补空 auto。"""
    ing_id = _make_ingredient(db_session, name="prod_match_ing_ep")
    pid = _make_product(db_session, ing_id, name="prod_match_ep")
    fdc_id = _make_usda_food(db_session, fdc_id=999888)
    resp = client.post(f"/api/v1/usda/match/product/{pid}", json={"fdc_id": fdc_id})
    assert resp.status_code == 200
    from app.models.product_entity import Product
    prod = db_session.query(Product).get(pid)
    db_session.refresh(prod)
    assert prod.custom_nutrition_data is not None  # 已写入
