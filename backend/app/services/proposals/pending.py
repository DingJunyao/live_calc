"""查询当前用户对某实体是否有待审提议。"""
from typing import Optional
from sqlalchemy.orm import Session
from app.models.change_proposal import ChangeProposal


def get_pending_proposal(db: Session, entity_type: str, entity_id: int, user_id: int) -> Optional[ChangeProposal]:
    """返回当前用户对该实体的一条待审提议，没有则返回 None。

    查询条件：匹配 entity_type/entity_id/proposer_id，status=pending 且 is_active。
    同一对 (entity_type, entity_id, user_id) 可能有多条待审提议，取最新一条。
    """
    return db.query(ChangeProposal).filter(
        ChangeProposal.entity_type == entity_type,
        ChangeProposal.entity_id == entity_id,
        ChangeProposal.proposer_id == user_id,
        ChangeProposal.status == "pending",
        ChangeProposal.is_active.is_(True),
    ).order_by(ChangeProposal.created_at.desc().nullslast()).first()
