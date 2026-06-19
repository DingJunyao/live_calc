# Agent 维护任务台 · 阶段 1（补单位质量）实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.
> 关联设计稿：[FEATURE_Agent维护任务台.md](./FEATURE_Agent维护任务台.md)

**Goal:** 实现任务台阶段 1——管理员点「补单位质量」按钮，后端用 claude code CLI（经第三方 Coding Plan 代理）驱动 Agent 自主统计/诊断/批量修正 `entity_unit_overrides.weight_per_unit`，前端流式展示对话、支持轮次间插话与危险写审批，会话持久化、刷新可回看；兼容 Windows 与 Linux。

**Architecture:** 后端新增 `agent_sessions`/`agent_messages`/`agent_approvals` 三表 + 受控 DB MCP（`db_read`/`db_write`/`describe`，危险写挂起审批）+ `ClaudeCodeRunner`（subprocess 调 CLI stream-json，线程桥接规避 Windows `SelectorEventLoop` 子进程限制）+ SSE 流式 + 后台线程调度（复用 [api_service.py](../backend/app/services/importer/api_service.py) 的 `ImportTask` 模式）。前端任务台页：按钮 + 对话流（SSE）+ 插话 + 确认弹窗 + 刷新重放。

**Tech Stack:** FastAPI、SQLAlchemy、Alembic、MCP Python SDK（`mcp`）、SSE（`sse-starlette`）、Vue 3 + Vuetify + EventSource。后端用 `uv` + `.venv`，前端 `npm`。

**项目适配约定（override skill 默认）：**
- **不自动 git commit**：每个 Task 末尾给「验收点」，由开发者确认后自行提交。
- **不在对话中启动服务**：验收基于已运行的自动重载前后端服务。
- **跨平台**：Windows/Linux 同一套「线程 `Popen` 逐行读 + `asyncio.Queue` 桥接」代码；路径用 `pathlib`；编码 `utf-8`；换行 `\n`。
- **TDD 适度**：纯逻辑（危险判定、prompt 渲染、消息聚合）写 `pytest` 单测；subprocess/SSE/前端集成用手动验收。
- **密度单位坑留阶段 2**，本计划不碰密度。

---

## Task 0: 技术验证 Spike（先验基石）

**目的：** 用最小脚本证明「subprocess 调 claude CLI 的 stream-json + 挂自制 MCP + `--resume` + 第三方代理 env」在 Windows 与 Linux 都跑通，再动正式代码。**这是降低后续所有风险的 gate。**

**Files:**
- Create: `backend/spikes/agent_cli_probe.py`
- Create: `backend/spikes/fake_db_mcp.py`
- Create: `backend/spikes/mcp_config.json`

**Step 1: 写最小受控 MCP server**（`fake_db_mcp.py`）

用 MCP Python SDK 暴露一个 `db_read` 工具，返回固定假数据，用于验证 CLI 能挂并调用自制 MCP。

```python
# backend/spikes/fake_db_mcp.py
"""最小 MCP server：暴露 db_read 返回固定行，供 spike 验证 CLI 挂载。"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("fake_db")


@mcp.tool()
def db_read(sql: str) -> str:
    """只读查询（spike 固定返回）。"""
    return "id|unit_name|weight_per_unit\n1|个|100\n2|根|100\n3|个|55"


if __name__ == "__main__":
    mcp.run(transport="stdio")
```

> 注：`mcp` 包的精确 API（`FastMCP` / 装饰器签名）以 Task 0 实跑时官方文档为准，`uv add mcp` 装包后核对。

**Step 2: 写 mcp_config.json**

```json
{
  "mcpServers": {
    "fake_db": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "python", "spikes/fake_db_mcp.py"],
      "cwd": "."
    }
  }
}
```

**Step 3: 写探针脚本**（`agent_cli_probe.py`）

后台线程用 `subprocess.Popen` 起 CLI、逐行读 stdout，打印每行事件类型；env 注入第三方代理（从 `.env` 或环境读 `ANTHROPIC_BASE_URL`/`ANTHROPIC_AUTH_TOKEN`）。

```python
# backend/spikes/agent_cli_probe.py
"""探针：验证 CLI stream-json + 自制 MCP + 第三方代理，跨平台。"""
import json
import os
import subprocess
import threading
from pathlib import Path

CWD = Path(__file__).resolve().parent
BACKEND = CWD.parent
CLI = os.environ.get("CLAUDE_CLI", "claude")
PROMPT = "用 db_read 查一下表里有哪些单位，然后告诉我你觉得哪个 weight_per_unit 不合理。"

env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"
# 第三方 Coding Plan 代理（在 .env 或 shell 里设好）
# env["ANTHROPIC_BASE_URL"] = "https://your-proxy"
# env["ANTHROPIC_AUTH_TOKEN"] = "xxx"

cmd = [
    CLI, "-p", PROMPT,
    "--output-format", "stream-json",
    "--include-partial-messages",
    "--verbose",
    "--mcp-config", str(CWD / "mcp_config.json"),
    "--allowedTools", "mcp__fake_db__db_read",
]

proc = subprocess.Popen(
    cmd, cwd=str(BACKEND), env=env,
    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, encoding="utf-8", bufsize=1,
)

event_types: list[str] = []


def read_stdout():
    for line in iter(proc.stdout.readline, ""):
        line = line.strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            print("RAW:", line[:200])
            continue
        t = evt.get("type")
        event_types.append(t)
        # 打印关键事件结构（截断）
        print(f"[{t}]", json.dumps(evt, ensure_ascii=False)[:300])


t = threading.Thread(target=read_stdout, daemon=True)
t.start()
proc.wait()
t.join(timeout=5)
print("\n=== 观察到的事件类型 ===", event_types)
```

**Step 4: Windows 上跑**

Run: `cd backend && uv run python spikes/agent_cli_probe.py`

Expected：打印出 `system`/`assistant`/`user`/`result` 等事件类型，能看到 `tool_use`（`mcp__fake_db__db_read`）与 `tool_result`，assistant 文本提到 `weight_per_unit=100` 不合理。

记录：事件字段结构、是否拿到 partial text 增量、第三方代理响应是否正常、CLI 进程是否正常退出。

**Step 5: Linux 上跑同样脚本**

Expected：行为一致（Linux `SelectorEventLoop` 支持子进程，但本脚本用线程 `Popen`，两平台同一套）。

**Step 6: 验证 `--resume`**

把 Step 3 的 `cmd` 第二次调用改成加 `--resume <首次输出的 session_id>` 并换一条新 prompt（如「把不合理的那个改成 5」），确认上下文连续（Agent 记得前文）。

**验收点：** 最小闭环「下指令 → Agent 调 `db_read` → 返回 → Agent 回复」可流式解析；`--resume` 跨进程上下文连续；Windows/Linux 一致。**若失败，回到 [设计稿 §11](./FEATURE_Agent维护任务台.md) 调整方案，不进 Task 1。** spike 脚本可保留在 `spikes/` 供回溯。

---

## Task 0 Spike 结论与计划调整（执行后补记）

Task 0 spike **5/5 PASS**（stream-json / MCP 挂载 / `--resume` / 第三方代理 / Windows）。关键约束与计划调整：

**全局约束（写入所有后续 Task）**：
- subprocess 起 claude 前 `env.pop("CLAUDECODE", None)`（嵌套启动陷阱，否则 CLI 拒绝启动）
- CLI 加 `--strict-mcp-config`（否则合并用户全局 MCP，越权风险——spike 实测 Agent 试图调开发者私人的 `live_calc_sqlite_mcp`）
- 文本增量解析路径：`stream_event.event.delta.text`（**不是**裸 `content_block_delta`）；事件落盘/传输用 utf-8（Windows 控制台 GBK 乱码）
- 加 `--max-budget-usd` 成本兜底（智谱 GLM Coding Plan / `glm-5`，$0.04–0.13/次）
- `mcp` 依赖须正式纳入项目依赖清单（spike 用 `uv pip install` 装入 `.venv`，未入 pyproject）

**方案 B 替代原设计 §6**（spike 验证后选定）：受控 MCP **只读**，写操作走文本解析。对后续 Task 的影响：
- **Task 2**：受控 MCP 只暴露 `db_read`/`describe`/`list_tables`（**无 `db_write` 工具**）；新增 `sql_extractor`（从 assistant 文本提取 ` ```sql ``` ` 块）+ `sql_guard` 危险判定
- **Task 3**：`_translate` 按 spike 真实事件结构映射（见上）；Runner 加 `env.pop("CLAUDECODE")`、`--strict-mcp-config`、`--max-budget-usd`
- **Task 4**：写操作流改为「`sql_extractor` 解析 → `sql_guard` → 安全直接执行 / 危险则写 `AgentApproval` + SSE 弹确认 → 执行结果作为下一轮 user 消息经 `--resume` 回流喂 Agent」
- **Task 5**：方案 B 固化——只读 MCP（`--strict-mcp-config` + `--allowedTools` 白名单）+ 写走文本解析 + `permission_denials` 监控越权

---

## Task 1: 数据模型与迁移

**Files:**
- Create: `backend/app/models/agent_session.py`
- Create: `backend/app/models/agent_message.py`
- Create: `backend/app/models/agent_approval.py`
- Modify: `backend/app/models/__init__.py`（导出新模型）
- Modify: `backend/app/models/entity_unit_override.py`（`source` 注释补 `agent`）
- Create: `backend/alembic/versions/<rev>_add_agent_tables.py`（autogenerate 后手修）
- Create: `cc/sql/agent_tables_sqlite.sql`、`cc/sql/agent_tables_mysql.sql`、`cc/sql/agent_tables_postgres.sql`

**Step 1: 写 `AgentSession`**（照 [import_task.py](../backend/app/models/import_task.py) 模式）

```python
# backend/app/models/agent_session.py
"""Agent 任务台会话模型。"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.core.database import Base


class AgentSession(Base):
    """一次 Agent 维护任务会话。"""
    __tablename__ = "agent_sessions"

    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String(32), nullable=False, index=True)
    # fill_piece_weight / fill_density / usda_translate / infer_quantities / infer_densities
    title = Column(String(128), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    # pending / running / awaiting_approval / success / failed / cancelled
    runner_type = Column(String(20), nullable=False, default="claude_code")
    # claude_code / native_loop
    claude_session_id = Column(String(128), nullable=True)  # CLI --resume 用
    initial_prompt = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "task_type": self.task_type, "title": self.title,
            "status": self.status, "runner_type": self.runner_type,
            "claude_session_id": self.claude_session_id,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
```

**Step 2: 写 `AgentMessage` 与 `AgentApproval`**

```python
# backend/app/models/agent_message.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class AgentMessage(Base):
    """会话对话流水，持久化以支持刷新重放。"""
    __tablename__ = "agent_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("agent_sessions.id"), nullable=False, index=True)
    seq = Column(Integer, nullable=False)  # 会话内顺序号
    role = Column(String(16), nullable=False)  # user / assistant / tool
    content = Column(Text, nullable=True)     # 文本（token 增量聚合后）
    tool_name = Column(String(64), nullable=True)
    tool_input = Column(JSON, nullable=True)
    tool_result = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
```

```python
# backend/app/models/agent_approval.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func
from app.core.database import Base


class AgentApproval(Base):
    """危险写操作的审批记录。"""
    __tablename__ = "agent_approvals"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("agent_sessions.id"), nullable=False, index=True)
    message_id = Column(Integer, ForeignKey("agent_messages.id"), nullable=True)
    sql = Column(Text, nullable=False)
    danger_reason = Column(String(128), nullable=True)
    affected_estimate = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    # pending / approved / rejected / auto_executed
    decided_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
```

**Step 3: 注册到 `app/models/__init__.py`**（加 `from .agent_session import AgentSession` 等）

**Step 4: `entity_unit_override.py` 的 `source` 注释补 `agent`**（不改类型，仍是 String）

**Step 5: 生成 alembic 迁移**

Run: `cd backend && uv run alembic revision --autogenerate -m "add agent session/message/approval"`

检查生成文件，确认三张表、外键、索引正确（autogenerate 偶有遗漏，手修）。

**Step 6: 写多引擎 SQL 脚本**（项目要求 SQLite/MySQL/PostgreSQL/PostgreSQL-PostGIS）。本改动与 PostGIS 无关，只出三份：`agent_tables_sqlite.sql`、`agent_tables_mysql.sql`、`agent_tables_postgres.sql`，内容与迁移一致（含 `source` 注释说明 agent）。

**Step 7: 应用迁移并验证**

Run: `cd backend && uv run alembic upgrade head`

用 sqlite MCP `describe_table` 确认三表字段。

**验收点：** 三表建好；迁移可正向；多引擎 SQL 齐全。开发者自行提交。

---

## Task 2: 受控 DB MCP server + 危险判定

**Files:**
- Create: `backend/app/services/agent/__init__.py`
- Create: `backend/app/services/agent/sql_guard.py`
- Create: `backend/app/services/agent/controlled_db_mcp.py`
- Test: `backend/tests/agent/__init__.py`、`backend/tests/agent/test_sql_guard.py`

**Step 1: 写危险判定的失败测试**

```python
# backend/tests/agent/test_sql_guard.py
import pytest
from app.services.agent.sql_guard import classify_sql, DangerLevel


def test_select_is_safe():
    assert classify_sql("SELECT * FROM entity_unit_overrides").dangerous is False


def test_delete_is_dangerous():
    assert classify_sql("DELETE FROM ingredients").dangerous is True


def test_update_without_where_is_dangerous():
    assert classify_sql("UPDATE entity_unit_overrides SET weight_per_unit=5").dangerous is True


def test_update_with_guarded_where_is_safe():
    sql = ("UPDATE entity_unit_overrides SET weight_per_unit=5, source='agent' "
           "WHERE id IN (1,2,3) AND weight_per_unit=100")
    assert classify_sql(sql).dangerous is False


def test_drop_is_dangerous():
    assert classify_sql("DROP TABLE ingredients").dangerous is True
```

**Step 2: 跑测试确认失败**

Run: `cd backend && uv run pytest tests/agent/test_sql_guard.py -v`
Expected: FAIL（`classify_sql` 未定义）

**Step 3: 实现 `sql_guard`**

```python
# backend/app/services/agent/sql_guard.py
"""SQL 危险判定。"""
import re
from dataclasses import dataclass


@dataclass
class SqlVerdict:
    dangerous: bool
    reason: str = ""


DangerLevel = SqlVerdict  # 别名，便于测试引用

_DANGEROUS_VERBS = re.compile(r"\b(DELETE|TRUNCATE|DROP|ALTER)\b", re.IGNORECASE)
_HAS_WHERE = re.compile(r"\bWHERE\b", re.IGNORECASE)


def classify_sql(sql: str) -> SqlVerdict:
    sql_stripped = sql.strip().rstrip(";").strip()
    if not sql_stripped:
        return SqlVerdict(False)

    if _DANGEROUS_VERBS.search(sql_stripped):
        verb = _DANGEROUS_VERBS.search(sql_stripped).group(1).upper()
        # DELETE 带 WHERE 且非 1=1 仍判危险（写操作一律人工确认更稳）
        return SqlVerdict(True, f"含 {verb} 写操作")

    if re.match(r"\s*UPDATE\b", sql_stripped, re.IGNORECASE):
        if not _HAS_WHERE.search(sql_stripped):
            return SqlVerdict(True, "UPDATE 无 WHERE")
        return SqlVerdict(False)

    if re.match(r"\s*INSERT\b", sql_stripped, re.IGNORECASE):
        return SqlVerdict(False)

    if re.match(r"\s*SELECT\b", sql_stripped, re.IGNORECASE):
        return SqlVerdict(False)

    # 其它未知语句保守判危险
    return SqlVerdict(True, "未识别语句类型")
```

**Step 4: 跑测试通过**

Run: `cd backend && uv run pytest tests/agent/test_sql_guard.py -v`
Expected: PASS（5 条全过）

**Step 5: 实现 `controlled_db_mcp.py`**（骨架，审批挂起接口在 Task 4 接通）

```python
# backend/app/services/agent/controlled_db_mcp.py
"""受控 DB MCP：CLI 通过 --mcp-config 挂载，db_write 过危险判定 + source=agent。

审批挂起（危险写）在 Task 4 经 session_runner 接通 SSE。本文件定义工具与判定入口。
"""
from __future__ import annotations
from typing import Any, Callable, Optional
from mcp.server.fastmcp import FastMCP

from app.services.agent.sql_guard import classify_sql


def build_server(
    db_url: str,
    *,
    on_dangerous_write: Optional[Callable[[str], "ApprovalDecision"]] = None,
) -> FastMCP:
    """构建受控 MCP server。

    on_dangerous_write: 危险写回调，返回是否放行（同步阻塞等用户确认）。
    生产中由 session_runner 注入，经 AgentApproval + SSE 桟接前端。
    """
    mcp = FastMCP("livecalc_db")

    @mcp.tool()
    def db_read(sql: str) -> str:
        """只读查询，返回 Markdown 表格（限 200 行）。仅允许 SELECT。"""
        # 实现：用 sqlalchemy 执行 sql，结果转 markdown；非 SELECT 拒绝
        ...  # 见 Step 6

    @mcp.tool()
    def db_write(sql: str) -> str:
        """写操作：过危险判定。安全直接执行（source=agent）；危险走 on_dangerous_write 审批。"""
        verdict = classify_sql(sql)
        if not verdict.dangerous:
            affected = _execute_write(db_url, sql, mark_source_agent=True)
            return f"已执行，影响 {affected} 行（source=agent）"
        if on_dangerous_write is None:
            return "拒绝：危险写且未配置审批通道"
        decision = on_dangerous_write(sql)
        if decision.approved:
            affected = _execute_write(db_url, sql, mark_source_agent=True)
            return f"已审批执行，影响 {affected} 行"
        return f"拒绝：{decision.reason}"

    @mcp.tool()
    def describe(table_name: str) -> str:
        """返回表结构（列名/类型）。"""
        ...  # 见 Step 6

    return mcp


def _execute_write(db_url: str, sql: str, *, mark_source_agent: bool) -> int:
    """执行写并返回影响行数。source=agent 标记由 SQL 自带（prompt 约束）或后续补充。"""
    ...  # 用 sqlalchemy engine，return rowcount


class ApprovalDecision:
    def __init__(self, approved: bool, reason: str = ""):
        self.approved = approved
        self.reason = reason
```

**Step 6: 补全 `db_read`/`describe`/`_execute_write`**

用 `sqlalchemy.create_engine(db_url)`（从 `app.core.config.settings.DATABASE_URL` 取）。`db_read` 限 `SELECT`、转 markdown 表格、截 200 行；`describe` 查 `information_schema` 或 `PRAGMA table_info`（按引擎，可先用 sqlalchemy inspect）。

**Step 7: 独立启动验证**

Run: `cd backend && uv run python -c "from app.services.agent.controlled_db_mcp import build_server; build_server('sqlite:///data/livecalc.db')"`

Expected: 不报错（MCP server 可构建）。用 Task 0 的 spike mcp_config 指向这个 server 跑一遍 `db_read`。

**验收点：** `sql_guard` 单测全过；MCP server 能独立构建并响应 `db_read`/`describe`。开发者自行提交。

---

## Task 3: AgentRunner 接口 + ClaudeCodeRunner

**Files:**
- Create: `backend/app/services/agent/runner.py`（接口 + 事件类型）
- Create: `backend/app/services/agent/claude_code_runner.py`

**Step 1: 定义 Runner 接口与事件类型**

```python
# backend/app/services/agent/runner.py
"""AgentRunner 接口与事件类型。"""
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional, Protocol


@dataclass
class AgentEvent:
    kind: str  # text_delta / tool_use / tool_result / approval_needed / done / error
    text: str = ""
    tool_name: str = ""
    tool_input: dict = field(default_factory=dict)
    tool_result: Any = None
    approval_id: Optional[int] = None
    error: str = ""


class AgentRunner(Protocol):
    """跑一轮 Agent 对话，流式产出 AgentEvent。"""

    def run(self, prompt: str, *, resume_session_id: Optional[str] = None) -> Iterator[AgentEvent]:
        ...

    @property
    def last_session_id(self) -> Optional[str]:
        ...
```

**Step 2: 实现 `ClaudeCodeRunner`**（核心：`Popen` + 线程逐行读 stream-json + queue 桥接）

```python
# backend/app/services/agent/claude_code_runner.py
"""ClaudeCodeRunner：subprocess 调 claude CLI stream-json，线程桥接规避 Windows 事件循环限制。"""
import json
import os
import queue
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Iterator, Optional

from app.services.agent.runner import AgentEvent


class ClaudeCodeRunner:
    def __init__(self, mcp_config_path: str, *, allowed_tools: list[str],
                 cwd: str = ".", timeout: int = 600, env: Optional[dict] = None):
        self.cli = shutil.which("claude") or "claude"
        self.mcp_config_path = mcp_config_path
        self.allowed_tools = allowed_tools
        self.cwd = cwd
        self.timeout = timeout
        self.env = {**os.environ, **(env or {}), "PYTHONIOENCODING": "utf-8"}
        self._last_session_id: Optional[str] = None

    @property
    def last_session_id(self) -> Optional[str]:
        return self._last_session_id

    def run(self, prompt: str, *, resume_session_id: Optional[str] = None) -> Iterator[AgentEvent]:
        cmd = [
            self.cli, "-p", prompt,
            "--output-format", "stream-json",
            "--include-partial-messages", "--verbose",
            "--mcp-config", self.mcp_config_path,
            "--allowedTools", ",".join(self.allowed_tools),
        ]
        if resume_session_id:
            cmd += ["--resume", resume_session_id]

        proc = subprocess.Popen(
            cmd, cwd=self.cwd, env=self.env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", bufsize=1,
        )
        line_q: "queue.Queue[Optional[str]]" = queue.Queue()

        def _pump():
            try:
                for line in iter(proc.stdout.readline, ""):
                    line_q.put(line)
            finally:
                line_q.put(None)  # EOF 哨兵

        threading.Thread(target=_pump, daemon=True).start()

        try:
            while True:
                line = line_q.get(timeout=self.timeout)
                if line is None:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    evt = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for ev in self._translate(evt):
                    yield ev
            proc.wait(timeout=10)
            yield AgentEvent(kind="done")
        except Exception as e:
            yield AgentEvent(kind="error", error=str(e))
        finally:
            if proc.poll() is None:
                proc.kill()

    def _translate(self, evt: dict) -> list[AgentEvent]:
        """把 CLI stream-json 事件翻译成 AgentEvent。具体字段以 Task 0 spike 观察为准。"""
        out: list[AgentEvent] = []
        t = evt.get("type")
        if t == "system":
            sid = evt.get("session_id") or evt.get("sessionId")
            if sid:
                self._last_session_id = sid
        elif t == "assistant":
            for block in evt.get("message", {}).get("content", []):
                if block.get("type") == "text":
                    out.append(AgentEvent(kind="text_delta", text=block["text"]))
                elif block.get("type") == "tool_use":
                    out.append(AgentEvent(kind="tool_use",
                                          tool_name=block.get("name", ""),
                                          tool_input=block.get("input", {})))
        elif t == "user":
            for block in evt.get("message", {}).get("content", []):
                if block.get("type") == "tool_result":
                    out.append(AgentEvent(kind="tool_result", tool_result=block.get("content")))
        # approval_needed 事件由 Task 4 session_runner 在 on_dangerous_write 内合成
        return out
```

> **关键**：`_translate` 的字段映射必须对照 Task 0 spike 实际观察到的事件结构调整（`system.init`、`assistant`/`user` 的 `message.content` 结构、partial text 事件名）。spike 记录的事件样例贴到本文件注释里。

**Step 3: 手动验证**

写个临时脚本起 `ClaudeCodeRunner`，跑一个简单 prompt（用 Task 0 的 fake_db MCP），打印 `AgentEvent` 序列。确认 Windows/Linux 一致。

**验收点：** Runner 能流式吐出 `AgentEvent`，`last_session_id` 正确捕获，跨平台一致。

---

## Task 4: 流式桥接与会话持久化 + 审批挂起

**Files:**
- Create: `backend/app/services/agent/stream_bridge.py`（asyncio.Queue 广播）
- Create: `backend/app/services/agent/session_runner.py`（编排：Runner → AgentMessage 落库 → 推 queue → 审批）

**Step 1: `stream_bridge.py`**——每会话一个 `asyncio.Queue`，SSE 订阅；提供 `publish`/`subscribe`。

```python
# backend/app/services/agent/stream_bridge.py
"""会话级事件广播：session_runner 发布，SSE 端点订阅。"""
import asyncio
from collections import defaultdict

_queues: dict[int, set[asyncio.Queue]] = defaultdict(set)
_lock = asyncio.Lock()


async def subscribe(session_id: int) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=1000)
    async with _lock:
        _queues[session_id].add(q)
    return q


async def unsubscribe(session_id: int, q: asyncio.Queue):
    async with _lock:
        _queues[session_id].discard(q)


def publish_sync(session_id: int, event: dict, loop: asyncio.AbstractEventLoop):
    """从后台线程发布事件到该会话所有订阅者。"""
    for q in list(_queues.get(session_id, ())):
        loop.call_soon_threadsafe(_try_put, q, event)


def _try_put(q: asyncio.Queue, event: dict):
    try:
        q.put_nowait(event)
    except asyncio.QueueFull:
        pass  # 慢订阅者丢弃旧事件，SSE 靠历史重放兜底
```

**Step 2: `session_runner.py`**——后台线程内：起 Runner，消费 `AgentEvent`，聚合成 `AgentMessage` 落库，发布到 stream_bridge；`db_write` 危险时通过 `on_dangerous_write` 闭包写 `AgentApproval` + 发布 `approval_needed` + 阻塞等用户决策。

```python
# backend/app/services/agent/session_runner.py（关键骨架）
"""在后台线程中跑一个 Agent 会话：事件聚合落库 + 流式广播 + 危险写审批。"""
import threading
from typing import Optional

from app.core.database import SessionLocal
from app.models.agent_session import AgentSession
from app.models.agent_message import AgentMessage
from app.models.agent_approval import AgentApproval
from app.services.agent.runner import AgentRunner
from app.services.agent.stream_bridge import publish_sync


def run_session(session_id: int, runner: AgentRunner, prompt: str,
                main_loop, *, resume: bool = False):
    """后台线程入口。main_loop 用于跨线程发布 SSE 事件。"""
    db = SessionLocal()
    pending_approvals: dict[str, threading.Event] = {}
    try:
        sess = db.query(AgentSession).get(session_id)
        sess.status = "running"; db.commit()
        seq = _next_seq(db, session_id)

        def on_dangerous_write(sql: str):
            # 写 AgentApproval + 发 approval_needed + 阻塞等
            ap = AgentApproval(session_id=session_id, sql=sql, status="pending")
            db.add(ap); db.commit(); db.refresh(ap)
            publish_sync(session_id, {"kind": "approval_needed",
                                      "approval_id": ap.id, "sql": sql}, main_loop)
            ev = threading.Event(); pending_approvals[str(ap.id)] = ev
            sess.status = "awaiting_approval"; db.commit()
            ev.wait(timeout=3600)  # 等前端 POST /approvals/{id} 唤醒
            # 重新查审批结果
            ap = db.query(AgentApproval).get(ap.id)
            from app.services.agent.controlled_db_mcp import ApprovalDecision
            return ApprovalDecision(ap.status == "approved", ap.danger_reason or "")

        # 把 on_dangerous_write 注入 runner 用的 controlled_db_mcp（构造时传入）
        resume_id = sess.claude_session_id if resume else None
        for event in runner.run(prompt, resume_session_id=resume_id):
            msg = _persist_event(db, session_id, seq, event); seq += 1
            publish_sync(session_id, _event_to_dict(event), main_loop)
            if event.kind == "done":
                break
        # 记录 CLI session_id 供后续 --resume
        sess.claude_session_id = runner.last_session_id
        sess.status = "success"; db.commit()
    except Exception as e:
        sess = db.query(AgentSession).get(session_id)
        if sess:
            sess.status = "failed"; sess.error = str(e); db.commit()
    finally:
        db.close()


def wake_approval(session_id: int, approval_id: int, approved: bool, user_id: int):
    """POST /approvals/{id} 调用：写决策 + 唤醒阻塞的 run_session。"""
    db = SessionLocal()
    try:
        ap = db.query(AgentApproval).get(approval_id)
        ap.status = "approved" if approved else "rejected"
        ap.decided_by = user_id
        from datetime import datetime
        ap.decided_at = datetime.utcnow(); db.commit()
    finally:
        db.close()
    # 唤醒（pending_approvals 跨线程访问需线程安全结构；实现时用模块级锁字典）
```

> 实现注意：`pending_approvals` 跨线程，需用模块级 `threading.Lock` 保护的字典（或 `queue.Queue`）。`_persist_event` 按 `event.kind` 聚合：`text_delta` 合并到当前 assistant 消息、`tool_use`/`tool_result` 各成一行、`done`/`error` 不落消息。`main_loop` 由 API 层（Task 5）创建会话时传入（`asyncio.get_event_loop()`）。

**Step 3: 手动验证**——构造假的 `AgentEvent` 序列喂给 `_persist_event`，确认 `AgentMessage` 正确落库（单测）。

**验收点：** 事件聚合落库正确；审批挂起/唤醒机制可跑通（模拟）。

---

## Task 5: SSE 与会话 API

**Files:**
- Create: `backend/app/schemas/agent.py`
- Create: `backend/app/api/agent_api.py`
- Modify: `backend/app/api/__init__.py` 或 `main.py`（注册 router）
- 添加依赖：`uv add sse-starlette`

**Step 1: 写 schemas**（`AgentSessionOut`、`AgentMessageOut`、`AgentApprovalOut`、`CreateSessionIn`、`PostMessageIn`、`ApprovalIn`）

**Step 2: 实现 `agent_api.py` 端点**

```python
# backend/app/api/agent_api.py（核心端点）
import asyncio, threading
from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.core.security import get_current_user
from app.models.agent_session import AgentSession
from app.models.agent_message import AgentMessage
from app.services.agent.session_runner import run_session, wake_approval
from app.services.agent.task_templates import get_template  # Task 6
from app.services.agent.claude_code_runner import ClaudeCodeRunner
from app.services.agent.stream_bridge import subscribe, unsubscribe

router = APIRouter(prefix="/agent", tags=["agent"])


def _require_admin(user):
    if not getattr(user, "is_admin", False):
        raise HTTPException(403, "仅管理员可使用任务台")


@router.post("/sessions")
def create_session(task_type: str, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    _require_admin(user)
    tpl = get_template(task_type)  # Task 6
    sess = AgentSession(task_type=task_type, title=tpl["title"],
                        status="pending", runner_type="claude_code",
                        initial_prompt=tpl["prompt"], user_id=user.id)
    db.add(sess); db.commit(); db.refresh(sess)

    loop = asyncio.get_event_loop()
    runner = _build_runner(task_type, tpl)  # 构造 ClaudeCodeRunner + 受控 MCP
    t = threading.Thread(target=run_session,
                         args=(sess.id, runner, tpl["prompt"], loop),
                         daemon=True)
    t.start()
    return {"session_id": sess.id}


@router.get("/sessions/{sid}/stream")
async def stream_session(sid: int, user=Depends(get_current_user)):
    _require_admin(user)
    db = SessionLocal()
    history = [m for m in db.query(AgentMessage)
               .filter(AgentMessage.session_id == sid).order_by(AgentMessage.seq)]
    db.close()

    async def event_gen():
        # 1) 先回放历史
        for m in history:
            yield {"event": "message", "data": _msg_to_sse(m)}
        # 2) 续接实时
        q = await subscribe(sid)
        try:
            while True:
                evt = await q.get()
                yield {"event": "message", "data": _json_dumps(evt)}
        finally:
            await unsubscribe(sid, q)

    return EventSourceResponse(event_gen())


@router.post("/sessions/{sid}/messages")
def post_message(sid: int, text: str, user=Depends(get_current_user)):
    _require_admin(user)
    # 用 --resume 起新轮：读 claude_session_id，起新 run_session(resume=True)
    ...


@router.post("/approvals/{aid}")
def decide_approval(aid: int, approved: bool, user=Depends(get_current_user)):
    _require_admin(user)
    ap = ...  # 查 approval
    wake_approval(ap.session_id, aid, approved, user.id)
    return {"ok": True}
```

> `EventSourceResponse` 来自 `sse-starlette`。`_build_runner` 在 Task 6 后接通受控 MCP（`on_dangerous_write` 闭包需访问会话——这里有个进程模型问题，见下）。

**Step 3: 受控 MCP 进程模型决策**

`controlled_db_mcp` 是 stdio 子进程（CLI 通过 `--mcp-config` 拉起），它**无法直接访问**主后端进程的 `pending_approvals`/`AgentApproval`。两个方案，Task 5 选定：

- **方案 A（推荐）**：受控 MCP 子进程通过 **HTTP 回调主后端**（`POST /agent/internal/db-write-request`）发起审批请求，主后端写 `AgentApproval` + SSE 通知前端 + 阻塞等 `wake_approval`，再 HTTP 回结果给 MCP 子进程。MCP 子进程只做 sql_guard + 执行，审批状态全在主进程。
- **方案 B**：受控 MCP 不做审批，`--allowedTools` 只给 `db_read`/`describe`，所有 `db_write` 由 Agent 在文本里输出 SQL，主后端解析 assistant 文本提取 SQL 再走守卫审批。绕开进程隔离，但要求 Agent 配合输出格式。

**spike（Task 0）若验证 CLI 能稳定调 stdio MCP，选 A；否则选 B。** plan 据此在 Task 5 实现对应通道。

**Step 4: 后台调度**——`create_session` 起 daemon 线程跑 `run_session`（复用 [api_service.py](../backend/app/services/importer/api_service.py) 的线程 + 独立 Session 模式）。

**Step 5: 手动验证**

Run（服务已在跑）：`curl -X POST 'http://localhost:8000/api/v1/agent/sessions?task_type=fill_piece_weight' -H 'Authorization: Bearer <token>'`
然后 `curl -N 'http://localhost:8000/api/v1/agent/sessions/<id>/stream' -H 'Authorization: Bearer <token>'`

Expected：SSE 流式推送 `AgentEvent`；刷新重连先回放历史再续接。

**验收点：** SSE 流式、刷新重放、插话与审批端点工作。

---

## Task 6: 补单位质量任务模板

**Files:**
- Create: `backend/app/services/agent/task_templates.py`

**Step 1: 写模板**

```python
# backend/app/services/agent/task_templates.py
"""预设任务模板：title + prompt + 允许工具。"""

_TEMPLATES = {
    "fill_piece_weight": {
        "title": "补单位质量（自定义单位对应克数）",
        "allowed_tools": ["mcp__livecalc_db__db_read",
                          "mcp__livecalc_db__db_write",
                          "mcp__livecalc_db__describe"],
        "prompt": (
            "你是食材数据维护助手。任务：维护 entity_unit_overrides 表里「自定义单位对应的质量」"
            "（weight_per_unit 字段，单位克）。\n\n"
            "步骤：\n"
            "1. 用 db_read 统计 entity_unit_overrides 里 weight_per_unit 缺失或明显占位"
            "（如 =100）的条目，按 unit_name 聚类看分布。\n"
            "2. 诊断哪些不合理（如「花椒 1 颗 =100g」实际应 ~0.02g、「干辣椒 1 个」应 ~2-3g）。\n"
            "3. 按食材常识估算合理克数，分类给出修正方案。\n"
            "4. 用 db_write 执行批量修正：UPDATE 必须带 WHERE id IN (...) "
            "AND weight_per_unit=<原占位值> 守卫，并把 source 设为 'agent'。\n"
            "5. 完成后用 db_read 复核改动行数。\n\n"
            "遇到不确定的值（如某罕见食材），先列出再问我，不要乱猜。"
        ),
    },
}


def get_template(task_type: str) -> dict:
    if task_type not in _TEMPLATES:
        raise KeyError(f"未知任务类型: {task_type}")
    return _TEMPLATES[task_type]
```

**Step 2: 单测**——`get_template("fill_piece_weight")` 返回含 `entity_unit_overrides`、`source`、`WHERE` 守卫提示的 prompt。

**验收点：** 模板可渲染，prompt 符合历史验证的「统计→诊断→守卫批量改」模式。

---

## Task 7: 前端 API + SSE composable

**Files:**
- Create: `frontend/src/types/agent.ts`
- Create: `frontend/src/api/agent.ts`
- Create: `frontend/src/composables/useAgentSession.ts`

**Step 1: types**（`Session`/`Message`/`Approval`/`AgentEvent`）

**Step 2: `api/agent.ts`**——`createSession`/`listSessions`/`getSession`/`postMessage`/`decideApproval`（axios，复用现有 api 客户端基座）

**Step 3: `useAgentSession.ts`**——`EventSource` 订阅 SSE，先重放历史（首条消息起按 seq）再接实时，维护响应式 `messages`，提供 `interject(text)`/`approve(id,ok)`。

```typescript
// frontend/src/composables/useAgentSession.ts（核心骨架）
import { ref, onUnmounted } from 'vue'
import { api } from '@/api/agent'

export function useAgentSession(sessionId: number) {
  const messages = ref<any[]>([])
  const status = ref<string>('pending')
  let es: EventSource | null = null

  async function connect() {
    // 1) 先拉历史
    const { data } = await api.getSession(sessionId)
    messages.value = data.messages
    status.value = data.status
    // 2) 续接 SSE
    const token = localStorage.getItem('token') // 按现有鉴权方式
    es = new EventSource(`/api/v1/agent/sessions/${sessionId}/stream?token=${token}`)
    es.onmessage = (e) => {
      const evt = JSON.parse(e.data)
      applyEvent(evt) // 按 kind 追加/合并到 messages
    }
  }

  function applyEvent(evt: any) {
    if (evt.kind === 'text_delta') { /* 追加到末尾 assistant 消息 */ }
    else if (evt.kind === 'tool_use') { /* push tool 卡片 */ }
    else if (evt.kind === 'tool_result') { /* 更新对应 tool 卡片 */ }
    else if (evt.kind === 'approval_needed') { /* push 待审批卡片 */ }
    else if (evt.kind === 'done') { status.value = 'success' }
  }

  function interject(text: string) { return api.postMessage(sessionId, text) }
  function approve(id: number, ok: boolean) { return api.decideApproval(id, ok) }

  onUnmounted(() => es?.close())
  return { messages, status, connect, interject, approve }
}
```

> **鉴权**：现有 SSE 用 `EventSource` 无法带自定义 header，token 走 query（后端 `/stream` 端点需支持 query token 鉴权），或用 `fetch` + `ReadableStream` 自实现 SSE 以带 header。按项目现有鉴权风格选定，Task 7 实现。

**Step 4: 构建验证**

Run: `cd frontend && npm run build`
Expected: 构建通过

**验收点：** 构建通过；composable 能订阅 SSE 并维护 `messages`。

---

## Task 8: 前端任务台 UI

**Files:**
- Create: `frontend/src/views/admin/AgentTaskConsole.vue`
- Modify: `frontend/src/router/index.ts`（路由）
- Modify: 管理页入口（导航/管理布局加「Agent 任务台」）

**Step 1: 布局**（Vuetify）：左侧任务按钮列表（「补单位质量」），右侧对话流，底部插话框；顶部历史会话切换。

**Step 2: 对话流渲染**——按 `AgentEvent` 类型：
- `assistant` 文本：流式追加
- `tool_use`：折叠卡片，显示 `tool_name` + `tool_input`（SQL 高亮）
- `tool_result`：更新卡片显示结果
- `approval_needed`：醒目卡片 + 「同意 / 拒绝」按钮

**Step 3: 流式渲染**——`text_delta` 实时追加到最后一条 assistant 消息，平滑滚动到底。

**Step 4: 插话框**——回车提交 `interject(text)`，触发后端 `--resume` 新轮。

**Step 5: 危险确认**——`approval_needed` 卡片的同意/拒绝调 `approve(id, ok)`。

**Step 6: 刷新重放**——`onMounted` 用 session_id `connect()`（拉历史 + 续接 SSE），F5 后对话完整回放。

**Step 7: 响应式**——桌面双栏（按钮 + 对话），移动单栏（按钮折叠到顶部/抽屉），符合项目响应式要求。

**Step 8: 构建验证**

Run: `cd frontend && npm run build`
Expected: 构建通过

**验收点：** 构建通过；各交互可用，移动端布局正常。

---

## Task 9: 端到端验收（补单位质量，Windows + Linux）

**前提：** 自动重载前后端已运行；claude code CLI 可用且第三方代理 env 配好（`ANTHROPIC_BASE_URL`/`ANTHROPIC_AUTH_TOKEN`）。

**Step 1: 造数据**——用 sqlite MCP `read_query` 确认 `entity_unit_overrides` 有一批 `weight_per_unit` 缺失/占位（=100）的条目；没有则临时插几条。

**Step 2: 触发**——打开任务台，点「补单位质量」。

**Step 3: 观察对话流**——确认 Agent 走「统计 → 诊断 → 方案 → 执行」：
- assistant 文本流式出现
- `tool_use(db_read)` 卡片显示统计 SQL，`tool_result` 显示分布
- 若 Agent 发起 `db_write` 且被 `sql_guard` 判危险 → 弹确认；安全 → 自动执行（`source='agent'`）

**Step 4: 验证数据**——sqlite MCP `read_query` 确认：`weight_per_unit` 被批量修正、`source='agent'`、**未误改已修正值**（守卫生效）。

**Step 5: 插话**——Agent 一轮结束后插「花椒 1 颗按 0.05g」，确认 `--resume` 新轮带上、对话连续。

**Step 6: 刷新**——F5，确认历史对话完整回放，会话状态正确。

**Step 7: Linux 验证**（若可用）——同样流程跑一遍，确认子进程桥接行为一致。

**验收点：** 全链路在 Windows（与 Linux）跑通：按钮 → Agent 流式 → 守卫审批 → 数据修正 → 插话 → 刷新重放。

---

## 风险闭环

- **Task 0 是 gate**：spike 失败则回 [设计稿 §11](./FEATURE_Agent维护任务台.md) 调整，不进 Task 1。
- **受控 MCP 进程模型**：Task 5 在 spike 结论基础上选方案 A（HTTP 回调审批）或 B（文本提 SQL）。
- **密度单位坑**：留阶段 2，本计划不碰。
- **鉴权跨 SSE**：Task 7 按项目现有鉴权风格定 token 传递方式。

## 阶段 1 范围之外（YAGNI，留后续阶段）
- 补密度、USDA 翻译任务（阶段 2）
- 导入推测端点 `/ai-infer/*` 改调 Runner（阶段 2）
- `NativeLoopRunner` 备用实现（阶段 3）
- 并发队列、审计日志、任务预算上限
