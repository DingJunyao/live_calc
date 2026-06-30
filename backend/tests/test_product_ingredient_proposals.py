"""商品/原料执行器级联 + 端点分流集成测试。"""
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
    return SimpleNamespace(
        action=action, payload=payload, entity_id=entity_id,
        snapshot=None, revert_payload=None, proposer_id=1,
    )


def _make_ingredient(db_session, name="测试原料_cascade"):
    from app.models.nutrition import Ingredient
    ing = Ingredient(name=name, is_active=True)
    db_session.add(ing)
    db_session.commit()
    db_session.refresh(ing)
    return ing.id


def _make_product(db_session, ingredient_id, name="测试商品", active=True, with_records=0):
    """建一个商品（+可选价格记录），返回 product。"""
    from app.models.product_entity import Product
    from app.models.product import ProductRecord
    from app.models.unit import Unit
    from app.models.user import User
    # 确保有一个质量单位（ProductRecord 需 original_unit_id/standard_unit_id）
    unit = db_session.query(Unit).filter(Unit.abbreviation == "g").first()
    if unit is None:
        unit = Unit(name="克", abbreviation="g", unit_type="mass", unit_system="metric")
        db_session.add(unit)
        db_session.commit()
        db_session.refresh(unit)
    user = db_session.query(User).first()
    if user is None:
        user = User(username="t_cascade", email="t_cascade@b.c", password_hash="x")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    uid = user.id
    p = Product(name=name, ingredient_id=ingredient_id, is_active=active, created_by=uid)
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    for _ in range(with_records):
        db_session.add(ProductRecord(
            user_id=uid, product_id=p.id, product_name=name, price=10,
            original_quantity=1, original_unit_id=unit.id,
            standard_quantity=1, standard_unit_id=unit.id, is_active=True,
        ))
    db_session.commit()
    return p


def test_product_delete_cascade_then_revert(db_session):
    """商品 delete 软删 + 级联软删 ProductRecord；revert 反级联复活。"""
    from app.services.proposals.executors.product import ProductExecutor
    from app.models.product_entity import Product
    from app.models.product import ProductRecord
    # 建原料 + 2 个商品（避免唯一商品检查）+ 商品 A 有 2 条价格记录
    ing_id = _make_ingredient(db_session)
    _make_product(db_session, ing_id, name="商品B")  # 兄弟，避免唯一
    p = _make_product(db_session, ing_id, name="商品A", with_records=2)
    record_ids = [r.id for r in db_session.query(ProductRecord).filter(ProductRecord.product_id == p.id).all()]

    ex = ProductExecutor()
    result = ex.apply(db_session, _proposal("delete", {}, entity_id=p.id))
    db_session.commit()
    db_session.refresh(p)
    assert p.is_active in (False, 0)
    assert all(
        r.is_active in (False, 0)
        for r in db_session.query(ProductRecord).filter(ProductRecord.id.in_(record_ids)).all()
    )
    # revert 反级联
    pr = _proposal("delete", {}, entity_id=p.id)
    pr.revert_payload = result.revert_payload
    pr.snapshot = result.snapshot
    ex.revert(db_session, pr)
    db_session.commit()
    db_session.refresh(p)
    assert p.is_active in (True, 1)
    assert all(
        r.is_active in (True, 1)
        for r in db_session.query(ProductRecord).filter(ProductRecord.id.in_(record_ids)).all()
    )


def test_product_delete_only_product_rejected(db_session):
    """唯一商品删除被拒（执行器 apply 时检查）。"""
    from app.services.proposals.executors.product import ProductExecutor
    ing_id = _make_ingredient(db_session)
    p = _make_product(db_session, ing_id, name="唯一商品")  # 无兄弟
    ex = ProductExecutor()
    with pytest.raises(Exception):
        ex.apply(db_session, _proposal("delete", {}, entity_id=p.id))


def test_ingredient_delete_cascade_then_revert(db_session):
    """原料 delete 级联软删商品+层级；revert 反级联复活。"""
    from app.services.proposals.executors.ingredient import IngredientExecutor
    from app.models.nutrition import Ingredient
    from app.models.product_entity import Product
    from app.models.ingredient_hierarchy import IngredientHierarchy

    ing_id = _make_ingredient(db_session, name="级联原料_x")
    child_ing_id = _make_ingredient(db_session, name="子原料_x")
    p = _make_product(db_session, ing_id, name="级联商品_x")
    h = IngredientHierarchy(parent_id=ing_id, child_id=child_ing_id, relation_type="contains", is_active=True)
    db_session.add(h)
    db_session.commit()
    db_session.refresh(h)

    ex = IngredientExecutor()
    result = ex.apply(db_session, _proposal("delete", {}, entity_id=ing_id))
    db_session.commit()
    db_session.refresh(p)
    db_session.refresh(h)
    ing = db_session.query(Ingredient).get(ing_id)
    assert ing.is_active in (False, 0)
    assert p.is_active in (False, 0)
    assert h.is_active in (False, 0)

    pr = _proposal("delete", {}, entity_id=ing_id)
    pr.revert_payload = result.revert_payload
    pr.snapshot = result.snapshot
    ex.revert(db_session, pr)
    db_session.commit()
    db_session.refresh(p)
    db_session.refresh(h)
    ing = db_session.query(Ingredient).get(ing_id)
    assert ing.is_active in (True, 1)
    assert p.is_active in (True, 1)
    assert h.is_active in (True, 1)


def test_ingredient_delete_with_recipe_rejected(db_session):
    """有菜谱引用的原料删除被拒（执行器 apply 时检查）。"""
    from app.services.proposals.executors.ingredient import IngredientExecutor
    from app.models.recipe import RecipeIngredient
    ing_id = _make_ingredient(db_session, name="被引原料_x")
    db_session.add(RecipeIngredient(recipe_id=999999, ingredient_id=ing_id,
                                    quantity="1", unit_id=1))
    db_session.commit()
    ex = IngredientExecutor()
    with pytest.raises(Exception):
        ex.apply(db_session, _proposal("delete", {}, entity_id=ing_id))


def test_product_executor_registered_manual(db_session):
    from app.services.proposals.registry import ExecutorRegistry
    assert ExecutorRegistry.get("product") is not None
    assert ExecutorRegistry.policy_for("product", "update") == "manual"
    assert ExecutorRegistry.policy_for("product", "delete") == "manual"


def test_admin_update_product_applied(db_session, as_admin):
    """管理员改商品即时生效。"""
    ing_id = _make_ingredient(db_session, name="upd_ing")
    p = _make_product(db_session, ing_id, name="旧名")
    resp = client.put(f"/api/v1/products/entity/{p.id}", json={"name": "新名"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "新名"


def test_non_admin_update_product_pending(db_session, as_non_admin):
    """普通用户改商品走 manual 待审（值未变）。"""
    ing_id = _make_ingredient(db_session, name="upd_ing2")
    p = _make_product(db_session, ing_id, name="旧名2")
    resp = client.put(f"/api/v1/products/entity/{p.id}", json={"name": "新名2"})
    assert resp.status_code == 200
    from app.models.product_entity import Product
    refreshed = db_session.query(Product).get(p.id)
    db_session.refresh(refreshed)
    assert refreshed.name == "旧名2"  # 待审未生效


def test_non_admin_delete_product_pending(db_session, as_non_admin):
    """普通用户删商品走 manual 待审（不立即删）。"""
    ing_id = _make_ingredient(db_session, name="del_ing")
    p = _make_product(db_session, ing_id, name="待删")
    _make_product(db_session, ing_id, name="兄弟")  # 避免唯一商品
    resp = client.delete(f"/api/v1/products/entity/{p.id}")
    assert resp.status_code == 200
    assert "已提交" in resp.json()["message"]
    from app.models.product_entity import Product
    refreshed = db_session.query(Product).get(p.id)
    db_session.refresh(refreshed)
    assert refreshed.is_active in (True, 1)  # 待审未删


def test_non_admin_update_ingredient_pending(db_session, as_non_admin):
    """普通用户改原料基本信息走 manual 待审。"""
    ing_id = _make_ingredient(db_session, name="原料_待改")
    resp = client.put(f"/api/v1/ingredients/{ing_id}", json={"aliases": ["新别名"]})
    assert resp.status_code == 200
    from app.models.nutrition import Ingredient
    refreshed = db_session.query(Ingredient).get(ing_id)
    db_session.refresh(refreshed)
    # 待审未生效（aliases 不是 ["新别名"]）
    assert refreshed.aliases != ["新别名"]


def test_non_admin_delete_ingredient_pending(db_session, as_non_admin):
    """普通用户删原料走 manual 待审。"""
    ing_id = _make_ingredient(db_session, name="原料_待删")
    resp = client.delete(f"/api/v1/nutrition/ingredients/{ing_id}")
    assert resp.status_code == 200
    assert "已提交" in resp.json()["message"]
    from app.models.nutrition import Ingredient
    refreshed = db_session.query(Ingredient).get(ing_id)
    db_session.refresh(refreshed)
    assert refreshed.is_active in (True, 1)  # 待审未删


def test_submit_prefills_snapshot_for_delete(db_session):
    """submit delete 提议时预填 snapshot（原内容），pending 也能看 before。"""
    from app.services.proposals import service as proposal_service
    from tests.conftest import NonAdminFakeUser

    ing_id = _make_ingredient(db_session, name="snap_ing")
    p = _make_product(db_session, ing_id, name="快照商品")
    p.barcode = "SNAP001"   # Product.barcode 是 String 列，直接置
    db_session.commit()
    db_session.refresh(p)
    _make_product(db_session, ing_id, name="兄弟")  # 避免唯一商品

    proposer = NonAdminFakeUser()
    prop = proposal_service.submit(
        db_session, entity_type="product", entity_id=p.id,
        action="delete", payload={}, proposer=proposer,
    )
    db_session.commit()
    db_session.refresh(prop)
    assert prop.status == "pending"
    assert prop.snapshot is not None
    assert prop.snapshot.get("name") == "快照商品"
    assert prop.snapshot.get("barcode") == "SNAP001"


def test_submit_prefills_snapshot_for_update(db_session):
    """submit update 提议时预填 snapshot（payload 字段的旧值）。"""
    from app.services.proposals import service as proposal_service
    from tests.conftest import NonAdminFakeUser

    ing_id = _make_ingredient(db_session, name="snap_ing2")
    p = _make_product(db_session, ing_id, name="旧名_snap")

    proposer = NonAdminFakeUser()
    prop = proposal_service.submit(
        db_session, entity_type="product", entity_id=p.id,
        action="update", payload={"name": "新名_snap"}, proposer=proposer,
    )
    db_session.commit()
    db_session.refresh(prop)
    assert prop.status == "pending"
    assert prop.snapshot is not None
    assert prop.snapshot.get("name") == "旧名_snap"  # payload 字段的旧值


def test_proposal_response_includes_snapshot(db_session):
    """ProposalResponse 序列化含 snapshot 字段。"""
    from app.schemas.proposal import ProposalResponse
    from app.services.proposals import service as proposal_service
    from tests.conftest import NonAdminFakeUser

    ing_id = _make_ingredient(db_session, name="snap_ing3")
    p = _make_product(db_session, ing_id, name="resp_snap")
    _make_product(db_session, ing_id, name="兄弟3")
    proposer = NonAdminFakeUser()
    prop = proposal_service.submit(
        db_session, entity_type="product", entity_id=p.id,
        action="delete", payload={}, proposer=proposer,
    )
    db_session.commit()
    db_session.refresh(prop)
    resp = ProposalResponse.model_validate(prop)
    assert resp.snapshot is not None
    assert resp.snapshot.get("name") == "resp_snap"


def test_entity_label_for_product_proposal(db_session):
    """product 提议的 entity_label 含商品名。"""
    from app.services.proposals.executors.product import ProductExecutor
    ing_id = _make_ingredient(db_session, name="label_ing")
    p = _make_product(db_session, ing_id, name="标签商品")
    ex = ProductExecutor()
    label = ex.entity_label(db_session, _proposal("update", {"name": "新"}, entity_id=p.id))
    assert label is not None
    assert "标签商品" in label


def test_entity_label_for_unit_override_proposal(db_session):
    """entity_unit_override 提议的 entity_label 含业务实体名 + unit_name。"""
    from app.services.proposals.executors.entity_unit_override import EntityUnitOverrideExecutor
    ing_id = _make_ingredient(db_session, name="鸡蛋_label")
    ex = EntityUnitOverrideExecutor()
    prop = _proposal("create", {
        "entity_type": "ingredient", "entity_id": ing_id,
        "unit_name": "盒", "weight_per_unit": 55,
    })
    label = ex.entity_label(db_session, prop)
    assert label is not None
    assert "鸡蛋_label" in label
    assert "盒" in label


def test_proposal_response_includes_entity_label(db_session, as_admin):
    """审核台 list 返回的提议含 entity_label。"""
    from app.services.proposals import service as proposal_service
    from tests.conftest import NonAdminFakeUser

    ing_id = _make_ingredient(db_session, name="鸡蛋_resp")
    p = _make_product(db_session, ing_id, name="响应商品")
    proposer = NonAdminFakeUser()
    prop = proposal_service.submit(
        db_session, entity_type="product", entity_id=p.id,
        action="update", payload={"name": "新名"}, proposer=proposer,
    )
    db_session.commit()
    db_session.refresh(prop)

    lst = client.get("/api/v1/proposals").json()
    found = [x for x in lst if x["id"] == prop.id]
    assert found
    assert found[0].get("entity_label") is not None
    assert "响应商品" in found[0]["entity_label"]

