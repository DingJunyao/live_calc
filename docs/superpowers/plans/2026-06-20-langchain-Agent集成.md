# langchain Agent 集成（OpenAI / Anthropic）实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让 OpenAI 兼容 / Anthropic 兼容两个 provider 以「自主 Agent 循环」方式跑四项 AI 后处理任务（食材翻译 / 营养素翻译 / 模糊量推测 / 密度推测），用 langchain 抹平两 provider 的 tool-use 差异，节约时间与 token。

**Architecture:** 新增 `LangChainRunner`（实现 `AgentRunner` 协议），与 `ClaudeCodeRunner` 平级——「只读 `@tool` 查库 + 文本吐 SQL + sql_guard 审批」行为对称。provider 无关的 `run_agent_loop` 不动，挂上即用。任务台按 provider 分流选 runner；老路径（TranslateTask / AIInferrer）引擎整体替换为 `LangChainRunner` + `run_agent_loop(unattended=True)`（无人值守，dangerous 自动跳过）。

**Tech Stack:** Python 3 / FastAPI / SQLAlchemy / langchain（`langchain` + `langchain-openai` + `langchain-anthropic`）/ pytest / Vue 3 + Vite + Vuetify。

> 设计依据：[2026-06-20-langchain-Agent集成-design.md](../specs/2026-06-20-langchain-Agent集成-design.md)

---

## 全局约定（执行前必读）

1. **git 规矩**：本项目规则——不主动 `git commit` / 开分支。每个 Task 末尾的 commit 步骤是计划形态，**执行时由小可爱确认后再触发**，或累积到阶段末统一提交。不要擅自提交。
2. **langchain API 以实测为准**：langchain 各包 API 随版本演进。涉及 `create_tool_calling_agent` / `AgentExecutor` / `ChatOpenAI` / `ChatAnthropic` / `@tool` / `FakeListChatModel` 的确切签名，**实现每个 Task 前用 context7（`mcp__context7__query-docs`，libraryId `/langchain-ai/langchain`）核对当前版本签名**，不要凭记忆。
3. **测试套路参照** [backend/tests/agent/test_agent_loop.py](../../../backend/tests/agent/test_agent_loop.py)：`FakeMultiTurnRunner`（按 run 调用次数返回事件序列）+ 内存 SQLite（`sqlite://` + `StaticPool`）+ monkeypatch `app.core.database.SessionLocal`。新测试复用这套。
4. **后端规范**：Black（line=88）/ isort / Flake8 / Google 风格 docstring；**所有后端修改确保无语法错误**。
5. **前端规范**：**所有前端修改确保 `npm run build` 通过**。
6. **不启动服务**：前后端自动重载服务已在运行，不要在对话里起服务。
7. **TDD**：每个 Task 先写失败测试 → 验证失败 → 最小实现 → 验证通过。

---

## Task 0：纳入 langchain 依赖

**Files:**
- Modify: `backend/pyproject.toml`

**Step 1: 确认当前依赖管理方式**

Run: `cd backend && cat pyproject.toml | head -60`
Expected: 看清是 poetry 还是 PEP 621 结构（FEATURE 记录项目为 poetry 结构，`uv add` 可能失败）。

**Step 2: 核对 langchain 三包最新版本与 API**

用 context7 查 `langchain` / `langchain-openai` / `langchain-anthropic` 当前版本，及 `create_tool_calling_agent`、`ChatAnthropic(base_url=...)`、`@tool` 签名。记录到本 Task 备注。

**Step 3: 加依赖**

在 `pyproject.toml` 的依赖区追加（版本以 Step 2 实测为准，示例）：

```toml
langchain = ">=0.3,<0.4"
langchain-openai = ">=0.2,<0.3"
langchain-anthropic = ">=0.2,<0.3"
```

按项目惯例（参照 `mcp` 先例）安装：`cd backend && uv pip install langchain langchain-openai langchain-anthropic`（若 `uv add` 可用则优先）。

**Step 4: 验证 import**

Run: `cd backend && python -c "import langchain; from langchain.agents import create_tool_calling_agent, AgentExecutor; from langchain_openai import ChatOpenAI; from langchain_anthropic import ChatAnthropic; from langchain_core.tools import tool; print('ok')"`
Expected: 输出 `ok`，无 ImportError。

**Step 5: Commit（待小可爱确认）**

```bash
git add backend/pyproject.toml backend/uv.lock
git commit -m "chore: 纳入 langchain 依赖"
```

---

## Task 1：只读 @tool（langchain_tools.py）

**Files:**
- Create: `backend/app/services/agent/langchain_tools.py`
- Test: `backend/tests/agent/test_langchain_tools.py`

**Step 1: 写失败测试**

```python
# backend/tests/agent/test_langchain_tools.py
"""只读 @tool 单测：查库正确 + db_read 拒非 SELECT。"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.services.agent.langchain_tools import db_read, describe, list_tables


@pytest.fixture()
def mem_db(monkeypatch):
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    with eng.connect() as conn:
        conn.execute(text("CREATE TABLE t (id INTEGER PRIMARY KEY, x INTEGER)"))
        conn.execute(text("INSERT INTO t (id, x) VALUES (1, 100), (2, 200)"))
        conn.commit()
    TestSession = sessionmaker(bind=eng, autoflush=False, autocommit=False)
    import app.core.database as dbmod
    monkeypatch.setattr(dbmod, "SessionLocal", TestSession)
    yield TestSession
    eng.dispose()


def test_db_read_select_returns_rows(mem_db):
    out = db_read.invoke({"sql": "SELECT id, x FROM t ORDER BY id"})
    assert "100" in out and "200" in out


def test_db_read_rejects_non_select(mem_db):
    # DELETE 非只读 → 工具返回错误串而非真执行
    out = db_read.invoke({"sql": "DELETE FROM t WHERE id=1"})
    assert "错误" in out or "拒绝" in out or "SELECT" in out
    # 确认数据没被删
    db = mem_db()
    try:
        assert db.execute(text("SELECT COUNT(*) FROM t")).scalar() == 2
    finally:
        db.close()


def test_list_tables_returns_t(mem_db):
    out = list_tables.invoke({})
    assert "t" in out


def test_describe_returns_columns(mem_db):
    out = describe.invoke({"table_name": "t"})
    assert "id" in out and "x" in out
```

**Step 2: 跑测试验证失败**

Run: `cd backend && python -m pytest tests/agent/test_langchain_tools.py -v`
Expected: FAIL（`ModuleNotFoundError: app.services.agent.langchain_tools`）。

**Step 3: 实现 langchain_tools.py**

```python
# backend/app/services/agent/langchain_tools.py
"""langchain Agent 的只读数据库工具。

复用 db_query._reject_non_select 的非 SELECT 判定，进程内独立 Session 查库。
工具名 db_read / describe / list_tables 与 task_templates 的 prompt 表述对齐。
"""
from __future__ import annotations

from langchain_core.tools import tool
from sqlalchemy import text

from app.services.agent.db_query import _format_rows, _reject_non_select


def _run_select(sql: str) -> str:
    """执行一条只读 SELECT，返回 markdown 表格；非 SELECT 返回错误串。"""
    try:
        _reject_non_select(sql)  # 内部对危险 SQL 直接 sys.exit(1)，需改为抛异常版
    except SystemExit:
        return "错误：只允许 SELECT 查询"
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        result = db.execute(text(sql))
        rows = result.fetchall()
        return _format_rows(rows, list(result.keys()))
    except Exception as exc:  # noqa: BLE001
        return f"查询失败: {exc}"
    finally:
        db.close()


@tool
def db_read(sql: str) -> str:
    """执行只读 SELECT 查询，返回 markdown 表格。严禁非 SELECT 语句。"""
    return _run_select(sql)


@tool
def list_tables() -> str:
    """列出数据库所有表名。"""
    return _run_select("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")


@tool
def describe(table_name: str) -> str:
    """查看指定表的列结构。"""
    return _run_select(f"PRAGMA table_info({table_name})")


READ_ONLY_TOOLS = [db_read, list_tables, describe]
```

**注意**：`db_query._reject_non_select` 当前对非 SELECT 调 `sys.exit(1)`。本 Task 需把它改成「抛 `ValueError` 或返回 False」，让 `@tool` 能捕获返回错误串而非杀进程。实现时同步修改 `db_query.py`（抽一个 `_is_read_only(sql) -> bool` 判定函数，`_reject_non_select` 与 `_run_select` 共用），**并确保 `db_query` 的 CLI 行为不变**（补一个针对 `db_query` 的回归测试）。

**Step 4: 跑测试验证通过**

Run: `cd backend && python -m pytest tests/agent/test_langchain_tools.py tests/agent -k db_query -v`（若有 db_query 现有测试则跑，无则跳过后半）
Expected: PASS。

**Step 5: Commit（待小可爱确认）**

```bash
git add backend/app/services/agent/langchain_tools.py backend/app/services/agent/db_query.py backend/tests/agent/test_langchain_tools.py
git commit -m "feat(agent): 新增 langchain 只读 @tool（db_read/describe/list_tables）"
```

---

## Task 2：provider 抹平（langchain_chat.py）

**Files:**
- Create: `backend/app/services/agent/langchain_chat.py`
- Test: `backend/tests/agent/test_langchain_chat.py`

**Step 1: 写失败测试**

```python
# backend/tests/agent/test_langchain_chat.py
"""按 provider + 配置构造 ChatOpenAI / ChatAnthropic。"""
from unittest.mock import patch
from app.services.agent.langchain_chat import build_chat_model


def test_build_openai():
    with patch("app.services.agent.langchain_chat.ChatOpenAI") as m:
        build_chat_model("openai", {"base_url": "https://x/v1", "api_key": "k", "model": "gpt-4o"})
        m.assert_called_once()
        kw = m.call_args.kwargs
        assert kw["model"] == "gpt-4o"
        assert kw["base_url"] == "https://x/v1"
        assert kw["api_key"] == "k"
        assert kw["streaming"] is True


def test_build_anthropic():
    with patch("app.services.agent.langchain_chat.ChatAnthropic") as m:
        build_chat_model("anthropic", {"base_url": "https://y", "api_key": "k", "model": "claude-3-5"})
        kw = m.assert_called_once().kwargs
        assert kw["model"] == "claude-3-5"
        assert kw["base_url"] == "https://y"


def test_build_unknown_raises():
    import pytest
    with pytest.raises(ValueError):
        build_chat_model("baidu", {})
```

**Step 2: 跑测试验证失败**

Run: `cd backend && python -m pytest tests/agent/test_langchain_chat.py -v`
Expected: FAIL（ModuleNotFoundError）。

**Step 3: 实现**

```python
# backend/app/services/agent/langchain_chat.py
"""按 provider + TranslationConfig 片段构造 langchain ChatModel。"""
from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI


def build_chat_model(provider: str, cfg: dict, *, timeout: float | None = None):
    """构造 langchain ChatModel（OpenAI 兼容 / Anthropic 兼容）。

    Args:
        provider: "openai" 或 "anthropic"。
        cfg: provider 配置（base_url / api_key / model）。
        timeout: 单次请求超时秒；None 用各自默认。

    Returns:
        配置好的 ChatOpenAI / ChatAnthropic（streaming=True）。
    """
    common = {"streaming": True}
    if timeout is not None:
        common["timeout"] = timeout
    if provider == "openai":
        return ChatOpenAI(
            model=cfg["model"], base_url=cfg["base_url"], api_key=cfg["api_key"], **common
        )
    if provider == "anthropic":
        return ChatAnthropic(
            model=cfg["model"], base_url=cfg["base_url"], api_key=cfg["api_key"], **common
        )
    raise ValueError(f"langchain 不支持的 provider: {provider}")
```

> 实现前用 context7 核对：`ChatAnthropic` 的 base_url 参数名（历史上有过 `anthropic_api_url`），以实测为准。

**Step 4: 跑测试验证通过**

Run: `cd backend && python -m pytest tests/agent/test_langchain_chat.py -v`
Expected: PASS。

**Step 5: Commit（待小可爱确认）**

```bash
git add backend/app/services/agent/langchain_chat.py backend/tests/agent/test_langchain_chat.py
git commit -m "feat(agent): provider 抹平构造 ChatModel"
```

---

## Task 3：LangChainRunner 事件适配（langchain_runner.py）核心

**Files:**
- Create: `backend/app/services/agent/langchain_runner.py`
- Test: `backend/tests/agent/test_langchain_runner.py`

**Step 1: 写失败测试（用 FakeListChatModel 驱动一轮 tool-use + SQL 输出）**

```python
# backend/tests/agent/test_langchain_runner.py
"""LangChainRunner：AgentExecutor.stream → AgentEvent 适配。"""
from __future__ import annotations

from langchain_community.chat_models.fake_chat_models import FakeListChatModel
# 或 from langchain_core.language_models.fake_llms import FakeListChatModel （以实测为准）

from app.services.agent.langchain_runner import LangChainRunner
from app.services.agent.langchain_tools import db_read  # 真工具或 mock 均可


def _fake_chat_one_tool_then_sql():
    """造一个会先调 db_read、再输出含 SQL 文本的假模型。"""
    # FakeListChatModel 不支持 tool calling；改用 GenericFakeChatModel 注入 messages
    from langchain_community.chat_models.fake_chat_models import GenericFakeChatModel
    from langchain_core.messages import AIMessage, HumanMessage
    seq = [
        AIMessage(content="", tool_calls=[{"name": "db_read", "args": {"sql": "SELECT 1"}, "id": "c1"}]),
        AIMessage(content="已查询，执行修正：\n```sql\nUPDATE t SET x=1 WHERE id=1;\n```\n完成。"),
    ]
    return GenericFakeChatModel(messages=iter(seq))


def test_runner_emits_tool_use_result_text_done():
    runner = LangChainRunner(
        chat=_fake_chat_one_tool_then_sql(),
        tools=[db_read],
        max_iterations=4,
    )
    events = list(runner.run("请处理 t 表"))
    kinds = [e.kind for e in events]
    assert "tool_use" in kinds
    assert "tool_result" in kinds
    assert "done" in kinds
    # 最终文本含 SQL 块（供 run_agent_loop 的 extract_sqls 消费）
    text = "".join(e.text for e in events if e.kind == "text_delta")
    assert "```sql" in text and "UPDATE t" in text
    # tool_use 带正确 tool_name
    tu = next(e for e in events if e.kind == "tool_use")
    assert tu.tool_name == "db_read"
```

**Step 2: 跑测试验证失败**

Run: `cd backend && python -m pytest tests/agent/test_langchain_runner.py -v`
Expected: FAIL（ModuleNotFoundError）。

**Step 3: 实现 langchain_runner.py**

> ⚠️ **langchain 已是 1.x（Task 0 实测：langchain 1.3.10）**：`create_tool_calling_agent` + `AgentExecutor` 已移除，改用 `create_agent(model, tools, system_prompt=..., middleware=...)`（基于 langgraph，返回的 agent 本身即执行器，支持 `.stream()`/`.astream()`）。**实现时按 v1 重写**：先用 context7（libraryId `/langchain-ai/langchain`）查 `create_agent` 的 stream 事件结构，再调整 `_map_chunk` 映射。测试用 `GenericFakeChatModel`（`langchain_core.language_models.fake_chat_models`，Task 0 已验证可用），不要用 `FakeListChatModel`（需额外装 langchain-community）。下面代码是 0.3.x 旧 API，仅作结构参考。

```python
# backend/app/services/agent/langchain_runner.py
"""LangChainRunner：用 langchain AgentExecutor 驱动 OpenAI/Anthropic 的 tool-use 循环，
产出 AgentEvent 流，与 ClaudeCodeRunner 行为对称（只读工具查库 + 文本吐 SQL）。"""
from __future__ import annotations

from typing import Any, Iterator

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.services.agent.runner import AgentEvent


class LangChainRunner:
    """实现 AgentRunner 协议的 langchain 版本。"""

    def __init__(self, chat, tools, *, max_iterations: int = 8, timeout: float | None = None):
        self.chat = chat
        self.tools = tools
        self.max_iterations = max_iterations
        self.timeout = timeout
        self._last_session_id: str | None = None
        # create_tool_calling_agent 需要含 agent_scratchpad + tools 占位的 prompt
        self._prompt = ChatPromptTemplate.from_messages([
            ("system", "{system_prompt}"),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ])
        self._agent = create_tool_calling_agent(chat, tools, self._prompt)
        self._executor = AgentExecutor(
            agent=self._agent, tools=tools, max_iterations=max_iterations,
            handle_parsing_errors=True, return_intermediate_steps=True,
        )

    @property
    def last_session_id(self) -> str | None:
        return self._last_session_id

    def run(self, prompt: str, *, resume_session_id: str | None = None) -> Iterator[AgentEvent]:
        """跑一轮 AgentExecutor.stream，把 (action, observation) 映射成 AgentEvent。"""
        inputs = {"input": prompt, "system_prompt": "你是生计应用的数据维护助手。"}
        if resume_session_id:
            inputs["chat_history"] = self._load_history(resume_session_id)
        try:
            for chunk in self._executor.stream(inputs):
                for ev in self._map_chunk(chunk):
                    yield ev
            self._last_session_id = resume_session_id
            yield AgentEvent(kind="done")
        except Exception as exc:  # noqa: BLE001
            yield AgentEvent(kind="error", error=f"{type(exc).__name__}: {exc}", is_error=True)

    def _map_chunk(self, chunk: dict) -> Iterator[AgentEvent]:
        """AgentExecutor.stream 的 chunk 形如 {'actions': [...], 'messages': [...]} 或 {'output': ...}。"""
        actions = chunk.get("actions") or []
        messages = chunk.get("messages") or []
        for action in actions:
            if action.tool:
                yield AgentEvent(
                    kind="tool_use", tool_name=action.tool,
                    tool_input=dict(action.tool_input) if isinstance(action.tool_input, dict) else {"input": action.tool_input},
                    tool_use_id=getattr(action, "tool_call_id", "") or "",
                )
        for msg in messages:
            content = getattr(msg, "content", "") or ""
            if content:
                yield AgentEvent(kind="text_delta", text=content)
            # tool 结果消息（ToolMessage）映射成 tool_result
            if msg.__class__.__name__ == "ToolMessage":
                yield AgentEvent(
                    kind="tool_result",
                    tool_use_id=getattr(msg, "tool_call_id", "") or "",
                    tool_result=getattr(msg, "content", ""),
                )

    @staticmethod
    def _load_history(session_id: str) -> list:
        """从 AgentMessage 表加载历史对话（resume 用）。"""
        from app.models.agent_message import AgentMessage
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            msgs = (
                db.query(AgentMessage)
                .filter(AgentMessage.session_id == int(session_id))
                .order_by(AgentMessage.seq.asc())
                .all()
            )
            history = []
            for m in msgs:
                if m.role == "user":
                    history.append(("human", m.content or ""))
                elif m.role == "assistant":
                    history.append(("ai", m.content or ""))
            return history
        finally:
            db.close()
```

> `create_tool_calling_agent` 要求模型支持 native tool calling。`GenericFakeChatModel` 测试场景下若不支持 tool_calls，需用支持 tool calling 的 fake（实测以 context7 / langchain 文档为准；必要时用真实 ChatModel 对小用例做集成测，单测则 mock executor.stream 的 chunk 形态）。
> 退路：若 `AgentExecutor.stream` 的 chunk 结构与上面 `_map_chunk` 假设不符，按实测 chunk 形态调整映射。

**Step 4: 跑测试验证通过**

Run: `cd backend && python -m pytest tests/agent/test_langchain_runner.py -v`
Expected: PASS。若 fake 模型 tool_calls 支持有困难，退路：直接构造 `AgentExecutor.stream` 的 chunk dict 喂给 `_map_chunk` 单测映射逻辑。

**Step 5: Commit（待小可爱确认）**

```bash
git add backend/app/services/agent/langchain_runner.py backend/tests/agent/test_langchain_runner.py
git commit -m "feat(agent): LangChainRunner 事件适配"
```

---

## Task 4：run_agent_loop unattended 模式

**Files:**
- Modify: `backend/app/services/agent/session_runner.py`（`run_agent_loop` 签名 + `_handle_dangerous_sql` 调用处）
- Test: `backend/tests/agent/test_agent_loop.py`（新增 unattended 用例）

**Step 1: 写失败测试（复用 test_agent_loop.py 的 FakeMultiTurnRunner + mem_db）**

在 `test_agent_loop.py` 末尾追加：

```python
def test_unattended_dangerous_sql_auto_skipped(mem_db):
    """unattended=True：dangerous SQL 不挂审批，自动跳过 + 记录，session 不进 awaiting_approval。"""
    sid = _make_session(mem_db, task_type="infer_densities")
    runner = FakeMultiTurnRunner([
        [AgentEvent(kind="text_delta", text="```sql\nDELETE FROM t;\n```\n"),
         AgentEvent(kind="done")],
        [AgentEvent(kind="done")],  # 第二轮：无 SQL → 完成
    ])
    main_loop = asyncio.new_event_loop()
    session_runner.run_agent_loop(
        sid, runner, "初始指令", main_loop, unattended=True, max_turns=4,
    )
    s = _session(mem_db, sid)
    assert s.status == "success"  # 未卡 awaiting_approval，未 failed
    # 数据未被删除（dangerous 自动跳过）
    db = mem_db()
    try:
        assert db.execute(text("SELECT COUNT(*) FROM t")).scalar() == 3
    finally:
        db.close()


def test_unattended_safe_sql_still_executed(mem_db):
    """unattended=True：safe SQL 照常执行。"""
    sid = _make_session(mem_db, task_type="infer_densities")
    runner = FakeMultiTurnRunner([
        [AgentEvent(kind="text_delta", text="```sql\nUPDATE t SET x=999 WHERE id=1;\n```\n"),
         AgentEvent(kind="done")],
        [AgentEvent(kind="done")],
    ])
    main_loop = asyncio.new_event_loop()
    session_runner.run_agent_loop(
        sid, runner, "初始指令", main_loop, unattended=True, max_turns=4,
    )
    db = mem_db()
    try:
        assert db.execute(text("SELECT x FROM t WHERE id=1")).scalar() == 999
    finally:
        db.close()
```

**Step 2: 跑测试验证失败**

Run: `cd backend && python -m pytest tests/agent/test_agent_loop.py -k unattended -v`
Expected: FAIL（`run_agent_loop() got an unexpected keyword argument 'unattended'`，或 dangerous 走了审批阻塞超时）。

**Step 3: 实现**

- `run_agent_loop` 签名加 `unattended: bool = False`，透传到 dangerous 分支。
- dangerous 分支：`if unattended` 时**不调用 `_handle_dangerous_sql`（不阻塞、不建 pending approval）**，改为「记日志 + 推一条 `sql_skipped` SSE + 返回摘要『已跳过（无人值守）』」。
- safe 分支不变。

伪代码（`session_runner.py` 内，dangerous 处理处）：

```python
if verdict.dangerous:
    if unattended:
        logger.warning("unattended 模式跳过 dangerous SQL: %s", sql[:120])
        _emit_sse(session_id, main_loop, {"kind": "sql_skipped", "sql": sql, "danger_reason": verdict.reason})
        summary_items.append(f"{index}. {preview} → 已跳过（无人值守，{verdict.reason}）")
    else:
        summary_items.append(_handle_dangerous_sql(...))
```

**Step 4: 跑测试验证通过**

Run: `cd backend && python -m pytest tests/agent/test_agent_loop.py -v`
Expected: 全 PASS（含原有用例 + 两个 unattended 新用例）。

**Step 5: Commit（待小可爱确认）**

```bash
git add backend/app/services/agent/session_runner.py backend/tests/agent/test_agent_loop.py
git commit -m "feat(agent): run_agent_loop 支持 unattended 无人值守模式"
```

---

## Task 5：runner_factory 分流 + agent_api 接 provider

**Files:**
- Modify: `backend/app/services/agent/runner_factory.py`（`build_runner` 加 `provider`）
- Modify: `backend/app/api/agent_api.py:87-148`（`create_session` 接 `provider`，`AgentSession.runner_type` 按它设）
- Modify: `backend/app/schemas/agent.py`（`CreateSessionIn` 加 `provider`）
- Test: `backend/tests/agent/test_agent_api.py`（新增 provider 分流用例）

**Step 1: 写失败测试**

```python
# 新增到 test_agent_api.py 或新建 test_runner_factory.py
def test_build_runner_openai_returns_langchain(monkeypatch):
    from app.services.agent import runner_factory
    r = runner_factory.build_runner("infer_densities", "sqlite:///./data/livecalc.db", provider="openai")
    from app.services.agent.langchain_runner import LangChainRunner
    assert isinstance(r, LangChainRunner)


def test_build_runner_claude_code_default(monkeypatch):
    from app.services.agent import runner_factory
    r = runner_factory.build_runner("infer_densities", "sqlite:///./data/livecalc.db")  # 默认
    from app.services.agent.claude_code_runner import ClaudeCodeRunner
    assert isinstance(r, ClaudeCodeRunner)
```

**Step 2: 跑测试验证失败**

Run: `cd backend && python -m pytest tests/agent -k build_runner -v`
Expected: FAIL（`build_runner` 无 `provider` 参数）。

**Step 3: 实现**

`runner_factory.build_runner` 加 `provider: str = "claude_code"`：

```python
def build_runner(task_type, db_url, *, provider="claude_code", max_budget_usd=None, ...):
    if provider in ("openai", "anthropic"):
        return _build_langchain_runner(task_type, provider)
    # 原有 ClaudeCodeRunner 构造逻辑不变
    ...

def _build_langchain_runner(task_type: str, provider: str) -> LangChainRunner:
    from app.models.usda import TranslationConfig
    from app.services.agent.langchain_chat import build_chat_model
    from app.services.agent.langchain_runner import LangChainRunner
    from app.services.agent.langchain_tools import READ_ONLY_TOOLS
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        cfg_row = db.query(TranslationConfig).first()
        cfg_dict = cfg_row.to_dict() if cfg_row else {}
    finally:
        db.close()
    from app.services.translate.registry import find_provider_section
    section = find_provider_section(cfg_dict, provider) or {}
    chat = build_chat_model(provider, section)
    return LangChainRunner(chat, READ_ONLY_TOOLS)
```

`agent_api.create_session`：`CreateSessionIn` 加 `provider: str = "claude_code"`；`AgentSession(runner_type=body.provider)`；`build_runner(body.task_type, db_url, provider=body.provider)`。

**Step 4: 跑测试验证通过**

Run: `cd backend && python -m pytest tests/agent -v`
Expected: PASS。

**Step 5: Commit（待小可爱确认）**

```bash
git add backend/app/services/agent/runner_factory.py backend/app/api/agent_api.py backend/app/schemas/agent.py backend/tests/agent/
git commit -m "feat(agent): runner_factory 按 provider 分流 + 任务台接 provider"
```

---

## Task 6：task_templates prompt 中性化

**Files:**
- Modify: `backend/app/services/agent/task_templates.py`（5 个 prompt 里 `mcp__controlled_db__db_read` → `db_read` 等）

**Step 1: 写验证（grep 检查无残留带前缀表述）**

Run: `cd backend && grep -c "mcp__controlled_db__" app/services/agent/task_templates.py`
Expected（改后）: `0`。

**Step 2: 中性化**

把每个 prompt 的「只读查询」段里 `mcp__controlled_db__db_read` / `mcp__controlled_db__describe` / `mcp__controlled_db__list_tables` 改为 `db_read` / `describe` / `list_tables`，并改述为「你有 db_read / describe / list_tables 三个只读工具（Claude Code 走受控 MCP、langchain 走进程内 @tool，环境自动选择）」。bash 备选段保留（Claude Code 非 MCP 模式仍用）。

**Step 3: 验证现有 agent 测试不破**

Run: `cd backend && python -m pytest tests/agent -v`
Expected: PASS。

**Step 4: Commit（待小可爱确认）**

```bash
git add backend/app/services/agent/task_templates.py
git commit -m "refactor(agent): task_templates 工具名中性化（两 runner 通用）"
```

---

## Task 7：老路径引擎替换 — TranslateTask（USDA 食材翻译）

**Files:**
- Modify: `backend/app/services/translate/task.py`
- Test: `backend/tests/translate/test_translate_task_agent.py`（新建）

**Step 1: 写集成测试（验证引擎替换后产出等价）**

```python
# backend/tests/translate/test_translate_task_agent.py
"""TranslateTask 引擎替换为 LangChainRunner 后，仍能正确翻译并写回 description_zh。"""
# 用 FakeMultiTurnRunner 注入：让 run_agent_loop 接收预设的 SQL 产出，
# 验证 usda_foods.description_zh 被更新、translate_status=done。
# （monkeypatch runner_factory.build_runner 返回 FakeMultiTurnRunner，
#  其事件流含 ```sql UPDATE usda_foods SET description_zh='水' ...```）
```

具体：monkeypatch `app.services.translate.task.run_agent_loop`（或 `runner_factory.build_runner`），注入一段含 `UPDATE usda_foods SET description_zh=..., translate_status='done' WHERE fdc_id IN (...)` 的 text_delta，断言库内对应行被更新。模板参见 `tests/agent/test_agent_loop.py`。

**Step 2: 跑测试验证失败**

Run: `cd backend && python -m pytest tests/translate/test_translate_task_agent.py -v`
Expected: FAIL（TranslateTask 仍是老的 translate_batch 分批逻辑）。

**Step 3: 实现引擎替换**

`TranslateTask.run` 改为：

```python
async def run(self, provider: str, config_dict: dict, ..., force=False) -> dict:
    from app.services.agent import runner_factory, session_runner
    from app.services.agent.task_templates import get_template
    prompt = get_template("usda_translate")["prompt"]
    if force:
        prompt = "强制重翻所有条目（含已 done/error）。\n\n" + prompt
    runner = runner_factory.build_runner("usda_translate", settings.database_url, provider=provider)
    import asyncio
    loop = asyncio.get_event_loop()
    # 复用 UsdaTask 记进度（保留前端进度展示）
    task = UsdaTask(task_type="translate", status="running", provider=provider)
    self.db.add(task); self.db.commit(); self.db.refresh(task)
    try:
        session_runner.run_agent_loop(
            0, runner, prompt, loop, unattended=True, db_session_factory=type(self.db).__class__ and None,
        )
        # 注意：unattended 模式不建 AgentSession（session_id=0 仅占位）——
        # 需让 run_agent_loop 支持不落 AgentMessage 的轻量模式，或建一个隐藏 session。
        task.status = "success"
    except Exception as e:
        task.status = "failed"; task.error_log = str(e)
    finally:
        self.db.commit()
    # 统计结果
    from app.models.usda import UsdaFood
    done = self.db.query(UsdaFood).filter(UsdaFood.translate_status == "done").count()
    total = self.db.query(UsdaFood).count()
    return {"translated": done, "total": total}
```

> **关键设计点**：`run_agent_loop` 当前强依赖 `AgentSession`（`_consume_events` 落 `AgentMessage`、status 管理）。老路径「不建 AgentSession」与现有 `run_agent_loop` 冲突。**Plan 决策**：老路径**也建一个 `AgentSession`**（`task_type` 对应、`runner_type` = provider、`title` 标「[后台]」），但前端任务台列表按 `title` 前缀或 `task_type` 过滤隐藏这些后台 session（或不动前端，仅在 USDA 维护页进度里关联展示）。这样复用 `run_agent_loop` 全套，改动最小。`session_id=0` 占位方案废弃，改为真实建 session。
>
> 落实：`TranslateTask.run` 先 `AgentSession(task_type="usda_translate", runner_type=provider, title="[后台]USDA翻译", status="pending")` 拿到真 sid，再传给 `run_agent_loop(sid, ..., unattended=True)`。`UsdaTask` 记 USDA 维护页进度；`AgentSession` 记 agent 对话（可在任务台回看）。

**Step 4: 跑测试验证通过**

Run: `cd backend && python -m pytest tests/translate/test_translate_task_agent.py -v`
Expected: PASS。

**Step 5: Commit（待小可爱确认）**

```bash
git add backend/app/services/translate/task.py backend/tests/translate/test_translate_task_agent.py
git commit -m "feat(translate): TranslateTask 引擎替换为 langchain Agent（unattended）"
```

---

## Task 8：老路径引擎替换 — TranslateNutrientsTask（营养素翻译）

**Files:**
- Modify: `backend/app/services/translate/nutrient_task.py`
- Test: `backend/tests/translate/test_nutrient_task_agent.py`

**同 Task 7 模式**，差异点：

- 模板用 `unmapped_nutrient_translate`。
- 写回表是 `usda_food_nutrients.name_zh`。
- 验证 `name_zh` 被更新。

**Step 1-5**：同 Task 7 结构（写测试 → 失败 → 实现 → 通过 → commit）。实现参照 Task 7 Step 3 的模式，仅替换模板名与统计查询。

**Commit（待小可爱确认）**：`feat(translate): TranslateNutrientsTask 引擎替换为 langchain Agent`

---

## Task 9：老路径引擎替换 — AIInferrer.infer_fuzzy_quantities（模糊量推测）

**Files:**
- Modify: `backend/app/services/importer/ai_inference/inferrer.py`（`infer_fuzzy_quantities`）
- Test: `backend/tests/importer/test_inferrer_agent.py`

**同 Task 7 模式**，差异点：

- 模板用 `infer_quantities`。
- `AIInferrer.__init__(db, ai_caller)` 的 `ai_caller` 在 Agent 模式下**不再逐条调用**——整个方法改为「构造 `LangChainRunner` + 渲染 `infer_quantities` prompt + `run_agent_loop(unattended=True)`」。
- `progress_callback` 改为订阅 `run_agent_loop` 的事件（或简化：跑前后统计 `recipe_ingredients.ai_inferred` 条数差）。
- 验证 `ingredients.piece_weight` 与 `recipe_ingredients.quantity_range` 被正确写入。

**关键决策**：`AIInferrer` 的 `ai_caller` 注入接口保留（向后兼容老的单条调用路径，如其它地方仍用），但 `infer_fuzzy_quantities` / `infer_densities` 内部优先走 Agent 路径。若 `ai_caller` 为 None 或 provider 非 openai/anthropic，回退老逻辑（逐条）——**保证不破坏现有调用方**。

**Step 1-5**：同 Task 7 结构。

**Commit（待小可爱确认）**：`feat(importer): 模糊量推测引擎替换为 langchain Agent`

---

## Task 10：老路径引擎替换 — AIInferrer.infer_densities（密度推测）

**Files:**
- Modify: `backend/app/services/importer/ai_inference/inferrer.py`（`infer_densities`）
- Test: `backend/tests/importer/test_inferrer_agent.py`（追加用例）

**同 Task 9 模式**，差异点：

- 模板用 `infer_densities`。
- 写回表是 `entity_densities`（INSERT 缺失，`source='agent'`）。
- **单位坑**（设计文档 §10 / FEATURE 记录）：`entity_densities.density` 是 kg/m³，prompt 已统一为 kg/m³（task_templates 的 `infer_densities` 模板已正确）。验证写入值合理（水=1000）。

**Step 1-5**：同 Task 9 结构。

**Commit（待小可爱确认）**：`feat(importer): 密度推测引擎替换为 langchain Agent`

---

## Task 11：前端任务台 provider 选择

**Files:**
- Modify: `frontend/src/views/admin/AgentTaskConsole.vue`
- Modify: `frontend/src/api/agent.ts`
- Modify: `backend/app/api/agent_api.py`（`/task-types` 可选返回各任务支持的 provider 列表，或前端硬编码三选项）

**Step 1: 后端 `/task-types` 暴露 provider 选项**（可选）

让 `list_task_types` 返回每个任务 `[{task_type, title, providers: ["claude_code", "openai", "anthropic"]}]`。或前端硬编码三选项（YAGNI，先硬编码）。

**Step 2: 前端加 provider 选择**

`AgentTaskConsole.vue` 任务按钮区加 provider 选择（`v-select`：Claude Code / OpenAI 兼容 / Anthropic 兼容），`createSession` 时带 `provider`。`api/agent.ts` 的 `createSession` payload 加 `provider` 字段。

**Step 3: 构建验证**

Run: `cd frontend && npm run build`
Expected: 构建通过，无 TS 错误。

**Step 4: Commit（待小可爱确认）**

```bash
git add frontend/src/views/admin/AgentTaskConsole.vue frontend/src/api/agent.ts
git commit -m "feat(agent): 任务台 provider 选择 UI"
```

---

## Task 12：端到端验收

**Step 1: 任务台验收（手测）**

- 配好 OpenAI 兼容 / Anthropic 兼容 provider（后台 AI 配置页）。
- 任务台选 provider=openai，点「补密度」任务，观察对话流（`db_read` 工具调用、SQL 输出、sql_guard 执行/审批）、刷新重放、`entity_densities` 写入。
- 同样测 provider=anthropic。
- 对比 Claude Code 路径行为是否对称。

**Step 2: 老路径验收（手测）**

- USDA 维护页点「翻译」（走 TranslateTask → LangChainRunner），观察 UsdaTask 进度、`usda_foods.description_zh` 写入、速度/token 对比改造前。
- 菜谱导入触发模糊量/密度推测，观察 `entity_densities` / `recipe_ingredients` 写入。

**Step 3: 全量测试**

Run: `cd backend && python -m pytest tests/ -v`
Expected: 本功能相关测试全绿；记录既有失败（FEATURE 记录有 13 个既有失败，与本功能无关）。

Run: `cd frontend && npm run build`
Expected: 构建通过。

**Step 4: 记录要点**

按项目规矩，实现完成后在 `cc/` 写 `FEATURE_langchain_Agent集成.md`，并更新 `CLAUDE.md` 项目索引（功能实现记录区）。

**Step 5: 最终 Commit（待小可爱确认）**

```bash
git add cc/FEATURE_langchain_Agent集成.md CLAUDE.md
git commit -m "docs: 记录 langchain Agent 集成功能"
```

---

## 风险提示（执行时盯紧）

1. **langchain API 版本漂移**：每个 Task 前用 context7 核对签名（见全局约定 2）。
2. **run_agent_loop 与老路径的 AgentSession 依赖**：Task 7 决策为「老路径也建隐藏 AgentSession」，落实时确认前端任务台列表是否需过滤这些 `[后台]` session。
3. **`db_query._reject_non_select` 重构**：Task 1 改为抛异常版，务必补 `db_query` CLI 回归测试，不破坏现有 Claude Code 非 MCP 模式。
4. **tool calling 遵循度**：OpenAI/Anthropic 对「文本输出 SQL 块」的格式遵循需手测；若不稳，退路是 `sql_extractor` 容错 + prompt 加强。
5. **AIInferrer 向后兼容**：Task 9/10 保留 `ai_caller` 老路径回退，不破坏现有调用方。
