"""Agent 维护任务台——记录 Agent 会话消息/工具调用。"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func

from app.core.database import Base


class AgentMessage(Base):
    """Agent 会话消息记录

    逐条记录 Agent 会话中的 user/assistant/tool 消息及工具调用详情。

    role 取值：user / assistant / tool
    """
    __tablename__ = "agent_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("agent_sessions.id"), nullable=True, index=True)
    seq = Column(Integer, nullable=True)
    role = Column(String(16), nullable=True)
    content = Column(Text, nullable=True)
    tool_name = Column(String(64), nullable=True)
    tool_use_id = Column(String(64), nullable=True, index=True)
    tool_input = Column(JSON, nullable=True)
    tool_result = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
