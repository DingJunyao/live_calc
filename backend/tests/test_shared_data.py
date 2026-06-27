"""P2 共享数据测试。"""
import pytest
from conftest import TestingSessionLocal, engine
from app.models.price_summary import ProductMerchantPriceSummary
from app.core.database import Base


def test_summary_has_no_user_or_record_type_columns():
    """汇总表去标识：不含 user_id / record_type。"""
    cols = {c.name for c in ProductMerchantPriceSummary.__table__.columns}
    assert "user_id" not in cols
    assert "record_type" not in cols


def test_recompute_summary_aggregates_price_records():
    """recompute_summary 把 ProductRecord（PRICE+PURCHASE）聚合为单价 ¥/斤 写入汇总表。"""
    from app.services.price_aggregator import recompute_summary
    from app.models.product import ProductRecord

    # 确保表存在（conftest 导入时已 create_all，这里幂等再保一次）
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        # 清理 + 构造 3 条 ProductRecord（2 PRICE + 1 PURCHASE，同 product×merchant）
        db.query(ProductRecord).delete()
        db.query(ProductMerchantPriceSummary).delete()
        db.commit()
        # 单价 = price × 500 / standard_quantity
        #  - price=10, std=500 → 10 ¥/斤（最近一条，records 按 recorded_at desc 取首）
        #  - price=20, std=1000 → 10 ¥/斤
        #  - price=30, std=250 → 60 ¥/斤
        for price, std, rt in [(10.0, 500, "price"), (20.0, 1000, "price"), (30.0, 250, "purchase")]:
            db.add(ProductRecord(
                user_id=1, product_id=10, product_name="测试", merchant_id=5,
                price=price, currency="CNY", original_quantity=1, original_unit_id=1,
                standard_quantity=std, standard_unit_id=1, record_type=rt,
            ))
        db.commit()
        recompute_summary(db, product_id=10, merchant_id=5)
        db.commit()
        row = db.query(ProductMerchantPriceSummary).filter_by(product_id=10, merchant_id=5).first()
        assert row is not None
        # 3 条都参与了聚合（PRICE + PURCHASE 一视同仁）
        assert row.sample_count == 3
        # 全部归一化为 ¥/斤 单价：min=10, max=60, avg=(10+10+60)/3=26.67
        assert row.min_price is not None and float(row.min_price) == 10.0
        assert row.max_price is not None and float(row.max_price) == 60.0
        assert row.avg_price_30d is not None and abs(float(row.avg_price_30d) - 80.0 / 3) < 0.01
        # recent_price：按 recorded_at desc 取首条有效单价；3 条同时间戳时取 ORM 返回首条
        assert row.recent_price is not None
    finally:
        db.query(ProductRecord).delete()
        db.query(ProductMerchantPriceSummary).delete()
        db.commit()
        db.close()


# ---------- merchants.py 共享池 ----------


@pytest.fixture()
def clean_merchants():
    """插入一条 user_id=999 的商家，yield 其 id，teardown 删除。

    语义：商家现在是「共享池」，user_id 仅代表录入者（999 = 他人的标记），
    任意登录用户都应能在列表中看到它。
    """
    from app.models.merchant import Merchant

    # 确保表存在（内存库在 conftest 导入时已 create_all，这里幂等再保一次）
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        db.query(Merchant).delete()
        db.commit()
        m = Merchant(user_id=999, name="他人商家", is_open=True)
        db.add(m)
        db.commit()
        db.refresh(m)
        merchant_id = m.id
    finally:
        db.close()

    yield merchant_id

    db = TestingSessionLocal()
    try:
        db.query(Merchant).delete()
        db.commit()
    finally:
        db.close()


def test_merchant_list_visible_to_all_logged_in_users(clean_merchants):
    """商家是共享池，任意登录用户可见全部（含他人录入的）。"""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db as _gdb
    from app.core.security import get_current_user as _gcu
    from conftest import override_get_db, _fake_non_admin_user

    client = TestClient(app)
    app.dependency_overrides[_gdb] = override_get_db
    app.dependency_overrides[_gcu] = _fake_non_admin_user
    try:
        r = client.get("/api/v1/merchants")
        assert r.status_code == 200
        # clean_merchants 插入了 user_id=999 的商家，非管理员（id=2）能看到
        ids = [m["id"] for m in r.json()["items"]]
        assert clean_merchants in ids
    finally:
        app.dependency_overrides.clear()


# ============================================================
# Task 2.5b: 共享写端点分流测试
#
# 每类改造的端点至少一个管理员直写 + 一个普通用户提交的测试，
# 覆盖 ingredient.merge / unit.create / hierarchy.create / merchant.update。
# 框架依赖 ExecutorRegistry 已注册（本模块 autouse fixture 注册）。
# ============================================================

import pytest as _pytest
from fastapi.testclient import TestClient as _TestClient
from app.main import app as _app
from app.core.database import get_db as _gdb
from app.core.security import get_current_user as _gcu
from conftest import (
    override_get_db as _override_get_db,
    fake_current_user as _fake_current_user,
    _fake_non_admin_user as _fake_non_admin_user,
    TestingSessionLocal as _TSL,
    engine as _engine,
)
from app.services.proposals.registry import ExecutorRegistry as _ER
from app.services.proposals.bootstrap import register_all as _register_all
from app.models.change_proposal import ChangeProposal as _CP


@_pytest.fixture(autouse=True, scope="module")
def _ensure_executors_registered():
    """模块级注册执行器（TestClient 不触发 main.py lifespan）。"""
    if not _ER.get("ingredient"):
        _register_all()
    yield


@_pytest.fixture()
def _clean_proposals():
    """每个测试前后清空 change_proposals，避免影响断言。"""
    Base.metadata.create_all(bind=_engine)
    db = _TSL()
    try:
        db.query(_CP).delete()
        db.commit()
    finally:
        db.close()
    yield
    db = _TSL()
    try:
        db.query(_CP).delete()
        db.commit()
    finally:
        db.close()


def _seed_ingredients_for_merge():
    """构造两个由管理员（id=1）创建的食材，返回 (src_id, tgt_id)。"""
    from app.models.nutrition import Ingredient
    Base.metadata.create_all(bind=_engine)
    db = _TSL()
    try:
        db.query(Ingredient).filter(Ingredient.name.in_(["分流测试源", "分流测试目标"])).delete(synchronize_session=False)
        db.commit()
        src = Ingredient(name="分流测试源", created_by=1)
        tgt = Ingredient(name="分流测试目标", created_by=1)
        db.add_all([src, tgt]); db.commit(); db.refresh(src); db.refresh(tgt)
        return src.id, tgt.id
    finally:
        db.close()


def _cleanup_ingredients(src_id, tgt_id):
    from app.models.nutrition import Ingredient
    from app.models.ingredient_merge_record import IngredientMergeRecord
    db = _TSL()
    try:
        db.query(IngredientMergeRecord).delete(synchronize_session=False)
        for iid in (src_id, tgt_id):
            ing = db.query(Ingredient).filter(Ingredient.id == iid).first()
            if ing:
                db.delete(ing)
        db.commit()
    finally:
        db.close()


def test_dispatch_ingredient_merge_admin_applies_directly(_clean_proposals):
    """管理员合并食材 → 经 apply_as_admin 直写，change_proposals 留痕 status=applied。"""
    src_id, tgt_id = _seed_ingredients_for_merge()
    client = _TestClient(_app)
    _app.dependency_overrides[_gdb] = _override_get_db
    _app.dependency_overrides[_gcu] = _fake_current_user  # is_admin=True
    try:
        r = client.post("/api/v1/ingredients/merge",
                        json={"source_ingredient_ids": [src_id], "target_ingredient_id": tgt_id})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["success"] is True
        assert "管理员直写" in body["message"]
        # 留痕：change_proposals 一条 applied 记录
        db = _TSL()
        try:
            cp = db.query(_CP).filter(
                _CP.entity_type == "ingredient", _CP.action == "merge"
            ).first()
            assert cp is not None
            assert cp.status == "applied"
        finally:
            db.close()
    finally:
        _app.dependency_overrides.clear()
        _cleanup_ingredients(src_id, tgt_id)


def test_dispatch_ingredient_merge_non_admin_submits_proposal(_clean_proposals):
    """普通用户合并自己创建的食材 → submit 提议；治理总表 ingredient.merge=manual → pending。"""
    src_id, tgt_id = _seed_ingredients_for_merge()
    # 改成非管理员「拥有」的食材（created_by=2 = NonAdminFakeUser.id）
    from app.models.nutrition import Ingredient
    db = _TSL()
    try:
        for ing in db.query(Ingredient).filter(Ingredient.id.in_([src_id, tgt_id])).all():
            ing.created_by = 2
        db.commit()
    finally:
        db.close()

    client = _TestClient(_app)
    _app.dependency_overrides[_gdb] = _override_get_db
    _app.dependency_overrides[_gcu] = _fake_non_admin_user  # is_admin=False, id=2
    try:
        r = client.post("/api/v1/ingredients/merge",
                        json={"source_ingredient_ids": [src_id], "target_ingredient_id": tgt_id})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["success"] is True
        assert "status=" in body["message"]
        # 提议已落库，pending（治理总表 manual）
        db = _TSL()
        try:
            cp = db.query(_CP).filter(
                _CP.entity_type == "ingredient", _CP.action == "merge"
            ).first()
            assert cp is not None
            assert cp.status == "pending"
            assert cp.proposer_id == 2
        finally:
            db.close()
    finally:
        _app.dependency_overrides.clear()
        _cleanup_ingredients(src_id, tgt_id)


def test_dispatch_unit_create_admin_applies(_clean_proposals):
    """管理员创建单位 → apply_as_admin 直写，单位立即生效。"""
    client = _TestClient(_app)
    _app.dependency_overrides[_gdb] = _override_get_db
    _app.dependency_overrides[_gcu] = _fake_current_user
    name, abbr = "分流单管", "fdug"
    try:
        r = client.post("/api/v1/units/",
                        json={"name": name, "abbreviation": abbr, "unit_type": "count"})
        assert r.status_code in (200, 201), r.text
        # 留痕
        db = _TSL()
        try:
            cp = db.query(_CP).filter(
                _CP.entity_type == "unit", _CP.action == "create"
            ).first()
            assert cp is not None and cp.status == "applied"
        finally:
            db.close()
    finally:
        _app.dependency_overrides.clear()
        from app.models.unit import Unit
        db = _TSL()
        try:
            db.query(Unit).filter(Unit.abbreviation == abbr).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()


def test_dispatch_unit_create_non_admin_auto_approve(_clean_proposals):
    """普通用户创建单位 → submit；治理总表 unit.create=auto_approve → 立即 applied。"""
    client = _TestClient(_app)
    _app.dependency_overrides[_gdb] = _override_get_db
    _app.dependency_overrides[_gcu] = _fake_non_admin_user
    name, abbr = "分流非管", "fdng"
    try:
        r = client.post("/api/v1/units/",
                        json={"name": name, "abbreviation": abbr, "unit_type": "count"})
        assert r.status_code in (200, 201), r.text
        db = _TSL()
        try:
            cp = db.query(_CP).filter(
                _CP.entity_type == "unit", _CP.action == "create"
            ).first()
            assert cp is not None and cp.status == "applied"
            assert cp.proposer_id == 2
        finally:
            db.close()
    finally:
        _app.dependency_overrides.clear()
        from app.models.unit import Unit
        db = _TSL()
        try:
            db.query(Unit).filter(Unit.abbreviation == abbr).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()


def _seed_ingredients_for_hierarchy():
    """构造两个食材用于 hierarchy create，返回 (parent_id, child_id)。"""
    from app.models.nutrition import Ingredient
    Base.metadata.create_all(bind=_engine)
    db = _TSL()
    try:
        db.query(Ingredient).filter(Ingredient.name.in_(["分流父层", "分流子层"])).delete(synchronize_session=False)
        db.commit()
        p = Ingredient(name="分流父层")
        c = Ingredient(name="分流子层")
        db.add_all([p, c]); db.commit(); db.refresh(p); db.refresh(c)
        return p.id, c.id
    finally:
        db.close()


def _cleanup_hierarchy(parent_id, child_id):
    from app.models.ingredient_hierarchy import IngredientHierarchy
    from app.models.nutrition import Ingredient
    db = _TSL()
    try:
        db.query(IngredientHierarchy).filter(IngredientHierarchy.parent_id == parent_id).delete(synchronize_session=False)
        for iid in (parent_id, child_id):
            ing = db.query(Ingredient).filter(Ingredient.id == iid).first()
            if ing:
                db.delete(ing)
        db.commit()
    finally:
        db.close()


def test_dispatch_hierarchy_create_admin_applies(_clean_proposals):
    """管理员创建层级关系 → apply_as_admin 直写。"""
    parent_id, child_id = _seed_ingredients_for_hierarchy()
    client = _TestClient(_app)
    _app.dependency_overrides[_gdb] = _override_get_db
    _app.dependency_overrides[_gcu] = _fake_current_user
    try:
        r = client.post("/api/v1/ingredients/hierarchy",
                        json={"parent_id": parent_id, "child_id": child_id,
                              "relation_type": "contains", "strength": 50})
        assert r.status_code == 200, r.text
        db = _TSL()
        try:
            cp = db.query(_CP).filter(
                _CP.entity_type == "hierarchy", _CP.action == "create"
            ).first()
            assert cp is not None and cp.status == "applied"
        finally:
            db.close()
    finally:
        _app.dependency_overrides.clear()
        _cleanup_hierarchy(parent_id, child_id)


def test_dispatch_hierarchy_create_non_admin_pending(_clean_proposals):
    """普通用户创建层级关系 → submit；治理总表 hierarchy 全 manual → pending。"""
    parent_id, child_id = _seed_ingredients_for_hierarchy()
    client = _TestClient(_app)
    _app.dependency_overrides[_gdb] = _override_get_db
    _app.dependency_overrides[_gcu] = _fake_non_admin_user
    try:
        r = client.post("/api/v1/ingredients/hierarchy",
                        json={"parent_id": parent_id, "child_id": child_id,
                              "relation_type": "contains", "strength": 50})
        assert r.status_code == 200, r.text
        db = _TSL()
        try:
            cp = db.query(_CP).filter(
                _CP.entity_type == "hierarchy", _CP.action == "create"
            ).first()
            assert cp is not None and cp.status == "pending"
            assert cp.proposer_id == 2
        finally:
            db.close()
    finally:
        _app.dependency_overrides.clear()
        _cleanup_hierarchy(parent_id, child_id)


def test_dispatch_merchant_update_admin_applies(_clean_proposals, clean_merchants):
    """管理员更新商家 → apply_as_admin 直写。"""
    client = _TestClient(_app)
    _app.dependency_overrides[_gdb] = _override_get_db
    _app.dependency_overrides[_gcu] = _fake_current_user
    try:
        r = client.put(f"/api/v1/merchants/{clean_merchants}",
                       json={"name": "管理员改名"})
        assert r.status_code == 200, r.text
        db = _TSL()
        try:
            cp = db.query(_CP).filter(
                _CP.entity_type == "merchant", _CP.action == "update"
            ).first()
            assert cp is not None and cp.status == "applied"
        finally:
            db.close()
    finally:
        _app.dependency_overrides.clear()


def test_dispatch_merchant_update_non_admin_pending(_clean_proposals, clean_merchants):
    """普通用户更新商家 → submit；治理总表 merchant.update=manual → pending。"""
    client = _TestClient(_app)
    _app.dependency_overrides[_gdb] = _override_get_db
    _app.dependency_overrides[_gcu] = _fake_non_admin_user
    try:
        r = client.put(f"/api/v1/merchants/{clean_merchants}",
                       json={"name": "用户提议改名"})
        # 非管理员：submit 提议（manual → pending），仍返回 200 + 当前商家（未变）
        assert r.status_code == 200, r.text
        db = _TSL()
        try:
            cp = db.query(_CP).filter(
                _CP.entity_type == "merchant", _CP.action == "update"
            ).first()
            assert cp is not None and cp.status == "pending"
            assert cp.proposer_id == 2
        finally:
            db.close()
    finally:
        _app.dependency_overrides.clear()
