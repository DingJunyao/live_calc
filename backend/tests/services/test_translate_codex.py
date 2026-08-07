import pytest

from app.services.translate.codex import CodexTranslator


@pytest.mark.asyncio
async def test_translate_batch(monkeypatch):
    translator = CodexTranslator(timeout=10)

    async def fake_run(self, prompt):
        return "苹果（生）\n鸡胸肉（生）"

    monkeypatch.setattr(CodexTranslator, "_run_codex", fake_run)
    out = await translator.translate_batch(["Apple, raw", "Chicken, breast, raw"])
    assert out == ["苹果（生）", "鸡胸肉（生）"]
