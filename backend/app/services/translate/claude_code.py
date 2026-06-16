"""Claude Code CLI 后端：调本机 claude 子进程。需 claude 在 PATH。"""
import asyncio
import shutil
from app.services.translate.base import FOOD_TRANSLATION_SYSTEM_PROMPT
from app.services.translate.openai_compat import OpenAICompatTranslator


class ClaudeCodeTranslator:
    name = "claude_code"

    def __init__(self, timeout: int, batch_size: int = 50, cli_path: str | None = None):
        self.timeout = timeout
        self.batch_size = batch_size
        self.cli_path = cli_path or shutil.which("claude") or "claude"

    async def _run_cli(self, prompt: str) -> str:
        """调 `claude -p <prompt>`，返回 stdout。具体参数以本机 claude 版本为准。"""
        proc = await asyncio.create_subprocess_exec(
            self.cli_path, "-p", prompt,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
        return stdout.decode("utf-8", errors="ignore").strip()

    async def translate_batch(self, texts: list[str]) -> list[str]:
        results: list[str] = []
        for i in range(0, len(texts), self.batch_size):
            chunk = texts[i:i + self.batch_size]
            prompt = FOOD_TRANSLATION_SYSTEM_PROMPT + "\n\n" + OpenAICompatTranslator._build_prompt(chunk)
            content = await self._run_cli(prompt)
            lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
            for j in range(len(chunk)):
                results.append(lines[j] if j < len(lines) else "")
        return results

    async def health_check(self) -> bool:
        if not shutil.which("claude"):
            return False
        try:
            out = await self.translate_batch(["Water"])
            return bool(out and out[0])
        except Exception:
            return False
