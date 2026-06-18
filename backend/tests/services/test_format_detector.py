"""测试格式检测器。"""
import json
import os
import tempfile

from app.services.importer.detectors.format_detector import FormatDetector
from app.services.importer.models import FileCollection, DataFile, FormatType


def _make_file(collection: FileCollection, rel_path: str, content: str):
    """在临时目录下创建测试文件。"""
    abspath = os.path.join(collection.temp_dir, rel_path.replace("/", os.sep))
    os.makedirs(os.path.dirname(abspath), exist_ok=True)
    with open(abspath, "w", encoding="utf-8") as f:
        f.write(content)
    collection.files.append(DataFile(
        relative_path=rel_path,
        absolute_path=abspath,
        size=len(content.encode()),
    ))


def test_detect_export_format():
    """检测到 manifest.json 时应返回 export。"""
    with tempfile.TemporaryDirectory() as tmp:
        collection = FileCollection(temp_dir=tmp)
        _make_file(collection, "manifest.json",
                    json.dumps({"version": "1.0", "scope": "full", "counts": {}}))
        _make_file(collection, "units.json", "[]")

        assert FormatDetector.detect(collection) == FormatType.EXPORT


def test_detect_howtocook_format():
    """检测到 ingredients.json + 菜谱 JSON 时应返回 howtocook_json。"""
    with tempfile.TemporaryDirectory() as tmp:
        collection = FileCollection(temp_dir=tmp)
        _make_file(collection, "ingredients.json",
                    json.dumps({"鸡蛋": {"name": "鸡蛋", "category": "禽蛋"}}))
        _make_file(collection, "西红柿炒鸡蛋.json",
                    json.dumps({"name": "西红柿炒鸡蛋", "ingredients": [], "steps": []}))

        assert FormatDetector.detect(collection) == FormatType.HOWTOCOOK_JSON


def test_detect_unknown_format():
    """空文件夹或不匹配的结构应返回 unknown。"""
    with tempfile.TemporaryDirectory() as tmp:
        collection = FileCollection(temp_dir=tmp)
        _make_file(collection, "readme.txt", "hello")
        assert FormatDetector.detect(collection) == FormatType.UNKNOWN


def test_detect_export_with_extra_files():
    """即使同时有 ingredients.json 和 manifest.json，也应优先识别为 export。"""
    with tempfile.TemporaryDirectory() as tmp:
        collection = FileCollection(temp_dir=tmp)
        _make_file(collection, "manifest.json",
                    json.dumps({"version": "1.0", "scope": "full", "counts": {}}))
        _make_file(collection, "ingredients.json",
                    json.dumps({"鸡蛋": {"name": "鸡蛋"}}))
        _make_file(collection, "西红柿炒鸡蛋.json",
                    json.dumps({"name": "西红柿炒鸡蛋", "ingredients": [], "steps": []}))

        assert FormatDetector.detect(collection) == FormatType.EXPORT
