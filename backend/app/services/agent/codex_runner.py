"""codex_runner - 用 openai-codex SDK 驱动本地 Codex app-server。"""

from __future__ import annotations

import json
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
        f'mcp_servers.{server_name}.env={{"LIVECALC_DB_URL"="{db_url}"}}',
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
                elapsed = time.monotonic() - start_time
                remaining = self.total_timeout - elapsed
                if remaining <= 0:
                    self._interrupt(client, thread_id, turn_id)
                    yield AgentEvent(
                        kind="error",
                        error=f"Codex 超过总超时 {self.total_timeout}s",
                    )
                    return
                try:
                    item = event_q.get(timeout=min(self.idle_timeout, remaining))
                except queue.Empty:
                    self._interrupt(client, thread_id, turn_id)
                    if remaining <= self.idle_timeout:
                        yield AgentEvent(
                            kind="error",
                            error=f"Codex 超过总超时 {self.total_timeout}s",
                        )
                    else:
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
