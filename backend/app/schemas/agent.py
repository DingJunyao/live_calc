"""Agent 任务台 API Pydantic schemas（Task 5）。

字段尽量对齐 ``AgentSession`` / ``AgentMessage`` / ``AgentApproval`` 模型，
datetime 统一序列化为 ISO 字符串。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# 入参
# --------------------------------------------------------------------------- #
class CreateSessionIn(BaseModel):
    """建会话入参。

    task_type 必须命中 ``TASK_TEMPLATES``（见 ``services/agent/task_templates.py``）；
    未知 task_type 由 ``agent_api.create_session`` 返回 400。可用类型清单见
    ``GET /api/v1/agent/task-types``。
    """

    task_type: str = Field(..., description="任务类型（fill_piece_weight 等）")
    force: bool = Field(False, description="强制重新处理全部（追加到 prompt 提示 Agent 忽略已处理标记）")


class PostMessageIn(BaseModel):
    """插话入参：在已终态会话上起 resume 新轮。"""

    text: str = Field(..., description="追加的用户消息文本")


class ApprovalDecisionIn(BaseModel):
    """审批决策入参。"""

    approved: bool = Field(..., description="True=批准并执行，False=拒绝")


# --------------------------------------------------------------------------- #
# 出参
# --------------------------------------------------------------------------- #
class AgentSessionOut(BaseModel):
    id: int
    task_type: Optional[str] = None
    title: Optional[str] = None
    status: str
    runner_type: str
    user_id: Optional[int] = None
    claude_session_id: Optional[str] = None
    cost_usd: Optional[float] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AgentMessageOut(BaseModel):
    id: int
    session_id: Optional[int] = None
    seq: Optional[int] = None
    role: Optional[str] = None
    content: Optional[str] = None
    tool_name: Optional[str] = None
    tool_use_id: Optional[str] = None
    tool_input: Optional[Any] = None
    tool_result: Optional[Any] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AgentApprovalOut(BaseModel):
    id: int
    session_id: Optional[int] = None
    sql: str
    danger_reason: Optional[str] = None
    affected_estimate: Optional[int] = None
    status: str
    decided_by: Optional[int] = None
    decided_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SessionDetailOut(BaseModel):
    session: AgentSessionOut
    messages: list[AgentMessageOut]
    pending_approvals: list[AgentApprovalOut]
