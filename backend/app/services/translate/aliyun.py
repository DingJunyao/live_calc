# backend/app/services/translate/aliyun.py
"""阿里云机器翻译通用 API（alimt TranslateGeneral）。POP 签名（HMAC-SHA1）。"""
import base64, hashlib, hmac, httpx, time, urllib.parse


class AliyunTranslator:
    name = "aliyun"
    ENDPOINT = "https://mt.aliyuncs.com"

    def __init__(self, access_key_id: str, access_key_secret: str, timeout: int, batch_size: int = 30):
        self.ak = access_key_id
        self.sk = access_key_secret
        self.timeout = timeout
        self.batch_size = batch_size

    def _sign(self, params: dict) -> str:
        sorted_q = "&".join(f"{urllib.parse.quote(k)}={urllib.parse.quote(str(v))}" for k, v in sorted(params.items()))
        string_to_sign = "GET&%2F&" + urllib.parse.quote(sorted_q, safe="")
        digest = hmac.new((self.sk + "&").encode(), string_to_sign.encode(), hashlib.sha1).digest()
        return base64.b64encode(digest).decode()

    async def _post(self, text: str) -> dict:
        params = {
            "FormatType": "text", "Scene": "general",
            "SourceLanguage": "en", "TargetLanguage": "zh",
            "SourceText": text,
            "AccessKeyId": self.ak,
            "Action": "TranslateGeneral", "Version": "2018-10-12",
            "SignatureMethod": "HMAC-SHA1", "SignatureVersion": "1.0",
            "SignatureNonce": str(int(time.time() * 1000)), "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        params["Signature"] = self._sign(params)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(self.ENDPOINT, params=params)
            r.raise_for_status()
            return r.json()

    async def translate_batch(self, texts: list[str]) -> list[str]:
        results: list[str] = []
        for i in range(0, len(texts), self.batch_size):
            chunk = texts[i:i + self.batch_size]
            for t in chunk:
                data = await self._post(t)
                results.append(data.get("Data", {}).get("Translated", ""))
        return results

    async def health_check(self) -> bool:
        try:
            out = await self.translate_batch(["Water"])
            return bool(out and out[0])
        except Exception:
            return False
