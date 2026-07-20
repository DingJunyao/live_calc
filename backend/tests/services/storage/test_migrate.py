"""测试 migrate.py 双向迁移核心（Task 9）。

用 MagicMock 假 backend，不真 import boto3（避免测试因缺 boto3 失败）。
"""
from pathlib import Path
from unittest.mock import MagicMock
import pytest


# ============================================================
# Task 9: migrate.py 双向迁移核心测试
# ============================================================


def test_migrate_to_s3_uploads_local_files(tmp_path):
    """to_s3：walk 本地 → put，幂等（已存在跳过）。"""
    from app.services.storage.migrate import _migrate_to_s3_core
    images = tmp_path / "images"
    (images / "recipes").mkdir(parents=True)
    (images / "recipes" / "a.jpg").write_bytes(b"x")
    (images / "recipes" / "b.jpg").write_bytes(b"y")
    fake_s3 = MagicMock()
    fake_s3.exists.return_value = False
    uploaded, skipped, failed = _migrate_to_s3_core(fake_s3, images)
    assert uploaded == 2
    assert fake_s3.put.call_count == 2


def test_migrate_to_s3_skips_existing(tmp_path):
    """to_s3：S3 已存在跳过。"""
    from app.services.storage.migrate import _migrate_to_s3_core
    images = tmp_path / "images"
    (images / "recipes").mkdir(parents=True)
    (images / "recipes" / "a.jpg").write_bytes(b"x")
    fake_s3 = MagicMock()
    fake_s3.exists.return_value = True   # 已存在
    uploaded, skipped, failed = _migrate_to_s3_core(fake_s3, images)
    assert uploaded == 0
    assert skipped == 1
    fake_s3.put.assert_not_called()


def test_migrate_from_s3_paginates_and_writes_local(tmp_path):
    """to_local：list_objects_v2 分页 + get + 落本地，幂等（本地已存在跳过）。"""
    from app.services.storage.migrate import _migrate_from_s3_core
    fake_s3 = MagicMock()
    fake_s3.bucket = "bkt"
    # 两页：第一页 2 个 + token，第二页 1 个 + 无 token
    fake_s3.client.list_objects_v2.side_effect = [
        {"Contents": [{"Key": "recipes/a.jpg"}, {"Key": "recipes/b.jpg"}],
         "IsTruncated": True, "NextContinuationToken": "tok"},
        {"Contents": [{"Key": "avatars/c.png"}], "IsTruncated": False},
    ]
    fake_s3.get.side_effect = [b"adata", b"bdata", b"cdata"]
    images = tmp_path / "images"
    uploaded, skipped, failed = _migrate_from_s3_core(fake_s3, images)
    assert uploaded == 3
    assert fake_s3.client.list_objects_v2.call_count == 2   # 分页两次
    assert (images / "recipes" / "a.jpg").read_bytes() == b"adata"
    assert (images / "avatars" / "c.png").read_bytes() == b"cdata"


def test_migrate_from_s3_skips_existing_local(tmp_path):
    """to_local：本地已存在跳过（不覆盖）。"""
    from app.services.storage.migrate import _migrate_from_s3_core
    fake_s3 = MagicMock()
    fake_s3.bucket = "bkt"
    fake_s3.client.list_objects_v2.return_value = {
        "Contents": [{"Key": "recipes/a.jpg"}], "IsTruncated": False,
    }
    images = tmp_path / "images"
    (images / "recipes").mkdir(parents=True)
    (images / "recipes" / "a.jpg").write_bytes(b"local-existing")   # 本地已存在
    uploaded, skipped, failed = _migrate_from_s3_core(fake_s3, images)
    assert uploaded == 0
    assert skipped == 1
    fake_s3.get.assert_not_called()   # 没下载
    assert (images / "recipes" / "a.jpg").read_bytes() == b"local-existing"  # 没覆盖
