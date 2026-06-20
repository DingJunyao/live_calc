"""Task 3：LangChainRunner 单测。

GenericFakeChatModel 不实现 ``bind_tools``（create_agent 必经路径），无法驱动
真实 agent tool-use 循环。退路（task 描述允许）：直接构造 create_agent stream
的 chunk dict（messages mode 的 AIMessageChunk + updates mode 的完整 AIMessage/
ToolMessage），喂给 ``_map_chunk`` 单独测事件映射；并 mock ``_run_stream`` 验证
``run()`` 的 done/error 顶层兜底。
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.agent_message import AgentMessage
from app.models.agent_session import AgentSession
from app.services.agent.langchain_runner import LangChainRunner


# --------------------------------------------------------------------------- #
# 内存库 fixture（resume 测试用 AgentMessage/AgentSession 表）。
# --------------------------------------------------------------------------- #
@pytest.fixture()
def mem_db(monkeypatch):
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    TestSession = sessionmaker(bind=eng, autoflush=False, autocommit=False)

    import app.core.database as dbmod

    monkeypatch.setattr(dbmod, "SessionLocal", TestSession)
    yield TestSession
    eng.dispose()


def _make_session(TestSession, **kw) -> int:
    db = TestSession()
    try:
        s = AgentSession(status="pending", **kw)
        db.add(s)
        db.commit()
        db.refresh(s)
        return s.id
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# chunk 构造辅助：模仿 create_agent stream (stream_mode=["messages","updates"],
# version="v2") 产出的 dict。
# --------------------------------------------------------------------------- #
def _msg_chunk(token, node: str = "model"):
    """messages mode chunk：data 为 (token, metadata) 元组。"""
    return {
        "type": "messages",
        "data": (token, {"langgraph_node": node}),
    }


def _updates_chunk(node: str, messages: list) -> dict:
    """updates mode chunk：data 为 {node_name: {"messages": [...]}}。"""
    return {
        "type": "updates",
        "data": {node: {"messages": messages}},
    }


def _ai_with_tool_call(name: str = "db_read", args: dict | None = None, cid="call_1"):
    from langchain_core.messages import AIMessage

    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": name,
                "args": args or {"sql": "SELECT 1"},
                "id": cid,
                "type": "tool_call",
            }
        ],
    )


def _ai_text_chunk(text: str):
    """messages mode 用的 AIMessageChunk（只带文本增量）。"""
    from langchain_core.messages import AIMessageChunk

    return AIMessageChunk(content=text)


def _ai_text_full(text: str):
    from langchain_core.messages import AIMessage

    return AIMessage(content=text)


def _tool_message(tool_call_id="call_1", content="rows: 1"):
    from langchain_core.messages import ToolMessage

    return ToolMessage(content=content, tool_call_id=tool_call_id)


def _human_message(content: str):
    from langchain_core.messages import HumanMessage

    return HumanMessage(content=content)


# --------------------------------------------------------------------------- #
# _map_chunk 单元测试：验证 stream chunk → AgentEvent 映射正确。
# --------------------------------------------------------------------------- #
def test_map_text_delta():
    runner = LangChainRunner(chat=None, tools=[])
    events = list(runner._map_chunk(_msg_chunk(_ai_text_chunk("hello"))))
    assert len(events) == 1
    assert events[0].kind == "text_delta"
    assert events[0].text == "hello"


def test_map_tool_use_from_updates_model_node():
    runner = LangChainRunner(chat=None, tools=[])
    ai = _ai_with_tool_call()
    events = list(runner._map_chunk(_updates_chunk("model", [ai])))
    assert len(events) == 1
    ev = events[0]
    assert ev.kind == "tool_use"
    assert ev.tool_name == "db_read"
    assert ev.tool_input == {"sql": "SELECT 1"}
    assert ev.tool_use_id == "call_1"


def test_map_tool_result_from_updates_tools_node():
    runner = LangChainRunner(chat=None, tools=[])
    tm = _tool_message(content="rows: 42")
    events = list(runner._map_chunk(_updates_chunk("tools", [tm])))
    assert len(events) == 1
    ev = events[0]
    assert ev.kind == "tool_result"
    assert ev.tool_use_id == "call_1"
    assert "42" in str(ev.tool_result)


def test_map_text_from_updates_model_node_no_tool_calls():
    """updates model 节点但 AIMessage 无 tool_calls：messages mode 已覆盖文本，
    updates 侧应跳过（否则重复）。"""
    runner = LangChainRunner(chat=None, tools=[])
    ai = _ai_text_full("only text")
    events = list(runner._map_chunk(_updates_chunk("model", [ai])))
    # 无 tool_calls 的 model updates 不产事件（文本已由 messages mode 覆盖）。
    assert events == []


def test_map_ignores_irrelevant_node():
    """非 model/tools 节点的 updates 跳过。"""
    runner = LangChainRunner(chat=None, tools=[])
    events = list(runner._map_chunk(_updates_chunk("some_other", [_ai_text_full("x")])))
    assert events == []


def test_map_unknown_chunk_type_returns_empty():
    runner = LangChainRunner(chat=None, tools=[])
    assert list(runner._map_chunk({"type": "custom", "data": "x"})) == []


# --------------------------------------------------------------------------- #
# 负样本：messages mode 流非 AI 消息时不应产 text_delta（避免用户输入回显与
# 工具结果重复）。tool_result 由 updates 侧负责。
# --------------------------------------------------------------------------- #
def test_map_messages_chunk_ignores_human_message():
    """HumanMessage（首轮用户输入）不应被当 assistant text_delta 回显。"""
    runner = LangChainRunner(chat=None, tools=[])
    events = list(runner._map_chunk(_msg_chunk(_human_message("用户输入"))))
    assert events == []  # 不产任何事件（无 text_delta）


def test_map_messages_chunk_ignores_tool_message():
    """ToolMessage（tools 节点执行工具时流的工具结果）不应在 messages 侧重复产
    text_delta——tool_result 由 updates 侧负责。"""
    runner = LangChainRunner(chat=None, tools=[])
    events = list(runner._map_chunk(_msg_chunk(_tool_message(content="工具结果"))))
    assert events == []  # 不产任何事件（无 text_delta）


# --------------------------------------------------------------------------- #
# run() 集成：mock _run_stream 返回 chunk 列表，验证聚合与终态。
# --------------------------------------------------------------------------- #
def _patch_stream(runner, chunks):
    """把 runner._run_stream 替换为返回固定 chunk 列表的生成器。"""
    runner._run_stream = lambda prompt, resume_sid=None: iter(chunks)  # type: ignore[assignment]


def test_run_full_turn_with_tool_use_and_sql():
    """一次完整轮：model 发 tool_call → tools 返回 → model 发含 SQL 的文本。"""
    chunks = [
        # 1) tool_use（updates model 节点）
        _updates_chunk("model", [_ai_with_tool_call()]),
        # 2) tool_result（updates tools 节点）
        _updates_chunk("tools", [_tool_message(content="rows: 1")]),
        # 3) 文本增量（messages mode）——含 SQL 块
        _msg_chunk(_ai_text_chunk("已查到数据。\n")),
        _msg_chunk(_ai_text_chunk("```sql\nUPDATE t SET x=1 WHERE id=1;\n```\n")),
    ]
    runner = LangChainRunner(chat=None, tools=[])
    _patch_stream(runner, chunks)

    events = list(runner.run("test prompt"))

    # 末尾应是 done。
    assert events[-1].kind == "done"
    assert events[-1].is_error is False

    # 含 tool_use。
    tool_uses = [e for e in events if e.kind == "tool_use"]
    assert len(tool_uses) == 1
    assert tool_uses[0].tool_name == "db_read"
    assert tool_uses[0].tool_use_id == "call_1"

    # 含 tool_result。
    tool_results = [e for e in events if e.kind == "tool_result"]
    assert len(tool_results) == 1
    assert tool_results[0].tool_use_id == "call_1"

    # 聚合文本含 SQL 块（extract_sqls 能消费）。
    text = "".join(e.text for e in events if e.kind == "text_delta")
    assert "```sql" in text
    assert "UPDATE t SET x=1 WHERE id=1;" in text


def test_run_emits_done_with_resume_session_id():
    chunks = [_msg_chunk(_ai_text_chunk("hi"))]
    runner = LangChainRunner(chat=None, tools=[])
    _patch_stream(runner, chunks)

    list(runner.run("p", resume_session_id="42"))
    assert runner.last_session_id == "42"


def test_run_error_when_stream_raises():
    runner = LangChainRunner(chat=None, tools=[])

    def boom(prompt, resume_sid=None):
        raise RuntimeError("boom")
        yield  # noqa: unreachable  - 使其为生成器函数

    runner._run_stream = boom  # type: ignore[assignment]
    events = list(runner.run("p"))
    # 末尾必为 error。
    assert events[-1].kind == "error"
    assert events[-1].is_error is True
    assert "RuntimeError" in events[-1].error
    assert "boom" in events[-1].error


def test_run_without_resume_has_no_session_id():
    chunks = [_msg_chunk(_ai_text_chunk("hi"))]
    runner = LangChainRunner(chat=None, tools=[])
    _patch_stream(runner, chunks)
    list(runner.run("p"))
    # 无 resume 且 runner 未从 stream 捕获 session → None。
    assert runner.last_session_id is None


# --------------------------------------------------------------------------- #
# _load_history：从 AgentMessage 表恢复 human/ai 历史。
# --------------------------------------------------------------------------- #
def test_load_history_from_messages(mem_db):
    sid = _make_session(mem_db)
    db = mem_db()
    try:
        db.add_all(
            [
                AgentMessage(session_id=sid, seq=1, role="user", content="hello"),
                AgentMessage(session_id=sid, seq=2, role="assistant", content="hi"),
                AgentMessage(session_id=sid, seq=3, role="tool", tool_name="db_read"),
            ]
        )
        db.commit()
    finally:
        db.close()

    history = LangChainRunner._load_history(str(sid))
    # tool 消息过滤；只保留 user/assistant，dict 形式（与 _run_stream 末尾一致）。
    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "hello"}
    assert history[1] == {"role": "assistant", "content": "hi"}


# --------------------------------------------------------------------------- #
# 协议契约：满足 AgentRunner（run 为同步生成器 + last_session_id 属性）。
# --------------------------------------------------------------------------- #
def test_runner_satisfies_protocol():
    from app.services.agent.runner import AgentRunner

    runner = LangChainRunner(chat=None, tools=[])
    assert isinstance(runner, AgentRunner)


def test_default_recursion_limit_sufficient_for_multi_step_tasks():
    """regression: infer_quantities 等任务摸底需十几个工具调用，recursion_limit 太小
    会让 Agent 在摸底阶段就 GraphRecursionError（session 失败案例 2026-06-20）。
    默认 max_iterations 应足够大，_recursion_limit >= 50。
    """
    runner = LangChainRunner(chat=None, tools=[])  # 默认 max_iterations
    assert runner.max_iterations >= 25, f"max_iterations={runner.max_iterations} 太小"
    assert runner._recursion_limit >= 50, (
        f"recursion_limit={runner._recursion_limit} 太小，复杂任务会撞 GraphRecursionError"
    )
