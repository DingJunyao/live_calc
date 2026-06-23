"""数据格式自动检测。"""
import json
import os

from app.services.importer.models import FileCollection, FormatType


class FormatDetector:
    """根据文件集合的结构自动识别数据格式。"""

    # 系统导出格式的标志文件
    EXPORT_MANIFEST = "manifest.json"

    # HowToCook_json 格式的标志文件
    HOWTOCOOK_INGREDIENTS = "ingredients.json"

    @classmethod
    def detect(cls, collection: FileCollection) -> FormatType:
        """检测文件集合的数据格式。"""
        json_files = [f for f in collection.files if f.name.endswith(".json")]

        # 检查是否包含 manifest.json（系统导出格式）
        if cls._has_manifest(json_files):
            return FormatType.EXPORT

        # 检查是否包含 ingredients.json + 菜谱 JSON
        if cls._has_ingredients_and_recipes(json_files):
            return FormatType.HOWTOCOOK_JSON

        return FormatType.UNKNOWN

    @classmethod
    def _has_manifest(cls, json_files: list) -> bool:
        """检查是否有含 version 字段的 manifest.json。"""
        manifest = cls._find_by_name(json_files, cls.EXPORT_MANIFEST)
        if not manifest:
            return False
        try:
            with open(manifest.absolute_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return "format_version" in data
        except (json.JSONDecodeError, IOError):
            return False

    @classmethod
    def _has_ingredients_and_recipes(cls, json_files: list) -> bool:
        """检查是否有 ingredients.json 和至少一个菜谱 JSON。"""
        has_ingredients = cls._find_by_name(json_files, cls.HOWTOCOOK_INGREDIENTS)
        if not has_ingredients:
            return False
        non_recipe = {"ingredients.json", "ingredients_raw.json",
                      "nutritions.json", "matched_ingredients.json",
                      "units.json"}
        recipe_files = [f for f in json_files
                        if f.name not in non_recipe]
        return len(recipe_files) > 0

    @staticmethod
    def _find_by_name(files: list, name: str):
        """在文件列表中按 name 字段查找。"""
        for f in files:
            if f.name == name:
                return f
        return None
