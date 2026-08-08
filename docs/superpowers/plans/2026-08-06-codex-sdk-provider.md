# Codex SDK Provider 接入 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 Codex provider，接入 Agent 任务台、USDA 翻译和黑名单 AI 匹配，并把会话锚点从 `claude_session_id` 迁移为 `external_session_id`。

**Architecture:** 使用 `openai-codex` Python SDK 驱动 app-server stdio；新增 `CodexRunner` 和 `CodexTranslator` 与 Claude Code 平级；前端统一从 translation config 读取已启用 provider 并显示可读标签；黑名单增加“AI 匹配全部”单会话入口。

**Tech Stack:** FastAPI、SQLAlchemy、Alembic、openai-codex、Vue 3、TypeScript、Vuetify。

---

## File Structure

- `backend/app/services/agent/codex_runner.py`：Codex SDK 的 `AgentRunner` 实现、MCP overrides、事件映射。
- `backend/app/services/translate/codex.py`：Codex 翻译后端。
- `backend/app/services/agent/blacklist_group_task.py`：单组和全部组 AI 匹配任务触发。
- `backend/app/services/agent/task_templates.py`：多分组匹配模板。
- `backend/app/api/blacklist_groups.py`：单组和全部组 AI 匹配 API。
- `backend/app/models/agent_session.py`、`backend/app/schemas/agent.py`、`backend/app/api/agent_api.py`、`backend/app/services/agent/session_runner.py`：`external_session_id` 替换。
- `backend/alembic/versions/20260806_0001_add_external_session_id.py`：列迁移。
- `frontend/src/utils/agentProviders.ts`：provider 标签和启用过滤。
- `frontend/src/views/admin/*.vue`：下拉和黑名单全部匹配入口。
- `frontend/src/api/local/*`：本地模式代理。

---

### Task 1: 添加 openai-codex 依赖

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/requirements.txt`
- Modify: `backend/uv.lock`

- [ ] **Step 1: 修改 pyproject.toml**

在 `backend/pyproject.toml` 的 `langchain-anthropic` 后追加：

```toml
	# Codex SDK Provider。0.144.4 会固定拉入 openai-codex-cli-bin 0.144.4。
	openai-codex = "==0.144.4"
```

- [ ] **Step 2: 修改 requirements.txt**

在 `requests>=2.31.0,<3.0.0` 后追加：

```text
openai-codex==0.144.4
```

- [ ] **Step 3: 更新 uv.lock**

Run:

```powershell
Set-Location backend; uv lock
```

Expected: 命令成功，`backend/uv.lock` 新增 `openai-codex` 和 `openai-codex-cli-bin` 条目。

- [ ] **Step 4: Commit**

```powershell
git add backend/pyproject.toml backend/requirements.txt backend/uv.lock
git commit -m "feat(codex): add openai-codex dependency"
```

---

### Task 2: 后端翻译配置补齐 codex 默认项

**Files:**
- Modify: `backend/app/api/usda_admin.py`
- Modify: `backend/app/services/translate/registry.py`
- Test: `backend/tests/services/test_translate_registry.py`

- [ ] **Step 1: 写失败测试**

Create `backend/tests/services/test_translate_registry.py`:

```python
from app.services.translate.registry import list_provider_names


def test_list_provider_names_has_codex_after_claude():
    names = list_provider_names()
    assert names.index("codex") == names.index("claude_code") + 1
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
Set-Location backend; & 'D:\code\livecalc\.venv\Scripts\python.exe' -m pytest tests/services/test_translate_registry.py -v
```

Expected: FAIL，`list_provider_names` 无 `codex`。

- [ ] **Step 3: 修改 usda_admin.py 默认配置**

把 `DEFAULT_TRANSLATION_CONFIG` 中：

```python
        "claude_code": {"enabled": False},
        "openai": {"enabled": False, "base_url": "https://api.openai.com/v1", "api_key": "", "model": "gpt-4o-mini"},
```

改为：

```python
        "claude_code": {"enabled": False},
        "codex": {"enabled": False},
        "openai": {"enabled": False, "base_url": "https://api.openai.com/v1", "api_key": "", "model": "gpt-4o-mini"},
```

同时把 `get_stored_translation_config` 改为深补默认值，避免旧配置缺 `codex`：

```python
def _merge_default_config(stored: dict) -> dict:
    import copy

    merged = copy.deepcopy(DEFAULT_TRANSLATION_CONFIG)
    for region in ("ai", "machine"):
        stored_providers = (stored.get(region) or {}).get("providers") or {}
        for key, value in stored_providers.items():
            merged[region]["providers"][key] = value
    return merged


def get_stored_translation_config(db: Session) -> TranslationConfig:
    cfg = db.query(TranslationConfig).first()
    if not cfg:
        cfg = TranslationConfig(config=DEFAULT_TRANSLATION_CONFIG)
        db.add(cfg); db.commit(); db.refresh(cfg)
    else:
        cfg.config = _merge_default_config(cfg.to_dict())
        db.commit()
        db.refresh(cfg)
    return cfg
```

- [ ] **Step 4: 修改 registry.py**

只修改 `list_provider_names`：

```python
def list_provider_names() -> list[str]:
    return ["claude_code", "codex", "openai", "anthropic", "baidu", "aliyun", "deepl"]
```

`get_translator` 的 codex 分支在 Task 6 补上。

- [ ] **Step 5: Commit**

```powershell
git add backend/app/api/usda_admin.py backend/app/services/translate/registry.py backend/tests/services/test_translate_registry.py
git commit -m "feat(codex): add codex translation config defaults and registry slot"
```

---

### Task 3: external_session_id 模型与迁移

**Files:**
- Modify: `backend/app/models/agent_session.py`
- Create: `backend/alembic/versions/20260806_0001_add_external_session_id.py`
- Modify: `backend/app/schemas/agent.py`
- Modify: `backend/app/api/agent_api.py`
- Modify: `backend/app/services/agent/session_runner.py`
- Modify: `backend/tests/agent/test_agent_api.py`

- [ ] **Step 1: 修改模型**

在 `backend/app/models/agent_session.py` 中把：

```python
    claude_session_id = Column(String(128), nullable=True)
```

改为：

```python
    external_session_id = Column(String(128), nullable=True)
```

并把 `to_dict` 的 `"claude_session_id"` 改为 `"external_session_id"`。

- [ ] **Step 2: 创建迁移**

Create `backend/alembic/versions/20260806_0001_add_external_session_id.py`:

```python
"""add external_session_id and drop claude_session_id

Revision ID: 20260806_0001
Revises: 20260723_0001
Create Date: 2026-08-06
"""
from alembic import op
import sqlalchemy as sa

revision = "20260806_0001"
down_revision = "20260723_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_sessions", sa.Column("external_session_id", sa.String(128), nullable=True))
    op.execute("UPDATE agent_sessions SET external_session_id = claude_session_id")
    with op.batch_alter_table("agent_sessions") as batch_op:
        batch_op.drop_column("claude_session_id")


def downgrade() -> None:
    op.add_column("agent_sessions", sa.Column("claude_session_id", sa.String(128), nullable=True))
    op.execute("UPDATE agent_sessions SET claude_session_id = external_session_id")
    with op.batch_alter_table("agent_sessions") as batch_op:
        batch_op.drop_column("external_session_id")
```

- [ ] **Step 3: 修改 schema**

在 `backend/app/schemas/agent.py` 中把：

```python
    claude_session_id: Optional[str] = None
```

改为：

```python
    external_session_id: Optional[str] = None
```

- [ ] **Step 4: 修改 agent_api.py**

把 `_session_to_out` 中：

```python
        claude_session_id=s.claude_session_id,
```

改为：

```python
        external_session_id=s.external_session_id,
```

把 `post_message` 中：

```python
    if not sess.claude_session_id:
        raise HTTPException(
            status_code=409,
            detail="会话缺少 claude_session_id，无法 resume",
        )

    resume_sid = sess.claude_session_id
```

改为：

```python
    if not sess.external_session_id:
        raise HTTPException(
            status_code=409,
            detail="会话缺少外部会话 ID，无法 resume",
        )

    resume_sid = sess.external_session_id
```

- [ ] **Step 5: 修改 session_runner.py**

把 `run_session` 中：

```python
        last_claude_sid: str | None
        try:
            last_claude_sid = runner.last_session_id
        except Exception:  # noqa: BLE001
            last_claude_sid = None

        sess = db.query(AgentSession).get(session_id)
        if sess is not None:
            sess.claude_session_id = last_claude_sid or sess.claude_session_id
```

改为：

```python
        last_external_sid: str | None
        try:
            last_external_sid = runner.last_session_id
        except Exception:  # noqa: BLE001
            last_external_sid = None

        sess = db.query(AgentSession).get(session_id)
        if sess is not None:
            sess.external_session_id = last_external_sid or sess.external_session_id
```

把 `run_agent_loop` 中所有 `s.claude_session_id = current_sid` 改为 `s.external_session_id = current_sid`。

- [ ] **Step 6: 更新 agent_api 测试**

把 `backend/tests/agent/test_agent_api.py` 中所有 `claude_session_id` 改为 `external_session_id`，包括 fixture 构造、`_patch_loop_immediate_success` 的 `s.claude_session_id = "claude-test-sid"` 和 409 断言。

- [ ] **Step 7: 运行测试**

Run:

```powershell
Set-Location backend; & 'D:\code\livecalc\.venv\Scripts\python.exe' -m pytest tests/agent/test_agent_api.py -v
```

Expected: PASS。

- [ ] **Step 8: 更新前端类型**

在 `frontend/src/types/agent.ts` 中把：

```ts
  claude_session_id: string | null
```

改为：

```ts
  external_session_id: string | null
```

- [ ] **Step 9: Commit**

```powershell
git add backend/app/models/agent_session.py backend/alembic/versions/20260806_0001_add_external_session_id.py backend/app/schemas/agent.py backend/app/api/agent_api.py backend/app/services/agent/session_runner.py backend/tests/agent/test_agent_api.py frontend/src/types/agent.ts
git commit -m "refactor(agent): use external_session_id"
```

---

### Task 4: CodexRunner 事件映射与 MCP overrides

**Files:**
- Create: `backend/app/services/agent/codex_runner.py`
- Test: `backend/tests/agent/test_codex_runner.py`

- [ ] **Step 1: 写失败测试**

Create `backend/tests/agent/test_codex_runner.py`:

```python
import pytest

from openai_codex.generated.v2_all import (
    AgentMessageDeltaNotification,
    ItemCompletedNotification,
    ItemStartedNotification,
    McpToolCallResult,
    McpToolCallThreadItem,
    ThreadItem,
    Turn,
    TurnCompletedNotification,
    TurnStatus,
)

from app.services.agent.codex_runner import (
    CodexRunner,
    build_config_overrides,
    translate_notification,
)
from app.services.agent.runner import AgentEvent, AgentRunner


def test_codex_runner_satisfies_protocol():
    runner = CodexRunner()
    assert isinstance(runner, AgentRunner)
    assert runner.last_session_id is None


def test_build_config_overrides_includes_mcp_env():
    overrides = build_config_overrides(
        python="python",
        cwd="backend",
        db_url="sqlite:///data/livecalc.db",
    )
    joined = "\n".join(overrides)
    assert "mcp_servers.controlled_db.enabled=true" in joined
    assert "controlled_db_mcp" in joined
    assert "LIVECALC_DB_URL" in joined


def test_translate_agent_message_delta():
    payload = AgentMessageDeltaNotification(
        delta="你好",
        itemId="item_1",
        threadId="thr_1",
        turnId="turn_1",
    )
    from openai_codex.models import Notification

    events = translate_notification(Notification(method="item/agentMessage/delta", payload=payload))
    assert events == [AgentEvent(kind="text_delta", text="你好")]


def test_translate_mcp_tool_events():
    from openai_codex.models import Notification

    item = ThreadItem(
        root=McpToolCallThreadItem(
            id="item_mcp",
            server="controlled_db",
            tool="db_read",
            arguments={"sql": "SELECT 1"},
            status="inProgress",
            type="mcpToolCall",
        )
    )
    start = Notification(
        method="item/started",
        payload=ItemStartedNotification(
            item=item,
            startedAtMs=1,
            threadId="thr_1",
            turnId="turn_1",
        ),
    )
    events = translate_notification(start)
    assert events[0].kind == "tool_use"
    assert events[0].tool_name == "mcp__controlled_db__db_read"


def test_translate_turn_completed_done():
    from openai_codex.models import Notification

    payload = TurnCompletedNotification(
        threadId="thr_1",
        turn=Turn(
            id="turn_1",
            status=TurnStatus.completed,
            items=[],
        ),
    )
    events = translate_notification(Notification(method="turn/completed", payload=payload))
    assert events[0].kind == "done"
    assert events[0].is_error is False
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
Set-Location backend; & 'D:\code\livecalc\.venv\Scripts\python.exe' -m pytest tests/agent/test_codex_runner.py -v
```

Expected: FAIL，模块不存在。

- [ ] **Step 3: 创建 codex_runner.py**

Create `backend/app/services/agent/codex_runner.py`:

```python
"""codex_runner - 用 openai-codex SDK 驱动本地 Codex app-server。"""

from __future__ import annotations

import json
import os
import queue
import threading
import time
from typing import Any, Iterator

from openai_codex.client import CodexClient, CodexConfig
from openai_codex.generated.v2_all import (
    AgentMessageDeltaNotification,
    ItemCompletedNotification,
    ItemStartedNotification,
    McpToolCallThreadItem,
    TurnCompletedNotification,
)
from openai_codex.models import Notification

from app.services.agent.runner import AgentEvent

__all__ = [
    "CodexRunner",
    "build_config_overrides",
    "translate_notification",
]


def build_config_overrides(
    *,
    python: str,
    cwd: str,
    db_url: str,
    server_name: str = "controlled_db",
) -> tuple[str, ...]:
    python_toml = python.replace("\\", "/")
    cwd_toml = cwd.replace("\\", "/")
    return (
        f"mcp_servers.{server_name}.enabled=true",
        f"mcp_servers.{server_name}.required=true",
        f'mcp_servers.{server_name}.command="{python_toml}"',
        f'mcp_servers.{server_name}.args=["-m", "app.services.agent.controlled_db_mcp"]',
        f'mcp_servers.{server_name}.cwd="{cwd_toml}"',
        f'mcp_servers.{server_name}.env={{"LIVECALC_DB_URL": "{db_url}"}}',
        f'mcp_servers.{server_name}.enabled_tools=["db_read", "describe", "list_tables"]',
    )


def _tool_name(server: str, tool: str) -> str:
    return f"mcp__{server}__{tool}"


def _coerce_mcp_result(result: Any) -> Any:
    if result is None:
        return ""
    if isinstance(result, str):
        return result
    content = getattr(result, "content", None)
    if not isinstance(content, list):
        return json.dumps(result, ensure_ascii=False, default=str)
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


def _translate_item(item: Any, *, completed: bool) -> list[AgentEvent]:
    root = item.root if hasattr(item, "root") else item
    if isinstance(root, McpToolCallThreadItem):
        if completed:
            return [
                AgentEvent(
                    kind="tool_result",
                    tool_use_id=root.id,
                    tool_result=_coerce_mcp_result(root.result),
                )
            ]
        return [
            AgentEvent(
                kind="tool_use",
                tool_name=_tool_name(root.server, root.tool),
                tool_input=root.arguments or {},
                tool_use_id=root.id,
            )
        ]
    return []


def translate_notification(notification: Notification) -> list[AgentEvent]:
    payload = notification.payload
    if isinstance(payload, AgentMessageDeltaNotification):
        return [AgentEvent(kind="text_delta", text=payload.delta)] if payload.delta else []
    if isinstance(payload, ItemStartedNotification):
        return _translate_item(payload.item, completed=False)
    if isinstance(payload, ItemCompletedNotification):
        return _translate_item(payload.item, completed=True)
    if isinstance(payload, TurnCompletedNotification):
        turn = payload.turn
        is_error = turn.status.value == "failed"
        return [
            AgentEvent(
                kind="done",
                is_error=is_error,
                error=turn.error.message if is_error and turn.error else "",
            )
        ]
    return []


def _reject_approval(method: str, params: dict | None) -> dict:
    if method.endswith("requestApproval"):
        return {"decision": "reject"}
    return {}


class CodexRunner:
    uses_db_pk_resume = False

    def __init__(
        self,
        *,
        cwd: str = ".",
        config_overrides: tuple[str, ...] = (),
        env: dict[str, str] | None = None,
        idle_timeout: float = 120.0,
        total_timeout: float = 600.0,
    ) -> None:
        self.cwd = str(cwd)
        self.config_overrides = tuple(config_overrides)
        self.env = dict(env) if env else None
        self.idle_timeout = float(idle_timeout)
        self.total_timeout = float(total_timeout)
        self._last_session_id: str | None = None
        self._current_client: CodexClient | None = None
        self._current_turn_id: str | None = None

    @property
    def last_session_id(self) -> str | None:
        return self._last_session_id

    def run(
        self, prompt: str, *, resume_session_id: str | None = None
    ) -> Iterator[AgentEvent]:
        self._last_session_id = None
        client = CodexClient(
            config=CodexConfig(
                cwd=self.cwd,
                config_overrides=self.config_overrides,
                env=self.env,
                client_name="livecalc_codex",
                client_title="LiveCalc Codex Agent",
            ),
            approval_handler=_reject_approval,
        )
        start_time = time.monotonic()
        try:
            client.start()
            client.initialize()
            if resume_session_id:
                started = client.thread_resume(
                    resume_session_id,
                    {"cwd": self.cwd, "sandbox": "read-only", "approvalPolicy": "never"},
                )
            else:
                started = client.thread_start(
                    {
                        "cwd": self.cwd,
                        "sandbox": "read-only",
                        "approvalPolicy": "never",
                        "ephemeral": False,
                    }
                )
            thread_id = started.thread.id
            self._last_session_id = thread_id
            turn = client.turn_start(
                thread_id,
                prompt,
                params={
                    "cwd": self.cwd,
                    "sandboxPolicy": {"type": "readOnly"},
                    "approvalPolicy": "never",
                },
            )
            turn_id = turn.turn.id
            self._current_client = client
            self._current_turn_id = turn_id

            event_q: "queue.Queue[Notification | BaseException]" = queue.Queue()

            def _pump() -> None:
                client.register_turn_notifications(turn_id)
                try:
                    while True:
                        notification = client.next_turn_notification(turn_id)
                        event_q.put(notification)
                        if (
                            notification.method == "turn/completed"
                            and isinstance(
                                notification.payload, TurnCompletedNotification
                            )
                            and notification.payload.turn.id == turn_id
                        ):
                            break
                except BaseException as exc:  # noqa: BLE001
                    event_q.put(exc)
                finally:
                    client.unregister_turn_notifications(turn_id)

            threading.Thread(target=_pump, daemon=True).start()
            done = False
            while not done:
                try:
                    item = event_q.get(timeout=self.idle_timeout)
                except queue.Empty:
                    self._interrupt(client, thread_id, turn_id)
                    yield AgentEvent(
                        kind="error",
                        error=f"Codex 超时（{self.idle_timeout}s 无输出）",
                    )
                    return
                if isinstance(item, BaseException):
                    yield AgentEvent(
                        kind="error",
                        is_error=True,
                        crash=True,
                        error=f"Codex SDK 异常: {item}",
                    )
                    return
                for agent_ev in translate_notification(item):
                    if agent_ev.kind == "done":
                        done = True
                    yield agent_ev
                if time.monotonic() - start_time > self.total_timeout:
                    self._interrupt(client, thread_id, turn_id)
                    yield AgentEvent(
                        kind="error",
                        error=f"Codex 超过总超时 {self.total_timeout}s",
                    )
                    return
        except Exception as exc:  # noqa: BLE001
            yield AgentEvent(
                kind="error",
                is_error=True,
                crash=True,
                error=f"Codex SDK 启动失败: {exc}",
            )
        finally:
            try:
                client.close()
            finally:
                self._current_client = None
                self._current_turn_id = None

    def cancel(self) -> None:
        client = self._current_client
        if client is not None and self._current_turn_id is not None:
            self._interrupt(client, self._last_session_id or "", self._current_turn_id)
            try:
                client.close()
            except Exception:
                pass

    @staticmethod
    def _interrupt(client: CodexClient, thread_id: str, turn_id: str) -> None:
        try:
            client.turn_interrupt(thread_id, turn_id)
        except Exception:
            pass
```

- [ ] **Step 4: 运行测试**

Run:

```powershell
Set-Location backend; & 'D:\code\livecalc\.venv\Scripts\python.exe' -m pytest tests/agent/test_codex_runner.py -v
```

Expected: PASS。

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/agent/codex_runner.py backend/tests/agent/test_codex_runner.py
git commit -m "feat(codex): add CodexRunner event adapter"
```

---

### Task 5: runner_factory 接 codex 分支

**Files:**
- Modify: `backend/app/services/agent/runner_factory.py`
- Modify: `backend/tests/agent/test_runner_factory.py`

- [ ] **Step 1: 写失败测试**

在 `backend/tests/agent/test_runner_factory.py` 末尾追加：

```python
def test_build_runner_codex_returns_codex_runner(monkeypatch):
    from app.services.agent import runner_factory
    from app.services.agent.codex_runner import CodexRunner

    monkeypatch.setattr(runner_factory, "_mcp_available", lambda: False)
    runner = runner_factory.build_runner(
        "infer_densities",
        "sqlite:///./data/livecalc.db",
        provider="codex",
    )
    assert isinstance(runner, CodexRunner)
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
Set-Location backend; & 'D:\code\livecalc\.venv\Scripts\python.exe' -m pytest tests/agent/test_runner_factory.py::test_build_runner_codex_returns_codex_runner -v
```

Expected: FAIL，`build_runner` 回退到 ClaudeCodeRunner。

- [ ] **Step 3: 修改 runner_factory.py**

在 import 区加：

```python
from app.services.agent.codex_runner import CodexRunner, build_config_overrides
```

在 `build_runner` 的 langchain 分支后加：

```python
    if provider == "codex":
        return _build_codex_runner(
            task_type,
            db_url,
            idle_timeout=idle_timeout,
            total_timeout=total_timeout,
            use_mcp=use_mcp,
        )
```

新增函数：

```python
def _build_codex_runner(
    task_type: str,
    db_url: str,
    *,
    idle_timeout: float | None = None,
    total_timeout: float | None = None,
    use_mcp: bool | None = None,
) -> CodexRunner:
    del task_type
    resolved_url = resolve_db_url(db_url)
    cwd = str(_backend_root())
    overrides: tuple[str, ...] = ()
    mcp_enabled = _mcp_available() if use_mcp is None else use_mcp
    if mcp_enabled:
        overrides = build_config_overrides(
            python=_root_venv_python(),
            cwd=cwd,
            db_url=resolved_url,
        )
    kwargs: dict[str, Any] = {
        "cwd": cwd,
        "config_overrides": overrides,
    }
    if idle_timeout is not None:
        kwargs["idle_timeout"] = idle_timeout
    if total_timeout is not None:
        kwargs["total_timeout"] = total_timeout
    return CodexRunner(**kwargs)
```

- [ ] **Step 4: 运行测试**

Run:

```powershell
Set-Location backend; & 'D:\code\livecalc\.venv\Scripts\python.exe' -m pytest tests/agent/test_runner_factory.py -v
```

Expected: PASS。

- [ ] **Step 5: Commit**

```powershell
git add backend/app/services/agent/runner_factory.py backend/tests/agent/test_runner_factory.py
git commit -m "feat(codex): route codex provider to CodexRunner"
```

---

### Task 6: CodexTranslator

**Files:**
- Create: `backend/app/services/translate/codex.py`
- Test: `backend/tests/services/test_translate_codex.py`
- Modify: `backend/app/services/translate/registry.py`
- Modify: `backend/tests/services/test_translate_registry.py`

- [ ] **Step 1: 写失败测试**

Create `backend/tests/services/test_translate_codex.py`:

```python
import pytest

from app.services.translate.codex import CodexTranslator


@pytest.mark.asyncio
async def test_translate_batch(monkeypatch):
    translator = CodexTranslator(timeout=10)

    async def fake_run(self, prompt):
        return "苹果（生）\n鸡胸肉（生）"

    monkeypatch.setattr(CodexTranslator, "_run_codex", fake_run)
    out = await translator.translate_batch(["Apple, raw", "Chicken, breast, raw"])
    assert out == ["苹果（生）", "鸡胸肉（生）"]
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
Set-Location backend; & 'D:\code\livecalc\.venv\Scripts\python.exe' -m pytest tests/services/test_translate_codex.py -v
```

Expected: FAIL，模块不存在。

- [ ] **Step 3: 创建 codex.py**

Create `backend/app/services/translate/codex.py`:

```python
"""Codex SDK 翻译后端：用 openai-codex 的 ephemeral thread 翻译。"""
import asyncio
from pathlib import Path

from openai_codex import ApprovalMode, AsyncCodex, CodexConfig, Sandbox

from app.services.translate.base import FOOD_TRANSLATION_SYSTEM_PROMPT
from app.services.translate.openai_compat import OpenAICompatTranslator


class CodexTranslator:
    name = "codex"

    def __init__(self, timeout: int, batch_size: int = 50, cwd: str | None = None):
        self.timeout = timeout
        self.batch_size = batch_size
        self.cwd = cwd or str(Path(__file__).resolve().parents[3])

    async def _run_codex(self, prompt: str) -> str:
        async def _run() -> str:
            async with AsyncCodex(
                config=CodexConfig(
                    cwd=self.cwd,
                    client_name="livecalc_codex_translate",
                    client_title="LiveCalc Codex Translator",
                )
            ) as codex:
                thread = await codex.thread_start(
                    ephemeral=True,
                    sandbox=Sandbox.read_only,
                    approval_mode=ApprovalMode.deny_all,
                )
                result = await thread.run(prompt)
                return result.final_response or ""

        return await asyncio.wait_for(_run(), timeout=self.timeout)

    async def translate_batch(
        self,
        texts: list[str],
        system_prompt: str = FOOD_TRANSLATION_SYSTEM_PROMPT,
    ) -> list[str]:
        results: list[str] = []
        for i in range(0, len(texts), self.batch_size):
            chunk = texts[i : i + self.batch_size]
            prompt = system_prompt + "\n\n" + OpenAICompatTranslator._build_prompt(chunk)
            content = await self._run_codex(prompt)
            lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
            for j in range(len(chunk)):
                results.append(lines[j] if j < len(lines) else "")
        return results

    async def health_check(self) -> bool:
        try:
            out = await self.translate_batch(["Water"])
            return bool(out and out[0])
        except Exception:
            return False
```

- [ ] **Step 4: 注册 get_translator**

在 `backend/app/services/translate/registry.py` 的 `claude_code` 分支后新增：

```python
    if provider == "codex":
        from app.services.translate.codex import CodexTranslator

        return CodexTranslator(timeout)
```

在 `backend/tests/services/test_translate_registry.py` 追加：

```python
def test_get_translator_codex():
    from app.services.translate.codex import CodexTranslator
    from app.services.translate.registry import get_translator

    translator = get_translator("codex", {"enabled": True}, timeout=10)
    assert isinstance(translator, CodexTranslator)
```

- [ ] **Step 5: 运行测试**

Run:

```powershell
Set-Location backend; & 'D:\code\livecalc\.venv\Scripts\python.exe' -m pytest tests/services/test_translate_codex.py tests/services/test_translate_registry.py -v
```

Expected: PASS。

- [ ] **Step 6: Commit**

```powershell
git add backend/app/services/translate/codex.py backend/tests/services/test_translate_codex.py
git commit -m "feat(codex): add CodexTranslator"
```

---

### Task 7: 黑名单全部匹配后端

**Files:**
- Modify: `backend/app/services/agent/task_templates.py`
- Modify: `backend/app/services/agent/blacklist_group_task.py`
- Modify: `backend/app/api/blacklist_groups.py`
- Test: `backend/tests/agent/test_blacklist_group_task.py`

- [ ] **Step 1: 写失败测试**

Create `backend/tests/agent/test_blacklist_group_task.py`:

```python
from unittest.mock import MagicMock, patch

from app.models.agent_session import AgentSession
from app.services.agent.blacklist_group_task import trigger_blacklist_group_match_all


def test_trigger_all_creates_one_session_with_all_groups():
    db = MagicMock()
    sessions: list[AgentSession] = []

    def fake_add(obj):
        obj.id = 1
        sessions.append(obj)

    db.add.side_effect = fake_add
    groups = [
        {"id": 1, "name": "坚果"},
        {"id": 2, "name": "海鲜"},
    ]
    with patch(
        "app.services.agent.blacklist_group_task.runner_factory.build_runner"
    ) as build_runner, patch(
        "app.services.agent.blacklist_group_task.session_runner.run_agent_loop"
    ) as run_agent_loop:
        sid = trigger_blacklist_group_match_all(
            db,
            groups=groups,
            admin_id=99,
            main_loop=None,
            provider="codex",
        )
    row = sessions[0]
    assert sid == 1
    assert row.runner_type == "codex"
    assert "坚果" in row.initial_prompt
    assert "海鲜" in row.initial_prompt
    build_runner.assert_called_once()
    assert build_runner.call_args.kwargs["provider"] == "codex"
    run_agent_loop.assert_called_once()
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
Set-Location backend; & 'D:\code\livecalc\.venv\Scripts\python.exe' -m pytest tests/agent/test_blacklist_group_task.py -v
```

Expected: FAIL，函数不存在。

- [ ] **Step 3: 新增任务模板**

在 `backend/app/services/agent/task_templates.py` 的 `_BLACKLIST_GROUP_MATCH_PROMPT` 后新增：

```python
_BLACKLIST_GROUP_MATCH_ALL_PROMPT = """你是「生计」应用的食材数据维护助手，负责根据多个原料黑名单分组名称搜索匹配数据库中的原料。

# 任务目标
以下启用分组都需要匹配：
{groups_block}

# 搜索策略
1. 对每个分组，先思考哪些食物属于该类别
2. 对每个可能的食物名，执行 SQL 搜索：
   ```sql
   SELECT id, name, aliases FROM ingredients
   WHERE is_active = true
     AND (name LIKE '%关键词%' OR aliases LIKE '%关键词%')
   ORDER BY name;
   ```
3. 用不同关键词多轮搜索，覆盖所有分组
4. 去重后输出每个分组的 ingredient_id

# 最终输出
在回复中列出每个分组的结果，格式：
- group_id: group_name -> ingredient_id: name (匹配依据)

最后按分组输出 INSERT。每个 INSERT 使用对应 group_id，`is_ai_matched = true`，`created_by = {admin_id}`：
```sql
INSERT INTO blacklist_group_ingredients (group_id, ingredient_id, is_ai_matched, created_by)
VALUES
  (该分组的实际 group_id, <id1>, true, {admin_id}),
  ...
;
```

注意：
- 只匹配明确属于该类别的原料
- 不确定的不加入
- 所有分组都要处理，不要遗漏
- 安全 SQL 自动执行，你可以放心输出 INSERT
"""
```

在 `TASK_TEMPLATES` 中新增：

```python
    "blacklist_group_match_all": {
        "title": "原料黑名单分组 AI 匹配（全部）",
        "allowed_tools": list(_READ_ONLY_TOOLS),
        "prompt": _BLACKLIST_GROUP_MATCH_ALL_PROMPT,
    },
```

把 `list_task_types` 改为：

```python
_INTERNAL_TASK_TYPES = {"blacklist_group_match_all"}


def list_task_types() -> list[dict]:
    return [
        {"task_type": k, "title": v["title"]}
        for k, v in TASK_TEMPLATES.items()
        if k not in _INTERNAL_TASK_TYPES
    ]
```

- [ ] **Step 4: 新增 trigger_blacklist_group_match_all**

在 `backend/app/services/agent/blacklist_group_task.py` 新增：

```python
def trigger_blacklist_group_match_all(
    db: Session,
    groups: list[dict],
    admin_id: int,
    main_loop: asyncio.AbstractEventLoop,
    provider: str = "claude_code",
) -> int:
    """触发一个覆盖所有启用分组的 AI 匹配 AgentSession。"""
    tpl = get_template("blacklist_group_match_all")
    groups_block = "\n".join(
        f"- id={group['id']}, name={group['name']}" for group in groups
    )
    prompt = tpl["prompt"].format(
        groups_block=groups_block,
        admin_id=admin_id,
    )
    sess = AgentSession(
        task_type="blacklist_group_match_all",
        title=f"原料黑名单匹配: 全部启用分组（{len(groups)} 个）",
        status="pending",
        runner_type=provider,
        initial_prompt=prompt,
        user_id=admin_id,
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    session_id = sess.id
    db_url = settings.database_url

    def _run_in_thread() -> None:
        try:
            runner = runner_factory.build_runner(
                "blacklist_group_match_all",
                db_url,
                provider=provider,
                idle_timeout=settings.agent_idle_timeout,
                total_timeout=settings.agent_total_timeout,
            )
            session_runner.run_agent_loop(
                session_id,
                runner,
                prompt,
                main_loop,
                db_session_factory=_get_session_factory(),
                unattended=True,
                safe_row_threshold=50000,
                max_turns=30,
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "原料黑名单全部匹配 Agent 异常 session=%s", session_id
            )
            _mark_session_failed(session_id)

    threading.Thread(target=_run_in_thread, daemon=True).start()
    return session_id
```

同时把现有 `trigger_blacklist_group_match` 增加 `provider: str = "claude_code"` 参数，写入 `runner_type` 并传给 `build_runner`。

具体修改为四处：

```python
def trigger_blacklist_group_match(
    db: Session,
    group_id: int,
    group_name: str,
    admin_id: int,
    main_loop: asyncio.AbstractEventLoop,
) -> int:
```

把函数签名改为 `main_loop: asyncio.AbstractEventLoop, provider: str = "claude_code",`。

```python
        runner_type="claude_code",
```

改为：

```python
        runner_type=provider,
```

```python
                provider="claude_code",
```

改为：

```python
                provider=provider,
```

文件中其余 `db.add/commit/refresh`、线程启动和 `run_agent_loop` 调用保持不变。

- [ ] **Step 5: 新增 API**

在 `backend/app/api/blacklist_groups.py` 中新增：

```python
@blacklist_group_admin_router.post("/blacklist-groups/ai-match-all", response_model=AiMatchResponse)
@blacklist_group_admin_router.post("/blacklist-groups/ai-match-all/", response_model=AiMatchResponse)
def trigger_ai_match_all(
    body: AiMatchRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """触发一个覆盖所有启用分组的 AI Agent 匹配任务。"""
    groups = (
        db.query(BlacklistGroup)
        .filter(BlacklistGroup.is_active == True)
        .order_by(BlacklistGroup.display_order, BlacklistGroup.id)
        .all()
    )
    if not groups:
        raise HTTPException(status_code=400, detail="没有可匹配的启用分组")

    from app.services.agent.blacklist_group_task import trigger_blacklist_group_match_all

    main_loop = asyncio.get_running_loop()
    session_id = trigger_blacklist_group_match_all(
        db,
        groups=[{"id": g.id, "name": g.name} for g in groups],
        admin_id=admin.id,
        main_loop=main_loop,
        provider=body.provider,
    )
    return AiMatchResponse(
        agent_session_id=session_id,
        message="已触发全部启用分组 AI 匹配任务，可在 Agent 任务台查看进度",
    )
```

同时把单组 `trigger_ai_match` 增加 `body: AiMatchRequest`，并把 `provider=body.provider` 传给 `trigger_blacklist_group_match`。

- [ ] **Step 6: 运行测试**

Run:

```powershell
Set-Location backend; & 'D:\code\livecalc\.venv\Scripts\python.exe' -m pytest tests/agent/test_blacklist_group_task.py -v
```

Expected: PASS。

- [ ] **Step 7: Commit**

```powershell
git add backend/app/services/agent/task_templates.py backend/app/services/agent/blacklist_group_task.py backend/app/api/blacklist_groups.py backend/tests/agent/test_blacklist_group_task.py
git commit -m "feat(blacklist): add match-all AI task"
```

---

### Task 8: 前端共享 provider 选项

**Files:**
- Create: `frontend/src/utils/agentProviders.ts`

- [ ] **Step 1: 创建共享定义**

Create `frontend/src/utils/agentProviders.ts`:

```ts
export interface ProviderOption {
  value: string
  label: string
}

export const AI_PROVIDER_ORDER = ['claude_code', 'codex', 'openai', 'anthropic']
export const MACHINE_PROVIDER_ORDER = ['baidu', 'aliyun', 'deepl']

export const PROVIDER_LABELS: Record<string, string> = {
  claude_code: 'Claude Code',
  codex: 'Codex',
  openai: 'OpenAI 兼容',
  anthropic: 'Anthropic 兼容',
  baidu: '百度翻译',
  aliyun: '阿里云机器翻译',
  deepl: 'DeepL',
}

export function enabledProviderOptions(
  config: any,
  regions: Array<'ai' | 'machine'>,
  localMode = false,
): ProviderOption[] {
  if (!config) return []
  const options: ProviderOption[] = []
  const seen = new Set<string>()
  const order = [...AI_PROVIDER_ORDER, ...MACHINE_PROVIDER_ORDER]
  for (const region of regions) {
    const providers = config?.[region]?.providers || {}
    for (const key of order) {
      const value = providers[key]
      if (!value || value.enabled !== true) continue
      if (localMode && (key === 'claude_code' || key === 'codex')) continue
      if (localMode && region === 'machine') continue
      if (seen.has(key)) continue
      seen.add(key)
      options.push({ value: key, label: PROVIDER_LABELS[key] || key })
    }
  }
  return options
}
```

- [ ] **Step 2: Commit**

```powershell
git add frontend/src/utils/agentProviders.ts
git commit -m "feat(frontend): add shared enabled provider options"
```

---

### Task 9: AgentTaskConsole 下拉只显示已启用 provider

**Files:**
- Modify: `frontend/src/api/agent.ts`
- Modify: `frontend/src/views/admin/AgentTaskConsole.vue`
- Modify: `frontend/src/composables/useAgentSession.ts`
- Modify: `frontend/src/api/local/agent/sessionRunner.ts`
- Modify: `frontend/src/api/local/handlers/agents.ts`

- [ ] **Step 1: 扩展 AgentProvider 类型**

在 `frontend/src/api/agent.ts` 中把：

```ts
export type AgentProvider = 'claude_code' | 'openai' | 'anthropic'
```

改为：

```ts
export type AgentProvider = 'claude_code' | 'codex' | 'openai' | 'anthropic'
```

- [ ] **Step 2: 修改 AgentTaskConsole providerOptions**

在 `AgentTaskConsole.vue` 中删除硬编码 `ALL_PROVIDERS`，改为：

```ts
const translationConfig = ref<any>(null)
const providerOptions = computed(() =>
  enabledProviderOptions(translationConfig.value, ['ai'], isLocalMode.value),
)
```

导入：

```ts
import { enabledProviderOptions } from '@/utils/agentProviders'
```

`onMounted` 中无论是否本地模式都先加载 config：

```ts
try {
  translationConfig.value = await api.get('/admin/translation-config')
  const options = providerOptions.value
  if (options.length) {
    const hasClaude = options.some((o) => o.value === provider.value)
    if (!hasClaude) provider.value = options[0].value
  }
} catch {
  // 配置读取失败时保留默认 provider
}
```

本地模式的 `localAiReady` 判断改为基于 `providerOptions.value.length > 0`。

模板中两个 `v-select` 增加：

```html
item-title="label"
item-value="value"
```

- [ ] **Step 3: 更新本地 runner**

在 `frontend/src/api/local/agent/sessionRunner.ts` 中把：

```ts
export type AgentProviderLike = 'claude_code' | 'openai' | 'anthropic'
```

改为：

```ts
export type AgentProviderLike = 'claude_code' | 'codex' | 'openai' | 'anthropic'
```

并让 `resolveAgentConfig` 对 codex 同样抛出：

```ts
if (provider === 'claude_code' || provider === 'codex') {
  throw new Error('本地模式不支持 CLI provider，请在 AI 配置中选择 OpenAI 或 Anthropic 兼容。')
}
```

在 `frontend/src/api/local/handlers/agents.ts` 的 `resolveLocalProvider` 中把过滤改为：

```ts
const enabled = Object.keys(ai).filter(
  (key) => key !== 'claude_code' && key !== 'codex' && ai[key]?.enabled,
)
```

在 `frontend/src/composables/useAgentSession.ts` 中把：

```ts
localProvider = provider === 'claude_code' ? null : provider
```

改为：

```ts
localProvider = provider === 'claude_code' || provider === 'codex' ? null : provider
```

- [ ] **Step 4: Build**

Run:

```powershell
Set-Location frontend; npm run build
```

Expected: 构建成功。

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/api/agent.ts frontend/src/views/admin/AgentTaskConsole.vue frontend/src/composables/useAgentSession.ts frontend/src/api/local/agent/sessionRunner.ts frontend/src/api/local/handlers/agents.ts
git commit -m "feat(frontend): filter agent provider options by enabled config"
```

---

### Task 10: 黑名单页 provider 与全部匹配

**Files:**
- Modify: `frontend/src/views/admin/BlacklistGroupsView.vue`
- Modify: `frontend/src/api/local/handlers/blacklistGroups.ts`
- Modify: `frontend/src/api/local/proxy.ts`

- [ ] **Step 1: 修改 local handler**

在 `frontend/src/api/local/handlers/blacklistGroups.ts` 新增：

```ts
export async function aiMatchAll(): Promise<any> {
  return { agent_session_id: 0, message: '本地模式暂不支持 AI 匹配' }
}
```

在 `frontend/src/api/local/proxy.ts` 的 `:id/ai-match` 前新增：

```ts
addRoute('/admin/blacklist-groups/ai-match-all', { post: blGroups.aiMatchAll })
```

- [ ] **Step 2: 修改 BlacklistGroupsView 脚本**

导入共享选项：

```ts
import { enabledProviderOptions, type ProviderOption } from '@/utils/agentProviders'
```

新增状态：

```ts
const translationConfig = ref<any>(null)
const aiProvider = ref('claude_code')
const aiMatchingAll = ref(false)
const providerOptions = computed<ProviderOption[]>(() =>
  enabledProviderOptions(translationConfig.value, ['ai'], isLocalMode.value),
)
```

`onMounted` 改为加载配置：

```ts
onMounted(async () => {
  try {
    translationConfig.value = await api.get('/admin/translation-config')
    if (providerOptions.value.length && !providerOptions.value.some((o) => o.value === aiProvider.value)) {
      aiProvider.value = providerOptions.value[0].value
    }
  } catch {
    // 保留默认 claude_code
  }
  await Promise.all([loadGroups(), loadAllergenStatus()])
})
```

新增 `triggerAiMatchAll`：

```ts
async function triggerAiMatchAll() {
  aiMatchingAll.value = true
  try {
    const data = await api.post('/admin/blacklist-groups/ai-match-all', {
      provider: aiProvider.value,
    })
    showInfo(`全部启用分组 AI 匹配任务已触发（任务 ID: ${data.agent_session_id}），可在 Agent 任务台查看进度。完成后请刷新本页。`)
  } catch (e: any) {
    showError('触发失败：' + (e?.userMessage || e?.message || '未知错误'))
  } finally {
    aiMatchingAll.value = false
  }
}
```

把 `triggerAiMatch` 的请求改为：

```ts
await api.post(`/admin/blacklist-groups/${group.id}/ai-match`, {
  provider: aiProvider.value,
})
```

- [ ] **Step 3: 修改模板**

在 `v-app-bar` 的 `#append` 中新增 provider 下拉和全部匹配按钮：

```html
<template #append>
  <v-select
    v-if="providerOptions.length"
    v-model="aiProvider"
    :items="providerOptions"
    item-title="label"
    item-value="value"
    label="AI Provider"
    variant="outlined"
    density="compact"
    hide-details
    class="mr-2 provider-select"
  />
  <v-btn
    color="primary"
    prepend-icon="mdi-robot"
    size="small"
    class="mr-2"
    :loading="aiMatchingAll"
    :disabled="!providerOptions.length || !groups.length"
    @click="triggerAiMatchAll"
  >
    AI 匹配全部
  </v-btn>
  <v-btn color="primary" prepend-icon="mdi-plus" size="small" @click="openCreate">
    新建分组
  </v-btn>
</template>
```

给 `provider-select` 加样式约束：

```css
.provider-select {
  max-width: 180px;
}
```

- [ ] **Step 4: Build**

Run:

```powershell
Set-Location frontend; npm run build
```

Expected: 构建成功。

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/views/admin/BlacklistGroupsView.vue frontend/src/api/local/handlers/blacklistGroups.ts frontend/src/api/local/proxy.ts
git commit -m "feat(blacklist): add provider selector and match-all button"
```

---

### Task 11: 翻译相关页面使用可读 provider 下拉

**Files:**
- Modify: `frontend/src/views/admin/DataMaintenanceView.vue`
- Modify: `frontend/src/views/admin/RecipeImportView.vue`

- [ ] **Step 1: DataMaintenanceView 改用共享选项**

导入：

```ts
import { enabledProviderOptions, type ProviderOption } from '@/utils/agentProviders'
```

把：

```ts
const enabledAiProviders = computed<string[]>(() => enabledIn('ai'))
const enabledTranslateProviders = computed<string[]>(() => [...enabledIn('ai'), ...enabledIn('machine')])
```

改为：

```ts
const aiProviderOptions = computed<ProviderOption[]>(() =>
  enabledProviderOptions(translationConfig.value, ['ai'], isLocalMode.value),
)
const translateProviderOptions = computed<ProviderOption[]>(() =>
  enabledProviderOptions(translationConfig.value, ['ai', 'machine'], isLocalMode.value),
)
const enabledAiProviders = computed<string[]>(() => aiProviderOptions.value.map((o) => o.value))
const enabledTranslateProviders = computed<string[]>(() => translateProviderOptions.value.map((o) => o.value))
```

模板中两个 `v-select` 改为：

```html
:items="aiProviderOptions"
item-title="label"
item-value="value"
```

和：

```html
:items="translateProviderOptions"
item-title="label"
item-value="value"
```

- [ ] **Step 2: RecipeImportView 改用共享选项**

把 `enabledIn` 和 `enabledProviders` 替换为：

```ts
const providerOptions = computed<ProviderOption[]>(() =>
  enabledProviderOptions(translationConfig.value, ['ai'], isLocalMode.value),
)
const enabledProviders = computed<string[]>(() => providerOptions.value.map((o) => o.value))
```

模板 `v-select` 改为：

```html
:items="providerOptions"
item-title="label"
item-value="value"
```

- [ ] **Step 3: Build**

Run:

```powershell
Set-Location frontend; npm run build
```

Expected: 构建成功。

- [ ] **Step 4: Commit**

```powershell
git add frontend/src/views/admin/DataMaintenanceView.vue frontend/src/views/admin/RecipeImportView.vue
git commit -m "feat(frontend): use labeled enabled provider dropdowns for translation"
```

---

### Task 12: AiConfigView 增加 Codex 卡片

**Files:**
- Modify: `frontend/src/views/admin/AiConfigView.vue`

- [ ] **Step 1: 修改 AI_PROVIDERS**

在 `claude_code` 卡片后新增：

```ts
  {
    key: 'codex',
    title: 'Codex（本机 SDK）',
    hint: '需服务器 ~/.codex/config.toml 配置 Codex 模型 provider。',
    fields: [{ key: 'enabled', label: '启用', type: 'switch' }],
  },
```

把 `isLocalMode` 的过滤改为同时排除 codex：

```ts
const aiProviders = computed(() =>
  isLocalMode.value ? AI_PROVIDERS.filter((p) => p.key !== 'claude_code' && p.key !== 'codex') : AI_PROVIDERS,
)
```

顶部说明文本改为：

```text
AI 走 {{ isLocalMode ? 'OpenAI 兼容 / Anthropic 兼容' : 'Claude Code / Codex / OpenAI 兼容 / Anthropic 兼容' }}；机翻走 百度 / 阿里云 / DeepL。
```

- [ ] **Step 2: Build**

Run:

```powershell
Set-Location frontend; npm run build
```

Expected: 构建成功。

- [ ] **Step 3: Commit**

```powershell
git add frontend/src/views/admin/AiConfigView.vue
git commit -m "feat(frontend): add Codex provider card after Claude Code"
```

---

### Task 13: 更新任务模板中的 CLI 表述

**Files:**
- Modify: `backend/app/services/agent/task_templates.py`

- [ ] **Step 1: 替换表述**

把所有 `Claude Code 环境下使用 MCP 只读工具` 替换为：

```text
Claude Code / Codex 环境下使用 MCP 只读工具
```

- [ ] **Step 2: 语法检查**

Run:

```powershell
Set-Location backend; & 'D:\code\livecalc\.venv\Scripts\python.exe' -m py_compile app/services/agent/task_templates.py
```

Expected: 无输出。

- [ ] **Step 3: Commit**

```powershell
git add backend/app/services/agent/task_templates.py
git commit -m "docs(agent): mention Codex in MCP task prompts"
```

---

### Task 14: 全量验证与收尾

**Files:**
- No new source files.

- [ ] **Step 1: 运行后端相关测试**

Run:

```powershell
Set-Location backend; & 'D:\code\livecalc\.venv\Scripts\python.exe' -m pytest tests/agent/test_codex_runner.py tests/agent/test_runner_factory.py tests/agent/test_agent_api.py tests/agent/test_blacklist_group_task.py tests/services/test_translate_codex.py tests/services/test_translate_registry.py -v
```

Expected: 全部 PASS。

- [ ] **Step 2: 运行后端编译检查**

Run:

```powershell
Set-Location backend; & 'D:\code\livecalc\.venv\Scripts\python.exe' -m compileall app
```

Expected: 无 syntax error。

- [ ] **Step 3: 运行前端 build**

Run:

```powershell
Set-Location frontend; npm run build
```

Expected: 构建成功。

- [ ] **Step 4: 检查 git status**

Run:

```powershell
git status --short
```

Expected: 只包含本次计划产生的改动，无临时目录。

- [ ] **Step 5: 提交剩余改动**

如果 `git status` 还有未提交文件，按文件归属补齐对应任务的 commit；最终确认工作区干净。

---

## Self-Review Notes

- Spec 的 CodexRunner、CodexTranslator、external_session_id、provider 下拉、黑名单全部匹配均已映射到 Task 1-14。
- 未使用占位符；测试和代码片段均为可直接落盘内容。
- `AgentProvider`、`AgentProviderLike`、`external_session_id` 在前后端命名保持一致。
