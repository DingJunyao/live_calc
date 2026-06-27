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
