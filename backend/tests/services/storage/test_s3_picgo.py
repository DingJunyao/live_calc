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


def test_s3_put_prepends_base_path():
    """put：DB 存逻辑 key（返回值不含 base_path），但 put_object 的 Key 含前缀。"""
    with patch("app.services.storage.s3.boto3.client") as mock_client:
        from app.services.storage.s3 import S3Backend
        b = S3Backend(endpoint="https://oss.example.com", bucket="bkt",
                      access_key="ak", secret_key="sk", url_style="virtual",
                      base_path="livecalc/")
        ret = b.put("avatars/x.png", b"data", "image/png")
    assert ret == "avatars/x.png"
    mock_client.return_value.put_object.assert_called_once()
    assert mock_client.return_value.put_object.call_args.kwargs["Key"] == "livecalc/avatars/x.png"


def test_s3_url_for_custom_domain_and_suffix():
    """url_for：custom_domain 优先 + url_suffix 末尾。"""
    with patch("app.services.storage.s3.boto3.client"):
        from app.services.storage.s3 import S3Backend
        b = S3Backend(endpoint="https://oss.example.com", bucket="bkt",
                      access_key="ak", secret_key="sk", url_style="virtual",
                      custom_domain="https://cdn.example.com", url_suffix="?imageslim")
        url = b.url_for("avatars/x.png")
    assert url == "https://cdn.example.com/avatars/x.png?imageslim"


def test_s3_url_for_base_path_with_endpoint():
    """url_for：无 custom_domain 时用 endpoint + base_path 前缀。"""
    with patch("app.services.storage.s3.boto3.client"):
        from app.services.storage.s3 import S3Backend
        b = S3Backend(endpoint="https://oss.example.com", bucket="bkt",
                      access_key="ak", secret_key="sk", url_style="path",
                      base_path="livecalc/")
        url = b.url_for("avatars/x.png")
    assert url == "https://oss.example.com/bkt/livecalc/avatars/x.png"


def test_s3_get_uses_full_key():
    """get：内部用 _full_key（含 base_path）。"""
    with patch("app.services.storage.s3.boto3.client") as mock_client:
        mock_client.return_value.get_object.return_value = {"Body": type("B", (), {"read": lambda self: b"x"})()}
        from app.services.storage.s3 import S3Backend
        b = S3Backend(endpoint="https://oss.example.com", bucket="bkt",
                      access_key="ak", secret_key="sk", url_style="path", base_path="lc/")
        b.get("avatars/x.png")
    assert mock_client.return_value.get_object.call_args.kwargs["Key"] == "lc/avatars/x.png"
