from unittest.mock import patch


def _make_backend(**kwargs):
    """构造 S3Backend 但 mock boto3.client（不发真请求）。"""
    with patch("app.services.storage.s3.boto3.client") as mock_client:
        from app.services.storage.s3 import S3Backend
        b = S3Backend(
            endpoint="https://oss.example.com",
            bucket="bkt",
            access_key="ak",
            secret_key="sk",
            url_style="virtual",
            **kwargs,
        )
    return b, mock_client


def test_s3_config_disables_streaming_unsigned_payload():
    """OSS 兼容：Config 必须含 payload_signing_enabled=True（强制签名，绕过 streaming-unsigned-payload-trailer）。"""
    b, mock_client = _make_backend()
    config = mock_client.call_args.kwargs["config"]
    # botocore Config 的 s3 配置——按实际 botocore API 访问调整（config.s3 可能是 dict 或属性）
    s3_cfg = config.s3
    if isinstance(s3_cfg, dict):
        assert s3_cfg.get("payload_signing_enabled") is True
    else:
        assert getattr(s3_cfg, "payload_signing_enabled", None) is True
    # 关默认 CRC checksum（boto3 2.x 默认开，OSS 可能不支持）
    assert (
        getattr(config, "request_checksum_calculation", None) == "when_required"
    )
    assert (
        getattr(config, "response_checksum_validation", None) == "when_required"
    )
