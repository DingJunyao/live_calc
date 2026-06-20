"""按 provider + TranslationConfig 片段构造 langchain ChatModel。

抹平 OpenAI 兼容端点与 Anthropic 兼容端点在 langchain 1.x 下的构造差异，
供 LangChainRunner（见 runner_factory）使用。配置由调用方从
``TranslationConfig.to_dict()['ai']['providers'][provider]`` 取出后传入，
本模块不负责读数据库。
"""

from __future__ import annotations

from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI


def build_chat_model(
    provider: str,
    cfg: dict,
    *,
    timeout: Optional[float] = None,
):
    """构造 langchain ChatModel（OpenAI 兼容 / Anthropic 兼容）。

    Args:
        provider: ``"openai"`` 或 ``"anthropic"``，其它值抛 ``ValueError``。
        cfg: provider 配置字典，需含 ``base_url`` / ``api_key`` / ``model``
            三个键（对应 ``TranslationConfig`` 中 ``ai.providers.<provider>``）。
        timeout: 单次请求超时秒数；``None`` 表示用各自默认值。

    Returns:
        配置好的 ``ChatOpenAI`` 或 ``ChatAnthropic`` 实例。

    Raises:
        ValueError: ``provider`` 既非 ``"openai"`` 也非 ``"anthropic"``。
    """
    # streaming=True：让 ChatModel 逐 token 流式输出 → langgraph create_agent 的
    # stream(stream_mode=["messages"]) 逐 token yield AIMessageChunk → LangChainRunner
    # 逐 text_delta → run_agent_loop 的 SSE 实时推前端。不开则等完整响应才产 chunk，
    # 任务台对话不实时更新（需刷新）。默认 False，必须显式开启。
    common: dict = {"streaming": True}
    if timeout is not None:
        common["timeout"] = timeout

    if provider == "openai":
        return ChatOpenAI(
            model=cfg["model"],
            base_url=cfg["base_url"],
            api_key=cfg["api_key"],
            **common,
        )
    if provider == "anthropic":
        return ChatAnthropic(
            model=cfg["model"],
            base_url=cfg["base_url"],
            api_key=cfg["api_key"],
            **common,
        )
    raise ValueError(f"langchain 不支持的 provider: {provider}")
