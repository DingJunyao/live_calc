# backend/app/services/translate/aliyun.py
"""阿里云机器翻译通用 API（alimt TranslateGeneral）。ACS3-HMAC-SHA256 V3 签名。

参考 D:\\code\\HowToCook_json_organizer\\scripts\\build_usda_data.py AliyunMTProvider。
旧版 POP HMAC-SHA1 签名会被阿里云新 API 拒绝，必须用 ACS3。
"""
import hashlib
import hmac
import time
import uuid
from urllib.parse import quote

import httpx


class AliyunTranslator:
    name = "aliyun"
    # 阿里云通用翻译默认杭州地域 host
    HOST = "mt.cn-hangzhou.aliyuncs.com"

    def __init__(self, access_key_id: str, access_key_secret: str, timeout: int, batch_size: int = 30):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.timeout = timeout
        self.batch_size = batch_size

    async def _post(self, text: str) -> str:
        """调用 TranslateGeneral，返回译文。ACS3-HMAC-SHA256 签名（RPC 风格，参数走 query）。"""
        query_params = {
            "Action": "TranslateGeneral",
            "Version": "2018-10-12",
            "FormatType": "text",
            "SourceLanguage": "en",
            "TargetLanguage": "zh",
            "SourceText": text,
            "Scene": "general",
        }
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        nonce = str(uuid.uuid4())
        hashed_payload = hashlib.sha256(b"").hexdigest()

        sign_headers = {
            "content-type": "application/json; charset=utf-8",
            "host": self.HOST,
            "x-acs-action": "TranslateGeneral",
            "x-acs-content-sha256": hashed_payload,
            "x-acs-date": now,
            "x-acs-signature-nonce": nonce,
            "x-acs-version": "2018-10-12",
        }

        canonical_qs = "&".join(
            f"{quote(k, safe='')}={quote(str(v), safe='')}" for k, v in sorted(query_params.items())
        )
        sorted_keys = sorted(sign_headers.keys())
        signed_headers_str = ";".join(sorted_keys)
        canonical_headers = "".join(f"{k}:{sign_headers[k].strip()}\n" for k in sorted_keys)
        canonical_request = (
            f"POST\n/\n{canonical_qs}\n{canonical_headers}\n{signed_headers_str}\n{hashed_payload}"
        )
        string_to_sign = f"ACS3-HMAC-SHA256\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        signature = hmac.new(
            self.access_key_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        authorization = (
            f"ACS3-HMAC-SHA256 Credential={self.access_key_id},"
            f"SignedHeaders={signed_headers_str},Signature={signature}"
        )

        qs = "&".join(f"{quote(k, safe='')}={quote(str(v), safe='')}" for k, v in query_params.items())
        url = f"https://{self.HOST}/?{qs}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(url, content=b"", headers={**sign_headers, "Authorization": authorization})
            r.raise_for_status()
            data = r.json()

        code = data.get("Code")
        if code is not None and str(code) != "200":
            raise RuntimeError(f"阿里云错误 {code}: {data.get('Message', '')}")
        return data.get("Data", {}).get("Translated", "") or ""

    async def translate_batch(self, texts: list[str], system_prompt: str | None = None) -> list[str]:
        results: list[str] = []
        for i in range(0, len(texts), self.batch_size):
            chunk = texts[i:i + self.batch_size]
            for t in chunk:
                results.append(await self._post(t))
        return results

    async def health_check(self) -> bool:
        try:
            out = await self.translate_batch(["Water"])
            return bool(out and out[0])
        except Exception:
            return False
