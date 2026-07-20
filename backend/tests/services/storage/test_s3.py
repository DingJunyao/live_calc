from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from app.services.storage.base import StorageBackend
from app.services.storage.s3 import S3Backend


def _backend(url_style: str = "path") -> S3Backend:
    """构造一个 S3Backend 并把真实 boto3 client 换成 MagicMock，测试不触网。"""
    b = S3Backend(
        endpoint="https://s3.example.com",
        bucket="live",
        access_key="ak",
        secret_key="sk",
        region="us-east-1",
        url_style=url_style,
    )
    b.client = MagicMock()
    return b


def test_put_calls_s3():
    """put 应调 put_object 并回传入参 key（便于调用方链式拿 key 存 DB）。"""
    b = _backend()
    key = b.put("recipes/a.png", b"data", "image/png")
    assert key == "recipes/a.png"
    b.client.put_object.assert_called_once()
    kwargs = b.client.put_object.call_args.kwargs
    assert kwargs["Bucket"] == "live"
    assert kwargs["Key"] == "recipes/a.png"
    assert kwargs["Body"] == b"data"
    assert kwargs["ContentType"] == "image/png"


def test_get_reads_body():
    """get 应调 get_object 并把 Body.read() 结果返出。"""
    b = _backend()
    b.client.get_object.return_value = {"Body": MagicMock(read=lambda: b"x")}
    assert b.get("k") == b"x"
    b.client.get_object.assert_called_once_with(Bucket="live", Key="k")


def test_delete_calls_s3():
    """delete 应调 delete_object。"""
    b = _backend()
    b.delete("k")
    b.client.delete_object.assert_called_once_with(Bucket="live", Key="k")


def test_exists_true_when_head_ok():
    """head_object 成功 → exists 返 True。"""
    b = _backend()
    b.client.head_object.return_value = {}
    assert b.exists("k") is True
    b.client.head_object.assert_called_once_with(Bucket="live", Key="k")


def test_exists_false_on_404_client_error():
    """head_object 抛 404 ClientError → exists 返 False（不向上抛）。"""
    b = _backend()
    b.client.head_object.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}}, "head_object"
    )
    assert b.exists("k") is False


def test_exists_propagates_non_404_error():
    """非 404 ClientError（如 403 权限）不应被吞，让调用方感知配置错误。"""
    b = _backend()
    b.client.head_object.side_effect = ClientError(
        {"Error": {"Code": "403", "Message": "Forbidden"}}, "head_object"
    )
    with pytest.raises(ClientError):
        b.exists("k")


def test_url_for_path_style():
    """path 风格：<endpoint>/<bucket>/<key>（MinIO / 多数自建）。"""
    b = _backend(url_style="path")
    assert b.url_for("recipes/a.png") == "https://s3.example.com/live/recipes/a.png"


def test_url_for_virtual_style():
    """virtual 风格：<scheme>://<bucket>.<host>/<key>（OSS / AWS S3 virtual-hosted）。"""
    b = S3Backend(
        endpoint="https://oss-cn-beijing.aliyuncs.com",
        bucket="livecalc",
        access_key="ak",
        secret_key="sk",
        region="cn-beijing",
        url_style="virtual",
    )
    b.client = MagicMock()
    assert (
        b.url_for("recipes/a.png")
        == "https://livecalc.oss-cn-beijing.aliyuncs.com/recipes/a.png"
    )


def test_url_for_virtual_style_with_port():
    """virtual 风格 endpoint 含端口时保留端口（netloc 整段提取）。"""
    b = S3Backend(
        endpoint="http://localhost:9000",
        bucket="live",
        access_key="ak",
        secret_key="sk",
        region="us-east-1",
        url_style="virtual",
    )
    b.client = MagicMock()
    assert b.url_for("k") == "http://live.localhost:9000/k"


def test_url_for_strips_endpoint_trailing_slash():
    """endpoint 带末尾斜杠时也应拼出单斜杠，避免 //live//。"""
    b = S3Backend(
        endpoint="https://s3.example.com/",
        bucket="live",
        access_key="ak",
        secret_key="sk",
        url_style="path",
    )
    b.client = MagicMock()
    assert b.url_for("k") == "https://s3.example.com/live/k"


def test_url_for_quote_special_chars():
    """key 含空格/中文时应经 quote 编码，避免 URL 破损。"""
    b = _backend(url_style="path")
    url = b.url_for("recipes/带 空 格.png")
    assert "recipes/%E5%B8%A6%20%E7%A9%BA%20%E6%A0%BC.png" in url


def test_default_url_style_is_path():
    """不传 url_style 时默认 path（与 Settings.s3_url_style 默认值对齐）。"""
    b = S3Backend(
        endpoint="https://s3.example.com",
        bucket="live",
        access_key="ak",
        secret_key="sk",
    )
    b.client = MagicMock()
    assert b.url_for("k") == "https://s3.example.com/live/k"


def test_s3_satisfies_protocol():
    """S3Backend 满足 StorageBackend Protocol（@runtime_checkable isinstance 验证）。

    构造时不触网（boto3.client 不做远程校验），可直接实例化。
    """
    b = S3Backend(
        endpoint="https://s3.example.com",
        bucket="live",
        access_key="ak",
        secret_key="sk",
    )
    assert isinstance(b, StorageBackend)


def test_invalid_url_style_rejected():
    """url_style 非 path/virtual 应在构造时 fail-fast 抛 ValueError。

    Literal 类型提示只被静态检查器/mypy 看到，运行时不拦；
    这里显式校验，避免配错（如 S3_URL_STYLE=bogus）静默走错 url_for 分支。
    """
    with pytest.raises(ValueError, match="url_style"):
        S3Backend(
            endpoint="https://s3.example.com",
            bucket="live",
            access_key="ak",
            secret_key="sk",
            url_style="bogus",  # type: ignore[arg-type]
        )


def test_empty_endpoint_rejected():
    """endpoint 为空字符串应在构造时 fail-fast 抛 ValueError（s3 模式必填）。

    避免 boto3.client 传 endpoint_url=None 静默走默认区域，行为与用户预期不符。
    """
    with pytest.raises(ValueError, match="endpoint"):
        S3Backend(
            endpoint="",
            bucket="live",
            access_key="ak",
            secret_key="sk",
        )


def test_url_for_virtual_style_schemeless_endpoint():
    """virtual 风格 endpoint 无 scheme（如 OSS 常见 `oss-cn-beijing.aliyuncs.com`）兜底。

    urlparse 无 scheme 时把整段当 path、scheme/netloc 均空；这里兜底 scheme 默认 https、
    netloc 取 path 段（即 host），避免产出 `://livecalc./k` 破损 URL。

    用户有真实 OSS bucket，必命中此场景。
    """
    b = S3Backend(
        endpoint="oss-cn-beijing.aliyuncs.com",
        bucket="livecalc",
        access_key="ak",
        secret_key="sk",
        region="cn-beijing",
        url_style="virtual",
    )
    b.client = MagicMock()
    assert (
        b.url_for("recipes/a.png")
        == "https://livecalc.oss-cn-beijing.aliyuncs.com/recipes/a.png"
    )


def test_get_nonexistent_raises_filenotfound():
    """get 不存在 key 应抛 FileNotFoundError（与 LocalBackend 一致，调用方可统一 try/except）。

    避免切 S3 后 `except FileNotFoundError` 失效。
    """
    b = _backend()
    b.client.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "Not Found"}}, "get_object"
    )
    with pytest.raises(FileNotFoundError):
        b.get("missing-key")


def test_get_propagates_non_notfound_error():
    """get 遇非 _NOT_FOUND_CODES 的 ClientError（如 403、NoSuchBucket）应向上抛，不吞。"""
    b = _backend()
    b.client.get_object.side_effect = ClientError(
        {"Error": {"Code": "403", "Message": "Forbidden"}}, "get_object"
    )
    with pytest.raises(ClientError):
        b.get("k")


def test_delete_idempotent_on_missing_key():
    """delete 不存在的 key 不应抛异常（S3 delete_object 本就幂等）。

    mock delete_object 默认不抛，验证 delete 调用即返回。
    """
    b = _backend()
    b.client.delete_object.return_value = {}
    # 不应抛
    b.delete("missing-key")
    b.client.delete_object.assert_called_once_with(Bucket="live", Key="missing-key")
