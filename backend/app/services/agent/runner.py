"""runner - Agent 执行引擎抽象层。

定义 Agent 事件数据类（``AgentEvent``）与执行器协议（``AgentRunner``）。

事件种类（``AgentEvent.kind``）：
- ``text_delta``  文本增量（来自 stream_event 的 content_block_delta.text_delta
                  或 assistant 消息的 text 段）。前端可累加展示。
- ``tool_use``    assistant 决定调用某个工具。带 ``tool_name``/``tool_input``。
- ``tool_result`` 工具返回（来自 user 消息的 tool_result 块）。带 ``tool_result`` 文本。
- ``done``        终态成功/失败。带 ``is_error``/``cost_usd``/``permission_denials``。
- ``error``       执行层异常（子进程崩、超时、JSON 解析连续失败等）。带 ``error`` 文本。

任何具体 Runner（如 ``ClaudeCodeRunner``）实现 ``AgentRunner`` 协议，``run`` 返回
一个 ``AgentEvent`` 迭代器，调用方按需消费、转发或落库（Task 4/5）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator, Protocol, runtime_checkable

__all__ = [
    "AgentEvent",
    "AgentRunner",
]


@dataclass
class AgentEvent:
    """Agent 执行过程中产生的一条事件。

    Attributes:
        kind: 事件种类，见模块 docstring。
        text: 文本内容（text_delta 的增量片段，或文本型 tool_result 的聚合）。
        tool_name: 工具名（tool_use 事件）。
        tool_input: 工具入参（tool_use 事件）。
        tool_use_id: 工具调用 id（tool_use / tool_result 配对用）。
        tool_result: 工具返回内容（tool_result 事件，统一规整为 Python 对象）。
        is_error: 终态是否出错（done 事件）。
        cost_usd: 本次会话累计成本（done 事件，可能为 None）。
        permission_denials: 权限拒绝列表（done 事件，原始结构，可能为空）。
        error: 错误描述（error 事件，或 done.is_error=True 时的补充说明）。
    """

    kind: str
    text: str = ""
    tool_name: str = ""
    tool_input: dict = field(default_factory=dict)
    tool_use_id: str = ""
    tool_result: Any = None
    is_error: bool = False
    crash: bool = False  # True 表示 CLI 自身崩溃（可重试），而非逻辑/超时错误
    cost_usd: float | None = None
    permission_denials: list = field(default_factory=list)
    error: str = ""


@runtime_checkable
class AgentRunner(Protocol):
    """Agent 执行器协议。"""

    def run(
        self, prompt: str, *, resume_session_id: str | None = None
    ) -> Iterator[AgentEvent]:
        """执行一次 prompt（可选 resume 上一次 session），流式产出事件。

        Args:
            prompt: 用户指令文本。
            resume_session_id: 若提供，则 resume 指定 session 继续；否则新会话。

        Yields:
            AgentEvent: 按 stream 顺序产出，最后必为 ``done`` 或 ``error``。
        """
        ...

    @property
    def last_session_id(self) -> str | None:
        """最近一次（或当前）会话的 session_id，未捕获到则为 None。"""
        ...

    @property
    def uses_db_pk_resume(self) -> bool:
        """resume 锚是否为 AgentSession 的 DB PK（字符串形式）而非外部 session id。

        - ``False``（默认）：resume 锚取 ``last_session_id``，适用于
          ``ClaudeCodeRunner``——它捕获 CLI 的 claude session id。
        - ``True``：resume 锚恒为 ``str(AgentSession.id)``，适用于
          ``LangChainRunner``——其 ``_load_history`` 按 ``AgentMessage.session_id``
          （= AgentSession DB PK）查历史，与外部 session id 无关。

        ``run_agent_loop`` 据此分流：True 时每轮 ``current_sid = str(session_id)``，
        首轮即写 ``claude_session_id`` 使插话不再 409；False 时保持原 ``runner
        .last_session_id`` 路径，不改 ClaudeCodeRunner 行为。
        """
        ...
