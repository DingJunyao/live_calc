import asyncio
import inspect
from unittest.mock import MagicMock, patch

from app.models.agent_session import AgentSession
from app.services.agent.blacklist_group_task import trigger_blacklist_group_match_all


def test_ai_match_endpoints_are_async():
    """同步端点无法调用 asyncio.get_running_loop，必须保持 async。"""
    from app.api.blacklist_groups import trigger_ai_match, trigger_ai_match_all

    assert inspect.iscoroutinefunction(trigger_ai_match)
    assert inspect.iscoroutinefunction(trigger_ai_match_all)


async def test_trigger_ai_match_all_resolves_running_loop():
    from app.api.blacklist_groups import AiMatchRequest, trigger_ai_match_all

    db = MagicMock()
    group = MagicMock(id=10, name="坚果")
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [group]
    admin = MagicMock()
    admin.id = 88

    with patch(
        "app.services.agent.blacklist_group_task.trigger_blacklist_group_match_all",
        return_value=42,
    ) as trigger:
        result = await trigger_ai_match_all(
            AiMatchRequest(provider="codex"),
            db=db,
            admin=admin,
        )

    assert result.agent_session_id == 42
    trigger.assert_called_once()
    assert trigger.call_args.kwargs["admin_id"] == 88
    assert trigger.call_args.kwargs["provider"] == "codex"
    assert trigger.call_args.kwargs["main_loop"] is asyncio.get_running_loop()


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
