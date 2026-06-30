"""提议相关 Pydantic schema。"""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class ProposalCreate(BaseModel):
    entity_type: str = Field(..., description="ingredient/nutrition/unit/merchant/...")
    entity_id: Optional[int] = None
    action: str = Field(..., description="create/update/delete/merge/publish")
    payload: dict = Field(..., description="变更内容")


class ProposalPreviewRequest(BaseModel):
    entity_type: str
    entity_id: Optional[int] = None
    action: str
    payload: dict


class ReviewDecision(BaseModel):
    approved: bool
    note: str = ""


class ProposalResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: Optional[int]
    action: str
    payload: dict
    snapshot: Optional[dict] = None   # before 快照（提交时预填，apply 时覆盖）
    status: str
    review_policy: str
    risk_level: str
    proposer_id: int
    reviewer_id: Optional[int]
    review_note: Optional[str]
    revertable_until: Optional[datetime]
    applied_at: Optional[datetime]
    reviewed_at: Optional[datetime]
    reverted_at: Optional[datetime]
    preview: Optional[dict] = None   # 可选附影响预览
    entity_label: Optional[str] = None   # 目标实体可读标签（审核台显示）

    model_config = {"from_attributes": True}
