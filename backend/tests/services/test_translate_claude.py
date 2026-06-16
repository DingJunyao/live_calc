import pytest
from app.services.translate.claude_code import ClaudeCodeTranslator


@pytest.mark.asyncio
async def test_translate_batch(monkeypatch):
    t = ClaudeCodeTranslator(timeout=10)

    async def fake_run(self, prompt):
        return "苹果（生）\n鸡胸肉（生）"

    monkeypatch.setattr(ClaudeCodeTranslator, "_run_cli", fake_run)
    out = await t.translate_batch(["Apple, raw", "Chicken, breast, raw"])
    assert out == ["苹果（生）", "鸡胸肉（生）"]
