"""端到端流程验证：普通用户改/删商品与原料 → manual 待审 → 管理员审核生效 → 回滚反级联。

覆盖 (a)-(g) 全链路，通过 TestClient + dependency_overrides 切换身份：
- 普通用户提交 → 值未变 + change_proposals status=pending
- 管理员审核通过 → applied + 软删/级联生效
- 管理员回滚 → reverted + 反级联复活
- 双层检查：端点提交即拒（唯一商品 / 有菜谱引用）→ 400，不进 pending

保留作为补充覆盖（验证审核台显示 product 类型 + 完整 apply/revert 链路）。
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.proposals.bootstrap import register_all
from tests.conftest import TestingSessionLocal, _fake_non_admin_user

# 模块级 client：lifespan 只在整个测试模块首次请求时运行一次（与既有测试同构）。
# 身份切换通过直接改写 app.dependency_overrides 实现（请求时实时读取）。
client = TestClient(app)


@pytest.fixture(autouse=True)
def _setup():
    register_all()
    previous = dict(app.dependency_overrides)
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)


def _make_ingredient(db, name="e2e_原料"):
    from app.models.nutrition import Ingredient
    ing = Ingredient(name=name, is_active=True)
    db.add(ing)
    db.commit()
    db.refresh(ing)
    return ing.id


def _make_product(db, ingredient_id, name="e2e_商品", active=True):
    from app.models.product_entity import Product
    from app.models.user import User
    user = db.query(User).first()
    if user is None:
        user = User(username="e2e_u", email="e2e@b.c", password_hash="x")
        db.add(user)
        db.commit()
        db.refresh(user)
    p = Product(name=name, ingredient_id=ingredient_id, is_active=active, created_by=user.id)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _make_price_record(db, product_id, name="e2e_商品"):
    from app.models.product import ProductRecord
    from app.models.unit import Unit
    from app.models.user import User
    unit = db.query(Unit).filter(Unit.abbreviation == "g").first()
    if unit is None:
        unit = Unit(name="克", abbreviation="g", unit_type="mass", unit_system="metric")
        db.add(unit)
        db.commit()
        db.refresh(unit)
    user = db.query(User).first()
    pr = ProductRecord(
        user_id=user.id, product_id=product_id, product_name=name, price=10,
        original_quantity=1, original_unit_id=unit.id,
        standard_quantity=1, standard_unit_id=unit.id, is_active=True,
    )
    db.add(pr)
    db.commit()
    db.refresh(pr)
    return pr.id


def _pending_proposals(db, entity_type, entity_id):
    from app.models.change_proposal import ChangeProposal
    return db.query(ChangeProposal).filter(
        ChangeProposal.entity_type == entity_type,
        ChangeProposal.entity_id == entity_id,
        ChangeProposal.status == "pending",
    ).all()


# ---------- (a) 普通用户改商品 → manual pending ----------
def test_a_non_admin_update_product_pending(db_session, as_non_admin):
    ing_id = _make_ingredient(db_session, name="e2e_a_ing")
    p = _make_product(db_session, ing_id, name="e2e_a_旧名")
    resp = client.put(f"/api/v1/products/entity/{p.id}", json={"name": "e2e_a_新名"})
    assert resp.status_code == 200
    db_session.expire_all()
    from app.models.product_entity import Product
    refreshed = db_session.query(Product).get(p.id)
    assert refreshed.name == "e2e_a_旧名"  # 待审，值未变
    assert len(_pending_proposals(db_session, "product", p.id)) >= 1


# ---------- (b) 普通用户删商品 → manual pending（不立即删）----------
def test_b_non_admin_delete_product_pending(db_session, as_non_admin):
    ing_id = _make_ingredient(db_session, name="e2e_b_ing")
    p = _make_product(db_session, ing_id, name="e2e_b_待删")
    _make_product(db_session, ing_id, name="e2e_b_兄弟")  # 避免唯一
    resp = client.delete(f"/api/v1/products/entity/{p.id}")
    assert resp.status_code == 200
    assert "已提交" in resp.json()["message"]
    db_session.expire_all()
    from app.models.product_entity import Product
    refreshed = db_session.query(Product).get(p.id)
    assert bool(refreshed.is_active)  # 待审，未删


# ---------- (c) 普通用户改原料基本信息 → manual pending ----------
def test_c_non_admin_update_ingredient_pending(db_session, as_non_admin):
    ing_id = _make_ingredient(db_session, name="e2e_c_原料")
    resp = client.put(f"/api/v1/ingredients/{ing_id}", json={"aliases": ["e2e_c_别名"]})
    assert resp.status_code == 200
    from app.models.nutrition import Ingredient
    db_session.expire_all()
    refreshed = db_session.query(Ingredient).get(ing_id)
    assert refreshed.aliases != ["e2e_c_别名"]  # 待审未生效
    assert len(_pending_proposals(db_session, "ingredient", ing_id)) >= 1


# ---------- (d) 普通用户删原料 → manual pending ----------
def test_d_non_admin_delete_ingredient_pending(db_session, as_non_admin):
    ing_id = _make_ingredient(db_session, name="e2e_d_原料")
    resp = client.delete(f"/api/v1/nutrition/ingredients/{ing_id}")
    assert resp.status_code == 200
    assert "已提交" in resp.json()["message"]
    from app.models.nutrition import Ingredient
    db_session.expire_all()
    refreshed = db_session.query(Ingredient).get(ing_id)
    assert bool(refreshed.is_active)


# ---------- (e) 管理员审核通过 delete 商品 → applied + 级联软删 ProductRecord ----------
def test_e_admin_review_product_delete_applied_with_cascade(db_session, as_admin):
    """普通用户提交（直调 service，避免中途切身份）→ 管理员 HTTP 审核通过 → 级联生效。"""
    from app.services.proposals import service as proposal_service
    from app.models.change_proposal import ChangeProposal
    from app.models.product_entity import Product
    from app.models.product import ProductRecord

    ing_id = _make_ingredient(db_session, name="e2e_e_ing")
    _make_product(db_session, ing_id, name="e2e_e_兄弟")
    p = _make_product(db_session, ing_id, name="e2e_e_待删")
    rec_id = _make_price_record(db_session, p.id, name="e2e_e_待删")

    # 普通用户提交删除提议（直调 service，身份=NonAdminFakeUser id=2）
    non_admin = _fake_non_admin_user()
    prop = proposal_service.submit(
        db_session, entity_type="product", entity_id=p.id,
        action="delete", payload={}, proposer=non_admin,
    )
    db_session.commit()
    assert prop.status == "pending"
    assert prop.review_policy == "manual"

    # 管理员审核通过（HTTP，as_admin fixture）
    resp = client.post(f"/api/v1/proposals/{prop.id}/review", json={"approved": True, "note": "同意"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "applied"

    db_session.expire_all()
    refreshed_p = db_session.query(Product).get(p.id)
    refreshed_rec = db_session.query(ProductRecord).get(rec_id)
    assert not bool(refreshed_p.is_active)        # 商品软删
    assert not bool(refreshed_rec.is_active)      # 级联 ProductRecord 软删

    # 审核台能显示 product 类型（entity_type 透传）
    assert resp.json()["entity_type"] == "product"


# ---------- (e2) 管理员审核通过 delete 原料 → applied + 级联软删 商品+层级 ----------
def test_e2_admin_review_ingredient_delete_applied_with_cascade(db_session, as_admin):
    from app.services.proposals import service as proposal_service
    from app.models.nutrition import Ingredient
    from app.models.product_entity import Product
    from app.models.ingredient_hierarchy import IngredientHierarchy

    ing_id = _make_ingredient(db_session, name="e2e_e2_主")
    child_id = _make_ingredient(db_session, name="e2e_e2_子")
    p = _make_product(db_session, ing_id, name="e2e_e2_商品")
    h = IngredientHierarchy(parent_id=ing_id, child_id=child_id,
                            relation_type="contains", is_active=True)
    db_session.add(h)
    db_session.commit()
    db_session.refresh(h)

    non_admin = _fake_non_admin_user()
    prop = proposal_service.submit(
        db_session, entity_type="ingredient", entity_id=ing_id,
        action="delete", payload={}, proposer=non_admin,
    )
    db_session.commit()
    assert prop.status == "pending"

    resp = client.post(f"/api/v1/proposals/{prop.id}/review", json={"approved": True})
    assert resp.status_code == 200
    assert resp.json()["status"] == "applied"

    db_session.expire_all()
    assert not bool(db_session.query(Ingredient).get(ing_id).is_active)
    assert not bool(db_session.query(Product).get(p.id).is_active)
    assert not bool(db_session.query(IngredientHierarchy).get(h.id).is_active)


# ---------- (f) 管理员回滚 delete 商品 → reverted + 反级联复活 ----------
def test_f_admin_revert_product_delete_revives_cascade(db_session, as_admin):
    from app.models.change_proposal import ChangeProposal
    from app.models.product_entity import Product
    from app.models.product import ProductRecord

    ing_id = _make_ingredient(db_session, name="e2e_f_ing")
    _make_product(db_session, ing_id, name="e2e_f_兄弟")
    p = _make_product(db_session, ing_id, name="e2e_f_待删")
    rec_id = _make_price_record(db_session, p.id, name="e2e_f_待删")

    # 管理员直删（apply_as_admin 立即 applied，留 revert_payload）
    resp = client.delete(f"/api/v1/products/entity/{p.id}")
    assert resp.status_code == 200
    prop = db_session.query(ChangeProposal).filter(
        ChangeProposal.entity_type == "product",
        ChangeProposal.entity_id == p.id,
        ChangeProposal.status == "applied",
    ).first()
    assert prop is not None
    assert prop.revert_payload is not None
    assert "cascade_record_ids" in prop.revert_payload

    db_session.expire_all()
    assert not bool(db_session.query(Product).get(p.id).is_active)
    assert not bool(db_session.query(ProductRecord).get(rec_id).is_active)

    # 回滚（同 as_admin 身份）
    resp = client.post(f"/api/v1/proposals/{prop.id}/revert")
    assert resp.status_code == 200
    assert resp.json()["status"] == "reverted"

    db_session.expire_all()
    assert bool(db_session.query(Product).get(p.id).is_active)       # 商品复活
    assert bool(db_session.query(ProductRecord).get(rec_id).is_active)  # 价格记录反级联复活


# ---------- (f2) 管理员回滚 delete 原料 → reverted + 反级联复活 商品+层级 ----------
def test_f2_admin_revert_ingredient_delete_revives_cascade(db_session, as_admin):
    from app.models.change_proposal import ChangeProposal
    from app.models.nutrition import Ingredient
    from app.models.product_entity import Product
    from app.models.ingredient_hierarchy import IngredientHierarchy

    ing_id = _make_ingredient(db_session, name="e2e_f2_主")
    child_id = _make_ingredient(db_session, name="e2e_f2_子")
    p = _make_product(db_session, ing_id, name="e2e_f2_商品")
    h = IngredientHierarchy(parent_id=ing_id, child_id=child_id,
                            relation_type="contains", is_active=True)
    db_session.add(h)
    db_session.commit()
    db_session.refresh(h)

    resp = client.delete(f"/api/v1/nutrition/ingredients/{ing_id}")
    assert resp.status_code == 200
    prop = db_session.query(ChangeProposal).filter(
        ChangeProposal.entity_type == "ingredient",
        ChangeProposal.entity_id == ing_id,
        ChangeProposal.status == "applied",
    ).first()
    assert prop is not None
    assert "cascade_product_ids" in (prop.revert_payload or {})
    assert "cascade_hierarchy_ids" in (prop.revert_payload or {})

    resp = client.post(f"/api/v1/proposals/{prop.id}/revert")
    assert resp.status_code == 200
    assert resp.json()["status"] == "reverted"

    db_session.expire_all()
    assert bool(db_session.query(Ingredient).get(ing_id).is_active)
    assert bool(db_session.query(Product).get(p.id).is_active)
    assert bool(db_session.query(IngredientHierarchy).get(h.id).is_active)


# ---------- (g) 双层检查：端点提交即拒 ----------
def test_g1_non_admin_delete_only_product_rejected_at_endpoint(db_session, as_non_admin):
    """普通用户删唯一商品 → 端点 400，不进 pending。"""
    from app.models.change_proposal import ChangeProposal
    ing_id = _make_ingredient(db_session, name="e2e_g1_ing")
    p = _make_product(db_session, ing_id, name="e2e_g1_唯一")  # 无兄弟
    resp = client.delete(f"/api/v1/products/entity/{p.id}")
    assert resp.status_code == 400
    assert "唯一" in resp.json()["detail"]
    # 未产生提议
    assert db_session.query(ChangeProposal).filter(
        ChangeProposal.entity_type == "product",
        ChangeProposal.entity_id == p.id,
    ).count() == 0


def test_g2_non_admin_delete_ingredient_with_recipe_rejected_at_endpoint(db_session, as_non_admin):
    """普通用户删有菜谱引用的原料 → 端点 400，不进 pending。"""
    from app.models.recipe import RecipeIngredient
    from app.models.change_proposal import ChangeProposal
    ing_id = _make_ingredient(db_session, name="e2e_g2_被引")
    db_session.add(RecipeIngredient(recipe_id=999999, ingredient_id=ing_id,
                                    quantity="1", unit_id=1))
    db_session.commit()
    resp = client.delete(f"/api/v1/nutrition/ingredients/{ing_id}")
    assert resp.status_code == 400
    assert "菜谱" in resp.json()["detail"]
    assert db_session.query(ChangeProposal).filter(
        ChangeProposal.entity_type == "ingredient",
        ChangeProposal.entity_id == ing_id,
    ).count() == 0


# ---------- 补充：管理员直改商品即时生效（apply_as_admin）----------
def test_admin_update_product_applied_immediately(db_session, as_admin):
    from app.models.product_entity import Product
    ing_id = _make_ingredient(db_session, name="e2e_admin_upd_ing")
    p = _make_product(db_session, ing_id, name="e2e_admin_旧")
    resp = client.put(f"/api/v1/products/entity/{p.id}", json={"name": "e2e_admin_新"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "e2e_admin_新"
    db_session.expire_all()
    assert db_session.query(Product).get(p.id).name == "e2e_admin_新"

