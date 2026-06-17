# backend/tests/services/test_translate_aliyun.py
import pytest
from unittest.mock import AsyncMock, patch
from app.services.translate.aliyun import AliyunTranslator


@pytest.mark.asyncio
async def test_translate_batch():
    t = AliyunTranslator(access_key_id="id", access_key_secret="s", timeout=10)
    with patch.object(t, "_post", new=AsyncMock(return_value="苹果（生）")):
        out = await t.translate_batch(["Apple, raw"])
    assert out == ["苹果（生）"]
