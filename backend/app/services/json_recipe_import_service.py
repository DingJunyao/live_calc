"""
从外部 JSON 仓库导入菜谱和原料的服务
"""
import json
import os
import tempfile
import zipfile
import requests
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.recipe import Recipe, RecipeIngredient
from app.models.nutrition import Ingredient
from app.models.ingredient_category import IngredientCategory
from app.services.unit_matcher import UnitMatcher
from sqlalchemy.exc import IntegrityError


class JsonRecipeImportService:
    """从 JSON 仓库导入菜谱和原料"""

    # 外部仓库 URL
    REPO_URL = "https://github.com/DingJunyao/HowToCook_json"
    REPO_ZIP_URL = "https://github.com/DingJunyao/HowToCook_json/archive/refs/heads/main.zip"
    REPO_RAW_BASE = "https://raw.githubusercontent.com/DingJunyao/HowToCook_json/main/out"

    # 本地静态文件目录
    STATIC_DIR = Path(__file__).parent.parent.parent / "static"
    IMAGES_DIR = STATIC_DIR / "images" / "recipes"

    # 分类映射
    CATEGORY_MAPPING = {
        "meat": "meat",
        "vegetables": "vegetables",
        "fruits": "fruits",
        "seafood": "seafood",
        "eggs": "eggs",
        "dairy": "dairy",
        "seasoning": "seasoning",
        "oil": "oil",
        "nuts": "nuts",
        "beverages": "beverages",
        "others": "others",
    }

    def __init__(self, db: Session, user_id: Optional[int] = None):
        self.db = db
        self.user_id = user_id or 1  # 默认使用用户 ID 1
        self.unit_matcher = UnitMatcher(db)
        # 确保图片目录存在（包括 recipes 子目录）
        self.IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    def _download_image(self, image_path: str, out_dir: str) -> Optional[str]:
        """
        下载图片到本地
        :param image_path: 原始图片路径（如 images/xxx.jpg）
        :param out_dir: 临时解压目录
        :return: 本地图片路径（如 /static/images/recipes/xxx.jpg）
        """
        try:
            # 获取文件名
            if image_path.startswith("images/"):
                filename = image_path[7:]
            else:
                filename = image_path

            # 检查临时目录中是否有该图片
            temp_image_path = os.path.join(out_dir, image_path)
            if not os.path.exists(temp_image_path):
                print(f"图片不存在，跳过: {image_path}")
                return None

            # 检查本地是否已存在该图片
            local_image_path = self.IMAGES_DIR / filename
            if local_image_path.exists():
                print(f"图片已存在，跳过下载: {filename}")
                return f"/static/images/recipes/{filename}"

            # 下载图片到本地
            shutil.copy2(temp_image_path, local_image_path)
            print(f"已下载图片: {filename}")

            return f"/static/images/recipes/{filename}"

        except Exception as e:
            print(f"下载图片失败 {image_path}: {str(e)}")
            return None

    def import_all(self) -> Dict[str, any]:
        """
        导入所有数据（原料和菜谱）
        """
        print("开始从 JSON 仓库导入数据...")

        results = {
            "ingredients": {"imported": 0, "skipped": 0, "failed": 0},
            "recipes": {"imported": 0, "skipped": 0, "failed": 0},
            "errors": []
        }

        try:
            # 1. 先导入原料
            print("1. 开始导入原料...")
            ingredients_result = self._import_ingredients()
            results["ingredients"] = ingredients_result

            # 2. 再导入菜谱
            print("2. 开始导入菜谱...")
            recipes_result = self._import_recipes()
            results["recipes"] = recipes_result

            results["success"] = True
            results["message"] = f"导入完成：原料 {ingredients_result['imported']} 个，菜谱 {recipes_result['imported']} 个"

        except Exception as e:
            results["success"] = False
            results["message"] = f"导入失败: {str(e)}"
            results["errors"].append(str(e))

        return results

    def _import_ingredients(self) -> Dict[str, any]:
        """
        导入原料数据
        """
        result = {"imported": 0, "skipped": 0, "failed": 0, "errors": []}

        try:
            # 从 GitHub 下载 ingredients.json
            response = requests.get(f"{self.REPO_RAW_BASE}/ingredients.json", timeout=30)
            response.raise_for_status()

            ingredients_data = response.json()

            # 获取所有分类
            categories = {cat.name: cat for cat in self.db.query(IngredientCategory).all()}

            for item in ingredients_data:
                try:
                    ingredient_name = item.get("ingredient_name", "").strip()
                    if not ingredient_name:
                        continue

                    # 检查是否已存在
                    existing = self.db.query(Ingredient).filter(
                        Ingredient.name == ingredient_name
                    ).first()

                    if existing:
                        result["skipped"] += 1
                        print(f"跳过已存在的原料: {ingredient_name}")
                        continue

                    # 获取分类
                    category_name = item.get("category", "others")
                    category = categories.get(category_name)

                    # 获取单位
                    unit_str = item.get("unit", "")
                    unit_obj = self.unit_matcher.match_or_create_unit(unit_str)
                    unit_id = unit_obj.id if unit_obj else None

                    # 创建原料
                    ingredient = Ingredient(
                        name=ingredient_name,
                        aliases=item.get("aliases", []),
                        category_id=category.id if category else None,
                        default_unit_id=unit_id,
                        is_imported=True
                    )

                    self.db.add(ingredient)
                    self.db.flush()
                    result["imported"] += 1
                    print(f"导入原料: {ingredient_name}")

                    # 自动创建对应的同名商品
                    try:
                        from app.models.product_entity import Product

                        # 检查是否已存在同名商品
                        existing_product = self.db.query(Product).filter(
                            Product.name == ingredient_name,
                            Product.is_active == True
                        ).first()

                        if not existing_product:
                            # 创建商品
                            new_product = Product(
                                name=ingredient_name,
                                ingredient_id=ingredient.id,
                                created_by=self.user_id,
                                updated_by=self.user_id,
                                is_active=True
                            )
                            self.db.add(new_product)
                            self.db.flush()
                            print(f"  -> 创建商品 {new_product.name}")
                    except Exception as e:
                        print(f"  -> 创建商品失败: {str(e)}")
                except Exception as e:
                    result["failed"] += 1
                    result["errors"].append(f"导入原料失败: {item.get('ingredient_name')} - {str(e)}")

            self.db.commit()
            print(f"原料导入完成: 成功 {result['imported']}，跳过 {result['skipped']}，失败 {result['failed']}")

        except Exception as e:
            self.db.rollback()
            result["errors"].append(f"原料导入过程出错: {str(e)}")
            result["failed"] = result["imported"]  # 标记所有导入为失败

        return result

    def _import_recipes(self) -> Dict[str, any]:
        """
        导入菜谱数据
        """
        result = {"imported": 0, "skipped": 0, "failed": 0, "errors": []}

        # 创建临时目录下载仓库
        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp(prefix="recipe_import_")

            # 下载仓库 ZIP
            print("正在下载仓库...")
            response = requests.get(self.REPO_ZIP_URL, timeout=60)
            response.raise_for_status()

            zip_path = os.path.join(temp_dir, "repo.zip")
            with open(zip_path, "wb") as f:
                f.write(response.content)

            # 解压
            print("正在解压...")
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)

            # 查找解压后的目录
            extracted_dirs = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))]
            if not extracted_dirs:
                raise Exception("解压后未找到目录")

            repo_dir = os.path.join(temp_dir, extracted_dirs[0])
            out_dir = os.path.join(repo_dir, "out")

            if not os.path.exists(out_dir):
                raise Exception("out 目录不存在")

            # 找到所有菜谱 JSON 文件（排除营养数据和匹配文件）
            recipe_files = []
            for filename in os.listdir(out_dir):
                file_path = os.path.join(out_dir, filename)
                if filename.endswith(".json") and filename not in [
                    "ingredients.json",
                    "ingredients_raw.json",
                    "nutritions.json",
                    "matched_ingredients.json"
                ]:
                    recipe_files.append(file_path)

            print(f"找到 {len(recipe_files)} 个菜谱文件")

            # 导入每个菜谱
            for recipe_file in recipe_files:
                try:
                    with open(recipe_file, "r", encoding="utf-8") as f:
                        recipe_data = json.load(f)

                    if self._import_single_recipe(recipe_data, out_dir):
                        result["imported"] += 1
                    else:
                        result["skipped"] += 1

                except Exception as e:
                    result["failed"] += 1
                    result["errors"].append(f"导入菜谱失败 {os.path.basename(recipe_file)}: {str(e)}")

            self.db.commit()
            print(f"菜谱导入完成: 成功 {result['imported']}，跳过 {result['skipped']}，失败 {result['failed']}")

        except Exception as e:
            self.db.rollback()
            result["errors"].append(f"菜谱导入过程出错: {str(e)}")
            result["failed"] = result["imported"]  # 标记所有导入为失败

        finally:
            # 清理临时目录
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

        return result

    def _import_single_recipe(self, recipe_data: Dict, out_dir: str) -> bool:
        """
        导入单个菜谱
        """
        try:
            name = recipe_data.get("name", "").strip()
            if not name:
                print("跳过空名称菜谱")
                return False

            # 检查是否已存在
            existing = self.db.query(Recipe).filter(Recipe.name == name).first()
            if existing:
                print(f"跳过已存在的菜谱: {name}")
                return False

            # 检查数据完整性
            ingredients = recipe_data.get("ingredients", [])
            steps = recipe_data.get("steps", [])

            if not ingredients:
                print(f"跳过无原料信息的菜谱: {name}")
                return False

            if not steps:
                print(f"跳过无步骤信息的菜谱: {name}")
                return False

            # 处理图片路径并下载到本地
            images = recipe_data.get("images", [])
            if images:
                processed_images = []
                for img in images:
                    # 规范化路径
                    if img.startswith("images/"):
                        normalized_path = img
                    else:
                        normalized_path = f"images/{img}"

                    # 下载图片到本地
                    local_path = self._download_image(normalized_path, out_dir)
                    if local_path:
                        processed_images.append(local_path)
                    else:
                        # 下载失败，保留原始路径
                        processed_images.append(normalized_path)

                images = processed_images

            # 创建菜谱
            recipe = Recipe(
                name=name,
                source="json_repo",
                category=recipe_data.get("category"),
                tags=[recipe_data.get("category")] if recipe_data.get("category") else [],
                cooking_steps=steps,
                total_time_minutes=recipe_data.get("total_time_minutes"),
                difficulty=recipe_data.get("difficulty", "simple"),
                servings=recipe_data.get("servings", 1),
                tips=recipe_data.get("tips", []),
                images=images,
                user_id=1  # 使用默认用户 ID
            )

            self.db.add(recipe)
            self.db.flush()

            # 添加原料
            for ing_data in ingredients:
                ingredient_name = ing_data.get("ingredient_name", "").strip()
                if not ingredient_name:
                    continue

                # 直接获取原始的 JSON 数据（保持原样）
                quantity_range = ing_data.get("quantity_range")
                original_quantity = ing_data.get("original_quantity")

                # 查找原料
                ingredient = self.db.query(Ingredient).filter(
                    Ingredient.name == ingredient_name
                ).first()

                if ingredient:
                    # 获取单位
                    unit_str = ing_data.get("unit", "")
                    unit_obj = self.unit_matcher.match_or_create_unit(unit_str)
                    unit_id = unit_obj.id if unit_obj else None

                    recipe_ingredient = RecipeIngredient(
                        recipe_id=recipe.id,
                        ingredient_id=ingredient.id,
                        quantity=str(ing_data.get("quantity", "")),
                        quantity_range=quantity_range,
                        unit_id=unit_id,
                        is_optional=ing_data.get("is_optional", False),
                        note=ing_data.get("note"),
                        original_quantity=original_quantity
                    )
                    self.db.add(recipe_ingredient)
                else:
                    # 原料不存在，创建新原料
                    new_ingredient = Ingredient(
                        name=ingredient_name,
                        is_imported=True
                    )
                    self.db.add(new_ingredient)
                    self.db.flush()

                    # 获取单位
                    unit_str = ing_data.get("unit", "")
                    unit_obj = self.unit_matcher.match_or_create_unit(unit_str)
                    unit_id = unit_obj.id if unit_obj else None

                    recipe_ingredient = RecipeIngredient(
                        recipe_id=recipe.id,
                        ingredient_id=new_ingredient.id,
                        quantity=str(ing_data.get("quantity", "")),
                        quantity_range=quantity_range,
                        unit_id=unit_id,
                        is_optional=ing_data.get("is_optional", False),
                        note=ing_data.get("note"),
                        original_quantity=original_quantity
                    )
                    self.db.add(recipe_ingredient)

            print(f"导入菜谱: {name}")
            return True

        except IntegrityError:
            self.db.rollback()
            print(f"菜谱已存在: {name}")
            return False
        except Exception as e:
            print(f"导入菜谱失败 {name}: {str(e)}")
            return False


def check_and_import_from_json_repo(db: Session, user_id: Optional[int] = None) -> Dict[str, any]:
    """
    检查是否需要从 JSON 仓库导入数据
    """
    # 检查是否已有来自 json_repo 的菜谱
    has_json_recipes = db.query(Recipe).filter(
        Recipe.source == "json_repo"
    ).first() is not None

    if has_json_recipes:
        print("JSON 仓库菜谱已存在，跳过导入")
        return {
            "success": True,
            "message": "JSON 仓库菜谱已存在，跳过导入"
        }

    print("未发现 JSON 仓库菜谱，开始导入...")
    service = JsonRecipeImportService(db, user_id=user_id)
    return service.import_all()
