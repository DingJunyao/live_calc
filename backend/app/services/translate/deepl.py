# backend/app/services/translate/deepl.py
"""DeepL 翻译（auth_key 以 :fx 结尾用 free 域名，否则 pro）。"""
import httpx


class DeepLTranslator:
    name = "deepl"

    def __init__(self, auth_key: str, timeout: int, batch_size: int = 50):
        self.auth_key = auth_key
        self.timeout = timeout
        self.batch_size = batch_size
        self.base = "https://api-free.deepl.com" if auth_key.endswith(":fx") else "https://api.deepl.com"

    async def _post(self, texts: list[str]) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(
                f"{self.base}/v2/translate",
                headers={"Authorization": f"DeepL-Auth-Key {self.auth_key}"},
                data=[("text", t) for t in texts] + [("source_lang", "EN"), ("target_lang", "ZH")],
            )
            r.raise_for_status()
            return r.json()

    async def translate_batch(self, texts: list[str]) -> list[str]:
        results: list[str] = []
        for i in range(0, len(texts), self.batch_size):
            chunk = texts[i:i + self.batch_size]
            data = await self._post(chunk)
            trans = data.get("translations", [])
            for j in range(len(chunk)):
                results.append(trans[j]["text"] if j < len(trans) else "")
        return results

    async def health_check(self) -> bool:
        try:
            out = await self.translate_batch(["Water"])
            return bool(out and out[0])
        except Exception:
            return False
