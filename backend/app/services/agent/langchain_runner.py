"""langchain_runner - 用 langchain 1.x ``create_agent`` 驱动 OpenAI/Anthropic 的
tool-use 循环，产出 ``AgentEvent`` 流，与 ``ClaudeCodeRunner`` 行为对称。

设计要点：

1. **v1 API**：``create_tool_calling_agent`` + ``AgentExecutor`` 在 langchain 1.x
   已移除。改用 ``create_agent(model, tools, system_prompt=...)``（基于 langgraph），
   agent 本身是可调用执行器，``.stream(...)`` 产 langgraph stream mode 事件。
2. **stream 模式**：用 ``stream_mode=["messages", "updates"]`` + ``version="v2"``：
   - ``messages``：``(AIMessageChunk, metadata)`` 增量，含 ``text`` 文本片段
     （**唯一文本源**，与 ClaudeCodeRunner 的 stream_event.text_delta 对称）。
   - ``updates``：``{node_name: {"messages": [完整消息]}}``，``model`` 节点的末条
     AIMessage 含完整 ``tool_calls``（tool_use 事件源）；``tools`` 节点的末条
     ToolMessage 是工具返回（tool_result 事件源）。
3. **对称性**：与 ``ClaudeCodeRunner`` 一致——``run()`` 为同步生成器，末尾必为
   ``done`` 或 ``error``。assistant 文本里要含 ```sql``` 块（供 ``run_agent_loop``
   的 ``extract_sqls`` 消费），由 system_prompt 引导 Agent 在写场景下用 SQL 代码块
   输出而非真写库（写库走审批通道）。
4. **死循环兜底**：``recursion_limit`` 封顶（langgraph 节点步数上限），默认约对应
   ``max_iterations`` 次 tool-use 轮次。
5. **resume**：``resume_session_id`` 从 ``AgentMessage`` 表恢复 human/ai 历史，
   作为新一轮 ``messages`` 前缀传入。

线程模型：``run()`` 同步生成器（在后台线程被 ``run_agent_loop`` 消费）。``.stream()``
本身同步。
"""

from __future__ import annotations

import threading
from typing import Any, Iterator

from langchain_core.messages import AIMessage, AIMessageChunk

from app.services.agent.runner import AgentEvent

__all__ = [
    "LangChainRunner",
    "DEFAULT_SYSTEM_PROMPT",
]

# 引导 Agent：只读工具查库 + 写场景以 ```sql``` 块输出（由主后端审批后执行）。
# 与 task_templates 的 prompt 表述、ClaudeCodeRunner 的行为保持一致。
DEFAULT_SYSTEM_PROMPT = (
    "你是一个数据库维护助手。可用工具：db_read（只读 SELECT）、list_tables、"
    "describe（查看表结构）。\n"
    "查询数据库用上述只读工具。如需写操作（INSERT/UPDATE/DELETE/DDL），"
    "请在回复中以 ```sql 代码块输出 SQL，由主后端审批后执行，不要尝试调用工具写库。"
)

# langgraph 节点名（stream updates 的 key）。
_MODEL_NODE = "model"
_TOOLS_NODE = "tools"


class LangChainRunner:
    """用 langchain ``create_agent`` 驱动 tool-use 循环的 AgentRunner 实现。

    Example:
        >>> runner = LangChainRunner(chat=chat_model, tools=READ_ONLY_TOOLS)
        >>> for ev in runner.run("列出所有表"):  # doctest: +SKIP
        ...     print(ev.kind, ev.text[:30])
    """

    def __init__(
        self,
        *,
        chat: Any,
        tools: list,
        max_iterations: int = 25,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        agent_factory: "Any | None" = None,
    ) -> None:
        """构造 Runner。

        Args:
            chat: langchain ChatModel（``ChatOpenAI`` / ``ChatAnthropic`` 等，需支持
                ``bind_tools``）。测试场景可传 ``None`` 并配合 ``agent_factory`` 或
                直接 mock ``_run_stream``。
            tools: 挂载到 Agent 的只读工具列表（如 ``READ_ONLY_TOOLS``）。
            max_iterations: tool-use 轮次上限，转成 langgraph ``recursion_limit``
                （每轮约 2 个节点步）。超出会抛 ``RecursionError``，由 ``run`` 兜底
                成 ``error`` 事件。
            system_prompt: Agent 的系统提示，引导只读 + ```sql``` 块输出。
            agent_factory: 可选，自定义 ``create_agent`` 调用（测试注入用）。
                签名 ``factory(chat, tools, system_prompt, recursion_limit)``
                返回 agent。``None`` 时用默认 ``create_agent``。
        """
        self.chat = chat
        self.tools = list(tools) if tools else []
        self.max_iterations = int(max_iterations)
        self.system_prompt = system_prompt
        self._agent_factory = agent_factory

        # langgraph recursion_limit 计的是图 superstep（每个 model/tools 节点一步），
        # 一轮 tool-use ≈ 2 步。复杂任务（如 infer_quantities 摸底十几个查询 + 估值
        # + 批量写 + 复核）需足够步数——默认 25 轮（54 步）覆盖大多数任务，且作死循环
        # 兜底（Agent 正常完成会提前停）。max_iterations=8（20 步）会让 infer_quantities
        # 摸底阶段就 GraphRecursionError（session 失败案例 2026-06-20）。
        self._recursion_limit = max(self.max_iterations * 2 + 4, 10)

        self._last_session_id: "str | None" = None
        self._agent: Any | None = None

        # 取消事件：cancel() 设置此事件，_run_stream 在下一个 chunk 到达时提前终止。
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        """从外部取消正在运行的 Agent 流。

        设置取消标志后，_run_stream 会在下一个 chunk 到达时提前终止（不再继续调
        LLM API），run() 随后正常产出 done 事件，run_agent_loop 收到后检查 DB
        status == 'cancelled' 并停止循环。
        """
        self._cancel_event.set()

    # ------------------------------------------------------------------ #
    # AgentRunner 协议
    # ------------------------------------------------------------------ #
    # langchain 路径的 resume 锚是 AgentSession DB PK（_load_history 按
    # AgentMessage.session_id 查历史），不是 CLI 捕获的外部 session id。
    # run_agent_loop 据此把 current_sid 设为 str(session_id)，首轮即写入
    # claude_session_id 使插话不再 409，且每轮 resume 都能恢复历史。
    uses_db_pk_resume = True

    @property
    def last_session_id(self) -> "str | None":
        return self._last_session_id

    def run(
        self, prompt: str, *, resume_session_id: "str | None" = None
    ) -> Iterator[AgentEvent]:
        """执行一次 prompt，流式产出 AgentEvent。

        Yields:
            AgentEvent: 按 stream 顺序；末尾必为 ``done`` 或 ``error``。
        """
        # 每次运行重置 session_id（与 ClaudeCodeRunner B-5 一致）。
        self._last_session_id = resume_session_id
        try:
            for chunk in self._run_stream(prompt, resume_session_id):
                for ev in self._map_chunk(chunk):
                    yield ev
            yield AgentEvent(kind="done")
        except Exception as exc:  # noqa: BLE001 - 顶层兜底，必须产 error 让调用方收尾
            yield AgentEvent(
                kind="error",
                error=f"{type(exc).__name__}: {exc}",
                is_error=True,
            )

    # ------------------------------------------------------------------ #
    # 内部：stream 驱动 + chunk 映射
    # ------------------------------------------------------------------ #
    def _run_stream(
        self, prompt: str, resume_session_id: "str | None"
    ) -> Iterator[dict]:
        """构建 agent 并流式产出 create_agent 的 stream chunk（dict）。

        抽成单独方法便于测试 mock（替换为返回固定 chunk 列表的迭代器）。
        每产出一个 chunk 后检查 _cancel_event，若已取消则提前终止 stream。
        """
        agent = self._build_agent()

        # 构造 messages：可选历史前缀 + 本轮 user 消息。
        messages: list = []
        if resume_session_id:
            messages.extend(self._load_history(resume_session_id))
        messages.append({"role": "user", "content": prompt})

        for chunk in agent.stream(
            {"messages": messages},
            stream_mode=["messages", "updates"],
            version="v2",
            config={"recursion_limit": self._recursion_limit},
        ):
            if self._cancel_event.is_set():
                break
            yield chunk

    def _build_agent(self):
        """惰性构建 create_agent（首次 run 时；agent_factory 支持测试注入）。"""
        if self._agent is not None:
            return self._agent
        if self._agent_factory is not None:
            self._agent = self._agent_factory(
                self.chat,
                self.tools,
                self.system_prompt,
                self._recursion_limit,
            )
            return self._agent

        from langchain.agents import create_agent

        self._agent = create_agent(
            model=self.chat,
            tools=self.tools,
            system_prompt=self.system_prompt,
        )
        return self._agent

    def _map_chunk(self, chunk: dict) -> Iterator[AgentEvent]:
        """把 create_agent stream 的一个 chunk（dict）映射成 0..n 条 AgentEvent。

        chunk 形态（``stream_mode=["messages","updates"]``, ``version="v2"``）：
        - ``{"type": "messages", "data": (token, metadata)}``：``token`` 为
          ``AIMessageChunk``，``token.text`` 为文本增量（唯一文本源）。
        - ``{"type": "updates", "data": {node_name: {"messages": [...]}}}``：
          ``model`` 节点末条 AIMessage 含完整 ``tool_calls`` → tool_use 事件；
          ``tools`` 节点末条 ToolMessage → tool_result 事件。
          （updates 的文本内容已被 messages mode 覆盖，不再产出避免重复。）
        """
        if not isinstance(chunk, dict):
            return

        ctype = chunk.get("type")
        data = chunk.get("data")

        if ctype == "messages":
            yield from self._map_messages_chunk(data)
        elif ctype == "updates":
            yield from self._map_updates_chunk(data)
        # 其它 mode（custom 等）忽略。

    @staticmethod
    def _map_messages_chunk(data: Any) -> Iterator[AgentEvent]:
        """messages mode chunk → text_delta 事件。

        只对 AI 消息（``AIMessage`` / ``AIMessageChunk``）产 text_delta——langgraph
        ``stream_mode=["messages"]`` 下，tools 节点执行工具时会流 ToolMessage，首轮
        还会流 HumanMessage。若一律取 ``.text``，会把用户输入误当 assistant 文本
        回显、把工具结果文本重复（updates 侧已产 tool_result）。故此处对非 AI 消息
        跳过，与 ClaudeCodeRunner 的 ``content_block_delta`` 行为对称。
        """
        if not isinstance(data, (tuple, list)) or len(data) < 1:
            return
        token = data[0]
        # 只对 AI 消息产文本增量；HumanMessage / ToolMessage 等跳过。
        if not isinstance(token, (AIMessage, AIMessageChunk)):
            return
        # token.text 是 langchain 的 AIMessageChunk 文本增量（其它 content_block
        # 形态此处不处理，仅取文本源）。
        text = getattr(token, "text", None) or ""
        if text:
            yield AgentEvent(kind="text_delta", text=text)

    @staticmethod
    def _map_updates_chunk(data: Any) -> Iterator[AgentEvent]:
        """updates mode chunk → tool_use / tool_result 事件。

        - ``model`` 节点：末条 AIMessage 若有 ``tool_calls``，每个产一条 tool_use。
          （无 tool_calls 时跳过——文本已由 messages mode 覆盖，避免重复。）
        - ``tools`` 节点：末条 ToolMessage 产一条 tool_result。
        - 其它节点忽略。
        """
        if not isinstance(data, dict):
            return

        for node_name, update in data.items():
            if not isinstance(update, dict):
                continue
            msgs = update.get("messages") or []
            if not msgs:
                continue
            last = msgs[-1]

            if node_name == _MODEL_NODE:
                tool_calls = getattr(last, "tool_calls", None) or []
                for tc in tool_calls:
                    name = tc.get("name", "") if isinstance(tc, dict) else ""
                    args = tc.get("args", {}) if isinstance(tc, dict) else {}
                    tcid = tc.get("id", "") if isinstance(tc, dict) else ""
                    if name:
                        yield AgentEvent(
                            kind="tool_use",
                            tool_name=str(name),
                            tool_input=dict(args) if isinstance(args, dict) else {},
                            tool_use_id=str(tcid),
                        )

            elif node_name == _TOOLS_NODE:
                # ToolMessage：content 可能是 str / list / dict，统一转字符串保留。
                content = getattr(last, "content", "")
                tcid = getattr(last, "tool_call_id", "") or ""
                yield AgentEvent(
                    kind="tool_result",
                    tool_use_id=str(tcid),
                    tool_result=_coerce_content(content),
                )

    @staticmethod
    def _load_history(session_id: str) -> list:
        """从 AgentMessage 表加载历史对话（resume 用）。

        user → ``{"role": "user", "content": ...}``，
        assistant → ``{"role": "assistant", "content": ...}``，
        tool 消息过滤（langgraph 会用 ToolMessage 重建工具上下文，但本项目 resume
        场景不需要——新一轮以纯文本历史续跑即可）。

        返回 dict 形式（与 ``_run_stream`` 末尾的 ``{"role":"user","content":prompt}``
        一致，``create_agent`` 接受 dict messages）。langchain 1.x 的 ``create_agent``
        对 tuple 形式兼容性不稳，resume 插话场景会踩，故统一为 dict。

        Args:
            session_id: AgentSession.id 的字符串形式。

        Returns:
            ``[{"role": "user"|"assistant", "content": str}, ...]``。
        """
        from app.core.database import SessionLocal
        from app.models.agent_message import AgentMessage

        db = SessionLocal()
        try:
            msgs = (
                db.query(AgentMessage)
                .filter(AgentMessage.session_id == int(session_id))
                .order_by(AgentMessage.seq.asc())
                .all()
            )
            history: list = []
            for m in msgs:
                if m.role == "user":
                    history.append({"role": "user", "content": m.content or ""})
                elif m.role == "assistant":
                    history.append({"role": "assistant", "content": m.content or ""})
            return history
        finally:
            db.close()


def _coerce_content(content: Any) -> str:
    """把 ToolMessage.content 规整成字符串（与 ClaudeCodeRunner 对称）。

    content 可能是 str / list[{type:text,text}] / dict，统一转字符串保留信息。
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    import json

    if isinstance(content, list):
        parts: list[str] = []
        for blk in content:
            if isinstance(blk, dict):
                if blk.get("type") == "text":
                    parts.append(str(blk.get("text", "")))
                else:
                    parts.append(json.dumps(blk, ensure_ascii=False))
            else:
                parts.append(str(blk))
        return "".join(parts)
    if isinstance(content, dict):
        return json.dumps(content, ensure_ascii=False)
    return str(content)
