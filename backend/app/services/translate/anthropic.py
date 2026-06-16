"""Anthropic 兼容后端（messages API，base_url 可指向兼容端点）。"""
import httpx
from app.services.translate.base import FOOD_TRANSLATION_SYSTEM_PROMPT
from app.services.translate.openai_compat import OpenAICompatTranslator  # 复用 _build_prompt


class AnthropicTranslator:
    name = "anthropic"

    def __init__(self, base_url: str, api_key: str, model: str, timeout: int, batch_size: int = 50):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.batch_size = batch_size

    async def _post_json(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(
                f"{self.base_url}/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
            )
            r.raise_for_status()
            return r.json()

    async def translate_batch(self, texts: list[str]) -> list[str]:
        results: list[str] = []
        for i in range(0, len(texts), self.batch_size):
            chunk = texts[i:i + self.batch_size]
            user_prompt = OpenAICompatTranslator._build_prompt(chunk)
            payload = {
                "model": self.model,
                "max_tokens": 2048,
                "system": FOOD_TRANSLATION_SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_prompt}],
            }
            data = await self._post_json(payload)
            content = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
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
