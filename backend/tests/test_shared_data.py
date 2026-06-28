"""P2 共享数据测试。"""
import pytest
from conftest import TestingSessionLocal, engine
from app.models.price_summary import ProductMerchantPriceSummary
from app.models.user_merchant_favorite import UserMerchantFavorite
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


# ============================================================
# Task 3.1: 商家合并执行器测试
#
# 复用食材合并的 snapshot/revert 范式：apply 前快照受影响行
# （ProductRecord.merchant_id / user_merchant_favorites / 源商家 is_open+name），
# 迁移引用，软停用源；revert 按快照还原。
# ============================================================


@pytest.fixture()
def db_with_merchants():
    """构造 2 商家 + 关联 ProductRecord + 收藏，返回 (src_id, tgt_id, price_record_id)。

    src 商家(id 运行时分配) 有 1 条 ProductRecord 引用 + 1 条收藏；
    tgt 商家无引用。用于验证合并迁移与回滚还原。
    """
    from app.models.merchant import Merchant
    from app.models.product import ProductRecord
    Base.metadata.create_all(bind=_engine)
    db = _TSL()
    try:
        db.query(ProductRecord).filter(ProductRecord.product_name == "合并测试商品").delete(synchronize_session=False)
        db.query(UserMerchantFavorite).delete(synchronize_session=False)
        db.query(Merchant).filter(Merchant.name.in_(["合并源商家", "合并目标商家"])).delete(synchronize_session=False)
        db.commit()

        src = Merchant(user_id=1, name="合并源商家", is_open=True)
        tgt = Merchant(user_id=1, name="合并目标商家", is_open=True)
        db.add_all([src, tgt]); db.commit(); db.refresh(src); db.refresh(tgt)

        pr = ProductRecord(
            user_id=1, product_id=99, product_name="合并测试商品", merchant_id=src.id,
            price=10, currency="CNY", original_quantity=1, original_unit_id=1,
            standard_quantity=500, standard_unit_id=1, record_type="price",
        )
        db.add(pr)
        fav = UserMerchantFavorite(user_id=1, merchant_id=src.id)
        db.add(fav)
        db.commit(); db.refresh(pr)
        ids = (src.id, tgt.id, pr.id)
    finally:
        db.close()

    yield ids

    db = _TSL()
    try:
        db.query(ProductRecord).filter(ProductRecord.product_name == "合并测试商品").delete(synchronize_session=False)
        db.query(UserMerchantFavorite).delete(synchronize_session=False)
        db.query(Merchant).filter(Merchant.name.in_(["合并源商家", "合并目标商家", "[已合并] 合并源商家"])).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def test_merchant_merge_executor_migrates_references(db_with_merchants):
    """apply 合并：ProductRecord.merchant_id 从源迁到目标，snapshot 含迁移前引用清单。"""
    from app.services.proposals.executors.merchant_merge import MerchantMergeExecutor
    from app.services.proposals.registry import ExecutorRegistry
    from app.models.product import ProductRecord

    src_id, tgt_id, pr_id = db_with_merchants
    ExecutorRegistry.reset()
    ExecutorRegistry.register(MerchantMergeExecutor(), default_policy="manual", default_risk="high")

    ex = ExecutorRegistry.get("merchant_merge")
    proposal = type("P", (), {
        "entity_type": "merchant_merge",
        "entity_id": src_id,
        "action": "merge",
        "payload": {"source_ids": [src_id], "target_id": tgt_id},
        "proposer_id": 1,
        "snapshot": None,
        "revert_payload": None,
    })()

    db = _TSL()
    try:
        result = ex.apply(db, proposal)
        db.commit()

        # 迁移：ProductRecord.merchant_id 从源迁到目标
        pr = db.query(ProductRecord).get(pr_id)
        assert pr.merchant_id == tgt_id

        # snapshot 含迁移前的引用清单
        assert "product_records" in result.snapshot
        assert result.snapshot["product_records"][0]["merchant_id"] == src_id
        assert "favorites" in result.snapshot
        assert result.snapshot["favorites"][0]["merchant_id"] == src_id
        assert "sources" in result.snapshot
        assert result.snapshot["sources"][0]["id"] == src_id

        # 源商家软停用：is_open=False + 名称加前缀
        from app.models.merchant import Merchant
        src_m = db.query(Merchant).get(src_id)
        assert src_m.is_open is False
        assert src_m.name.startswith("[已合并] ")
    finally:
        db.close()


def test_merchant_merge_executor_revert_restores(db_with_merchants):
    """revert：ProductRecord.merchant_id 还原、源商家复活（is_open/名称）、收藏重新插入。"""
    from app.services.proposals.executors.merchant_merge import MerchantMergeExecutor
    from app.services.proposals.registry import ExecutorRegistry
    from app.services.proposals import service as proposal_service
    from app.models.product import ProductRecord
    from app.models.merchant import Merchant

    src_id, tgt_id, pr_id = db_with_merchants
    ExecutorRegistry.reset()
    ExecutorRegistry.register(MerchantMergeExecutor(), default_policy="manual", default_risk="high")

    ex = ExecutorRegistry.get("merchant_merge")
    admin = type("A", (), {"id": 1, "is_admin": True})()

    db = _TSL()
    try:
        # 走 apply_as_admin 落完整快照（service._do_apply 把 snapshot 写入 proposal.snapshot）
        proposal = proposal_service.apply_as_admin(
            db, entity_type="merchant_merge", entity_id=src_id,
            action="merge",
            payload={"source_ids": [src_id], "target_id": tgt_id},
            admin=admin,
        )
        db.commit()

        # 回滚
        proposal_service.revert(db, proposal_id=proposal.id, reviewer=admin)
        db.commit()

        # ProductRecord.merchant_id 还原回源
        pr = db.query(ProductRecord).get(pr_id)
        assert pr.merchant_id == src_id

        # 源商家复活：is_open=True、名称还原
        src_m = db.query(Merchant).get(src_id)
        assert src_m.is_open is True
        assert src_m.name == "合并源商家"

        # 收藏重新插入（user_id+merchant_id 命中）
        fav = db.query(UserMerchantFavorite).filter(
            UserMerchantFavorite.user_id == 1,
            UserMerchantFavorite.merchant_id == src_id,
        ).first()
        assert fav is not None
    finally:
        db.close()


def test_dispatch_merchant_merge_admin_applies(_clean_proposals, db_with_merchants):
    """管理员合并商家 → POST /merchants/merge 经 apply_as_admin 直写，留痕 status=applied。"""
    src_id, tgt_id, _pr_id = db_with_merchants
    client = _TestClient(_app)
    _app.dependency_overrides[_gdb] = _override_get_db
    _app.dependency_overrides[_gcu] = _fake_current_user  # is_admin=True
    try:
        r = client.post("/api/v1/merchants/merge",
                        json={"source_ids": [src_id], "target_id": tgt_id})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["success"] is True
        assert "管理员" in body["message"]
        db = _TSL()
        try:
            cp = db.query(_CP).filter(
                _CP.entity_type == "merchant_merge", _CP.action == "merge"
            ).first()
            assert cp is not None
            assert cp.status == "applied"
        finally:
            db.close()
    finally:
        _app.dependency_overrides.clear()


def test_dispatch_merchant_merge_non_admin_submits(_clean_proposals, db_with_merchants):
    """普通用户合并商家 → submit；治理总表 merchant_merge.merge=manual → pending。"""
    src_id, tgt_id, _pr_id = db_with_merchants
    client = _TestClient(_app)
    _app.dependency_overrides[_gdb] = _override_get_db
    _app.dependency_overrides[_gcu] = _fake_non_admin_user  # is_admin=False, id=2
    try:
        r = client.post("/api/v1/merchants/merge",
                        json={"source_ids": [src_id], "target_id": tgt_id})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["success"] is True
        assert "status=" in body["message"]
        db = _TSL()
        try:
            cp = db.query(_CP).filter(
                _CP.entity_type == "merchant_merge", _CP.action == "merge"
            ).first()
            assert cp is not None
            assert cp.status == "pending"
            assert cp.proposer_id == 2
        finally:
            db.close()
    finally:
        _app.dependency_overrides.clear()
