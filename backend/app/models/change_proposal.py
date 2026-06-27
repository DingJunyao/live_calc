"""通用变更提议模型——治理共享数据的写入。"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.base_model import AuditMixin


class ChangeProposal(Base, AuditMixin):
    """一条对共享数据的变更提议。

    普通用户提交 → 按审核策略（auto_approve/auto_review/manual）流转；
    管理员直写不经过本表（分流模式在 service 层）。
    """
    __tablename__ = "change_proposals"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(32), nullable=False, index=True)
    # ingredient / nutrition / unit / merchant / hierarchy / merge / recipe / ...
    entity_id = Column(Integer, nullable=True, index=True)      # 新增（create）时空
    action = Column(String(16), nullable=False)                 # create/update/delete/merge/publish
    payload = Column(JSON, nullable=False)                      # 变更内容
    snapshot = Column(JSON, nullable=True)                      # apply 前快照（供 revert）
    revert_payload = Column(JSON, nullable=True)                # apply 生成的逆向操作

    review_policy = Column(String(16), nullable=False, default="manual")
    # auto_approve / auto_review / manual
    risk_level = Column(String(8), nullable=False, default="mid")  # low/mid/high（信息性，由 policy 驱动）
    status = Column(String(20), nullable=False, default="pending", index=True)
    # pending / auto_approved / approved / rejected / applied / reverted / cancelled

    proposer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_note = Column(Text, nullable=True)

    revertable_until = Column(DateTime(timezone=True), nullable=True)  # 高风险回滚窗口截止
    applied_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reverted_at = Column(DateTime(timezone=True), nullable=True)
    # created_at/updated_at/created_by/updated_by/is_active 继承自 AuditMixin
