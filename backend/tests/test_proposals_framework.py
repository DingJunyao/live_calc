"""P1 框架单元测试：执行器基类、自动审核协议、默认实现。"""
from app.services.proposals.base import ApplyResult, ProposalExecutor
from app.services.proposals.auto_reviewer import DefaultAutoReviewer


def test_apply_result_defaults():
    r = ApplyResult(snapshot={"a": 1}, revert_payload={"undo": True})
    assert r.snapshot == {"a": 1}
    assert r.revert_payload == {"undo": True}
    assert r.summary == ""


def test_default_auto_reviewer_escalates():
    reviewer = DefaultAutoReviewer()
    result = reviewer.review(db=None, proposal=None)
    assert result.decision == "escalate"
    assert "默认" in result.reason or "escalate" in result.reason


# --- Task 1.3: 执行器注册表 + 策略配置 ---
from app.services.proposals.registry import ExecutorRegistry


class _StubExecutor(ProposalExecutor):
    entity_type = "stub"

    def validate(self, db, proposal):
        pass

    def preview(self, db, proposal):
        return {"note": "stub"}

    def apply(self, db, proposal):
        return ApplyResult(snapshot={"x": 1}, revert_payload={"x": 0}, summary="stub applied")

    def revert(self, db, proposal):
        pass


def test_registry_register_and_get():
    ExecutorRegistry.reset()
    ExecutorRegistry.register(_StubExecutor())
    assert ExecutorRegistry.get("stub").entity_type == "stub"
    assert ExecutorRegistry.get("missing") is None


def test_registry_policy_default_and_override():
    ExecutorRegistry.reset()
    ExecutorRegistry.register(_StubExecutor())
    # 默认 policy = manual
    assert ExecutorRegistry.policy_for("stub", "update") == "manual"
    # 覆盖
    ExecutorRegistry.set_policy("stub", "update", "auto_approve")
    assert ExecutorRegistry.policy_for("stub", "update") == "auto_approve"


# --- Task 1.4: 提议业务服务（submit/review/revert/apply_as_admin） ---
import pytest
from app.services.proposals import service as proposal_service
from app.core.database import Base
import app.models.change_proposal  # noqa: F401 — 确保 ChangeProposal 注册到 metadata
from conftest import TestingSessionLocal, engine as _testing_engine
from app.models.change_proposal import ChangeProposal


class _RecordingExecutor(ProposalExecutor):
    """记录 apply/revert 调用，便于断言。"""
    entity_type = "rec"
    applied = 0
    reverted = 0

    def validate(self, db, proposal): pass
    def preview(self, db, proposal): return {}
    def apply(self, db, proposal):
        type(self).applied += 1
        return ApplyResult(snapshot={"v": 1}, revert_payload={"v": 0}, summary="ok")
    def revert(self, db, proposal):
        type(self).reverted += 1


@pytest.fixture()
def db():
    # 确保内存库已建表（conftest 的 create_all 在本模块导入前执行，可能未含 change_proposals）
    Base.metadata.create_all(bind=_testing_engine)
    s = TestingSessionLocal()
    yield s
    s.query(ChangeProposal).delete(); s.commit(); s.close()


@pytest.fixture(autouse=True)
def _reset_registry():
    ExecutorRegistry.reset()
    ExecutorRegistry.register(_RecordingExecutor())
    _RecordingExecutor.applied = 0
    _RecordingExecutor.reverted = 0
    yield


class _U:
    id = 5
    is_admin = False


def test_submit_manual_stays_pending(db):
    ExecutorRegistry.set_policy("rec", "update", "manual")
    p = proposal_service.submit(db, entity_type="rec", entity_id=1, action="update",
                                payload={"v": 1}, proposer=_U())
    db.commit()
    assert p.status == "pending"
    assert _RecordingExecutor.applied == 0


def test_submit_auto_approve_applies(db):
    ExecutorRegistry.set_policy("rec", "update", "auto_approve")
    p = proposal_service.submit(db, entity_type="rec", entity_id=1, action="update",
                                payload={"v": 1}, proposer=_U())
    db.commit()
    assert p.status == "applied"
    assert _RecordingExecutor.applied == 1
    assert p.snapshot == {"v": 1}
    assert p.revert_payload == {"v": 0}


def test_review_approve_applies(db):
    ExecutorRegistry.set_policy("rec", "update", "manual")
    p = proposal_service.submit(db, entity_type="rec", entity_id=1, action="update",
                                payload={"v": 1}, proposer=_U())
    db.commit()
    admin = type("A", (), {"id": 1, "is_admin": True})()
    proposal_service.review(db, proposal_id=p.id, approved=True, reviewer=admin, note="ok")
    db.commit()
    assert p.status == "applied"
    assert _RecordingExecutor.applied == 1
    assert p.reviewer_id == 1


def test_revert_calls_executor(db):
    ExecutorRegistry.set_policy("rec", "update", "auto_approve")
    p = proposal_service.submit(db, entity_type="rec", entity_id=1, action="update",
                                payload={"v": 1}, proposer=_U())
    db.commit()
    admin = type("A", (), {"id": 1, "is_admin": True})()
    proposal_service.revert(db, proposal_id=p.id, reviewer=admin)
    db.commit()
    assert p.status == "reverted"
    assert _RecordingExecutor.reverted == 1


# --- Task 1.6: 提议-审核 API + 路由注册 ---
from fastapi.testclient import TestClient
from app.main import app as _fastapi_app   # 别名：避免后续 `import app.models.X` 覆盖
from app.core.database import get_db as _get_db
from app.core.security import get_current_user as _get_cu
from conftest import (
    override_get_db,
    fake_current_user,
    _fake_non_admin_user,
    engine as _testing_engine,
)

api_client = TestClient(_fastapi_app)


def test_submit_via_api_requires_auth():
    """未登录提交提议 → 401。"""
    # 不安装 dependency_overrides → get_current_user 走真实鉴权，无 token → 401
    _fastapi_app.dependency_overrides.clear()
    r = api_client.post("/api/v1/proposals", json={
        "entity_type": "rec", "entity_id": 1, "action": "update", "payload": {}})
    assert r.status_code in (401, 403)


def test_non_admin_submit_then_admin_review():
    """非管理员提交 → pending；非管理员审核 → 403；管理员审核 → applied。"""
    ExecutorRegistry.reset()
    ExecutorRegistry.register(_RecordingExecutor())
    ExecutorRegistry.set_policy("rec", "update", "manual")

    _fastapi_app.dependency_overrides[_get_db] = override_get_db
    _fastapi_app.dependency_overrides[_get_cu] = _fake_non_admin_user
    try:
        # 确保 change_proposals 表在测试 DB 存在（conftest create_all 早于模型注册）
        Base.metadata.create_all(bind=_testing_engine)

        # 非管理员提交
        r = api_client.post("/api/v1/proposals", json={
            "entity_type": "rec", "entity_id": 1, "action": "update", "payload": {"v": 1}})
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        assert r.json()["status"] == "pending"

        # 非管理员审核 → 403
        r2 = api_client.post(f"/api/v1/proposals/{pid}/review", json={"approved": True})
        assert r2.status_code == 403

        # 管理员审核 → applied
        _fastapi_app.dependency_overrides[_get_cu] = fake_current_user
        r3 = api_client.post(f"/api/v1/proposals/{pid}/review", json={"approved": True})
        assert r3.status_code == 200, r3.text
        assert r3.json()["status"] == "applied"
    finally:
        _fastapi_app.dependency_overrides.clear()


# --- Task 2.4: 菜谱发布执行器 ---
def test_recipe_publish_executor_sets_is_public(db):
    from app.services.proposals.executors.recipe_publish import RecipePublishExecutor
    from app.models.recipe import Recipe
    from conftest import engine as _testing_engine
    Base.metadata.create_all(bind=_testing_engine)
    # 插一条私有菜谱
    r = Recipe(name="测试菜谱", user_id=5, source=None)
    db.add(r); db.commit(); db.refresh(r)
    rid = r.id

    ExecutorRegistry.reset()
    ExecutorRegistry.register(RecipePublishExecutor(), default_policy="manual", default_risk="mid")
    ex = ExecutorRegistry.get("recipe")
    proposal = type("P", (), {"entity_type": "recipe", "entity_id": rid,
                              "action": "publish", "payload": {}, "proposer_id": 5})()
    result = ex.apply(db, proposal)
    db.commit()
    refreshed = db.query(Recipe).get(rid)
    assert refreshed.is_public is True
    assert result.revert_payload == {"set_public": False}


# --- Task 2.5: 业务执行器（ingredient 合并 snapshot/revert + 简单执行器 CRUD） ---
import app.models.nutrition  # noqa: F401 — 注册 Ingredient 等到 metadata
import app.models.recipe  # noqa: F401
import app.models.product  # noqa: F401
import app.models.product_ingredient_link  # noqa: F401
import app.models.ingredient_hierarchy  # noqa: F401
import app.models.ingredient_merge_record  # noqa: F401
import app.models.ingredient_category  # noqa: F401
import app.models.unit  # noqa: F401
import app.models.merchant  # noqa: F401
import app.models.nutrition_data  # noqa: F401
from app.models.nutrition import Ingredient, IngredientNutritionMapping
from app.models.recipe import Recipe, RecipeIngredient
from app.models.product_ingredient_link import ProductIngredientLink
from app.models.ingredient_hierarchy import IngredientHierarchy
from app.models.ingredient_merge_record import IngredientMergeRecord
from app.models.unit import Unit
from app.models.merchant import Merchant
from app.models.product import ProductRecord, RecordType
from app.models.nutrition_data import NutritionData
from app.services.proposals.executors.ingredient import IngredientExecutor
from app.services.proposals.executors.unit import UnitExecutor
from app.services.proposals.executors.hierarchy import HierarchyExecutor
from app.services.proposals.executors.merchant import MerchantExecutor
from app.services.proposals.executors.nutrition import NutritionExecutor
from app.services.proposals.bootstrap import register_all


def _proposal(entity_type, entity_id, action, payload, proposer_id=5):
    """构造一个最小 proposal 对象（满足执行器读取的字段）。"""
    return type("P", (), {
        "entity_type": entity_type, "entity_id": entity_id, "action": action,
        "payload": payload, "proposer_id": proposer_id,
        "snapshot": None, "revert_payload": None,
    })()


def test_ingredient_merge_executor_snapshots_and_reverts(db):
    """合并执行器：apply 快照受影响行 + 迁移引用；revert 还原引用 + 复活源 + 删合并记录。"""
    Base.metadata.create_all(bind=_testing_engine)
    # 构造：源食材 A、目标食材 B；A 被 recipe 引用 + product link + hierarchy
    src = Ingredient(name="土豆")
    tgt = Ingredient(name="马铃薯")
    db.add_all([src, tgt]); db.commit(); db.refresh(src); db.refresh(tgt)
    rec = Recipe(name="土豆丝", user_id=5, source=None)
    db.add(rec); db.commit(); db.refresh(rec)
    unit = Unit(name="克_test_ing", abbreviation="g_ti", unit_type="mass")
    db.add(unit); db.commit(); db.refresh(unit)
    ri = RecipeIngredient(recipe_id=rec.id, ingredient_id=src.id, quantity="100", unit_id=unit.id)
    db.add(ri)
    hi = IngredientHierarchy(parent_id=src.id, child_id=tgt.id, relation_type="contains", strength=50)
    db.add(hi); db.commit()
    # ProductIngredientLink.product_id / IngredientNutritionMapping.nutrition_id 均非空，
    # 需真实 Product / NutritionData 才能构造；此处只验 recipe_ingredients + hierarchies
    # 两类引用的 snapshot/revert（核心机制一致），足以覆盖迁移 + 还原路径。

    ExecutorRegistry.reset()
    register_all()
    ex = ExecutorRegistry.get("ingredient")

    proposal = _proposal("ingredient", tgt.id, "merge",
                         {"source_ids": [src.id], "target_id": tgt.id})

    # --- apply ---
    result = ex.apply(db, proposal)
    db.commit()

    # snapshot 含受影响行
    assert len(result.snapshot["sources"]) == 1
    assert result.snapshot["sources"][0]["id"] == src.id
    assert len(result.snapshot["hierarchies"]) == 1
    # 引用已迁移到目标
    ri_after = db.query(RecipeIngredient).filter_by(recipe_id=rec.id).first()
    assert ri_after.ingredient_id == tgt.id
    # 源食材被标记合并
    src_after = db.query(Ingredient).get(src.id)
    assert src_after.is_merged is True
    assert src_after.merged_into_id == tgt.id
    # 合并记录存在
    merge_recs = db.query(IngredientMergeRecord).filter_by(
        source_ingredient_id=src.id, target_ingredient_id=tgt.id).all()
    assert len(merge_recs) == 1

    # --- revert（模拟 service.revert：先回填 snapshot/revert_payload 到 proposal）---
    proposal.snapshot = result.snapshot
    proposal.revert_payload = result.revert_payload
    ex.revert(db, proposal)
    db.commit()

    # 引用还原
    ri_restored = db.query(RecipeIngredient).filter_by(recipe_id=rec.id).first()
    assert ri_restored.ingredient_id == src.id
    # 源食材复活
    src_restored = db.query(Ingredient).get(src.id)
    assert src_restored.is_merged is False
    assert src_restored.merged_into_id is None
    # 合并记录删除
    merge_recs_after = db.query(IngredientMergeRecord).filter_by(
        source_ingredient_id=src.id, target_ingredient_id=tgt.id).all()
    assert len(merge_recs_after) == 0


def test_unit_executor_create_and_revert(db):
    Base.metadata.create_all(bind=_testing_engine)
    ExecutorRegistry.reset()
    register_all()
    ex = ExecutorRegistry.get("unit")
    payload = {"name": "撮_test", "abbreviation": "cuo_t", "unit_type": "count"}
    proposal = _proposal("unit", None, "create", payload)
    result = ex.apply(db, proposal)
    db.commit()
    assert result.revert_payload["delete_id"] is not None
    created = db.query(Unit).filter_by(name="撮_test").first()
    assert created is not None
    # revert 删除
    proposal.snapshot = result.snapshot
    proposal.revert_payload = result.revert_payload
    ex.revert(db, proposal)
    db.commit()
    assert db.query(Unit).filter_by(name="撮_test").first() is None


def test_unit_executor_rejects_standard_unit_change(db):
    Base.metadata.create_all(bind=_testing_engine)
    ExecutorRegistry.reset()
    register_all()
    ex = ExecutorRegistry.get("unit")
    u = Unit(name="斤_std", abbreviation="jin_std", unit_type="mass", is_standard=True)
    db.add(u); db.commit(); db.refresh(u)
    import pytest as _pytest
    with _pytest.raises(Exception):
        ex.validate(db, _proposal("unit", u.id, "update", {"name": "改"}))


def test_hierarchy_executor_create_and_revert(db):
    Base.metadata.create_all(bind=_testing_engine)
    # 构造两个食材做 parent/child
    a = Ingredient(name="父_hi"); b = Ingredient(name="子_hi")
    db.add_all([a, b]); db.commit(); db.refresh(a); db.refresh(b)
    ExecutorRegistry.reset()
    register_all()
    ex = ExecutorRegistry.get("hierarchy")
    payload = {"parent_id": a.id, "child_id": b.id, "relation_type": "contains", "strength": 80}
    proposal = _proposal("hierarchy", None, "create", payload)
    result = ex.apply(db, proposal)
    db.commit()
    h = db.query(IngredientHierarchy).filter_by(parent_id=a.id, child_id=b.id).first()
    assert h is not None and h.strength == 80
    proposal.snapshot = result.snapshot
    proposal.revert_payload = result.revert_payload
    ex.revert(db, proposal)
    db.commit()
    assert db.query(IngredientHierarchy).filter_by(parent_id=a.id, child_id=b.id).first() is None


def test_merchant_executor_delete_and_revert_with_references(db):
    """商家删除：软停用 + 引用置 NULL；revert 还原名称/状态 + 还原引用。"""
    Base.metadata.create_all(bind=_testing_engine)
    ExecutorRegistry.reset()
    register_all()
    ex = ExecutorRegistry.get("merchant")
    m = Merchant(name="测试商家", user_id=5, is_open=True)
    db.add(m); db.commit(); db.refresh(m)
    # 需真实 Product（ingredient_id 非空）+ Unit 给 ProductRecord
    prod_ing = Ingredient(name="测试商品食材_m")
    db.add(prod_ing); db.commit(); db.refresh(prod_ing)
    from app.models.product_entity import Product
    prod = Product(name="测试商品", ingredient_id=prod_ing.id)
    db.add(prod); db.commit(); db.refresh(prod)
    u = Unit(name="克_m_test", abbreviation="g_mt", unit_type="mass")
    db.add(u); db.commit(); db.refresh(u)
    pr = ProductRecord(user_id=5, product_id=prod.id, product_name="测试商品",
                       merchant_id=m.id, price=10, original_quantity=1, original_unit_id=u.id,
                       standard_quantity=1, standard_unit_id=u.id)
    db.add(pr); db.commit(); db.refresh(pr)
    pr_id = pr.id

    proposal = _proposal("merchant", m.id, "delete", {})
    result = ex.apply(db, proposal)
    db.commit()
    refreshed_m = db.query(Merchant).get(m.id)
    assert refreshed_m.is_open is False
    assert refreshed_m.name.startswith("[已停用] ")
    refreshed_pr = db.query(ProductRecord).get(pr_id)
    assert refreshed_pr.merchant_id is None
    # snapshot 含引用
    assert len(result.snapshot["product_records"]) == 1
    assert result.snapshot["product_records"][0]["id"] == pr_id

    # revert
    proposal.snapshot = result.snapshot
    proposal.revert_payload = result.revert_payload
    ex.revert(db, proposal)
    db.commit()
    m_restored = db.query(Merchant).get(m.id)
    assert m_restored.is_open is True
    assert m_restored.name == "测试商家"
    pr_restored = db.query(ProductRecord).get(pr_id)
    assert pr_restored.merchant_id == m.id


# --- Task 3.2: 反垃圾——一键回退某用户全部已生效提议 ---
def test_revert_all_by_user_admin_only_and_bulk(db):
    from app.services.proposals import service as proposal_service
    from app.services.proposals.registry import ExecutorRegistry
    ExecutorRegistry.reset(); ExecutorRegistry.register(_RecordingExecutor())
    ExecutorRegistry.set_policy("rec", "update", "auto_approve")
    u = type("U", (), {"id": 5, "is_admin": False})()
    for _ in range(3):
        p = proposal_service.submit(db, entity_type="rec", entity_id=1,
                                    action="update", payload={"v": 1}, proposer=u)
    db.commit()
    admin = type("A", (), {"id": 1, "is_admin": True})()
    n = proposal_service.revert_all_by_user(db, user_id=5, reviewer=admin)
    db.commit()
    assert n == 3
    assert _RecordingExecutor.reverted == 3


def test_register_all_sets_governance_policies():
    """治理总表策略在 register_all 后正确落地。"""
    ExecutorRegistry.reset()
    register_all()
    # 食材
    assert ExecutorRegistry.policy_for("ingredient", "create") == "auto_approve"
    assert ExecutorRegistry.policy_for("ingredient", "update") == "manual"
    assert ExecutorRegistry.policy_for("ingredient", "delete") == "manual"
    assert ExecutorRegistry.policy_for("ingredient", "merge") == "manual"
    assert ExecutorRegistry.risk_for("ingredient", "merge") == "high"
    assert ExecutorRegistry.risk_for("ingredient", "delete") == "high"
    # 营养默认 manual
    assert ExecutorRegistry.policy_for("nutrition", "update") == "manual"
    # 单位
    assert ExecutorRegistry.policy_for("unit", "create") == "auto_approve"
    assert ExecutorRegistry.policy_for("unit", "update") == "manual"
    # 层级全 manual
    assert ExecutorRegistry.policy_for("hierarchy", "create") == "manual"
    # 商家
    assert ExecutorRegistry.policy_for("merchant", "create") == "auto_approve"
    assert ExecutorRegistry.policy_for("merchant", "update") == "manual"
    assert ExecutorRegistry.risk_for("merchant", "update") == "high"
    # 菜谱
    assert ExecutorRegistry.policy_for("recipe", "publish") == "manual"
    # 6 个执行器全部注册
    for et in ("ingredient", "nutrition", "unit", "hierarchy", "merchant", "recipe"):
        assert ExecutorRegistry.get(et) is not None


# --- 审核策略配置 API（GET/PUT /proposals/policies）+ 持久化 ---
from app.models.system_config import SystemConfig


def _setup_real_executors(db):
    """注册真实执行器（覆盖 autouse fixture 的 _RecordingExecutor），返回 db。"""
    ExecutorRegistry.reset()
    from app.services.proposals.bootstrap import register_all
    register_all(db=db)
    # 清掉历史持久化策略键，确保测试起点干净
    db.query(SystemConfig).filter(SystemConfig.key.like("proposal_policy:%")).delete()
    db.commit()
    # 重载默认（删除后 registry 仍持有上次 load 的值 → 重置）
    ExecutorRegistry.reset()
    register_all(db=db)


def test_list_policies_requires_admin():
    """非管理员访问 GET /proposals/policies → 403。"""
    _fastapi_app.dependency_overrides.clear()
    _fastapi_app.dependency_overrides[_get_db] = override_get_db
    _fastapi_app.dependency_overrides[_get_cu] = _fake_non_admin_user
    try:
        Base.metadata.create_all(bind=_testing_engine)
        r = api_client.get("/api/v1/proposals/policies")
        assert r.status_code == 403
    finally:
        _fastapi_app.dependency_overrides.clear()


def test_list_policies_returns_all_registered():
    """GET 返回全部已注册的 (entity_type, action)，含 is_default 标记。"""
    _fastapi_app.dependency_overrides.clear()
    _fastapi_app.dependency_overrides[_get_db] = override_get_db
    _fastapi_app.dependency_overrides[_get_cu] = fake_current_user
    try:
        Base.metadata.create_all(bind=_testing_engine)
        # 用一个独立 session 做前置清理（override_get_db 与本 fixture 的 db 不同 session）
        s = TestingSessionLocal()
        _setup_real_executors(s)
        s.close()

        r = api_client.get("/api/v1/proposals/policies")
        assert r.status_code == 200, r.text
        items = r.json()
        assert len(items) > 0
        # 抽样：ingredient/create 未被 bootstrap 覆盖 → 默认 auto_approve → is_default True
        ing_create = next(it for it in items if it["entity_type"] == "ingredient" and it["action"] == "create")
        assert ing_create["policy"] == "auto_approve"
        assert ing_create["is_default"] is True
        # ingredient/update 被 bootstrap 显式设为 manual（默认是 auto_approve）→ is_default False
        ing_update = next(it for it in items if it["entity_type"] == "ingredient" and it["action"] == "update")
        assert ing_update["policy"] == "manual"
        assert ing_update["is_default"] is False
        # 每个 item 含必要字段
        for it in items:
            assert {"entity_type", "action", "policy", "risk_level", "is_default"} <= set(it.keys())
    finally:
        _fastapi_app.dependency_overrides.clear()


def test_update_policy_persists_and_updates_registry():
    """PUT 写 system_config + 即时改 registry；重启（重新 load）保持。"""
    _fastapi_app.dependency_overrides.clear()
    _fastapi_app.dependency_overrides[_get_db] = override_get_db
    _fastapi_app.dependency_overrides[_get_cu] = fake_current_user
    try:
        Base.metadata.create_all(bind=_testing_engine)
        s = TestingSessionLocal()
        _setup_real_executors(s)
        s.close()

        # 改 ingredient/update manual → auto_approve
        # （ingredient 默认是 auto_approve，bootstrap 把 update 改成 manual；
        #  现在改回 auto_approve → 与默认一致 → is_default True）
        r = api_client.put("/api/v1/proposals/policies", json={
            "entity_type": "ingredient", "action": "update", "policy": "auto_approve"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["policy"] == "auto_approve"
        assert body["is_default"] is True

        # registry 即时更新
        assert ExecutorRegistry.policy_for("ingredient", "update") == "auto_approve"

        # system_config 已写入
        s2 = TestingSessionLocal()
        row = s2.query(SystemConfig).filter(
            SystemConfig.key == "proposal_policy:ingredient:update").first()
        assert row is not None
        assert row.value == "auto_approve"
        s2.close()

        # 模拟「重启」：重置 registry 再 load_persisted_policies
        ExecutorRegistry.reset()
        from app.services.proposals.bootstrap import register_all
        s3 = TestingSessionLocal()
        register_all(db=s3)
        s3.close()
        assert ExecutorRegistry.policy_for("ingredient", "update") == "auto_approve"

        # 清理
        s4 = TestingSessionLocal()
        s4.query(SystemConfig).filter(
            SystemConfig.key == "proposal_policy:ingredient:update").delete()
        s4.commit()
        s4.close()
    finally:
        _fastapi_app.dependency_overrides.clear()


def test_update_policy_rejects_invalid():
    """非法 policy → 400；未注册类型 → 400。"""
    _fastapi_app.dependency_overrides.clear()
    _fastapi_app.dependency_overrides[_get_db] = override_get_db
    _fastapi_app.dependency_overrides[_get_cu] = fake_current_user
    try:
        Base.metadata.create_all(bind=_testing_engine)
        s = TestingSessionLocal()
        _setup_real_executors(s)
        s.close()

        # 非法 policy
        r = api_client.put("/api/v1/proposals/policies", json={
            "entity_type": "ingredient", "action": "update", "policy": "bogus"})
        assert r.status_code == 400

        # 未注册类型
        r2 = api_client.put("/api/v1/proposals/policies", json={
            "entity_type": "nonexistent", "action": "update", "policy": "manual"})
        assert r2.status_code == 400
    finally:
        _fastapi_app.dependency_overrides.clear()
