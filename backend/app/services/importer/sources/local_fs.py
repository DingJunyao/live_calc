"""从本地文件系统获取数据文件。"""
import os
import tempfile
import zipfile

from app.services.importer.models import DataSource, FileCollection, DataFile


class LocalDirSource(DataSource):
    """从本地目录读取数据文件。"""

    def __init__(self, local_path: str):
        self.local_path = local_path
        if not os.path.isdir(local_path):
            raise NotADirectoryError(f"路径不是有效目录: {local_path}")

    def collect_files(self) -> FileCollection:
        collection = FileCollection()
        for root, _dirs, files in os.walk(self.local_path):
            for fname in files:
                abs_path = os.path.join(root, fname)
                rel_path = os.path.relpath(abs_path, self.local_path)
                size = os.path.getsize(abs_path)
                collection.files.append(DataFile(rel_path, abs_path, size))
        return collection


class UploadArchiveSource(DataSource):
    """从上传的 ZIP 压缩包读取数据文件。"""

    def __init__(self, zip_path: str):
        self.zip_path = zip_path
        if not os.path.isfile(zip_path):
            raise FileNotFoundError(f"ZIP 文件不存在: {zip_path}")

    def collect_files(self) -> FileCollection:
        temp_dir = tempfile.mkdtemp(prefix="upload_import_")

        # 解压到临时目录
        with zipfile.ZipFile(self.zip_path, "r") as zf:
            zf.extractall(temp_dir)

        # 自动检测 zip 中是否只有一个顶层目录
        entries = os.listdir(temp_dir)
        if len(entries) == 1 and os.path.isdir(os.path.join(temp_dir, entries[0])):
            scan_root = os.path.join(temp_dir, entries[0])
        else:
            scan_root = temp_dir

        # 扫描文件
        collection = FileCollection()
        for root, _dirs, files in os.walk(scan_root):
            for fname in files:
                abs_path = os.path.join(root, fname)
                rel_path = os.path.relpath(abs_path, scan_root)
                size = os.path.getsize(abs_path)
                collection.files.append(DataFile(rel_path, abs_path, size))

        collection.temp_dir = temp_dir
        collection.cleanup = lambda: self._cleanup(temp_dir)
        return collection

    @staticmethod
    def _cleanup(temp_dir: str):
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
