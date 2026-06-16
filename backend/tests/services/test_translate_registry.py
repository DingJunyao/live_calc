# backend/tests/services/test_translate_registry.py
import pytest
from app.services.translate.registry import get_translator, list_provider_names, find_provider_section
from app.services.translate.openai_compat import OpenAICompatTranslator


def test_build_openai():
    cfg = {"enabled": True, "base_url": "http://x/v1", "api_key": "k", "model": "m"}
    t = get_translator("openai", cfg, timeout=10)
    assert isinstance(t, OpenAICompatTranslator)


def test_unknown_raises():
    with pytest.raises(ValueError):
        get_translator("nope", {}, timeout=10)


def test_lists_all_six():
    names = set(list_provider_names())
    assert names == {"claude_code", "openai", "anthropic", "baidu", "aliyun", "deepl"}


def test_find_provider_section():
    config_dict = {
        "ai": {"providers": {"openai": {"enabled": True}}},
        "machine": {"providers": {"baidu": {"enabled": True}}},
    }
    assert find_provider_section(config_dict, "openai") == {"enabled": True}
    assert find_provider_section(config_dict, "baidu") == {"enabled": True}
    assert find_provider_section(config_dict, "deepl") is None
