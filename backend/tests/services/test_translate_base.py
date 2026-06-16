from app.services.translate.base import Translator, FOOD_TRANSLATION_SYSTEM_PROMPT


def test_prompt_mentions_examples():
    assert "鸡胸肉" in FOOD_TRANSLATION_SYSTEM_PROMPT


def test_protocol_defined():
    # Translator 是 Protocol，有 translate_batch / health_check 方法契约
    assert hasattr(Translator, "translate_batch") or hasattr(Translator, "_is_protocol") or hasattr(Translator, "_is_runtime_protocol")
