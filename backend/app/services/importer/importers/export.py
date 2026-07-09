"""系统导出格式导入器。"""
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.models.entity_density import EntityDensity
from app.models.ingredient_category import IngredientCategory
from app.models.ingredient_hierarchy import IngredientHierarchy
from app.models.merchant import Merchant
from app.models.user_place import UserPlace
from app.models.nutrition import Ingredient
from app.models.nutrition_data import NutritionData
from app.models.product import ProductRecord
from app.models.product_barcode import ProductBarcode
from app.models.product_entity import Product
from app.models.product_ingredient_link import ProductIngredientLink
from app.models.recipe import Recipe, RecipeIngredient
from app.models.unit import UnitConversion
from app.services.importer.models import Importer, ImportResult, FileCollection
from app.services.unit_matcher import UnitMatcher


class ReferenceMapping:
    """旧 ID → 新 ID 的映射表。"""
    def __init__(self):
        self.ingredients: dict[int, int] = {}
        self.recipes: dict[int, int] = {}
        self.products: dict[int, int] = {}
        self.merchants: dict[int, int] = {}
        self.units: dict[int, int] = {}
        self.categories: dict[int, int] = {}


class ExportImporter(Importer):
    """从系统导出 ZIP 导入数据。"""

    IMAGES_DIR = Path(__file__).parent.parent.parent.parent.parent / "static" / "images" / "recipes"

    def __init__(self, db, user_id: int):
        super().__init__(db, user_id)
        self.unit_matcher = UnitMatcher(db)
        self.mapping = ReferenceMapping()
        self.result = ImportResult()
        self.IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    def import_all(self, collection: FileCollection) -> ImportResult:
        self.result = ImportResult()

        try:
            self._import_units(collection)
            self._import_unit_conversions(collection)
            self._import_ingredient_categories(collection)
            self._import_ingredients(collection)
            self._import_entity_densities(collection)
            self._import_nutritions(collection)
            self._import_ingredient_hierarchy(collection)
            self._import_recipes(collection)
            self._import_products(collection)
            self._import_product_barcodes(collection)
            self._import_product_links(collection)
            self._import_merchants(collection)
            self._import_user_places(collection)
            self._import_price_records(collection)
            self._import_images(collection)

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            self.result.stats = {}  # 回滚后统计无意义，清空
            self.result.errors.append(f"导入过程出错: {str(e)}")

        return self.result

    def _load_json(self, collection: FileCollection, filename: str):
        """从文件集合中加载 JSON 文件。"""
        f = collection.find_one(filename)
        if not f:
            return None
        with open(f.absolute_path, "r", encoding="utf-8") as fp:
            return json.load(fp)

    def _match_ingredient_by_name(self, name: str) -> Optional[Ingredient]:
        return self.db.query(Ingredient).filter(
            Ingredient.name == name,
            Ingredient.is_active == True,
        ).first()

    def _match_recipe_by_name(self, name: str) -> Optional[Recipe]:
        return self.db.query(Recipe).filter(
            Recipe.name == name,
            Recipe.is_active == True,
        ).first()

    def _match_merchant_by_name(self, name: str) -> Optional[Merchant]:
        return self.db.query(Merchant).filter(
            Merchant.name == name,
            Merchant.is_open == True,
        ).first()

    def _import_units(self, collection):
        data = self._load_json(collection, "units.json")
        if not data:
            return
        imported = 0
        for item in data:
            name = item.get("name", "").strip()
            if not name:
                continue
            existing, is_new = self.unit_matcher.match_unit(name)
            if existing:
                if is_new:
                    imported += 1
                old_id = item.get("id")
                if old_id:
                    self.mapping.units[old_id] = existing.id
        self.result.stats["units"] = imported

    def _import_unit_conversions(self, collection):
        data = self._load_json(collection, "unit_conversions.json")
        if not data:
            return
        imported = 0
        for item in data:
            from_unit_id = item.get("from_unit_id")
            to_unit_id = item.get("to_unit_id")
            if not from_unit_id or not to_unit_id:
                continue
            mapped_from = self.mapping.units.get(from_unit_id)
            mapped_to = self.mapping.units.get(to_unit_id)
            if not mapped_from or not mapped_to:
                continue
            conversion_factor = item.get("conversion_factor")
            if not conversion_factor:
                continue
            existing = self.db.query(UnitConversion).filter(
                UnitConversion.from_unit_id == mapped_from,
                UnitConversion.to_unit_id == mapped_to,
            ).first()
            if existing:
                continue
            self.db.add(UnitConversion(
                from_unit_id=mapped_from,
                to_unit_id=mapped_to,
                conversion_factor=conversion_factor,
            ))
            imported += 1
        self.result.stats["unit_conversions"] = imported

    def _import_ingredient_categories(self, collection):
        data = self._load_json(collection, "ingredient_categories.json")
        if not data:
            return
        imported = 0
        cats = {c.name: c for c in self.db.query(IngredientCategory).all()}
        for item in data:
            name = item.get("name", "").strip()
            if not name:
                continue
            if name in cats:
                old_id = item.get("id")
                if old_id:
                    self.mapping.categories[old_id] = cats[name].id
                continue
            c = IngredientCategory(
                name=name,
                display_name=item.get("display_name", name),
            )
            self.db.add(c)
            self.db.flush()
            imported += 1
            cats[name] = c
            old_id = item.get("id")
            if old_id:
                self.mapping.categories[old_id] = c.id
        self.result.stats["ingredient_categories"] = imported

    def _import_ingredients(self, collection):
        data = self._load_json(collection, "ingredients.json")
        if not data:
            return
        imported = 0
        skipped = 0
        items = data if isinstance(data, list) else data.values()
        for item in items:
            name = item.get("name", "").strip() if isinstance(item, dict) else ""
            if not name:
                continue
            existing = self._match_ingredient_by_name(name)
            if existing:
                skipped += 1
                old_id = item.get("id")
                if old_id:
                    self.mapping.ingredients[old_id] = existing.id
                density_val = item.get("density")
                if density_val is not None and existing.density is None:
                    existing.density = density_val
                continue
            ingredient = Ingredient(
                name=name,
                aliases=item.get("aliases", []),
                category_id=self.mapping.categories.get(item.get("category_id")),
                density=item.get("density"),
                is_imported=item.get("is_imported", False),
            )
            self.db.add(ingredient)
            self.db.flush()
            imported += 1
            old_id = item.get("id")
            if old_id:
                self.mapping.ingredients[old_id] = ingredient.id
        self.result.stats["ingredients"] = imported

    def _import_entity_densities(self, collection):
        """导入实体密度数据。

        导出格式使用 EntityDensity 模型（entity_type/entity_id/density），
        与已废弃的 IngredientDensity 不同。
        """
        data = self._load_json(collection, "entity_densities.json")
        if not data:
            return
        imported = 0
        for item in data:
            entity_type = item.get("entity_type", "")
            old_entity_id = item.get("entity_id")
            if not entity_type or not old_entity_id:
                continue
            if entity_type == "ingredient":
                new_entity_id = self.mapping.ingredients.get(old_entity_id)
            elif entity_type == "product":
                new_entity_id = self.mapping.products.get(old_entity_id)
            else:
                continue
            if not new_entity_id:
                continue
            condition = item.get("condition", "")
            existing = self.db.query(EntityDensity).filter(
                EntityDensity.entity_type == entity_type,
                EntityDensity.entity_id == new_entity_id,
                EntityDensity.condition == condition,
                EntityDensity.is_active.is_(True),
            ).first()
            if existing:
                continue
            self.db.add(EntityDensity(
                entity_type=entity_type,
                entity_id=new_entity_id,
                density=item.get("density"),
                temperature=item.get("temperature"),
                condition=condition,
                source=item.get("source", "import"),
                confidence=item.get("confidence", 1.0),
            ))
            imported += 1
        self.result.stats["entity_densities"] = imported

    def _import_nutritions(self, collection):
        data = self._load_json(collection, "nutritions.json")
        if not data:
            return
        imported = 0
        items = data if isinstance(data, list) else data.values()
        for item in items:
            old_ing_id = item.get("ingredient_id")
            new_ing_id = self.mapping.ingredients.get(old_ing_id) if old_ing_id else None
            if not new_ing_id:
                continue
            existing = self.db.query(NutritionData).filter(
                NutritionData.ingredient_id == new_ing_id,
            ).first()
            if existing:
                continue
            self.db.add(NutritionData(
                ingredient_id=new_ing_id,
                nutrients=item.get("raw_nutrients") or item.get("nutrients", {}),
                source=item.get("source", "import"),
                is_verified=item.get("is_verified", False),
            ))
            imported += 1
        self.result.stats["nutritions"] = imported

    def _import_ingredient_hierarchy(self, collection):
        data = self._load_json(collection, "ingredient_hierarchy.json")
        if not data:
            return
        imported = 0
        for item in data:
            parent_id = self.mapping.ingredients.get(item.get("parent_id"))
            child_id = self.mapping.ingredients.get(item.get("child_id"))
            if not parent_id or not child_id:
                continue
            existing = self.db.query(IngredientHierarchy).filter(
                IngredientHierarchy.parent_id == parent_id,
                IngredientHierarchy.child_id == child_id,
            ).first()
            if existing:
                continue
            self.db.add(IngredientHierarchy(
                parent_id=parent_id,
                child_id=child_id,
                relation_type=item.get("relation_type", "substitute"),
            ))
            imported += 1
        self.result.stats["ingredient_hierarchy"] = imported

    def _import_recipes(self, collection):
        recipe_files = collection.find("recipes/")
        if not recipe_files:
            return
        imported = 0
        for rf in recipe_files:
            with open(rf.absolute_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            name = data.get("name", "").strip()
            if not name:
                continue
            existing = self._match_recipe_by_name(name)
            if existing:
                old_id = data.get("id")
                if old_id:
                    self.mapping.recipes[old_id] = existing.id
                continue

            recipe = Recipe(
                name=name,
                source="import",
                is_public=True,  # 导入菜谱默认公共
                category=data.get("category"),
                user_id=self.user_id,
                tags=data.get("tags", []),
                cooking_steps=data.get("steps") or data.get("cooking_steps", []),
                total_time_minutes=data.get("total_time_minutes"),
                difficulty=data.get("difficulty", "simple"),
                servings=data.get("servings", 1),
                tips=data.get("tips", []),
                description=data.get("description", ""),
                images=self._restore_image_paths(data.get("images", [])),
            )
            self.db.add(recipe)
            self.db.flush()
            imported += 1
            old_id = data.get("id")
            if old_id:
                self.mapping.recipes[old_id] = recipe.id

            for ing_data in data.get("ingredients", []):
                old_ing_id = ing_data.get("ingredient_id")
                new_ing_id = self.mapping.ingredients.get(old_ing_id) if old_ing_id else None
                if not new_ing_id:
                    ing = self._match_ingredient_by_name(ing_data.get("ingredient_name", ""))
                    new_ing_id = ing.id if ing else None
                if not new_ing_id:
                    continue
                old_unit_id = ing_data.get("unit_id")
                new_unit_id = self.mapping.units.get(old_unit_id) if old_unit_id else None
                ri = RecipeIngredient(
                    recipe_id=recipe.id,
                    ingredient_id=new_ing_id,
                    quantity=ing_data.get("quantity"),
                    quantity_range=ing_data.get("quantity_range"),
                    unit_id=new_unit_id,
                    is_optional=ing_data.get("is_optional", False),
                    note=ing_data.get("note"),
                    original_quantity=ing_data.get("original_quantity"),
                )
                self.db.add(ri)
        self.result.stats["recipes"] = imported

    def _import_products(self, collection):
        data = self._load_json(collection, "products.json")
        if not data:
            return
        imported = 0
        items = data if isinstance(data, list) else data.values()
        for item in items:
            name = item.get("name", "").strip()
            if not name:
                continue
            ing_id = self.mapping.ingredients.get(item.get("ingredient_id"))
            # 映射表未命中时，尝试按名字查找原料
            if not ing_id:
                ing_name = item.get("ingredient_name", "").strip()
                if ing_name:
                    matched = self._match_ingredient_by_name(ing_name)
                    if matched:
                        ing_id = matched.id
                # 退而求其次：用商品名找同名原料
                if not ing_id:
                    matched = self._match_ingredient_by_name(name)
                    if matched:
                        ing_id = matched.id
            if not ing_id:
                self.result.warnings.append(
                    f"商品「{name}」缺少关联原料，已跳过"
                )
                continue
            existing = self.db.query(Product).filter(
                Product.name == name,
                Product.is_active == True,
            ).first()
            if existing:
                old_id = item.get("id")
                if old_id:
                    self.mapping.products[old_id] = existing.id
                continue
            product = Product(
                name=name,
                ingredient_id=ing_id,
                brand=item.get("brand"),
                aliases=item.get("aliases", []),
                tags=item.get("tags", []),
                is_active=True,
                created_by=self.user_id,
                updated_by=self.user_id,
            )
            self.db.add(product)
            self.db.flush()
            imported += 1
            old_id = item.get("id")
            if old_id:
                self.mapping.products[old_id] = product.id
        self.result.stats["products"] = imported

    def _import_product_barcodes(self, collection):
        data = self._load_json(collection, "product_barcodes.json")
        if not data:
            return
        imported = 0
        for item in data:
            old_prod_id = item.get("product_id")
            new_prod_id = self.mapping.products.get(old_prod_id)
            if not new_prod_id:
                continue
            barcode = item.get("barcode", "").strip()
            if not barcode:
                continue
            existing = self.db.query(ProductBarcode).filter(
                ProductBarcode.barcode == barcode,
            ).first()
            if existing:
                continue
            self.db.add(ProductBarcode(
                product_id=new_prod_id,
                barcode=barcode,
                barcode_type=item.get("barcode_type", "internal"),
                is_primary=item.get("is_primary", False),
            ))
            imported += 1
        self.result.stats["product_barcodes"] = imported

    def _import_product_links(self, collection):
        data = self._load_json(collection, "product_ingredient_links.json")
        if not data:
            return
        imported = 0
        for item in data:
            old_prod_id = item.get("product_id")
            old_ing_id = item.get("ingredient_id")
            new_prod_id = self.mapping.products.get(old_prod_id)
            new_ing_id = self.mapping.ingredients.get(old_ing_id)
            if not new_prod_id or not new_ing_id:
                continue
            existing = self.db.query(ProductIngredientLink).filter(
                ProductIngredientLink.product_id == new_prod_id,
                ProductIngredientLink.ingredient_id == new_ing_id,
            ).first()
            if existing:
                continue
            self.db.add(ProductIngredientLink(
                product_id=new_prod_id,
                ingredient_id=new_ing_id,
            ))
            imported += 1
        self.result.stats["product_links"] = imported

    def _import_merchants(self, collection):
        data = self._load_json(collection, "merchants.json")
        if not data:
            return
        imported = 0
        for item in data:
            name = item.get("name", "").strip()
            if not name:
                continue
            existing = self._match_merchant_by_name(name)
            if existing:
                old_id = item.get("id")
                if old_id:
                    self.mapping.merchants[old_id] = existing.id
                # 同步更新营业状态
                if "is_open" in item:
                    existing.is_open = item["is_open"]
                continue
            merchant = Merchant(
                name=name,
                user_id=self.user_id,
                address=item.get("address"),
                latitude=item.get("latitude"),
                longitude=item.get("longitude"),
                is_open=item.get("is_open", True),
            )
            self.db.add(merchant)
            self.db.flush()
            imported += 1
            old_id = item.get("id")
            if old_id:
                self.mapping.merchants[old_id] = merchant.id
        self.result.stats["merchants"] = imported

    def _import_user_places(self, collection):
        """导入用户常用地点（家/公司等）。"""
        data = self._load_json(collection, "user_places.json")
        if not data:
            return
        imported = 0
        for item in data:
            name = item.get("name", "").strip()
            if not name:
                continue
            existing = self.db.query(UserPlace).filter(
                UserPlace.name == name,
                UserPlace.user_id == self.user_id,
            ).first()
            if existing:
                continue
            self.db.add(UserPlace(
                user_id=self.user_id,
                name=name,
                kind=item.get("kind", "custom"),
                latitude=item.get("latitude", 0),
                longitude=item.get("longitude", 0),
                address=item.get("address"),
                is_default=item.get("is_default", False),
                sort_order=item.get("sort_order", 0),
            ))
            imported += 1
        self.result.stats["user_places"] = imported

    @staticmethod
    def _restore_image_paths(images: list) -> list:
        """将导出时的相对图片路径还原为本地 /static/... 路径。

        导出时 convert_image_path 把 /static/ 前缀去掉 → images/recipes/xxx.jpg。
        导入时反向：images/xxx → /static/images/xxx；外链 http(s):// 原样保留。
        """
        result = []
        for img in images:
            if not isinstance(img, str):
                result.append(img)
            elif img.startswith(("http://", "https://")):
                result.append(img)
            else:
                result.append("/static/" + img)
        return result

    @staticmethod
    def _parse_iso_datetime(value):
        """将 ISO 8601 字符串解析为 timezone-aware datetime。"""
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        dt = datetime.fromisoformat(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def _import_price_records(self, collection):
        data = self._load_json(collection, "price_records.json")
        if not data:
            return
        imported = 0
        for item in data:
            old_prod_id = item.get("product_id")
            old_mer_id = item.get("merchant_id")
            new_prod_id = self.mapping.products.get(old_prod_id) if old_prod_id else None
            new_mer_id = self.mapping.merchants.get(old_mer_id) if old_mer_id else None
            if not new_prod_id:
                continue

            old_orig_unit = item.get("original_unit_id")
            old_std_unit = item.get("standard_unit_id")
            new_orig_unit_id = self.mapping.units.get(old_orig_unit) if old_orig_unit else None
            new_std_unit_id = self.mapping.units.get(old_std_unit) if old_std_unit else None

            rec = ProductRecord(
                user_id=self.user_id,
                product_id=new_prod_id,
                product_name=item.get("product_name", ""),
                merchant_id=new_mer_id,
                price=item.get("price", 0),
                currency=item.get("currency", "CNY"),
                original_quantity=item.get("original_quantity", 1),
                original_unit_id=new_orig_unit_id,
                standard_quantity=item.get("standard_quantity", 1),
                standard_unit_id=new_std_unit_id,
                record_type=item.get("record_type", "price"),
                recorded_at=self._parse_iso_datetime(item.get("recorded_at")),
                notes=item.get("notes"),
            )
            self.db.add(rec)
            imported += 1
        self.result.stats["price_records"] = imported

    def _import_images(self, collection):
        image_files = collection.find("images/")
        imported = 0
        for img in image_files:
            dest = self.IMAGES_DIR / img.name
            if dest.exists():
                continue
            try:
                shutil.copy2(img.absolute_path, dest)
                imported += 1
            except OSError:
                pass
        self.result.stats["images"] = imported
