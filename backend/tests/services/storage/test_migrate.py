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


def test_start_migrate_task_passes_args_positionally(monkeypatch):
    """start_migrate_task 把 direction/s3_config 位置传给 start_background_import（防 TypeError 回归）。

    start_background_import(db, task_type, user_id, import_func, *args) 只接位置 *args，
    direction/s3_config 必须位置传进 *args，_run_import_task 才能透传给 _run_migrate_task。
    之前误用关键字 → TypeError: got an unexpected keyword argument 'direction'。
    """
    from app.services.storage import migrate as M
    captured = {}

    def fake_start(db, task_type, user_id, import_func, *args):
        captured.update(task_type=task_type, user_id=user_id,
                        import_func=import_func, args=args)
        return 42

    monkeypatch.setattr("app.services.importer.api_service.start_background_import", fake_start)
    task_id = M.start_migrate_task(db=None, direction="to_s3", s3_config={"x": 1}, user_id=1)
    assert task_id == 42
    assert captured["task_type"] == "storage_migrate"
    assert captured["user_id"] == 1
    assert captured["import_func"] == M._run_migrate_task
    assert captured["args"] == ("to_s3", {"x": 1})   # direction/s3_config 位置进 *args


def test_run_migrate_task_to_s3_uses_s3_config(monkeypatch):
    """_run_migrate_task(direction, s3_config, progress_callback) 签名匹配 + to_s3 用 s3_config 建 backend。

    防 _run_migrate_task 误带 db 参数错位回归（db 收 direction → direction 收 s3_config(dict) →
    != 'to_s3' → 走 to_local → 用 effective(local 无 endpoint) → 报 s3 endpoint required）。
    """
    from app.services.storage import migrate as M
    captured = {}

    def fake_build(s3_config):
        captured["s3_config_arg"] = s3_config
        return MagicMock()

    def fake_core(backend, images_dir, cb):
        captured["backend"] = backend
        return (1, 0, 0)

    monkeypatch.setattr(M, "_build_s3_from_config", fake_build)
    monkeypatch.setattr(M, "_migrate_to_s3_core", fake_core)

    cfg = {"s3_endpoint": "https://x", "s3_bucket": "b", "s3_access_key": "ak",
           "s3_secret_key": "sk", "s3_base_path": "livecalc/"}
    result = M._run_migrate_task(direction="to_s3", s3_config=cfg)

    assert captured["s3_config_arg"] == cfg   # to_s3 用 s3_config（非 None）—— 错位时会传 None
    assert result.stats["direction"] == "to_s3"
    assert result.stats["uploaded"] == 1
