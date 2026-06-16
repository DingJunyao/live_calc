import pytest
from unittest.mock import AsyncMock, patch
from app.services.translate.openai_compat import OpenAICompatTranslator


@pytest.mark.asyncio
async def test_translate_batch_returns_translations():
    t = OpenAICompatTranslator(base_url="http://x/v1", api_key="k", model="m", timeout=10)
    fake_resp = {"choices": [{"message": {"content": "苹果（生）\n鸡胸肉（生）"}}]}
    with patch.object(t, "_post_json", new=AsyncMock(return_value=fake_resp)):
        out = await t.translate_batch(["Apple, raw", "Chicken, breast, raw"])
    assert out == ["苹果（生）", "鸡胸肉（生）"]
