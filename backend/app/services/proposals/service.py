"""提议业务服务：提交（策略分流）、审核、apply、回滚。

事务约定：本服务层只 db.add/flush，不 commit（由 API 层 get_db 依赖在端点返回后 commit）。
若 executor.apply/revert 抛异常，调用方应不 commit（让事务随请求结束而丢弃），避免残留
「pending 但已部分执行」的脏数据——FastAPI 的 get_db 在异常路径下不会 commit，天然兜底。
权限校验统一由 API 层 Depends(get_current_admin_user / get_current_user) 负责。
"""
from datetime import datetime, timedelta
from typing import Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.change_proposal import ChangeProposal
from app.services.proposals.base import ProposalExecutor, ApplyResult
from app.services.proposals.registry import ExecutorRegistry
from app.services.proposals.auto_reviewer import DefaultAutoReviewer

# 高风险回滚窗口（天）
REVERT_WINDOW_DAYS = 7

_auto_reviewer = DefaultAutoReviewer()


def _get_executor(entity_type: str) -> ProposalExecutor:
    ex = ExecutorRegistry.get(entity_type)
    if ex is None:
        raise HTTPException(status_code=400, detail=f"不支持的提议类型: {entity_type}")
    return ex


def _now() -> datetime:
    return datetime.utcnow()


def submit(db: Session, *, entity_type: str, entity_id: Optional[int], action: str,
           payload: dict, proposer) -> ChangeProposal:
    """普通用户提交提议。按策略分流：auto_approve 立即 apply；auto_review 走自动审核；manual 待审。"""
    executor = _get_executor(entity_type)
    policy = ExecutorRegistry.policy_for(entity_type, action)
    risk = ExecutorRegistry.risk_for(entity_type, action)

    proposal = ChangeProposal(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        payload=payload,
        review_policy=policy,
        risk_level=risk,
        status="pending",
        proposer_id=proposer.id,
    )
    # validate 在持久化前跑（含互斥检查），但互斥检查需 proposal 已存在 → 先 add flush 拿 id
    db.add(proposal)
    db.flush()
    executor.validate(db, proposal)

    if policy == "auto_approve":
        _do_apply(db, proposal, executor)
        proposal.status = "applied"
    elif policy == "auto_review":
        result = _auto_reviewer.review(db, proposal)
        if result.decision == "approve":
            _do_apply(db, proposal, executor)
            proposal.status = "applied"
            proposal.review_note = f"自动审核通过: {result.reason}"
            proposal.reviewed_at = _now()
        elif result.decision == "reject":
            proposal.status = "rejected"
            proposal.review_note = f"自动审核驳回: {result.reason}"
            proposal.reviewed_at = _now()
        # escalate → 保持 pending
    # manual → 保持 pending
    return proposal


def review(db: Session, *, proposal_id: int, approved: bool, reviewer, note: str = "") -> ChangeProposal:
    """管理员审核：approved → apply；否则 rejected。

    权限校验由 API 层 Depends(get_current_admin_user) 负责，本函数不重复校验。
    """
    proposal = db.query(ChangeProposal).filter(ChangeProposal.id == proposal_id).first()
    if proposal is None:
        raise HTTPException(status_code=404, detail="提议不存在")
    if proposal.status not in ("pending",):
        raise HTTPException(status_code=409, detail=f"提议已处理（status={proposal.status}），不能重复审核")

    proposal.reviewer_id = reviewer.id
    proposal.reviewed_at = _now()
    proposal.review_note = note

    if approved:
        executor = _get_executor(proposal.entity_type)
        _do_apply(db, proposal, executor)
        proposal.status = "applied"
    else:
        proposal.status = "rejected"
    return proposal


def revert(db: Session, *, proposal_id: int, reviewer) -> ChangeProposal:
    """回滚已 apply 的提议（回滚窗口内）。

    权限校验由 API 层 Depends(get_current_admin_user) 负责，本函数不重复校验。
    """
    proposal = db.query(ChangeProposal).filter(ChangeProposal.id == proposal_id).first()
    if proposal is None:
        raise HTTPException(status_code=404, detail="提议不存在")
    if proposal.status != "applied":
        raise HTTPException(status_code=409, detail=f"仅 applied 提议可回滚（当前 status={proposal.status}）")
    if proposal.revertable_until and _now() > proposal.revertable_until.replace(tzinfo=None):
        raise HTTPException(status_code=403, detail="回滚窗口已过")

    executor = _get_executor(proposal.entity_type)
    executor.revert(db, proposal)
    proposal.status = "reverted"
    proposal.reverted_at = _now()
    proposal.reviewer_id = reviewer.id
    return proposal


def apply_as_admin(db: Session, *, entity_type: str, entity_id: Optional[int], action: str,
                   payload: dict, admin) -> ChangeProposal:
    """管理员直写：绕过审核，立即 apply。单用户场景的核心路径。

    权限校验由 API 层 Depends(get_current_admin_user) 负责，本函数不重复校验 admin 身份。
    """
    executor = _get_executor(entity_type)
    risk = ExecutorRegistry.risk_for(entity_type, action)
    proposal = ChangeProposal(
        entity_type=entity_type, entity_id=entity_id, action=action, payload=payload,
        review_policy="auto_approve", risk_level=risk, status="applied",
        proposer_id=admin.id, reviewer_id=admin.id,
    )
    db.add(proposal)
    db.flush()
    executor.validate(db, proposal)
    _do_apply(db, proposal, executor)
    proposal.status = "applied"
    return proposal


def _do_apply(db: Session, proposal: ChangeProposal, executor: ProposalExecutor) -> None:
    """调执行器 apply，落快照与逆向操作；高风险设回滚窗口。"""
    result: ApplyResult = executor.apply(db, proposal)
    proposal.snapshot = result.snapshot
    proposal.revert_payload = result.revert_payload
    proposal.applied_at = _now()
    if proposal.risk_level == "high":
        proposal.revertable_until = _now() + timedelta(days=REVERT_WINDOW_DAYS)
