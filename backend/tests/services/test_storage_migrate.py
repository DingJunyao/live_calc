"""图片迁移服务单测。

覆盖：base_path 前缀剥离、路径限定、目录占位符过滤、
progress_callback 的实时计数与取消信号、_run_import_task 保留 cancelled。
"""
from pathlib import Path

from app.services.storage.migrate import (
    _migrate_from_s3_core,
    _migrate_to_s3_core,
    _strip_base_path,
)


# ---- make_progress_callback / _run_import_task 用的 fake 基础设施 ----


class _FakeTask:
    def __init__(self, status="running"):
        self.status = status
        self.progress = None
        self.stats = None
        self.error = None


class _FakeQuery:
    def __init__(self, task):
        self._task = task

    def get(self, _id):
        return self._task


class _FakeSession:
    def __init__(self, task):
        self._task = task

    def query(self, _model):
        return _FakeQuery(self._task)

    def commit(self):
        pass

    def close(self):
        pass


# ---- S3Backend fake（模拟 _full_key 语义 + list_objects_v2）----


class _FakeS3Client:
    def __init__(self, real_keys):
        self._keys = list(real_keys)

    def list_objects_v2(self, **kwargs):
        prefix = kwargs.get("Prefix", "")
        keys = [k for k in self._keys if (not prefix) or k.startswith(prefix)]
        return {"Contents": [{"Key": k} for k in keys], "IsTruncated": False}


class _FakeS3:
    """模拟 S3Backend：get/put/exists 内部用 _full(key)=base_path/key 查 store，
    与真实 S3Backend._full_key 语义一致，以验证迁移循环传入的是「逻辑 key」。"""

    def __init__(self, base_path="", real_keys=None):
        self.base_path = base_path
        self.bucket = "test-bucket"
        self._store = {k: b"data:" + k.encode() for k in (real_keys or [])}
        self.get_calls = []
        self.put_calls = []
        self.client = _FakeS3Client(list(self._store.keys()))

    def _full(self, key):
        return f"{self.base_path}/{key}" if self.base_path else key

    def get(self, key):
        self.get_calls.append(key)
        full = self._full(key)
        if full not in self._store:
            raise FileNotFoundError(key)
        return self._store[full]

    def put(self, key, data, content_type):
        self.put_calls.append(key)
        self._store[self._full(key)] = data
        return key

    def exists(self, key):
        return self._full(key) in self._store


def test_progress_callback_merges_counts_and_signals_cancel(monkeypatch):
    from app.services.importer import api_service

    task = _FakeTask(status="running")
    monkeypatch.setattr("app.core.database.SessionLocal", lambda: _FakeSession(task))
    cb = api_service.make_progress_callback(1)

    # 正常：返回 False，progress 合并 counts
    cancelled = cb("迁移到本地", 3, 10, "recipes/a.jpg",
                   counts={"uploaded": 2, "skipped": 1, "failed": 0})
    assert cancelled is False
    assert task.progress["uploaded"] == 2
    assert task.progress["skipped"] == 1
    assert task.progress["current"] == 3

    # 不传 counts：progress 不含 uploaded 键（向后兼容 importer）
    cb("迁移到本地", 4, 10, "recipes/b.jpg")
    assert "uploaded" not in task.progress

    # status=cancelled：返回 True
    task.status = "cancelled"
    cancelled = cb("迁移到本地", 5, 10, "recipes/c.jpg")
    assert cancelled is True


def test_strip_base_path():
    assert _strip_base_path("livecalc/recipes/a.jpg", "livecalc") == "recipes/a.jpg"
    assert _strip_base_path("recipes/a.jpg", "livecalc") == "recipes/a.jpg"  # 不带前缀原样
    assert _strip_base_path("livecalc/recipes/a.jpg", "") == "livecalc/recipes/a.jpg"
    assert _strip_base_path("livecalc/recipes/a.jpg", "livecalc/") == "recipes/a.jpg"  # 容忍尾斜杠


def test_from_s3_strips_base_path_and_lands_logical_key(tmp_path):
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    fake = _FakeS3(base_path="livecalc",
                   real_keys=["livecalc/recipes/a.jpg", "livecalc/recipes/b.jpg"])
    uploaded, skipped, failed = _migrate_from_s3_core(fake, images_dir)
    assert (uploaded, skipped, failed) == (2, 0, 0)
    # get 收到逻辑 key（剥掉 livecalc/ 前缀），不再翻倍
    assert fake.get_calls == ["recipes/a.jpg", "recipes/b.jpg"]
    # 落地用逻辑 key
    assert (images_dir / "recipes" / "a.jpg").read_bytes() == b"data:livecalc/recipes/a.jpg"
    assert (images_dir / "recipes" / "b.jpg").exists()


def test_from_s3_limits_prefix_to_base_path(tmp_path):
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    fake = _FakeS3(base_path="livecalc",
                   real_keys=["livecalc/recipes/a.jpg", "other-app/x.png"])
    uploaded, *_ = _migrate_from_s3_core(fake, images_dir)
    assert uploaded == 1
    assert (images_dir / "recipes" / "a.jpg").exists()
    assert not (images_dir / "other-app").exists()  # base_path 外的不迁


def test_from_s3_skips_dir_placeholder(tmp_path):
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    fake = _FakeS3(base_path="livecalc",
                   real_keys=["livecalc/recipes/a.jpg", "livecalc/recipes/"])
    uploaded, skipped, failed = _migrate_from_s3_core(fake, images_dir)
    assert uploaded == 1
    assert fake.get_calls == ["recipes/a.jpg"]  # 目录占位符未传给 get


def test_from_s3_passes_live_counts(tmp_path):
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    fake = _FakeS3(base_path="livecalc", real_keys=["livecalc/recipes/a.jpg"])
    seen = {}

    def cb(stage, cur, total, msg, counts=None):
        seen.update(counts or {})
        return False

    _migrate_from_s3_core(fake, images_dir, cb)
    assert seen.get("uploaded") == 1
    assert seen.get("failed") == 0


def test_from_s3_breaks_on_cancel(tmp_path):
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    fake = _FakeS3(base_path="livecalc",
                   real_keys=["livecalc/recipes/a.jpg", "livecalc/recipes/b.jpg",
                              "livecalc/recipes/c.jpg"])

    def cb(stage, cur, total, msg, counts=None):
        return cur >= 1  # 第一个文件处理后中止

    uploaded, skipped, failed = _migrate_from_s3_core(fake, images_dir, cb)
    assert uploaded == 1
    assert fake.get_calls == ["recipes/a.jpg"]  # 后两个未处理


def test_from_s3_no_base_path_lists_whole_bucket(tmp_path):
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    fake = _FakeS3(base_path="", real_keys=["recipes/a.jpg", "products/b.png"])
    uploaded, *_ = _migrate_from_s3_core(fake, images_dir)
    assert uploaded == 2
    assert fake.get_calls == ["recipes/a.jpg", "products/b.png"]


def test_to_s3_passes_live_counts_and_breaks_on_cancel(tmp_path):
    images_dir = tmp_path / "images"
    (images_dir / "recipes").mkdir(parents=True)
    (images_dir / "recipes" / "a.jpg").write_bytes(b"a")
    (images_dir / "recipes" / "b.jpg").write_bytes(b"b")
    fake = _FakeS3(base_path="livecalc")  # 空 store：exists 全 False，走 put
    seen = []

    def cb(stage, cur, total, msg, counts=None):
        seen.append(dict(counts or {}))
        return cur >= 1  # 第一个文件处理后中止

    uploaded, skipped, failed = _migrate_to_s3_core(fake, images_dir, cb)
    assert uploaded == 1
    assert len(fake.put_calls) == 1  # 第二个未处理
    assert seen[0]["uploaded"] == 1


def test_to_s3_idempotent_skips_existing(tmp_path):
    images_dir = tmp_path / "images"
    (images_dir / "recipes").mkdir(parents=True)
    (images_dir / "recipes" / "a.jpg").write_bytes(b"a")
    # S3 已存在同一逻辑 key（store 里存真实 key livecalc/recipes/a.jpg）
    fake = _FakeS3(base_path="livecalc", real_keys=["livecalc/recipes/a.jpg"])
    uploaded, skipped, failed = _migrate_to_s3_core(fake, images_dir, None)
    assert (uploaded, skipped, failed) == (0, 1, 0)
    assert fake.put_calls == []


def test_run_import_task_keeps_cancelled_status(monkeypatch):
    from app.services.importer import api_service
    from app.services.importer.models import ImportResult

    task = _FakeTask(status="pending")
    monkeypatch.setattr("app.core.database.SessionLocal", lambda: _FakeSession(task))

    def fake_import(progress_callback=None):
        task.status = "cancelled"  # 模拟 cancel 端点在运行中置位
        r = ImportResult()
        r.stats = {"direction": "to_local", "uploaded": 3, "skipped": 1,
                   "failed": 0, "total": 4}
        r.errors = []
        return r

    api_service._run_import_task(99, fake_import)
    assert task.status == "cancelled"           # 保留，未被 success 覆盖
    assert task.progress["stage"] == "已取消"
    assert task.stats["uploaded"] == 3          # 部分统计仍记录
    assert task.error is None


def test_run_import_task_success_when_not_cancelled(monkeypatch):
    from app.services.importer import api_service
    from app.services.importer.models import ImportResult

    task = _FakeTask(status="pending")
    monkeypatch.setattr("app.core.database.SessionLocal", lambda: _FakeSession(task))

    def fake_import(progress_callback=None):
        r = ImportResult()
        r.stats = {"uploaded": 5}
        r.errors = []
        return r

    api_service._run_import_task(1, fake_import)
    assert task.status == "success"
    assert task.progress["stage"] == "完成"


def test_run_import_task_failed_when_errors_and_not_cancelled(monkeypatch):
    from app.services.importer import api_service
    from app.services.importer.models import ImportResult

    task = _FakeTask(status="pending")
    monkeypatch.setattr("app.core.database.SessionLocal", lambda: _FakeSession(task))

    def fake_import(progress_callback=None):
        r = ImportResult()
        r.stats = {"uploaded": 0}
        r.errors = ["boom"]
        return r

    api_service._run_import_task(1, fake_import)
    assert task.status == "failed"
    assert task.error == "boom"
