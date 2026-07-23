"""StorageBackend list 方法测试。"""
from unittest.mock import MagicMock

from pathlib import Path

from app.services.storage.local import LocalBackend


def _mkdir_parent(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def test_local_list_returns_all_keys(tmp_path):
    images = tmp_path / "images"
    _mkdir_parent(images / "recipes" / "a.jpg")
    (images / "recipes" / "a.jpg").write_bytes(b"a")
    _mkdir_parent(images / "recipes" / "sub" / "b.jpg")
    (images / "recipes" / "sub" / "b.jpg").write_bytes(b"b")
    _mkdir_parent(images / "avatars" / "c.png")
    (images / "avatars" / "c.png").write_bytes(b"c")

    lb = LocalBackend(root=tmp_path)
    items = lb.list("")
    item_keys = [k for k, _ in items]
    assert "recipes/a.jpg" in item_keys
    assert "recipes/sub/b.jpg" in item_keys
    assert "avatars/c.png" in item_keys
    assert len(items) == 3


def test_local_list_prefix_filters(tmp_path):
    images = tmp_path / "images"
    _mkdir_parent(images / "recipes" / "a.jpg")
    (images / "recipes" / "a.jpg").write_bytes(b"a")
    _mkdir_parent(images / "avatars" / "b.png")
    (images / "avatars" / "b.png").write_bytes(b"b")

    lb = LocalBackend(root=tmp_path)
    items = lb.list("recipes/")
    assert items == [("recipes/a.jpg", 1)]


def test_local_list_empty_dir(tmp_path):
    lb = LocalBackend(root=tmp_path)
    assert lb.list("") == []


# ———— S3Backend list ————


def _fake_s3_client(responses):
    """创建 mock S3 client，按顺序返回每页 list_objects_v2 响应。"""
    client = MagicMock()
    client.list_objects_v2.side_effect = responses
    return client


def test_s3_list_returns_all_keys():
    from app.services.storage.s3 import S3Backend

    fake = _fake_s3_client([
        {"Contents": [{"Key": "recipes/a.jpg"}], "IsTruncated": True,
         "NextContinuationToken": "tok1"},
        {"Contents": [{"Key": "avatars/b.png"}], "IsTruncated": False},
    ])
    backend = S3Backend(endpoint="https://s3.example.com", bucket="test",
                        access_key="ak", secret_key="sk")
    backend.client = fake
    keys = backend.list("")
    item_keys = [k for k, _ in keys]
    assert "recipes/a.jpg" in item_keys
    assert "avatars/b.png" in item_keys
    assert len(keys) == 2
    assert fake.list_objects_v2.call_count == 2
    _, kwargs = fake.list_objects_v2.call_args
    assert kwargs.get("ContinuationToken") == "tok1"


def test_s3_list_prefix_passed():
    from app.services.storage.s3 import S3Backend

    fake = _fake_s3_client([{"Contents": [], "IsTruncated": False}])
    backend = S3Backend(endpoint="https://s3.example.com", bucket="test",
                        access_key="ak", secret_key="sk")
    backend.client = fake
    backend.list("recipes/")
    _, kwargs = fake.list_objects_v2.call_args
    assert kwargs.get("Prefix") == "recipes/"


def test_s3_list_with_base_path_strips_prefix():
    from app.services.storage.s3 import S3Backend

    fake = _fake_s3_client([
        {"Contents": [{"Key": "livecalc/recipes/a.jpg"}, {"Key": "livecalc/avatars/b.png"}],
         "IsTruncated": False},
    ])
    backend = S3Backend(endpoint="https://s3.example.com", bucket="test",
                        access_key="ak", secret_key="sk",
                        base_path="livecalc")
    backend.client = fake
    keys = backend.list("")
    item_keys = [k for k, _ in keys]
    assert "recipes/a.jpg" in item_keys
    assert "avatars/b.png" in item_keys
    # 验证 S3 Prefix 正确加了 base_path
    _, kwargs = fake.list_objects_v2.call_args
    assert kwargs.get("Prefix") == "livecalc/"


def test_s3_list_empty():
    from app.services.storage.s3 import S3Backend

    fake = _fake_s3_client([{"Contents": [], "IsTruncated": False}])
    backend = S3Backend(endpoint="https://s3.example.com", bucket="test",
                        access_key="ak", secret_key="sk")
    backend.client = fake
    assert backend.list("") == []


# ———— _collect_used_image_keys ————


def test_collect_used_keys_aggregates_all_sources():
    from app.api.admin import _collect_used_image_keys

    db = MagicMock()
    q1 = MagicMock()
    q1.all.return_value = [(['recipes/a.jpg', 'recipes/b.jpg'],), ([],)]
    q2 = MagicMock()
    q2.filter.return_value.all.return_value = [('avatars/old.png',), (None,)]
    q3 = MagicMock()
    q3.filter.return_value.all.return_value = [('http://example.com/img.png',), ('recipes/c.jpg',), (None,)]

    db.query.side_effect = [q1, q2, q3]

    used = _collect_used_image_keys(db)
    assert "recipes/a.jpg" in used
    assert "recipes/b.jpg" in used
    assert "avatars/old.png" in used
    assert "recipes/c.jpg" in used          # 内部 key
    assert "http://example.com/img.png" not in used  # 外部 URL 排除
    assert len(used) == 4