"""从 git 仓库获取数据文件。"""
import logging
import os
import subprocess
import tempfile
import time
from typing import Optional

import requests
import zipfile

from app.services.importer.models import DataSource, FileCollection, DataFile

logger = logging.getLogger("app.importer.git_repo")


def _get_repo_config():
    """从 Settings 读取数据仓库配置"""
    from app.config import settings
    return {
        "url": settings.data_repo_url,
        "branch": settings.data_repo_branch,
        "data_dir": settings.data_repo_dir,
        "timeout": settings.import_download_timeout,
    }


class GitRepoSource(DataSource):
    """从 git 仓库拉取数据文件。优先 git clone，失败退回到 ZIP 下载。"""

    MAX_RETRIES = 3
    RETRY_DELAY = 2

    def __init__(self):
        self.config = _get_repo_config()

    def collect_files(self) -> FileCollection:
        temp_dir = tempfile.mkdtemp(prefix="recipe_import_")
        logger.info("正在从仓库获取数据: %s (分支: %s)", self.config["url"], self.config["branch"])
        repo_dir = self._try_clone(temp_dir)

        if not repo_dir:
            logger.warning("git clone 失败，尝试下载 ZIP...")
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

        logger.info("git clone: %s [%s]", repo_url, branch)
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
                returncode = process.wait(timeout=self.config["timeout"])
            except subprocess.TimeoutExpired:
                logger.error("git clone 超时（%ds）", self.config["timeout"])
                process.kill()
                process.wait()
                return None

            if returncode == 0:
                logger.info("git clone 成功: %s", repo_path)
                return repo_path
            logger.error("git clone 失败，退出码: %d", returncode)
            return None
        except FileNotFoundError:
            logger.warning("git 命令未找到")
            return None
        except Exception as e:
            logger.error("git clone 异常: %s", e)
            return None

    def _try_download_zip(self, parent_dir: str) -> Optional[str]:
        """退回到 ZIP 下载。返回解压后的目录，失败返回 None。"""
        repo_url = self.config["url"].rstrip("/").removesuffix(".git")
        branch = self.config["branch"]
        zip_url = f"{repo_url}/archive/refs/heads/{branch}.zip"

        logger.info("下载 ZIP: %s", zip_url)
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.info("ZIP 下载 (第 %d/%d 次)", attempt, self.MAX_RETRIES)
                resp = requests.get(zip_url, timeout=self.config["timeout"])
                resp.raise_for_status()
                zip_path = os.path.join(parent_dir, "repo.zip")
                with open(zip_path, "wb") as f:
                    f.write(resp.content)
                logger.info("ZIP 下载完成（%d 字节），正在解压...", len(resp.content))
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(parent_dir)
                extracted = [d for d in os.listdir(parent_dir)
                             if os.path.isdir(os.path.join(parent_dir, d))]
                if extracted:
                    logger.info("ZIP 解压完成")
                    return os.path.join(parent_dir, extracted[0])
                return None
            except requests.RequestException as e:
                logger.warning("ZIP 下载失败 (第 %d 次): %s", attempt, e)
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY * attempt)
                    continue
                return None
        return None

    def _locate_data_dir(self, repo_dir: str) -> Optional[str]:
        """定位数据子目录。"""
        candidate = os.path.join(repo_dir, self.config["data_dir"])
        if os.path.isdir(candidate):
            logger.info("使用数据子目录: %s", candidate)
            return candidate
        logger.info("使用仓库根目录: %s", repo_dir)
        return repo_dir

    def _scan_files(self, data_dir: str) -> FileCollection:
        """扫描数据目录生成 FileCollection。"""
        collection = FileCollection()
        for root, _dirs, files in os.walk(data_dir):
            for fname in files:
                abs_path = os.path.join(root, fname)
                rel_path = os.path.relpath(abs_path, data_dir)
                size = os.path.getsize(abs_path)
                collection.files.append(DataFile(rel_path, abs_path, size))
        logger.info("扫描到 %d 个文件", len(collection.files))
        return collection
