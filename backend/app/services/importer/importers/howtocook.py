"""HowToCook_json 格式导入器。"""
import json
import os
import shutil
from pathlib import Path
from typing import Optional

from app.models.ingredient_category import IngredientCategory
from app.models.nutrition import Ingredient
from app.models.product_entity import Product
from app.models.recipe import Recipe, RecipeIngredient
from app.services.importer.models import Importer, ImportResult, FileCollection
from app.services.unit_conversion_service import UnitConversionService
from app.services.unit_matcher import UnitMatcher


# 不属于菜谱的文件名
NON_RECIPE_FILES = {
    "ingredients.json", "ingredients_raw.json",
    "nutritions.json", "matched_ingredients.json", "units.json",
}

# 分类映射
CATEGORY_MAPPING = {
    "谷物": "grains", "主食/谷物": "grains", "淀粉/粉类": "grains",
    "肉类": "meat", "蔬菜": "vegetables", "水果": "fruits",
    "海鲜": "seafood", "水产": "seafood", "禽蛋": "eggs",
    "乳制品": "dairy", "豆制品": "soy",
    "调味品": "seasoning", "调料": "seasoning", "油脂": "oil",
    "坚果": "nuts", "饮品": "beverages",
    "干货": "others", "菌菇": "others", "糖/蜂蜜": "others", "其他": "others",
    "grains": "grains", "meat": "meat", "vegetables": "vegetables",
    "fruits": "fruits", "seafood": "seafood", "eggs": "eggs",
    "dairy": "dairy", "soy": "soy", "seasoning": "seasoning",
    "oil": "oil", "nuts": "nuts", "beverages": "beverages", "others": "others",
}


class HowToCookImporter(Importer):
    """HowToCook_json 格式导入器。"""

    IMAGES_DIR = Path(__file__).parent.parent.parent.parent / "static" / "images" / "recipes"

    def __init__(self, db, user_id: int = 1):
        super().__init__(db, user_id)
        self.unit_matcher = UnitMatcher(db)
        self.result = ImportResult()
        self.IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    def import_all(self, collection: FileCollection) -> ImportResult:
        self.result = ImportResult()

        # 1. 导入单位
        self._import_units(collection)

        # 2. 导入原料
        self._import_ingredients(collection)

        # 3. 导入菜谱
        self._import_recipes(collection)

        self.db.commit()
        return self.result

    def _import_units(self, collection: FileCollection):
        unit_file = collection.find_one("units.json")
        if not unit_file:
            return

        with open(unit_file.absolute_path, "r", encoding="utf-8") as f:
            units_data = json.load(f)

        imported = 0
        for item in units_data:
            name = item.get("name", "").strip()
            if not name:
                continue
            aliases = item.get("aliases", [])
            existing, is_new = self.unit_matcher.match_unit(name)
            if existing:
                for alias in aliases:
                    if alias and alias not in self.unit_matcher.unit_cache:
                        self.unit_matcher.unit_cache[alias] = existing
                if is_new:
                    imported += 1
            else:
                self.result.warnings.append(f"无法创建单位: {name}")

        self.result.stats["units"] = imported

    def _import_ingredients(self, collection: FileCollection):
        ing_file = collection.find_one("ingredients.json")
        if not ing_file:
            return

        with open(ing_file.absolute_path, "r", encoding="utf-8") as f:
            ingredients_data = json.load(f)

        categories = {cat.name: cat
                      for cat in self.db.query(IngredientCategory).all()}

        imported = 0
        for key, item in ingredients_data.items():
            ing_name = item.get("name", "").strip() or key.strip()
            if not ing_name:
                continue

            existing = self.db.query(Ingredient).filter(
                Ingredient.name == ing_name
            ).first()
            if existing:
                continue

            category_name = item.get("category", "others")
            mapped = CATEGORY_MAPPING.get(category_name, category_name)
            category = categories.get(mapped) or categories.get(category_name)

            unit_obj = self.unit_matcher.match_or_create_unit("斤")

            ingredient = Ingredient(
                name=ing_name,
                aliases=item.get("aliases", []),
                category_id=category.id if category else None,
                default_unit_id=unit_obj.id if unit_obj else None,
                is_imported=True,
            )
            self.db.add(ingredient)
            self.db.flush()

            # 自动创建同名商品
            existing_product = self.db.query(Product).filter(
                Product.name == ing_name,
                Product.is_active == True,
            ).first()
            if not existing_product:
                self.db.add(Product(
                    name=ing_name,
                    ingredient_id=ingredient.id,
                    created_by=self.user_id,
                    updated_by=self.user_id,
                    is_active=True,
                ))
                self.db.flush()

            imported += 1

        self.result.stats["ingredients"] = imported

    def _import_recipes(self, collection: FileCollection):
        recipe_files = [f for f in collection.files
                        if f.name.endswith(".json")
                        and f.name not in NON_RECIPE_FILES]

        imported = 0
        for rf in recipe_files:
            try:
                with open(rf.absolute_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                self.result.warnings.append(
                    f"跳过无效 JSON 文件 {rf.relative_path}: {e}"
                )
                continue

            name = data.get("name", "").strip()
            if not name:
                continue

            existing = self.db.query(Recipe).filter(Recipe.name == name).first()
            if existing:
                continue

            ingredients = data.get("ingredients", [])
            steps = data.get("steps", [])
            if not ingredients or not steps:
                continue

            # 处理图片
            images = []
            for img in data.get("images", []):
                local_path = self._download_image(img, rf.dirname)
                images.append(local_path or img)

            recipe = Recipe(
                name=name,
                source="json_repo",
                category=data.get("category"),
                user_id=self.user_id,
                tags=[data.get("category")] if data.get("category") else [],
                cooking_steps=steps,
                total_time_minutes=data.get("total_time_minutes"),
                difficulty=data.get("difficulty", "simple"),
                servings=data.get("servings", 1),
                tips=data.get("tips", []),
                description=data.get("description", ""),
                images=images,
            )
            self.db.add(recipe)
            self.db.flush()

            for ing_data in ingredients:
                self._add_recipe_ingredient(recipe, ing_data)

            imported += 1

        self.result.stats["recipes"] = imported

    def _download_image(self, image_path: str, recipe_dir: str) -> Optional[str]:
        """从本地文件复制图片到 static 目录。"""
        if not recipe_dir:
            return None
        img_file = os.path.join(recipe_dir, image_path)
        if not os.path.exists(img_file):
            return None
        filename = os.path.basename(image_path)
        local_path = self.IMAGES_DIR / filename
        if local_path.exists():
            return f"/static/images/recipes/{filename}"
        shutil.copy2(img_file, local_path)
        return f"/static/images/recipes/{filename}"

    def _add_recipe_ingredient(self, recipe: Recipe, ing_data: dict):
        """添加菜谱原料。"""
        ing_name = ing_data.get("ingredient_name", "").strip()
        if not ing_name:
            return

        ingredient = self._find_ingredient(ing_name)
        if not ingredient:
            unit_obj = self.unit_matcher.match_or_create_unit("斤")
            ingredient = Ingredient(
                name=ing_name,
                is_imported=True,
                default_unit_id=unit_obj.id if unit_obj else None,
            )
            self.db.add(ingredient)
            self.db.flush()

        unit_str = ing_data.get("unit", "")
        unit_obj = self.unit_matcher.match_or_create_unit(unit_str) if unit_str else None

        raw_qty = ing_data.get("quantity")
        qty_range = ing_data.get("quantity_range")
        original_qty = ing_data.get("original_quantity")
        qty_desc = ing_data.get("quantity_description", "")
        if not original_qty and qty_desc:
            original_qty = qty_desc

        ri = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            quantity=str(raw_qty) if raw_qty is not None else None,
            quantity_range=qty_range,
            unit_id=unit_obj.id if unit_obj else None,
            is_optional=ing_data.get("is_optional", False),
            note=ing_data.get("note"),
            original_quantity=original_qty,
        )
        self.db.add(ri)

        # 自动创建实体单位覆盖
        if unit_obj and ingredient:
            ucs = UnitConversionService(self.db)
            ucs.auto_create_entity_override(
                "ingredient", ingredient.id, unit_obj.abbreviation
            )

    def _find_ingredient(self, name: str) -> Optional[Ingredient]:
        """按名称或别名查找原料。"""
        ingredient = self.db.query(Ingredient).filter(
            Ingredient.name == name
        ).first()
        if ingredient:
            return ingredient

        candidates = self.db.query(Ingredient).filter(
            Ingredient.aliases.isnot(None),
            Ingredient.aliases != "[]",
        ).all()
        for c in candidates:
            if c.aliases and name in c.aliases:
                return c
        return None
