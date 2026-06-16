import pytest
from unittest.mock import AsyncMock, patch
from app.services.translate.anthropic import AnthropicTranslator


@pytest.mark.asyncio
async def test_translate_batch():
    t = AnthropicTranslator(base_url="https://api.anthropic.com", api_key="k", model="claude-sonnet-4-6", timeout=10)
    fake = {"content": [{"type": "text", "text": "苹果（生）"}]}
    with patch.object(t, "_post_json", new=AsyncMock(return_value=fake)):
        out = await t.translate_batch(["Apple, raw"])
    assert out == ["苹果（生）"]
