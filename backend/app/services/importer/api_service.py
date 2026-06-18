"""导入 API 编排服务——协调输入源、格式检测、导入器和 AI 后处理。"""
import os
import tempfile
from typing import Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.services.importer.models import FileCollection, FormatType, ImportResult
from app.services.importer.sources.local_fs import LocalDirSource, UploadArchiveSource
from app.services.importer.sources.git_repo import GitRepoSource
from app.services.importer.detectors.format_detector import FormatDetector
from app.services.importer.importers.howtocook import HowToCookImporter
from app.services.importer.importers.export import ExportImporter


def import_from_git_repo(db: Session, user_id: int) -> ImportResult:
    """从 git 仓库导入（启动时或管理员触发）。"""
    source = GitRepoSource()
    collection = source.collect_files()
    fmt = FormatDetector.detect(collection)

    if fmt == FormatType.HOWTOCOOK_JSON:
        importer = HowToCookImporter(db, user_id=user_id)
    elif fmt == FormatType.EXPORT:
        importer = ExportImporter(db, user_id=user_id)
    else:
        raise ValueError(f"无法识别的数据格式: {fmt}")

    result = importer.import_all(collection)
    collection.cleanup_temp()
    return result


def import_from_local_dir(db: Session, local_path: str,
                           user_id: int) -> ImportResult:
    """从本地目录导入。"""
    source = LocalDirSource(local_path)
    collection = source.collect_files()
    fmt = FormatDetector.detect(collection)

    if fmt == FormatType.HOWTOCOOK_JSON:
        importer = HowToCookImporter(db, user_id=user_id)
    elif fmt == FormatType.EXPORT:
        importer = ExportImporter(db, user_id=user_id)
    else:
        raise ValueError(f"无法识别的数据格式: {fmt}")

    return importer.import_all(collection)


def import_from_upload(db: Session, file: UploadFile,
                        user_id: int, is_admin: bool) -> ImportResult:
    """从上传的压缩包导入。"""
    suffix = os.path.splitext(file.filename or "upload.zip")[1] or ".zip"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    collection = None
    try:
        content = file.read()
        tmp.write(content)
        tmp.close()

        source = UploadArchiveSource(tmp.name)
        collection = source.collect_files()
        fmt = FormatDetector.detect(collection)

        if fmt == FormatType.HOWTOCOOK_JSON and not is_admin:
            raise PermissionError("仅管理员可导入 HowToCook 格式数据")

        if fmt == FormatType.HOWTOCOOK_JSON:
            importer = HowToCookImporter(db, user_id=user_id)
        elif fmt == FormatType.EXPORT:
            importer = ExportImporter(db, user_id=user_id)
        else:
            raise ValueError("无法识别的数据格式，支持 HowToCook_json 和系统导出格式")

        result = importer.import_all(collection)
        return result
    finally:
        if collection:
            try:
                collection.cleanup_temp()
            except Exception:
                pass
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
