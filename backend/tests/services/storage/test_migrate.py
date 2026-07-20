"""Test migrate_local_to_s3 迁移脚本。

测试策略：
- ``_infer_content_type`` / ``_compute_key`` 为纯函数，直接测。
- ``_migrate_all``：mock S3Backend + tmp_path 文件系统，验证上传数/跳过/key 正确。
- ``main()``：mock settings + S3Backend 验证配置校验/目录缺失等 CLI 入口。
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def images_dir(tmp_path: Path) -> Path:
    """创建含有测试图片的临时目录。

    结构::

        images/
        ├── other.png
        └── recipes/
            ├── a.png
            └── sub/
                └── b.jpg
    """
    img = tmp_path / "images"
    (img / "recipes" / "sub").mkdir(parents=True)
    (img / "recipes" / "a.png").write_bytes(b"png-data")
    (img / "recipes" / "sub" / "b.jpg").write_bytes(b"jpg-data")
    (img / "other.png").write_bytes(b"other-png")
    return img


@pytest.fixture
def mock_backend() -> MagicMock:
    """带 MagicMock 的伪 S3Backend。"""
    return MagicMock()


# ============================================================
# 纯函数测试
# ============================================================


def test_infer_content_type_known():
    from scripts.migrate_local_to_s3 import _infer_content_type

    assert _infer_content_type(Path("x.png")) == "image/png"
    assert _infer_content_type(Path("x.jpg")) == "image/jpeg"
    assert _infer_content_type(Path("x.jpeg")) == "image/jpeg"
    assert _infer_content_type(Path("x.gif")) == "image/gif"
    assert _infer_content_type(Path("x.webp")) == "image/webp"
    assert _infer_content_type(Path("x.svg")) == "image/svg+xml"


def test_infer_content_type_fallback():
    from scripts.migrate_local_to_s3 import _infer_content_type

    assert _infer_content_type(Path("x.unknown")) == "application/octet-stream"
    assert _infer_content_type(Path("")) == "application/octet-stream"


def test_compute_key(images_dir: Path):
    from scripts.migrate_local_to_s3 import _compute_key

    assert _compute_key(images_dir / "recipes" / "a.png", images_dir) == "recipes/a.png"
    assert (
        _compute_key(images_dir / "recipes" / "sub" / "b.jpg", images_dir)
        == "recipes/sub/b.jpg"
    )
    assert _compute_key(images_dir / "other.png", images_dir) == "other.png"


# ============================================================
# _migrate_all 核心逻辑测试
# ============================================================


def test_migrate_all_new(images_dir: Path, mock_backend: MagicMock):
    """没有已存在的文件时，应上传全部文件。"""
    from scripts.migrate_local_to_s3 import _migrate_all

    mock_backend.exists.return_value = False

    uploaded, skipped, failed = _migrate_all(mock_backend, images_dir, quiet=True)

    assert uploaded == 3
    assert skipped == 0
    assert failed == 0
    assert mock_backend.put.call_count == 3


def test_migrate_all_skip_existing(images_dir: Path, mock_backend: MagicMock):
    """已存在的文件应跳过。"""
    from scripts.migrate_local_to_s3 import _migrate_all

    def exists_side_effect(key: str) -> bool:
        return key == "recipes/a.png"

    mock_backend.exists.side_effect = exists_side_effect

    uploaded, skipped, failed = _migrate_all(mock_backend, images_dir, quiet=True)

    assert uploaded == 2  # b.jpg + other.png
    assert skipped == 1  # a.png
    assert failed == 0
    assert mock_backend.put.call_count == 2


def test_migrate_all_all_exist(images_dir: Path, mock_backend: MagicMock):
    """所有文件已存在于 S3 时应全部跳过。"""
    from scripts.migrate_local_to_s3 import _migrate_all

    mock_backend.exists.return_value = True

    uploaded, skipped, failed = _migrate_all(mock_backend, images_dir, quiet=True)

    assert uploaded == 0
    assert skipped == 3
    assert failed == 0
    assert mock_backend.put.call_count == 0


def test_migrate_all_put_call_args(images_dir: Path, mock_backend: MagicMock):
    """put 调用的 (key, data, content_type) 应正确。"""
    from scripts.migrate_local_to_s3 import _migrate_all

    mock_backend.exists.return_value = False

    _migrate_all(mock_backend, images_dir, quiet=True)

    calls = mock_backend.put.call_args_list
    assert len(calls) == 3

    # 按 key 排序后断言，保证确定性
    by_key: dict[str, tuple[bytes, str]] = {}
    for call in calls:
        key = call[0][0]
        data = call[0][1]
        ct = call[0][2]
        by_key[key] = (data, ct)

    assert by_key["recipes/a.png"] == (b"png-data", "image/png")
    assert by_key["recipes/sub/b.jpg"] == (b"jpg-data", "image/jpeg")
    assert by_key["other.png"] == (b"other-png", "image/png")


def test_migrate_all_empty_dir(tmp_path: Path, mock_backend: MagicMock):
    """空目录应上传 0 / 跳过 0 / 失败 0。"""
    from scripts.migrate_local_to_s3 import _migrate_all

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    uploaded, skipped, failed = _migrate_all(mock_backend, empty_dir, quiet=True)

    assert uploaded == 0
    assert skipped == 0
    assert failed == 0
    mock_backend.put.assert_not_called()


def test_migrate_all_partial_failure(images_dir: Path, mock_backend: MagicMock):
    """部分文件上传失败应累加 failed 计数。"""
    from scripts.migrate_local_to_s3 import _migrate_all

    mock_backend.exists.return_value = False

    # 让 recipes/sub/b.jpg 上传抛异常
    def put_side_effect(key: str, data: bytes, content_type: str) -> str:
        if key == "recipes/sub/b.jpg":
            raise RuntimeError("connection reset")
        return key

    mock_backend.put.side_effect = put_side_effect

    uploaded, skipped, failed = _migrate_all(mock_backend, images_dir, quiet=True)

    assert uploaded == 2  # a.png + other.png
    assert skipped == 0
    assert failed == 1  # b.jpg
    assert mock_backend.put.call_count == 3


# ============================================================
# main() CLI 入口测试
# ============================================================


def test_main_no_images_dir(tmp_path: Path):
    """不存在的 images 目录应输出 [SKIP] 并返回 0。"""
    import scripts.migrate_local_to_s3 as mod

    original = mod.IMAGES_DIR
    mod.IMAGES_DIR = tmp_path / "nonexistent"
    try:
        rc = mod.main()
        assert rc == 0
    finally:
        mod.IMAGES_DIR = original


def test_main_empty_dir(tmp_path: Path):
    """空 images 目录应输出 [DONE] 并返回 0。"""
    import scripts.migrate_local_to_s3 as mod

    empty_dir = tmp_path / "images"
    empty_dir.mkdir()
    original = mod.IMAGES_DIR
    mod.IMAGES_DIR = empty_dir
    try:
        rc = mod.main()
        assert rc == 0
    finally:
        mod.IMAGES_DIR = original


def test_main_missing_s3_config(tmp_path: Path):
    """缺少 S3 配置时 main() 应返回 1 并打印 [ERR]。"""
    import scripts.migrate_local_to_s3 as mod

    # 准备一个带文件的 images 目录（让 main 走到配置校验步）
    img_dir = tmp_path / "images"
    img_dir.mkdir()
    (img_dir / "test.png").write_bytes(b"x")
    original_dir = mod.IMAGES_DIR
    mod.IMAGES_DIR = img_dir
    try:
        # 确保 settings 中 S3 配置为空
        with (
            patch.object(mod.settings, "s3_endpoint", ""),
            patch.object(mod.settings, "s3_bucket", ""),
            patch.object(mod.settings, "s3_access_key", "ak"),
            patch.object(mod.settings, "s3_secret_key", "sk"),
        ):
            rc = mod.main()
        assert rc == 1  # s3_endpoint 和 s3_bucket 都缺，应失败
    finally:
        mod.IMAGES_DIR = original_dir


def test_main_full_flow(tmp_path: Path):
    """完整流程：images 下 2 文件，mock S3Backend，应 upload 2。"""
    import scripts.migrate_local_to_s3 as mod

    img_dir = tmp_path / "images"
    (img_dir / "recipes").mkdir(parents=True)
    (img_dir / "recipes" / "a.png").write_bytes(b"d")
    (img_dir / "b.jpg").write_bytes(b"d")
    original_dir = mod.IMAGES_DIR
    mod.IMAGES_DIR = img_dir

    mock_backend = MagicMock()
    mock_backend.exists.return_value = False

    try:
        with (
            patch.object(mod.settings, "s3_endpoint", "https://s3.example.com"),
            patch.object(mod.settings, "s3_bucket", "test-bucket"),
            patch.object(mod.settings, "s3_access_key", "ak"),
            patch.object(mod.settings, "s3_secret_key", "sk"),
            patch.object(mod.settings, "s3_region", "us-east-1"),
            patch.object(mod.settings, "s3_url_style", "path"),
            patch.object(mod, "S3Backend", return_value=mock_backend),
        ):
            rc = mod.main()
        assert rc == 0
        assert mock_backend.put.call_count == 2
    finally:
        mod.IMAGES_DIR = original_dir
