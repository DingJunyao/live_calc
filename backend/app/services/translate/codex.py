"""Codex SDK 翻译后端：用 openai-codex 的 ephemeral thread 翻译。"""
import asyncio
from pathlib import Path

from openai_codex import ApprovalMode, AsyncCodex, CodexConfig, Sandbox

from app.services.translate.base import FOOD_TRANSLATION_SYSTEM_PROMPT
from app.services.translate.openai_compat import OpenAICompatTranslator


class CodexTranslator:
    name = "codex"

    def __init__(self, timeout: int, batch_size: int = 50, cwd: str | None = None):
        self.timeout = timeout
        self.batch_size = batch_size
        self.cwd = cwd or str(Path(__file__).resolve().parents[3])

    async def _run_codex(self, prompt: str) -> str:
        async def _run() -> str:
            async with AsyncCodex(
                config=CodexConfig(
                    cwd=self.cwd,
                    client_name="livecalc_codex_translate",
                    client_title="LiveCalc Codex Translator",
                )
            ) as codex:
                thread = await codex.thread_start(
                    ephemeral=True,
                    sandbox=Sandbox.read_only,
                    approval_mode=ApprovalMode.deny_all,
                )
                result = await thread.run(prompt)
                return result.final_response or ""

        return await asyncio.wait_for(_run(), timeout=self.timeout)

    async def translate_batch(
        self,
        texts: list[str],
        system_prompt: str = FOOD_TRANSLATION_SYSTEM_PROMPT,
    ) -> list[str]:
        results: list[str] = []
        for i in range(0, len(texts), self.batch_size):
            chunk = texts[i : i + self.batch_size]
            prompt = system_prompt + "\n\n" + OpenAICompatTranslator._build_prompt(chunk)
            content = await self._run_codex(prompt)
            lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
            for j in range(len(chunk)):
                results.append(lines[j] if j < len(lines) else "")
        return results

    async def health_check(self) -> bool:
        try:
            out = await self.translate_batch(["Water"])
            return bool(out and out[0])
        except Exception:
            return False
