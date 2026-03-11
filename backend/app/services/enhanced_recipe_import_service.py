"""
增强的菜谱导入服务
支持进度显示、重试机制和更健壮的错误处理
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


class EnhancedRecipeImportService:
    """增强的菜谱导入服务，支持进度显示和错误重试"""

    # 外部仓库 URL
    REPO_URL = "https://github.com/DingJunyao/HowToCook_json.git"
    REPO_ZIP_URL = "https://github.com/DingJunyao/HowToCook_json/archive/refs/heads/main.zip"
    REPO_RAW_BASE = "https://raw.githubusercontent.com/DingJunyao/HowToCook_json/main/out"

    # 本地静态文件目录
    STATIC_DIR = Path(__file__).parent.parent.parent / "static"
    IMAGES_DIR = STATIC_DIR / "images" / "recipes"

    # 超时和重试配置
    DOWNLOAD_TIMEOUT = 300  # 5分钟超时（100MB 文件可能需要更长时间）
    MAX_RETRIES = 3  # 最大重试次数
    RETRY_DELAY = 2  # 重试延迟（秒）

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

    def __init__(
        self,
        db: Session,
        user_id: Optional[int] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ):
        """
        初始化导入服务

        Args:
            db: 数据库会话
            user_id: 用户 ID（默认为 1）
            progress_callback: 进度回调函数，格式为 (stage, current, total)
        """
        self.db = db
        self.unit_matcher = UnitMatcher(db)
        self.progress_callback = progress_callback
        self.user_id = user_id or 1  # 默认使用用户 ID 1

        # 确保图片目录存在（包括 recipes 子目录）
        self.IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    def _report_progress(self, stage: str, current: int, total: int, message: str = ""):
        """
        报告进度

        Args:
            stage: 当前阶段（如"下载"、"解压"、"导入原料"）
            current: 当前进度
            total: 总数
            message: 附加消息
        """
        if self.progress_callback:
            self.progress_callback(stage, current, total, message)

        # 计算进度百分比
        if total > 0:
            percentage = (current / total) * 100
            print(f"[{percentage:.1f}%] {stage}: {current}/{total} {message}")
        else:
            print(f"[{stage}] {message}")

    def _download_with_retry(self, url: str, timeout: int, description: str = "") -> Optional[bytes]:
        """
        带重试和进度显示的下载

        Args:
            url: 下载地址
            timeout: 超时时间（秒）
            description: 下载描述

        Returns:
            下载的内容，失败返回 None
        """
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                self._report_progress("下载", attempt, self.MAX_RETRIES,
                                f"{description} (第 {attempt} 次尝试)")
                response = requests.get(url, timeout=timeout, stream=True)
                response.raise_for_status()

                # 分块读取内容
                content = bytearray()
                total_size = int(response.headers.get('content-length', 0))

                # 计算 MB 大小
                total_mb = total_size / (1024 * 1024)

                for chunk in response.iter_content(chunk_size=8192):
                    content.extend(chunk)
                    if total_size > 0:
                        downloaded = len(content)
                        # 确保百分比不超过 100%
                        percentage = min((downloaded / total_size) * 100, 100)
                        downloaded_mb = downloaded / (1024 * 1024)

                        # 更新进度
                        self._report_progress("下载", percentage, 100, "")
                        print(f"[{percentage:.1f}%] {description}: {downloaded_mb:.1f} MB / {total_mb:.1f} MB")

                return bytes(content)

            except requests.exceptions.Timeout:
                print(f"下载超时: {description} (第 {attempt}/{self.MAX_RETRIES} 次)")
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY * attempt)  # 递增延迟
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
        """
        从克隆的仓库复制图片到本地静态目录

        Args:
            image_path: 原始图片路径（如 images/xxx.jpg）
            out_dir: 仓库 out 目录路径

        Returns:
            本地图片路径（如 /static/images/recipes/xxx.jpg）
        """
        try:
            # 获取文件名
            if image_path.startswith("images/"):
                filename = image_path[7:]
            else:
                filename = image_path

            # 检查仓库目录中是否有该图片
            repo_image_path = os.path.join(out_dir, image_path)
            if not os.path.exists(repo_image_path):
                print(f"图片不存在，跳过: {image_path}")
                return None

            # 检查本地是否已存在该图片
            local_image_path = self.IMAGES_DIR / filename
            if local_image_path.exists():
                print(f"图片已存在，跳过: {filename}")
                return f"/static/images/recipes/{filename}"

            # 直接从仓库复制图片
            shutil.copy2(repo_image_path, local_image_path)
            print(f"已复制图片: {filename}")
            return f"/static/images/recipes/{filename}"

        except Exception as e:
            print(f"复制图片失败 {image_path}: {str(e)}")
            return None

    def import_all(self) -> Dict[str, any]:
        """
        导入所有数据（原料、菜谱和营养数据）- 增强版
        使用统一的 git clone 获取仓库，一次性导入所有数据
        """
        self._report_progress("开始", 0, 1, "准备导入数据")

        results = {
            "ingredients": {"imported": 0, "skipped": 0, "failed": 0},
            "recipes": {"imported": 0, "skipped": 0, "failed": 0},
            "nutrition": {"imported": 0, "updated": 0, "skipped": 0, "failed": 0},
            "errors": []
        }

        # 创建临时目录
        temp_dir = None
        repo_dir = None

        try:
            temp_dir = tempfile.mkdtemp(prefix="recipe_import_")

            # 一次性克隆仓库
            self._report_progress("克隆仓库", 0, 1, "")
            repo_dir = self._clone_repo_via_git(temp_dir)

            # 如果 git clone 失败，回退到下载 ZIP
            if not repo_dir:
                print("git clone 失败，尝试下载 ZIP 文件...")

                # 下载仓库 ZIP
                self._report_progress("下载仓库", 0, 1, "")
                zip_content = self._download_with_retry(
                    self.REPO_ZIP_URL,
                    self.DOWNLOAD_TIMEOUT,
                    "菜谱仓库 ZIP"
                )

                if not zip_content:
                    raise Exception("下载仓库失败，请检查网络连接")

                zip_path = os.path.join(temp_dir, "repo.zip")
                with open(zip_path, "wb") as f:
                    f.write(zip_content)

                self._report_progress("下载仓库", 1, 2, f"文件大小: {len(zip_content)} 字节")

                # 解压
                self._report_progress("解压仓库", 0, 2, "")
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(temp_dir)

                # 查找解压后的目录
                extracted_dirs = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))]
                if not extracted_dirs:
                    raise Exception("解压后未找到目录")

                repo_dir = os.path.join(temp_dir, extracted_dirs[0])
                self._report_progress("解压仓库", 1, 2, "")
            else:
                self._report_progress("克隆仓库", 1, 1, "仓库获取成功")

            # 从克隆的仓库中获取数据
            out_dir = os.path.join(repo_dir, "out")
            if not os.path.exists(out_dir):
                raise Exception("out 目录不存在")

            # 读取 ingredients.json
            ingredients_file = os.path.join(out_dir, "ingredients.json")
            if not os.path.exists(ingredients_file):
                raise Exception("ingredients.json 不存在")

            with open(ingredients_file, "r", encoding="utf-8") as f:
                ingredients_data = json.load(f)

            self._report_progress("准备导入原料", 1, 1, f"共 {len(ingredients_data)} 个原料")

            # 1. 导入原料
            ingredients_result = self._import_ingredients_from_data(ingredients_data)
            results["ingredients"] = ingredients_result

            # 2. 导入菜谱
            recipes_result = self._import_recipes_from_dir(out_dir)
            results["recipes"] = recipes_result

            # 3. 导入营养数据（从本地仓库）
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
                self._report_progress("导入营养", 1, 1, f"导入完成")
            except Exception as e:
                print(f"营养数据导入失败: {str(e)}")
                results["errors"].append(f"营养数据导入失败: {str(e)}")
                results["nutrition"]["failed"] = 1

            results["success"] = True
            results["message"] = (
                f"导入完成：原料 {ingredients_result['imported']} 个，"
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
            # 清理临时目录
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    print("已清理临时目录")
                except Exception as e:
                    print(f"清理临时目录失败: {str(e)}")

        return results

    def _import_ingredients_from_data(self, ingredients_data: List[Dict]) -> Dict[str, any]:
        """
        从已加载的原料数据导入原料（增强版）

        Args:
            ingredients_data: 原料数据列表

        Returns:
            导入结果
        """
        result = {"imported": 0, "skipped": 0, "failed": 0, "errors": []}

        try:
            self._report_progress("导入原料", 0, 2, "")

            # 获取所有分类
            categories = {cat.name: cat for cat in self.db.query(IngredientCategory).all()}

            self._report_progress("处理原料", 0, len(ingredients_data), "")

            for idx, item in enumerate(ingredients_data, 1):
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
                        if idx % 100 == 0:
                            self._report_progress("处理原料", idx, len(ingredients_data),
                                            f"已跳过 {result['skipped']} 个")
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

                    if idx % 50 == 0:
                        self._report_progress("处理原料", idx, len(ingredients_data),
                                            f"已导入 {result['imported']} 个")

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
                    except Exception as e:
                        print(f"  -> 创建商品失败: {str(e)}")

                except Exception as e:
                    result["failed"] += 1
                    result["errors"].append(f"导入原料失败: {item.get('ingredient_name')} - {str(e)}")

            self.db.commit()
            self._report_progress("导入原料", 1, 2, "")
            self._report_progress("处理原料", len(ingredients_data), len(ingredients_data),
                                f"成功 {result['imported']} 个，跳过 {result['skipped']} 个，失败 {result['failed']} 个")

        except Exception as e:
            self.db.rollback()
            result["errors"].append(f"原料导入过程出错: {str(e)}")
            result["failed"] = result["imported"]  # 标记所有导入为失败

        return result

    def _clone_repo_via_git(self, temp_dir: str) -> str:
        """
        使用 git clone 获取仓库（优先方法，带进度显示）

        Args:
            temp_dir: 临时目录

        Returns:
            仓库路径，失败返回 None
        """
        import subprocess
        import time

        try:
            repo_path = os.path.join(temp_dir, "HowToCook_json")

            # 如果仓库已存在，直接返回
            if os.path.exists(repo_path):
                out_dir = os.path.join(repo_path, "out")
                if os.path.exists(out_dir):
                    print(f"仓库已存在: {repo_path}")
                    return repo_path

            self._report_progress("克隆仓库", 0, 100, "准备克隆...")
            print(f"正在克隆仓库: {self.REPO_URL}")

            # 使用 git clone --depth=1 --verbose 只克隆最新版本，显示详细输出
            result = subprocess.run(
                ["git", "clone", "--depth", "1", "--verbose", self.REPO_URL, repo_path],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=self.DOWNLOAD_TIMEOUT
            )

            # 输出 Git 的详细输出（用于调试）
            if result.stdout:
                print(f"[Git stdout]:\n{result.stdout}")
            if result.stderr:
                print(f"[Git stderr]:\n{result.stderr}")

            if result.returncode == 0:
                print(f"✓ Git clone 成功")
                self._report_progress("克隆仓库", 100, 100, "克隆完成")

                out_dir = os.path.join(repo_path, "out")
                if os.path.exists(out_dir):
                    return repo_path
                else:
                    print(f"git clone 成功，但 out 目录不存在")
                    return None
            else:
                print(f"✗ Git clone 失败，退出码: {result.returncode}")
                print(f"错误输出: {result.stderr}")
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

    def _import_recipes_from_dir(self, out_dir: str) -> Dict[str, any]:
        """
        从目录导入菜谱数据（增强版）

        Args:
            out_dir: 仓库 out 目录路径

        Returns:
            导入结果
        """
        result = {"imported": 0, "skipped": 0, "failed": 0, "errors": []}

        try:
            self._report_progress("导入菜谱", 0, 2, "")

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

            if not recipe_files:
                raise Exception("未找到菜谱文件")

            self._report_progress("准备导入", 1, 1, f"找到 {len(recipe_files)} 个菜谱文件")

            # 导入每个菜谱
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
                                            f"已导入 {result['imported']} 个，跳过 {result['skipped']} 个")

                except Exception as e:
                    result["failed"] += 1
                    result["errors"].append(f"导入菜谱失败 {os.path.basename(recipe_file)}: {str(e)}")

            self.db.commit()
            self._report_progress("导入菜谱", 1, 2, "")
            self._report_progress("导入菜谱", total_files, total_files,
                                f"成功 {result['imported']} 个，跳过 {result['skipped']} 个，失败 {result['failed']} 个")

        except Exception as e:
            self.db.rollback()
            result["errors"].append(f"菜谱导入过程出错: {str(e)}")
            result["failed"] = result["imported"]  # 标记所有导入为失败

        return result

    def _import_single_recipe(self, recipe_data: Dict, out_dir: str) -> bool:
        """
        导入单个菜谱（增强版）
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
            processed_images = []

            if images:
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
                        print(f"图片下载失败，保留原始路径: {img}")
                        processed_images.append(normalized_path)
                images = processed_images

            # 创建菜谱
            recipe = Recipe(
                name=name,
                source="json_repo",
                category=recipe_data.get("category"),
                user_id=self.user_id,
                tags=[recipe_data.get("category")] if recipe_data.get("category") else [],
                cooking_steps=steps,  # JSON 中的 steps 是字典列表，不需要 model_dump
                total_time_minutes=recipe_data.get("total_time_minutes"),
                difficulty=recipe_data.get("difficulty", "simple"),
                servings=recipe_data.get("servings", 1),
                images=images
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


# 保持向后兼容的函数别名
def check_and_import_initial_recipes(db: Session, user_id: Optional[int] = None, force_reimport: bool = False) -> Dict[str, any]:
    """
    检查是否需要从 JSON 仓库导入数据

    Args:
        db: 数据库会话
        user_id: 用户 ID（可选）
        force_reimport: 是否强制重新导入（删除已有数据后重新导入）

    Returns:
        导入结果统计
    """
    # 检查是否已有来自 json_repo 的菜谱
    has_json_recipes = db.query(Recipe).filter(
        Recipe.source == "json_repo"
    ).first() is not None

    if has_json_recipes and not force_reimport:
        count = db.query(Recipe).filter(Recipe.source == "json_repo").count()
        print(f"发现 JSON 仓库菜谱已存在（共 {count} 条），跳过导入。")
        print("如需重新导入，请设置 force_reimport=True")
        return {
            "success": True,
            "message": f"跳过导入：已有 {count} 条 JSON 仓库菜谱",
            "imported": 0,
            "skipped": 0,
            "failed": 0
        }

    if has_json_recipes and force_reimport:
        print("发现 JSON 仓库菜谱已存在，正在删除以重新导入...")

        # 先获取所有需要删除的菜谱 ID
        recipe_ids = [r[0] for r in db.query(Recipe).filter(Recipe.source == "json_repo").with_entities(Recipe.id).all()]

        # 删除关联的原料记录
        if recipe_ids:
            from app.models.recipe import RecipeIngredient
            db.query(RecipeIngredient).filter(
                RecipeIngredient.recipe_id.in_(recipe_ids)
            ).delete(synchronize_session=False)

        # 删除菜谱
        db.query(Recipe).filter(Recipe.source == "json_repo").delete()

        # 清除已导入的原料标记
        from app.models.nutrition import Ingredient
        db.query(Ingredient).filter(Ingredient.is_imported == True).update(
            {Ingredient.is_imported: False}
        )

        db.commit()
        print("已清空 JSON 仓库菜谱数据，开始重新导入...")

    print("开始导入 JSON 仓库菜谱...")
    service = EnhancedRecipeImportService(db, user_id=user_id)
    return service.import_all()


# 别名函数，与 json_recipe_import_service 保持兼容
check_and_import_from_json_repo = check_and_import_initial_recipes
