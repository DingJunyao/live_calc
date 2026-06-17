# backend/app/services/translate/baidu.py
"""百度翻译通用 API（标准版免费，注意 QPS 限制）。签名：sign = md5(appid + q + salt + secret)"""
import hashlib, random
import httpx


class BaiduTranslator:
    name = "baidu"
    ENDPOINT = "https://fanyi-api.baidu.com/api/trans/vip/translate"

    def __init__(self, appid: str, secret: str, timeout: int, batch_size: int = 30, qps: int = 10):
        self.appid = appid
        self.secret = secret
        self.timeout = timeout
        self.batch_size = batch_size
        self.qps = qps

    def _sign(self, q: str, salt: str) -> str:
        return hashlib.md5(f"{self.appid}{q}{salt}{self.secret}".encode()).hexdigest()

    async def _post(self, q: str, salt: str) -> dict:
        params = {"q": q, "from": "en", "to": "zh", "appid": self.appid,
                  "salt": salt, "sign": self._sign(q, salt)}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(self.ENDPOINT, data=params)
            r.raise_for_status()
            data = r.json()
        # 百度错误以 error_code 返回（非 HTTP 错误），转抛以便上层诊断
        if data.get("error_code"):
            raise RuntimeError(f"百度错误 {data.get('error_code')}: {data.get('error_msg', '')}")
        return data

    async def translate_batch(self, texts: list[str], system_prompt: str | None = None) -> list[str]:
        results: list[str] = []
        for i in range(0, len(texts), self.batch_size):
            chunk = texts[i:i + self.batch_size]
            q = "\n".join(chunk)
            salt = str(random.randint(32768, 65536))
            data = await self._post(q, salt)
            trans = data.get("trans_result", [])
            for j in range(len(chunk)):
                results.append(trans[j]["dst"] if j < len(trans) else "")
            if self.qps:
                import asyncio
                await asyncio.sleep(1.0 / self.qps)
        return results

    async def health_check(self) -> bool:
        try:
            out = await self.translate_batch(["Water"])
            return bool(out and out[0])
        except Exception:
            return False
