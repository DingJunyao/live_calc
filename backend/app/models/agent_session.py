"""Agent 维护任务台——记录 Agent（claude code CLI）会话。"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func

from app.core.database import Base


class AgentSession(Base):
    """Agent 会话记录

    记录一次 claude code CLI 驱动的 Agent 维护任务会话。

    task_type 取值：
        - fill_piece_weight: 补全个数重量
        - fill_density: 补全密度
        - usda_translate: USDA 翻译
        - infer_quantities: 推测量程
        - infer_densities: 推测密度
    status 取值：
        - pending: 待执行
        - running: 运行中
        - awaiting_approval: 等待人工审批
        - success: 成功
        - failed: 失败
        - cancelled: 已取消
    """
    __tablename__ = "agent_sessions"

    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String(32), nullable=True, index=True)
    title = Column(String(128), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    runner_type = Column(String(20), nullable=False, default="claude_code")
    claude_session_id = Column(String(128), nullable=True)
    initial_prompt = Column(Text, nullable=True)
    cost_usd = Column(Numeric(10, 4), nullable=True)
    error = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())

    def __init__(self, **kwargs):
        kwargs.setdefault("status", "pending")
        kwargs.setdefault("runner_type", "claude_code")
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            "id": self.id,
            "task_type": self.task_type,
            "title": self.title,
            "status": self.status,
            "runner_type": self.runner_type,
            "claude_session_id": self.claude_session_id,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
