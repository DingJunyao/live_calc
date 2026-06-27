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
from app.main import app
from app.core.database import get_db as _get_db
from app.core.security import get_current_user as _get_cu
from conftest import (
    override_get_db,
    fake_current_user,
    _fake_non_admin_user,
    engine as _testing_engine,
)

api_client = TestClient(app)


def test_submit_via_api_requires_auth():
    """未登录提交提议 → 401。"""
    # 不安装 dependency_overrides → get_current_user 走真实鉴权，无 token → 401
    app.dependency_overrides.clear()
    r = api_client.post("/api/v1/proposals", json={
        "entity_type": "rec", "entity_id": 1, "action": "update", "payload": {}})
    assert r.status_code in (401, 403)


def test_non_admin_submit_then_admin_review():
    """非管理员提交 → pending；非管理员审核 → 403；管理员审核 → applied。"""
    ExecutorRegistry.reset()
    ExecutorRegistry.register(_RecordingExecutor())
    ExecutorRegistry.set_policy("rec", "update", "manual")

    app.dependency_overrides[_get_db] = override_get_db
    app.dependency_overrides[_get_cu] = _fake_non_admin_user
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
        app.dependency_overrides[_get_cu] = fake_current_user
        r3 = api_client.post(f"/api/v1/proposals/{pid}/review", json={"approved": True})
        assert r3.status_code == 200, r3.text
        assert r3.json()["status"] == "applied"
    finally:
        app.dependency_overrides.clear()


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
