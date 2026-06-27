"""通用提议-审核 API。"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user
from app.models.user import User
from app.models.change_proposal import ChangeProposal
from app.services.proposals import service as proposal_service
from app.services.proposals.registry import ExecutorRegistry
from app.schemas.proposal import (
    ProposalCreate,
    ProposalResponse,
    ProposalPreviewRequest,
    ReviewDecision,
)

router = APIRouter()


def _to_response(p: ChangeProposal) -> ProposalResponse:
    return ProposalResponse(
        id=p.id, entity_type=p.entity_type, entity_id=p.entity_id, action=p.action,
        payload=p.payload or {}, status=p.status, review_policy=p.review_policy,
        risk_level=p.risk_level, proposer_id=p.proposer_id, reviewer_id=p.reviewer_id,
        review_note=p.review_note, revertable_until=p.revertable_until,
        applied_at=p.applied_at, reviewed_at=p.reviewed_at, reverted_at=p.reverted_at,
    )


@router.post("/proposals", response_model=ProposalResponse)
def submit_proposal(body: ProposalCreate,
                    db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    """提交变更提议（任意登录用户）。按策略分流。"""
    p = proposal_service.submit(
        db, entity_type=body.entity_type, entity_id=body.entity_id,
        action=body.action, payload=body.payload, proposer=current_user,
    )
    db.commit()
    return _to_response(p)


@router.post("/proposals/preview")
def preview_proposal(body: ProposalPreviewRequest,
                     db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    """预览提议影响（如合并会影响多少引用）。"""
    executor = ExecutorRegistry.get(body.entity_type)
    if executor is None:
        raise HTTPException(status_code=400, detail=f"不支持的提议类型: {body.entity_type}")
    # 构造临时 proposal 供 preview
    tmp = ChangeProposal(entity_type=body.entity_type, entity_id=body.entity_id,
                         action=body.action, payload=body.payload, proposer_id=current_user.id)
    return executor.preview(db, tmp)


@router.get("/proposals", response_model=List[ProposalResponse])
def list_proposals(status_filter: Optional[str] = Query(None, alias="status"),
                   limit: int = Query(50, ge=1, le=200),
                   db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    """管理员看全部；普通用户只看自己提交的。"""
    q = db.query(ChangeProposal)
    if not current_user.is_admin:
        q = q.filter(ChangeProposal.proposer_id == current_user.id)
    if status_filter:
        q = q.filter(ChangeProposal.status == status_filter)
    items = q.order_by(ChangeProposal.id.desc()).limit(limit).all()
    return [_to_response(p) for p in items]


@router.get("/proposals/{proposal_id}", response_model=ProposalResponse)
def get_proposal(proposal_id: int,
                 db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    p = db.query(ChangeProposal).filter(ChangeProposal.id == proposal_id).first()
    if p is None:
        raise HTTPException(status_code=404, detail="提议不存在")
    if not current_user.is_admin and p.proposer_id != current_user.id:
        # 越权访问他人提议 → 同样 404（不泄露存在性）
        raise HTTPException(status_code=404, detail="提议不存在")
    return _to_response(p)


@router.post("/proposals/{proposal_id}/review", response_model=ProposalResponse)
def review_proposal(proposal_id: int, body: ReviewDecision,
                    db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_admin_user)):
    """审核提议（仅管理员）。"""
    p = proposal_service.review(db, proposal_id=proposal_id, approved=body.approved,
                                reviewer=current_user, note=body.note)
    db.commit()
    return _to_response(p)


@router.post("/proposals/{proposal_id}/revert", response_model=ProposalResponse)
def revert_proposal(proposal_id: int,
                    db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_admin_user)):
    """回滚已 apply 的提议（仅管理员）。"""
    p = proposal_service.revert(db, proposal_id=proposal_id, reviewer=current_user)
    db.commit()
    return _to_response(p)
