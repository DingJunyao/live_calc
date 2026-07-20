"""测试 effective.py 三层配置合并逻辑。"""
from unittest.mock import patch, MagicMock


def test_effective_db_overrides_env():
    """DB 字段非空时覆盖 .env。"""
    from app.services.storage.effective import load_effective_storage_config
    fake_row = MagicMock(
        backend="s3", storage_base_url=None,
        s3_endpoint="https://db.example.com", s3_access_key="db-ak",
        s3_secret_key="db-sk", s3_bucket="db-bucket", s3_region="db-r",
        s3_url_style="virtual",
    )
    with patch("app.services.storage.effective._query_db_row", return_value=fake_row):
        cfg = load_effective_storage_config()
    assert cfg.backend == "s3"
    assert cfg.s3_endpoint == "https://db.example.com"
    assert cfg.sources["s3_endpoint"] == "db"
    assert cfg.sources["backend"] == "db"


def test_effective_falls_back_to_env():
    """DB 字段为空时回落 .env。"""
    from app.services.storage.effective import load_effective_storage_config
    fake_row = MagicMock(backend=None, storage_base_url=None, s3_endpoint=None,
                         s3_access_key=None, s3_secret_key=None, s3_bucket=None,
                         s3_region=None, s3_url_style=None)
    with patch("app.services.storage.effective._query_db_row", return_value=fake_row), \
         patch("app.services.storage.effective.settings") as s:
        s.bootstrap_storage_backend = "s3"
        s.bootstrap_s3_endpoint = "https://env.example.com"
        s.bootstrap_storage_base_url = ""
        s.bootstrap_s3_access_key = ""; s.bootstrap_s3_secret_key = ""
        s.bootstrap_s3_bucket = ""; s.bootstrap_s3_region = ""
        s.bootstrap_s3_url_style = "path"
        cfg = load_effective_storage_config()
    assert cfg.backend == "s3"
    assert cfg.s3_endpoint == "https://env.example.com"
    assert cfg.sources["s3_endpoint"] == "env"


def test_effective_default_when_all_empty():
    """DB 与 .env 都空时用代码默认。"""
    from app.services.storage.effective import load_effective_storage_config
    fake_row = MagicMock(backend=None, storage_base_url=None, s3_endpoint=None,
                         s3_access_key=None, s3_secret_key=None, s3_bucket=None,
                         s3_region=None, s3_url_style=None)
    with patch("app.services.storage.effective._query_db_row", return_value=fake_row), \
         patch("app.services.storage.effective.settings") as s:
        # 所有 bootstrap 字段都为空，回落到代码默认
        s.bootstrap_storage_backend = None; s.bootstrap_storage_base_url = None
        s.bootstrap_s3_endpoint = None; s.bootstrap_s3_access_key = None
        s.bootstrap_s3_secret_key = None; s.bootstrap_s3_bucket = None
        s.bootstrap_s3_region = None; s.bootstrap_s3_url_style = None
        cfg = load_effective_storage_config()
    assert cfg.backend == "local"
    assert cfg.sources["backend"] == "default"
