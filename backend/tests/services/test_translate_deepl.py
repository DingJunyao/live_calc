# backend/tests/services/test_translate_deepl.py
import pytest
from unittest.mock import AsyncMock, patch
from app.services.translate.deepl import DeepLTranslator


@pytest.mark.asyncio
async def test_translate_batch():
    t = DeepLTranslator(auth_key="xxx:fx", timeout=10)
    fake = {"translations": [{"text": "苹果（生）"}, {"text": "鸡肉"}]}
    with patch.object(t, "_post", new=AsyncMock(return_value=fake)):
        out = await t.translate_batch(["Apple, raw", "Chicken"])
    assert out == ["苹果（生）", "鸡肉"]
