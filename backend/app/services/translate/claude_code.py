"""Claude Code CLI 后端：调本机 claude 子进程。需 claude 在 PATH。"""
import asyncio
import shutil
import subprocess
from app.services.translate.base import FOOD_TRANSLATION_SYSTEM_PROMPT
from app.services.translate.openai_compat import OpenAICompatTranslator


class ClaudeCodeTranslator:
    name = "claude_code"

    def __init__(self, timeout: int, batch_size: int = 50, cli_path: str | None = None):
        self.timeout = timeout
        self.batch_size = batch_size
        self.cli_path = cli_path or shutil.which("claude") or "claude"

    async def _run_cli(self, prompt: str) -> str:
        """调本机 claude CLI：prompt 经 stdin 传入，用同步 subprocess + asyncio.to_thread。

        Windows 上 asyncio.create_subprocess_exec 在 SelectorEventLoop 下会抛
        NotImplementedError（子进程传输未实现），故改用线程跑同步 subprocess.run
        （与参考项目 HowToCook_json_organizer 一致），避开事件循环子进程。
        """
        def _sync() -> str:
            result = subprocess.run(
                [self.cli_path, "-p", "--allowedTools", "Read,Write"],
                input=prompt,
                capture_output=True, text=True,
                timeout=self.timeout,
                encoding="utf-8",
            )
            return result.stdout.strip()

        return await asyncio.to_thread(_sync)

    async def translate_batch(self, texts: list[str], system_prompt: str = FOOD_TRANSLATION_SYSTEM_PROMPT) -> list[str]:
        results: list[str] = []
        for i in range(0, len(texts), self.batch_size):
            chunk = texts[i:i + self.batch_size]
            prompt = system_prompt + "\n\n" + OpenAICompatTranslator._build_prompt(chunk)
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
