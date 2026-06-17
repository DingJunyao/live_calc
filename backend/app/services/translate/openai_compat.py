"""OpenAI 兼容后端（兼容 DeepSeek/Ollama/各种代理）。

batch_size 控制每批条数；prompt 要求模型按行返回与输入等长的译文。"""
import httpx
from app.services.translate.base import FOOD_TRANSLATION_SYSTEM_PROMPT


class OpenAICompatTranslator:
    name = "openai"

    def __init__(self, base_url: str, api_key: str, model: str, timeout: int, batch_size: int = 50):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.batch_size = batch_size

    async def _post_json(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            r.raise_for_status()
            return r.json()

    @staticmethod
    def _build_prompt(texts: list[str]) -> str:
        return (
            "请逐行翻译下列条目，输出行数必须与输入完全一致，"
            "不要编号、不要解释：\n" + "\n".join(texts)
        )

    async def translate_batch(self, texts: list[str], system_prompt: str = FOOD_TRANSLATION_SYSTEM_PROMPT) -> list[str]:
        results: list[str] = []
        for i in range(0, len(texts), self.batch_size):
            chunk = texts[i:i + self.batch_size]
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": self._build_prompt(chunk)},
                ],
                "temperature": 0.2,
            }
            data = await self._post_json(payload)
            content = data["choices"][0]["message"]["content"]
            lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
            # 对齐：若模型行数不匹配，按位置填，缺位补空串
            for j in range(len(chunk)):
                results.append(lines[j] if j < len(lines) else "")
        return results

    async def health_check(self) -> bool:
        try:
            out = await self.translate_batch(["Water"])
            return bool(out and out[0])
        except Exception:
            return False
