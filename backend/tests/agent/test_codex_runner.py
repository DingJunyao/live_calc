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
from openai_codex.models import Notification

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
    assert 'mcp_servers.controlled_db.env={"LIVECALC_DB_URL"="sqlite:///data/livecalc.db"}' in joined


def test_translate_agent_message_delta():
    payload = AgentMessageDeltaNotification(
        delta="你好",
        itemId="item_1",
        threadId="thr_1",
        turnId="turn_1",
    )
    events = translate_notification(
        Notification(method="item/agentMessage/delta", payload=payload)
    )
    assert events == [AgentEvent(kind="text_delta", text="你好")]


def test_translate_mcp_tool_events():
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
    payload = TurnCompletedNotification(
        threadId="thr_1",
        turn=Turn(
            id="turn_1",
            status=TurnStatus.completed,
            items=[],
        ),
    )
    events = translate_notification(
        Notification(method="turn/completed", payload=payload)
    )
    assert events[0].kind == "done"
    assert events[0].is_error is False
