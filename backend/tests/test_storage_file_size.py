"""Test storage backend file_size method."""

import pytest
import tempfile
from pathlib import Path
from app.services.storage.local import LocalBackend


@pytest.fixture
def local_backend():
    tmp = tempfile.mkdtemp()
    backend = LocalBackend(Path(tmp), base_url="/api/v1/static")
    yield backend


class TestLocalBackendFileSize:
    def test_file_size_returns_correct_bytes(self, local_backend):
        key = "test/size.txt"
        data = b"hello world"  # 11 bytes
        local_backend.put(key, data, "text/plain")
        assert local_backend.file_size(key) == 11

    def test_file_size_missing_key_raises(self, local_backend):
        with pytest.raises(FileNotFoundError):
            local_backend.file_size("nonexistent/key.txt")

    def test_file_size_path_traversal_raises(self, local_backend):
        with pytest.raises(ValueError):
            local_backend.file_size("../../etc/passwd")
