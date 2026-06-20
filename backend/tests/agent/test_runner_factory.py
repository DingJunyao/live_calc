"""runner_factory 按 provider 分流构造 runner（Task 5）。

验证四件事：
1. ``provider="openai"`` / ``"anthropic"`` → 走 ``_build_langchain_runner`` 分支，
   构造 ``LangChainRunner``，不碰 MCP 配置。
2. 默认 ``provider="claude_code"``（或不传）→ 走原 ``ClaudeCodeRunner`` 分支不变。
3. ``_build_langchain_runner`` 从 ``TranslationConfig.to_dict()`` 取 provider 配置
   片段，调 ``build_chat_model(provider, section)`` 构造 chat model，最终用
   ``LangChainRunner(chat, READ_ONLY_TOOLS)`` 装配。
4. 配置中找不到 provider → 抛 ``ValueError``。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# --------------------------------------------------------------------------- #
# build_runner 按 provider 分流
# --------------------------------------------------------------------------- #
def test_build_runner_openai_calls_langchain_branch():
    """provider=openai → 走 _build_langchain_runner，不调 ClaudeCodeRunner。"""
    from app.services.agent import runner_factory

    with patch("app.services.agent.runner_factory._build_langchain_runner") as m:
        runner_factory.build_runner(
            "infer_densities",
            "sqlite:///./data/livecalc.db",
            provider="openai",
        )
        m.assert_called_once_with("infer_densities", provider="openai")


def test_build_runner_anthropic_calls_langchain_branch():
    """provider=anthropic → 走 _build_langchain_runner。"""
    from app.services.agent import runner_factory

    with patch("app.services.agent.runner_factory._build_langchain_runner") as m:
        runner_factory.build_runner(
            "infer_densities",
            "sqlite:///./data/livecalc.db",
            provider="anthropic",
        )
        m.assert_called_once_with("infer_densities", provider="anthropic")


def test_build_runner_claude_code_default_returns_claude_code_runner(
    monkeypatch,
):
    """默认 provider=claude_code（或不传）→ 返回 ClaudeCodeRunner（MCP 关闭）。"""
    from app.services.agent import runner_factory
    from app.services.agent.claude_code_runner import ClaudeCodeRunner

    # 关闭 MCP 检测，避免生成 mcp_config.json 副作用。
    monkeypatch.setattr(runner_factory, "_mcp_available", lambda: False)
    r = runner_factory.build_runner("infer_densities", "sqlite:///./data/livecalc.db")
    assert isinstance(r, ClaudeCodeRunner)

    # 显式传 claude_code 也走同一分支。
    r2 = runner_factory.build_runner(
        "infer_densities",
        "sqlite:///./data/livecalc.db",
        provider="claude_code",
    )
    assert isinstance(r2, ClaudeCodeRunner)


# --------------------------------------------------------------------------- #
# _build_langchain_runner：从 TranslationConfig 取配置 + 装配 LangChainRunner
# --------------------------------------------------------------------------- #
def test_build_langchain_runner_builds_from_config():
    """_build_langchain_runner 读 TranslationConfig → find_provider_section →
    build_chat_model(provider, section) → LangChainRunner(chat, READ_ONLY_TOOLS)。

    ``_build_langchain_runner`` 内部用 ``from ... import`` 取依赖，故 patch
    依赖所在的源模块属性（``app.services.agent.langchain_chat.build_chat_model``
    等）即可生效。SessionLocal 走 ``app.core.database`` 模块属性访问。
    """
    from app.services.agent import runner_factory

    fake_cfg = {
        "ai": {
            "providers": {
                "openai": {
                    "base_url": "http://x",
                    "api_key": "k",
                    "model": "m",
                }
            }
        },
        "machine": {"providers": {}},
    }
    with patch("app.core.database.SessionLocal") as MS, patch(
        "app.services.agent.langchain_chat.build_chat_model"
    ) as MB, patch("app.services.agent.langchain_runner.LangChainRunner") as ML, patch(
        "app.services.agent.langchain_tools.READ_ONLY_TOOLS",
        ["tool_stub"],
    ):
        db = MagicMock()
        cfg_row = MagicMock()
        cfg_row.to_dict.return_value = fake_cfg
        db.query.return_value.first.return_value = cfg_row
        MS.return_value = db

        runner_factory._build_langchain_runner("infer_densities", provider="openai")

        # build_chat_model 用 provider + section 调用。
        MB.assert_called_once_with(
            "openai",
            {"base_url": "http://x", "api_key": "k", "model": "m"},
        )
        # LangChainRunner 用 chat + READ_ONLY_TOOLS 装配。
        ML.assert_called_once()
        kwargs = ML.call_args.kwargs
        assert kwargs["chat"] is MB.return_value
        assert kwargs["tools"] == ["tool_stub"]


def test_build_langchain_runner_missing_provider_raises():
    """配置中找不到 provider → ValueError（提示用户去后台配置）。"""
    from app.services.agent import runner_factory

    # 空 ai/machine providers。
    fake_cfg = {"ai": {"providers": {}}, "machine": {"providers": {}}}
    with patch("app.core.database.SessionLocal") as MS:
        db = MagicMock()
        cfg_row = MagicMock()
        cfg_row.to_dict.return_value = fake_cfg
        db.query.return_value.first.return_value = cfg_row
        MS.return_value = db

        with pytest.raises(ValueError, match="openai"):
            runner_factory._build_langchain_runner("infer_densities", provider="openai")
