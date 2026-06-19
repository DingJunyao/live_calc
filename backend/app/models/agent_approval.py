"""Agent 维护任务台——记录需要人工审批的 SQL 执行项。"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey

from sqlalchemy.sql import func

from app.core.database import Base


class AgentApproval(Base):
    """Agent 会话审批记录

    记录 Agent 生成、需人工审批的危险 SQL。

    status 取值：
        - pending: 待审批
        - approved: 已批准
        - rejected: 已拒绝
        - auto_executed: 自动执行（安全级别）
    """
    __tablename__ = "agent_approvals"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("agent_sessions.id"), nullable=True, index=True)
    message_id = Column(Integer, ForeignKey("agent_messages.id"), nullable=True)
    sql = Column(Text, nullable=False)
    danger_reason = Column(String(128), nullable=True)
    affected_estimate = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    decided_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("status", "pending")
        super().__init__(**kwargs)
