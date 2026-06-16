# backend/app/services/translate/registry.py
"""翻译后端工厂：按 provider 名 + 配置构造 Translator。"""
from app.services.translate.base import Translator
from app.services.translate.openai_compat import OpenAICompatTranslator
from app.services.translate.anthropic import AnthropicTranslator
from app.services.translate.claude_code import ClaudeCodeTranslator
from app.services.translate.baidu import BaiduTranslator
from app.services.translate.aliyun import AliyunTranslator
from app.services.translate.deepl import DeepLTranslator


def get_translator(provider: str, cfg: dict, timeout: int) -> Translator:
    if provider == "openai":
        return OpenAICompatTranslator(cfg["base_url"], cfg["api_key"], cfg["model"], timeout)
    if provider == "anthropic":
        return AnthropicTranslator(cfg["base_url"], cfg["api_key"], cfg["model"], timeout)
    if provider == "claude_code":
        return ClaudeCodeTranslator(timeout)
    if provider == "baidu":
        return BaiduTranslator(cfg["appid"], cfg["secret"], timeout)
    if provider == "aliyun":
        return AliyunTranslator(cfg["access_key_id"], cfg["access_key_secret"], timeout)
    if provider == "deepl":
        return DeepLTranslator(cfg["auth_key"], timeout)
    raise ValueError(f"未知翻译后端: {provider}")


def list_provider_names() -> list[str]:
    return ["claude_code", "openai", "anthropic", "baidu", "aliyun", "deepl"]


def find_provider_section(config_dict: dict, provider: str) -> dict | None:
    """在 translation_config 的 ai/machine 两区里找 provider 配置。"""
    for region in ("ai", "machine"):
        provs = config_dict.get(region, {}).get("providers", {})
        if provider in provs:
            return provs[provider]
    return None
