"""导入模块共享数据模型。"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


class FormatType(str, Enum):
    """数据格式类型"""
    HOWTOCOOK_JSON = "howtocook_json"
    EXPORT = "export"
    UNKNOWN = "unknown"


@dataclass
class DataFile:
    """文件集合中的单个文件"""
    relative_path: str          # 在集合中的相对路径，如 "recipes/西红柿炒鸡蛋.json"
    absolute_path: str          # 磁盘上的绝对路径
    size: int                   # 文件大小（字节）

    @property
    def name(self) -> str:
        """返回文件名，如 '西红柿炒鸡蛋.json'"""
        return os.path.basename(self.relative_path)

    @property
    def dirname(self) -> str:
        """返回文件所在目录的相对路径"""
        return os.path.dirname(self.relative_path)


@dataclass
class FileCollection:
    """输入源产出的扁平文件集合"""
    files: list[DataFile] = field(default_factory=list)
    temp_dir: Optional[str] = None      # 需要清理的临时目录
    cleanup: Optional[Callable] = None  # 清理回调

    def find(self, pattern: str) -> list[DataFile]:
        """按相对路径前缀匹配文件（如 'recipes/'）"""
        pattern = pattern.replace("\\", "/")
        return [
            f for f in self.files
            if f.relative_path.replace("\\", "/").startswith(pattern)
        ]

    def find_one(self, name: str) -> Optional[DataFile]:
        """按文件名查找唯一文件（如 'ingredients.json'）"""
        for f in self.files:
            if f.name == name:
                return f
        return None

    def cleanup_temp(self):
        """执行清理（如果有）"""
        if self.cleanup:
            self.cleanup()
        elif self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)


class DataSource:
    """输入源基类——所有输入源实现此接口。"""
    def collect_files(self) -> FileCollection:
        """获取原始文件集合。"""
        raise NotImplementedError


@dataclass
class ImportResult:
    """导入操作的统计结果"""
    stats: dict[str, int] = field(default_factory=dict)   # {"recipes": 5, "ingredients": 3, ...}
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped: dict[str, int] = field(default_factory=dict)  # 按桶/原因计数，如 {"blacklist_groups": 3}


class Importer:
    """导入器基类。"""
    def __init__(self, db, user_id: int, is_admin: bool = False):
        self.db = db
        self.user_id = user_id
        self.is_admin = is_admin

    def import_all(
        self,
        collection: FileCollection,
        progress_callback: Optional[Callable] = None,
    ) -> ImportResult:
        """将文件集合中的数据导入数据库。

        progress_callback(stage, current, total, message="") 可选，用于回报
        导入进度。子类应在阶段边界与长循环中调用它，否则前端只能看到转圈、
        感知不到进度（大包导入可能持续数十秒到几分钟）。
        """
        raise NotImplementedError
