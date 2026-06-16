# backend/tests/services/test_translate_baidu.py
import pytest
from unittest.mock import AsyncMock, patch
from app.services.translate.baidu import BaiduTranslator


@pytest.mark.asyncio
async def test_translate_batch():
    t = BaiduTranslator(appid="id", secret="s", timeout=10, qps=0)  # qps=0 跳过限速 sleep
    fake = {"trans_result": [{"src": "Apple, raw", "dst": "苹果（生）"}, {"src": "Chicken", "dst": "鸡肉"}]}
    with patch.object(t, "_post", new=AsyncMock(return_value=fake)):
        out = await t.translate_batch(["Apple, raw", "Chicken"])
    assert out == ["苹果（生）", "鸡肉"]
