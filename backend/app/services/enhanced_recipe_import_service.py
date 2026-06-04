"""
增强的菜谱导入服务
支持进度显示、重试机制和更健壮的错误处理

数据仓库结构（corr 分支）:
  out/
  ├── ingredients.json       # 原料数据（dict: name -> {name, aliases, category, usda_id, usda_match_status}）
  ├── ingredients_raw.json   # 原料默认单位（list: {ingredient_name, unit}）
  ├── units.json             # 单位列表（list: {name, aliases}）
  ├── nutritions.json        # 营养数据（list: {usda_id, ingredient_name, usda_name, nutrients: [{name, name_en, value, unit, ...}]}）
  ├── matched_ingredients.json # 匹配记录（list: {ingredient_name, usda_id, usda_name}）
  └── *.json                 # 菜谱文件（{name, ingredients: [...], steps: [{content, ...}], ...}）
"""
import json
import os
import re
import tempfile
import zipfile
import requests
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Callable
from sqlalchemy.orm import Session
from app.models.recipe import Recipe, RecipeIngredient
from app.models.nutrition import Ingredient
from app.models.ingredient_category import IngredientCategory
from app.services.unit_matcher import UnitMatcher
from sqlalchemy.exc import IntegrityError


def _get_repo_config():
    """从环境变量读取数据仓库配置"""
    return {
        "url": os.getenv("DATA_REPO_URL", "https://github.com/DingJunyao/HowToCook_json.git"),
        "branch": os.getenv("DATA_REPO_BRANCH", "corr"),
        "data_dir": os.getenv("DATA_REPO_DIR", "out"),
    }


class EnhancedRecipeImportService:
    """增强的菜谱导入服务，支持进度显示和错误重试"""

    # 本地静态文件目录
    STATIC_DIR = Path(__file__).parent.parent.parent / "static"
    IMAGES_DIR = STATIC_DIR / "images" / "recipes"

    # 超时和重试配置
    DOWNLOAD_TIMEOUT = 300  # 5分钟超时
    MAX_RETRIES = 3
    RETRY_DELAY = 2

    # 分类映射（中文 -> 系统分类 key）
    CATEGORY_MAPPING = {
        "肉类": "meat",
        "蔬菜": "vegetables",
        "水果": "fruits",
        "海鲜": "seafood",
        "禽蛋": "eggs",
        "乳制品": "dairy",
        "调味品": "seasoning",
        "油脂": "oil",
        "坚果": "nuts",
        "饮品": "beverages",
        "其他": "others",
        # 兼容英文分类
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

    # 不属于菜谱的文件名
    NON_RECIPE_FILES = {
        "ingredients.json",
        "ingredients_raw.json",
        "nutritions.json",
        "matched_ingredients.json",
        "units.json",
    }

    def __init__(
        self,
        db: Session,
        user_id: Optional[int] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ):
        self.db = db
        self.unit_matcher = UnitMatcher(db)
        self.progress_callback = progress_callback
        self.user_id = user_id or 1

        # 读取仓库配置
        self._repo_config = _get_repo_config()

        # 确保图片目录存在
        self.IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 进度与下载
    # ------------------------------------------------------------------

    def _report_progress(self, stage: str, current: int, total: int, message: str = ""):
        if self.progress_callback:
            self.progress_callback(stage, current, total, message)
        if total > 0:
            percentage = (current / total) * 100
            print(f"[{percentage:.1f}%] {stage}: {current}/{total} {message}")
        else:
            print(f"[{stage}] {message}")

    def _download_with_retry(self, url: str, timeout: int, description: str = "") -> Optional[bytes]:
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                self._report_progress("下载", attempt, self.MAX_RETRIES,
                                      f"{description} (第 {attempt} 次尝试)")
                response = requests.get(url, timeout=timeout, stream=True)
                response.raise_for_status()

                content = bytearray()
                total_size = int(response.headers.get('content-length', 0))
                total_mb = total_size / (1024 * 1024)

                for chunk in response.iter_content(chunk_size=8192):
                    content.extend(chunk)
                    if total_size > 0:
                        percentage = min((len(content) / total_size) * 100, 100)
                        downloaded_mb = len(content) / (1024 * 1024)
                        self._report_progress("下载", percentage, 100, "")
                        print(f"[{percentage:.1f}%] {description}: {downloaded_mb:.1f} MB / {total_mb:.1f} MB")

                return bytes(content)

            except requests.exceptions.Timeout:
                print(f"下载超时: {description} (第 {attempt}/{self.MAX_RETRIES} 次)")
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY * attempt)
                    continue
                return None
            except requests.exceptions.RequestException as e:
                print(f"下载失败: {description} - {str(e)}")
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY * attempt)
                    continue
                return None
            except Exception as e:
                print(f"下载异常: {description} - {type(e).__name__}: {str(e)}")
                return None
        return None

    def _download_image(self, image_path: str, out_dir: str) -> Optional[str]:
        try:
            filename = image_path[7:] if image_path.startswith("images/") else image_path
            repo_image_path = os.path.join(out_dir, image_path)
            if not os.path.exists(repo_image_path):
                print(f"图片不存在，跳过: {image_path}")
                return None

            local_image_path = self.IMAGES_DIR / filename
            if local_image_path.exists():
                return f"/static/images/recipes/{filename}"

            shutil.copy2(repo_image_path, local_image_path)
            return f"/static/images/recipes/{filename}"
        except Exception as e:
            print(f"复制图片失败 {image_path}: {str(e)}")
            return None

    # ------------------------------------------------------------------
    # 仓库获取
    # ------------------------------------------------------------------

    def _clone_repo_via_git(self, temp_dir: str) -> Optional[str]:
        """使用 git clone 获取仓库（指定分支）"""
        import subprocess

        repo_cfg = self._repo_config
        repo_url = repo_cfg["url"]
        branch = repo_cfg["branch"]
        data_dir = repo_cfg["data_dir"]

        # 从 URL 推算目录名
        repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        repo_path = os.path.join(temp_dir, repo_name)

        try:
            if os.path.exists(repo_path):
                target_dir = os.path.join(repo_path, data_dir)
                if os.path.exists(target_dir):
                    print(f"仓库已存在: {repo_path}")
                    return repo_path

            self._report_progress("克隆仓库", 0, 100, f"克隆 {repo_url} (分支: {branch})...")
            result = subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", branch, "--verbose",
                 repo_url, repo_path],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=self.DOWNLOAD_TIMEOUT
            )

            if result.stdout:
                print(f"[Git stdout]:\n{result.stdout}")
            if result.stderr:
                print(f"[Git stderr]:\n{result.stderr}")

            if result.returncode == 0:
                print("✓ Git clone 成功")
                self._report_progress("克隆仓库", 100, 100, "克隆完成")
                target_dir = os.path.join(repo_path, data_dir)
                return repo_path if os.path.exists(target_dir) else None
            else:
                print(f"✗ Git clone 失败，退出码: {result.returncode}")
                return None

        except FileNotFoundError:
            print("git 命令未找到，将使用备用下载方式")
            return None
        except subprocess.TimeoutExpired:
            print("git clone 超时")
            return None
        except Exception as e:
            print(f"git clone 异常: {type(e).__name__}: {str(e)}")
            return None

    def _get_zip_url(self) -> str:
        """根据仓库 URL 和分支生成 ZIP 下载地址"""
        repo_url = self._repo_config["url"].rstrip("/").removesuffix(".git")
        branch = self._repo_config["branch"]
        return f"{repo_url}/archive/refs/heads/{branch}.zip"

    # ------------------------------------------------------------------
    # 主导入流程
    # ------------------------------------------------------------------

    def import_all(self) -> Dict[str, any]:
        """导入所有数据（单位、原料、菜谱和营养数据）"""
        self._report_progress("开始", 0, 1, "准备导入数据")

        results = {
            "units": {"imported": 0, "skipped": 0, "failed": 0},
            "ingredients": {"imported": 0, "skipped": 0, "failed": 0},
            "recipes": {"imported": 0, "skipped": 0, "failed": 0},
            "nutrition": {"imported": 0, "updated": 0, "skipped": 0, "failed": 0},
            "errors": []
        }

        temp_dir = None
        repo_dir = None

        try:
            temp_dir = tempfile.mkdtemp(prefix="recipe_import_")

            # 克隆仓库
            self._report_progress("克隆仓库", 0, 1, "")
            repo_dir = self._clone_repo_via_git(temp_dir)

            if not repo_dir:
                print("git clone 失败，尝试下载 ZIP 文件...")
                self._report_progress("下载仓库", 0, 1, "")
                zip_content = self._download_with_retry(
                    self._get_zip_url(),
                    self.DOWNLOAD_TIMEOUT,
                    "菜谱仓库 ZIP"
                )
                if not zip_content:
                    raise Exception("下载仓库失败，请检查网络连接")

                zip_path = os.path.join(temp_dir, "repo.zip")
                with open(zip_path, "wb") as f:
                    f.write(zip_content)

                self._report_progress("下载仓库", 1, 2, f"文件大小: {len(zip_content)} 字节")

                self._report_progress("解压仓库", 0, 2, "")
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(temp_dir)

                extracted_dirs = [d for d in os.listdir(temp_dir)
                                  if os.path.isdir(os.path.join(temp_dir, d))]
                if not extracted_dirs:
                    raise Exception("解压后未找到目录")
                repo_dir = os.path.join(temp_dir, extracted_dirs[0])
                self._report_progress("解压仓库", 1, 2, "")
            else:
                self._report_progress("克隆仓库", 1, 1, "仓库获取成功")

            # 定位数据目录
            data_dir_name = self._repo_config["data_dir"]
            out_dir = os.path.join(repo_dir, data_dir_name)
            if not os.path.exists(out_dir):
                raise Exception(f"数据目录 '{data_dir_name}' 不存在")

            # 0. 导入 units.json
            units_result = self._import_units(out_dir)
            results["units"] = units_result

            # 1. 导入原料
            ingredients_result = self._import_ingredients(out_dir)
            results["ingredients"] = ingredients_result

            # 2. 导入菜谱
            recipes_result = self._import_recipes_from_dir(out_dir)
            results["recipes"] = recipes_result

            # 3. 导入营养数据
            try:
                self._report_progress("导入营养", 0, 1, "")
                from app.services.nutrition_import_service import check_and_import_nutrition
                nutrition_result = check_and_import_nutrition(
                    self.db,
                    mode="incremental",
                    force_update=False,
                    repo_dir=repo_dir
                )
                results["nutrition"] = nutrition_result
                self._report_progress("导入营养", 1, 1, "导入完成")
            except Exception as e:
                print(f"营养数据导入失败: {str(e)}")
                results["errors"].append(f"营养数据导入失败: {str(e)}")
                results["nutrition"]["failed"] = 1

            results["success"] = True
            results["message"] = (
                f"导入完成：单位 {units_result['imported']} 个，"
                f"原料 {ingredients_result['imported']} 个，"
                f"菜谱 {recipes_result['imported']} 个，"
                f"营养数据 {results['nutrition'].get('imported', 0)} 个"
            )
            self._report_progress("完成", 1, 1, "导入成功")

        except Exception as e:
            results["success"] = False
            results["message"] = f"导入失败: {str(e)}"
            results["errors"].append(str(e))
            self._report_progress("失败", 0, 1, str(e))

        finally:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    print("已清理临时目录")
                except Exception as e:
                    print(f"清理临时目录失败: {str(e)}")

        return results

    # ------------------------------------------------------------------
    # units.json 导入
    # ------------------------------------------------------------------

    def _import_units(self, out_dir: str) -> Dict[str, any]:
        """从 units.json 导入单位数据到系统单位表

        units.json 格式: [{"name": "茶匙", "aliases": ["tsp", "小匙", "茶匙"]}, ...]
        别名用于丰富 UnitMatcher 的查找缓存，使别名也能匹配到对应单位。
        """
        result = {"imported": 0, "skipped": 0, "failed": 0, "errors": []}
        units_file = os.path.join(out_dir, "units.json")

        if not os.path.exists(units_file):
            print("units.json 不存在，跳过单位导入")
            return result

        try:
            with open(units_file, "r", encoding="utf-8") as f:
                units_data = json.load(f)

            self._report_progress("导入单位", 0, len(units_data), f"共 {len(units_data)} 个单位")

            for idx, item in enumerate(units_data, 1):
                try:
                    name = item.get("name", "").strip()
                    if not name:
                        continue

                    aliases = item.get("aliases", [])

                    # 尝试匹配已有单位
                    existing_unit, is_new = self.unit_matcher.match_unit(name)

                    if existing_unit and not is_new:
                        # 已存在，将别名加入匹配缓存以便查找
                        for alias in aliases:
                            if alias and alias not in self.unit_matcher.unit_cache:
                                self.unit_matcher.unit_cache[alias] = existing_unit
                        result["skipped"] += 1
                    elif existing_unit and is_new:
                        # 新创建的单位，将别名加入缓存
                        for alias in aliases:
                            if alias and alias not in self.unit_matcher.unit_cache:
                                self.unit_matcher.unit_cache[alias] = existing_unit
                        result["imported"] += 1
                    else:
                        result["skipped"] += 1

                    if idx % 50 == 0:
                        self._report_progress("导入单位", idx, len(units_data),
                                              f"已导入 {result['imported']} 个")

                except Exception as e:
                    result["failed"] += 1
                    result["errors"].append(f"导入单位失败: {item.get('name')} - {str(e)}")

            self.db.commit()
            self._report_progress("导入单位", len(units_data), len(units_data),
                                  f"成功 {result['imported']}，跳过 {result['skipped']}")

        except Exception as e:
            self.db.rollback()
            result["errors"].append(f"单位导入出错: {str(e)}")

        return result

    # ------------------------------------------------------------------
    # 原料导入
    # ------------------------------------------------------------------

    def _import_ingredients(self, out_dir: str) -> Dict[str, any]:
        """
        从 ingredients.json + ingredients_raw.json 导入原料

        ingredients.json: dict { name: {name, aliases, category, usda_id, usda_match_status} }
        ingredients_raw.json: list [{ingredient_name, unit}]
        """
        result = {"imported": 0, "skipped": 0, "failed": 0, "errors": []}

        try:
            # 读取 ingredients.json
            ingredients_file = os.path.join(out_dir, "ingredients.json")
            if not os.path.exists(ingredients_file):
                raise Exception("ingredients.json 不存在")

            with open(ingredients_file, "r", encoding="utf-8") as f:
                ingredients_data = json.load(f)

            # 读取 ingredients_raw.json（单位映射）
            raw_units: Dict[str, str] = {}
            raw_file = os.path.join(out_dir, "ingredients_raw.json")
            if os.path.exists(raw_file):
                with open(raw_file, "r", encoding="utf-8") as f:
                    raw_list = json.load(f)
                raw_units = {
                    item["ingredient_name"]: item.get("unit", "")
                    for item in raw_list
                    if item.get("ingredient_name")
                }

            self._report_progress("准备导入原料", 1, 1,
                                  f"共 {len(ingredients_data)} 个原料，{len(raw_units)} 个单位映射")

            categories = {cat.name: cat for cat in self.db.query(IngredientCategory).all()}

            self._report_progress("处理原料", 0, len(ingredients_data), "")

            for idx, (key, item) in enumerate(ingredients_data.items(), 1):
                try:
                    ingredient_name = item.get("name", "").strip() or key.strip()
                    if not ingredient_name:
                        continue

                    # 检查是否已存在
                    existing = self.db.query(Ingredient).filter(
                        Ingredient.name == ingredient_name
                    ).first()

                    if existing:
                        result["skipped"] += 1
                        if idx % 100 == 0:
                            self._report_progress("处理原料", idx, len(ingredients_data),
                                                  f"已跳过 {result['skipped']} 个")
                        continue

                    # 获取分类（新格式使用中文名）
                    category_name = item.get("category", "others")
                    mapped_category = self.CATEGORY_MAPPING.get(category_name, category_name)
                    category = categories.get(mapped_category) or categories.get(category_name)

                    # 获取默认单位（从 ingredients_raw.json）
                    unit_str = raw_units.get(ingredient_name, "")
                    unit_obj = self.unit_matcher.match_or_create_unit(unit_str) if unit_str else None
                    unit_id = unit_obj.id if unit_obj else None

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

                    if idx % 50 == 0:
                        self._report_progress("处理原料", idx, len(ingredients_data),
                                              f"已导入 {result['imported']} 个")

                    # 自动创建对应的同名商品
                    try:
                        from app.models.product_entity import Product
                        existing_product = self.db.query(Product).filter(
                            Product.name == ingredient_name,
                            Product.is_active == True
                        ).first()
                        if not existing_product:
                            new_product = Product(
                                name=ingredient_name,
                                ingredient_id=ingredient.id,
                                created_by=self.user_id,
                                updated_by=self.user_id,
                                is_active=True
                            )
                            self.db.add(new_product)
                            self.db.flush()
                    except Exception as e:
                        print(f"  -> 创建商品失败: {str(e)}")

                except Exception as e:
                    result["failed"] += 1
                    result["errors"].append(f"导入原料失败: {item.get('name', key)} - {str(e)}")

            self.db.commit()
            self._report_progress("处理原料", len(ingredients_data), len(ingredients_data),
                                  f"成功 {result['imported']}，跳过 {result['skipped']}，失败 {result['failed']}")

        except Exception as e:
            self.db.rollback()
            result["errors"].append(f"原料导入过程出错: {str(e)}")
            result["failed"] = result["imported"]

        return result

    # ------------------------------------------------------------------
    # 菜谱导入
    # ------------------------------------------------------------------

    def _import_recipes_from_dir(self, out_dir: str) -> Dict[str, any]:
        """从目录导入菜谱数据"""
        result = {"imported": 0, "skipped": 0, "failed": 0, "errors": []}

        try:
            self._report_progress("导入菜谱", 0, 2, "")

            recipe_files = []
            for filename in os.listdir(out_dir):
                if filename.endswith(".json") and filename not in self.NON_RECIPE_FILES:
                    recipe_files.append(os.path.join(out_dir, filename))

            if not recipe_files:
                raise Exception("未找到菜谱文件")

            self._report_progress("准备导入", 1, 1, f"找到 {len(recipe_files)} 个菜谱文件")

            total_files = len(recipe_files)
            for idx, recipe_file in enumerate(recipe_files, 1):
                try:
                    self._report_progress("导入菜谱", idx, total_files,
                                          f"处理 {os.path.basename(recipe_file)}")

                    with open(recipe_file, "r", encoding="utf-8") as f:
                        recipe_data = json.load(f)

                    if self._import_single_recipe(recipe_data, out_dir):
                        result["imported"] += 1
                    else:
                        result["skipped"] += 1

                    if idx % 20 == 0:
                        self._report_progress("导入菜谱", idx, total_files,
                                              f"已导入 {result['imported']}，跳过 {result['skipped']}")

                except Exception as e:
                    result["failed"] += 1
                    result["errors"].append(f"导入菜谱失败 {os.path.basename(recipe_file)}: {str(e)}")

            self.db.commit()
            self._report_progress("导入菜谱", total_files, total_files,
                                  f"成功 {result['imported']}，跳过 {result['skipped']}，失败 {result['failed']}")

        except Exception as e:
            self.db.rollback()
            result["errors"].append(f"菜谱导入过程出错: {str(e)}")
            result["failed"] = result["imported"]

        return result

    def _import_single_recipe(self, recipe_data: Dict, out_dir: str) -> bool:
        """导入单个菜谱（新版格式：steps 为对象列表）"""
        try:
            name = recipe_data.get("name", "").strip()
            if not name:
                print("跳过空名称菜谱")
                return False

            existing = self.db.query(Recipe).filter(Recipe.name == name).first()
            if existing:
                print(f"跳过已存在的菜谱: {name}")
                return False

            ingredients = recipe_data.get("ingredients", [])
            steps = recipe_data.get("steps", [])
            if not ingredients:
                print(f"跳过无原料信息的菜谱: {name}")
                return False
            if not steps:
                print(f"跳过无步骤信息的菜谱: {name}")
                return False

            # 处理图片
            images = recipe_data.get("images", [])
            processed_images = []
            if images:
                for img in images:
                    normalized_path = img if img.startswith("images/") else f"images/{img}"
                    local_path = self._download_image(normalized_path, out_dir)
                    processed_images.append(local_path or normalized_path)
                images = processed_images

            # 创建菜谱
            recipe = Recipe(
                name=name,
                source="json_repo",
                category=recipe_data.get("category"),
                user_id=self.user_id,
                tags=[recipe_data.get("category")] if recipe_data.get("category") else [],
                cooking_steps=steps,  # 新版 steps 为 [{content, duration_minutes, tips}]
                total_time_minutes=recipe_data.get("total_time_minutes"),
                difficulty=recipe_data.get("difficulty", "simple"),
                servings=recipe_data.get("servings", 1),
                tips=recipe_data.get("tips", []),
                description=recipe_data.get("description", ""),
                images=images
            )

            self.db.add(recipe)
            self.db.flush()

            # 添加原料
            for ing_data in ingredients:
                ingredient_name = ing_data.get("ingredient_name", "").strip()
                if not ingredient_name:
                    continue

                quantity_range = ing_data.get("quantity_range")
                original_quantity = ing_data.get("original_quantity")
                # 新版数据中 "适量/少许" 存在 quantity_description 字段
                quantity_description = ing_data.get("quantity_description", "")
                if not original_quantity and quantity_description:
                    original_quantity = quantity_description

                ingredient = self.db.query(Ingredient).filter(
                    Ingredient.name == ingredient_name
                ).first()

                unit_str = ing_data.get("unit", "")
                unit_obj = self.unit_matcher.match_or_create_unit(unit_str) if unit_str else None
                unit_id = unit_obj.id if unit_obj else None

                if not ingredient:
                    ingredient = Ingredient(
                        name=ingredient_name,
                        is_imported=True
                    )
                    self.db.add(ingredient)
                    self.db.flush()

                raw_quantity = ing_data.get("quantity")
                recipe_ingredient = RecipeIngredient(
                    recipe_id=recipe.id,
                    ingredient_id=ingredient.id,
                    quantity=str(raw_quantity) if raw_quantity is not None else None,
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


# ======================================================================
# 便捷函数
# ======================================================================

def check_and_import_initial_recipes(
    db: Session,
    user_id: Optional[int] = None,
    force_reimport: bool = False
) -> Dict[str, any]:
    """
    检查是否需要从 JSON 仓库导入数据

    Args:
        db: 数据库会话
        user_id: 用户 ID（可选）
        force_reimport: 是否强制重新导入

    Returns:
        导入结果统计
    """
    has_json_recipes = db.query(Recipe).filter(
        Recipe.source == "json_repo"
    ).first() is not None

    if has_json_recipes and not force_reimport:
        count = db.query(Recipe).filter(Recipe.source == "json_repo").count()
        print(f"发现 JSON 仓库菜谱已存在（共 {count} 条），跳过导入。")
        return {
            "success": True,
            "message": f"跳过导入：已有 {count} 条 JSON 仓库菜谱",
            "imported": 0,
            "skipped": 0,
            "failed": 0
        }

    if has_json_recipes and force_reimport:
        print("发现 JSON 仓库菜谱已存在，正在删除以重新导入...")
        recipe_ids = [r[0] for r in db.query(Recipe).filter(
            Recipe.source == "json_repo").with_entities(Recipe.id).all()]
        if recipe_ids:
            db.query(RecipeIngredient).filter(
                RecipeIngredient.recipe_id.in_(recipe_ids)
            ).delete(synchronize_session=False)
        db.query(Recipe).filter(Recipe.source == "json_repo").delete()

        from app.models.nutrition import Ingredient
        db.query(Ingredient).filter(Ingredient.is_imported == True).update(
            {Ingredient.is_imported: False}
        )
        db.commit()
        print("已清空 JSON 仓库菜谱数据，开始重新导入...")

    print("开始导入 JSON 仓库菜谱...")
    service = EnhancedRecipeImportService(db, user_id=user_id)
    return service.import_all()


# 别名函数
check_and_import_from_json_repo = check_and_import_initial_recipes
