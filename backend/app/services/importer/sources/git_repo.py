"""从 git 仓库获取数据文件。"""
import os
import subprocess
import tempfile
import time
from typing import Optional

import requests
import zipfile

from app.services.importer.models import DataSource, FileCollection, DataFile


def _get_repo_config():
    """从环境变量读取数据仓库配置"""
    return {
        "url": os.getenv("DATA_REPO_URL",
                         "https://github.com/DingJunyao/HowToCook_json.git"),
        "branch": os.getenv("DATA_REPO_BRANCH", "corr"),
        "data_dir": os.getenv("DATA_REPO_DIR", "out"),
    }


class GitRepoSource(DataSource):
    """从 git 仓库拉取数据文件。优先 git clone，失败退回到 ZIP 下载。"""

    DOWNLOAD_TIMEOUT = 300
    MAX_RETRIES = 3
    RETRY_DELAY = 2

    def __init__(self):
        self.config = _get_repo_config()

    def collect_files(self) -> FileCollection:
        temp_dir = tempfile.mkdtemp(prefix="recipe_import_")
        repo_dir = self._try_clone(temp_dir)

        if not repo_dir:
            repo_dir = self._try_download_zip(temp_dir)

        if not repo_dir:
            raise RuntimeError(
                f"无法获取仓库 {self.config['url']}（分支: {self.config['branch']}）"
            )

        data_dir = self._locate_data_dir(repo_dir)
        if not data_dir:
            raise RuntimeError(
                f"数据目录 '{self.config['data_dir']}' 不存在于仓库中"
            )

        collection = self._scan_files(data_dir)
        collection.temp_dir = temp_dir
        return collection

    def _try_clone(self, parent_dir: str) -> Optional[str]:
        """尝试 git clone。返回仓库根目录，失败返回 None。"""
        repo_url = self.config["url"]
        branch = self.config["branch"]
        repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        repo_path = os.path.join(parent_dir, repo_name)

        try:
            process = subprocess.Popen(
                ["git", "clone", "--depth", "1", "--branch", branch,
                 "--single-branch", "--no-tags", repo_url, repo_path],
                cwd=parent_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                returncode = process.wait(timeout=self.DOWNLOAD_TIMEOUT)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                return None

            if returncode == 0:
                return repo_path
            return None
        except FileNotFoundError:
            return None
        except Exception:
            return None

    def _try_download_zip(self, parent_dir: str) -> Optional[str]:
        """退回到 ZIP 下载。返回解压后的目录，失败返回 None。"""
        repo_url = self.config["url"].rstrip("/").removesuffix(".git")
        branch = self.config["branch"]
        zip_url = f"{repo_url}/archive/refs/heads/{branch}.zip"

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                resp = requests.get(zip_url, timeout=self.DOWNLOAD_TIMEOUT)
                resp.raise_for_status()
                zip_path = os.path.join(parent_dir, "repo.zip")
                with open(zip_path, "wb") as f:
                    f.write(resp.content)
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(parent_dir)
                extracted = [d for d in os.listdir(parent_dir)
                             if os.path.isdir(os.path.join(parent_dir, d))]
                if extracted:
                    return os.path.join(parent_dir, extracted[0])
                return None
            except Exception:
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY * attempt)
                    continue
                return None
        return None

    def _locate_data_dir(self, repo_dir: str) -> Optional[str]:
        """定位数据子目录。"""
        candidate = os.path.join(repo_dir, self.config["data_dir"])
        if os.path.isdir(candidate):
            return candidate
        if os.path.isdir(repo_dir):
            return repo_dir
        return None

    def _scan_files(self, data_dir: str) -> FileCollection:
        """扫描数据目录生成 FileCollection。"""
        collection = FileCollection()
        for root, _dirs, files in os.walk(data_dir):
            for fname in files:
                abs_path = os.path.join(root, fname)
                rel_path = os.path.relpath(abs_path, data_dir)
                size = os.path.getsize(abs_path)
                collection.files.append(DataFile(rel_path, abs_path, size))
        return collection
