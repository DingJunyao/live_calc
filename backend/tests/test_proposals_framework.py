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
