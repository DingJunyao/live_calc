"""按 provider + 配置构造 ChatOpenAI / ChatAnthropic。"""

from unittest.mock import patch

import pytest

from app.services.agent.langchain_chat import build_chat_model


def test_build_openai():
    with patch("app.services.agent.langchain_chat.ChatOpenAI") as m:
        build_chat_model(
            "openai",
            {"base_url": "https://x/v1", "api_key": "k", "model": "gpt-4o"},
        )
        m.assert_called_once()
        kw = m.call_args.kwargs
        assert kw["model"] == "gpt-4o"
        assert kw["base_url"] == "https://x/v1"
        assert kw["api_key"] == "k"
        assert kw["streaming"] is True  # 流式：SSE 实时推送


def test_build_anthropic():
    with patch("app.services.agent.langchain_chat.ChatAnthropic") as m:
        build_chat_model(
            "anthropic",
            {"base_url": "https://y", "api_key": "k", "model": "claude-3-5"},
        )
        m.assert_called_once()
        kw = m.call_args.kwargs
        assert kw["model"] == "claude-3-5"
        assert kw["base_url"] == "https://y"
        assert kw["api_key"] == "k"


def test_build_unknown_raises():
    with pytest.raises(ValueError):
        build_chat_model("baidu", {})


def test_build_with_timeout():
    """timeout 应透传到 ChatModel（可选）。"""
    with patch("app.services.agent.langchain_chat.ChatOpenAI") as m:
        build_chat_model(
            "openai",
            {"base_url": "https://x/v1", "api_key": "k", "model": "gpt-4o"},
            timeout=30.0,
        )
        assert m.call_args.kwargs["timeout"] == 30.0
