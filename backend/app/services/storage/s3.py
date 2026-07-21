from typing import Literal
from urllib.parse import quote, urlparse

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

_UrlStyle = Literal["path", "virtual"]
# 注意：NoSuchBucket 不在此列——bucket 配错属配置错误，应向上抛而非当成 key 不存在
_NOT_FOUND_CODES = frozenset({"404", "NoSuchKey", "NotFound"})


class S3Backend:
    """S3 兼容对象存储后端（阿里云 OSS / 腾讯云 COS / MinIO / AWS S3）。

    DB 只存 key（如 `recipes/abc.png`），url_for 拼最终可访问 URL。
    bucket 假设公共读（Task 4 工厂会校验），url_for 返永久 URL（不签名）。

    与 StorageBackend Protocol 结构性兼容（@runtime_checkable isinstance 可验证）。

    url_for 风格（url_style）：
        path     → `<endpoint>/<bucket>/<key>`（MinIO / 多数自建）
        virtual  → `<scheme>://<bucket>.<host>[:<port>]/<key>`（OSS / AWS S3 virtual-hosted）
    OSS 实际为 virtual-hosted，配 OSS 时设 `virtual`；默认 `path` 兼容 MinIO。
    """

    def __init__(
        self,
        endpoint: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        region: str = "",
        url_style: _UrlStyle = "path",
    ) -> None:
        if not endpoint:
            raise ValueError("s3 endpoint is required")
        if url_style not in ("path", "virtual"):
            raise ValueError(
                f"invalid url_style: {url_style!r}, must be 'path' or 'virtual'"
            )
        # botocore 要求 endpoint_url 含 scheme（is_valid_endpoint_url 校验）；
        # 无 scheme 时默认 https（OSS 常见 schemeless 写法如 `oss-cn-beijing.aliyuncs.com`）
        if "://" not in endpoint:
            endpoint = f"https://{endpoint}"
        self.endpoint = endpoint.rstrip("/")
        self.bucket = bucket
        self.url_style: _UrlStyle = url_style
        # SigV4：OSS/COS 等 S3 兼容服务要求；addressing_style 与 url_style 对齐避免认知割裂
        # 注意：addressing_style 只影响 boto3 API 调用的 URL 形态，不影响 url_for 的公开 URL
        config = Config(
            signature_version="s3v4",
            s3={
                "addressing_style": "virtual"
                if url_style == "virtual"
                else "path",
                # OSS 兼容：强制签名（AWS4-HMAC-SHA256），绕过 streaming-unsigned-payload-trailer
                "payload_signing_enabled": True,
            },
            # OSS 兼容：关默认 CRC32C checksum（boto3 2.x 默认开，OSS 不支持）
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        )
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint or None,
            aws_access_key_id=access_key or None,
            aws_secret_access_key=secret_key or None,
            region_name=region or None,
            config=config,
        )

    def put(self, key: str, data: bytes, content_type: str) -> str:
        """上传，回传入参 key（便于调用方链式拿 key 存 DB）。"""
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return key

    def get(self, key: str) -> bytes:
        """下载。key 不存在时抛 FileNotFoundError（与 LocalBackend 一致，调用方可统一 try/except）。

        其他 ClientError（如 403 权限、NoSuchBucket）向上抛，由调用方处理。
        """
        try:
            return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except ClientError as e:
            if e.response.get("Error", {}).get("Code", "") in _NOT_FOUND_CODES:
                raise FileNotFoundError(key) from e
            raise

    def delete(self, key: str) -> None:
        """删除。key 不存在时 S3 delete_object 幂等返 204（不抛）。"""
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def exists(self, key: str) -> bool:
        """存在性。head_object 成功 → True；404/NoSuchKey/NotFound → False；其他错（如 403）向上抛。

        403 等权限错误不吞：配错 access_key/bucket 应尽早暴露而非误判为「key 不存在」。
        """
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in _NOT_FOUND_CODES:
                return False
            raise

    def url_for(self, key: str) -> str:
        """对外可访问 URL。key 经 quote 编码以兼容空格/中文/特殊字符。

        path 风格：`<endpoint>/<bucket>/<key>`（自建 / MinIO）
        virtual 风格：从 endpoint 解析 scheme + netloc（含端口），拼 `<scheme>://<bucket>.<netloc>/<key>`（OSS / S3）

        virtual 风格对无 scheme 的 endpoint（如 `oss-cn-beijing.aliyuncs.com`，OSS 常见写法）
        兜底：scheme 默认 https，netloc 取 urlparse 的 path 段（无 scheme 时 path 即 host）。
        """
        quoted = quote(key)
        if self.url_style == "virtual":
            parsed = urlparse(self.endpoint)
            scheme = parsed.scheme or "https"
            netloc = parsed.netloc or parsed.path  # 无 scheme 时 path 段即 host
            return f"{scheme}://{self.bucket}.{netloc}/{quoted}"
        return f"{self.endpoint}/{self.bucket}/{quoted}"
