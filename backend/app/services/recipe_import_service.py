import json
import os
import zipfile
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.recipe import Recipe, RecipeIngredient
from app.models.nutrition import Ingredient
from app.schemas.recipe import RecipeCreate, RecipeIngredientCreate, CookingStep
from app.core.database import get_db
from sqlalchemy.exc import IntegrityError
import tempfile
import re


class RecipeImportService:
    """菜谱导入服务"""

    def __init__(self, db: Session):
        self.db = db

    def import_recipes_from_cook_repo(self, repo_url: str = "https://github.com/Anduin2017/HowToCook",
                                     branch: str = "master") -> Dict[str, any]:
        """
        从 HowToCook 仓库导入菜谱
        """
        try:
            # 构建下载链接
            zip_url = f"{repo_url}/archive/{branch}.zip"

            # 下载仓库 ZIP
            response = requests.get(zip_url)
            response.raise_for_status()

            # 创建临时文件存储下载的内容
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                tmp_file.write(response.content)
                tmp_filename = tmp_file.name

            try:
                # 解压 ZIP 文件
                with zipfile.ZipFile(tmp_filename, 'r') as zip_ref:
                    # 找到菜谱文件夹
                    recipe_files = self._find_recipe_files(zip_ref)

                    imported_count = 0
                    failed_count = 0
                    errors = []

                    for recipe_file in recipe_files:
                        try:
                            recipe_data = self._parse_recipe_file(zip_ref, recipe_file)
                            if recipe_data:
                                success = self._import_single_recipe(recipe_data)
                                if success:
                                    imported_count += 1
                                else:
                                    failed_count += 1
                            else:
                                failed_count += 1
                        except Exception as e:
                            failed_count += 1
                            errors.append(f"解析文件 {recipe_file} 时出错: {str(e)}")

                return {
                    "success": True,
                    "imported_count": imported_count,
                    "failed_count": failed_count,
                    "errors": errors
                }
            finally:
                # 删除临时文件
                os.unlink(tmp_filename)

        except requests.RequestException as e:
            return {
                "success": False,
                "error": f"下载仓库失败: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"导入过程中发生错误: {str(e)}"
            }

    def import_recipes_from_zip_file(self, zip_file_path: str) -> Dict[str, any]:
        """
        从上传的 ZIP 文件导入菜谱
        """
        try:
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                # 找到菜谱文件夹
                recipe_files = self._find_recipe_files(zip_ref)

                imported_count = 0
                failed_count = 0
                errors = []

                for recipe_file in recipe_files:
                    try:
                        recipe_data = self._parse_recipe_file(zip_ref, recipe_file)
                        if recipe_data:
                            success = self._import_single_recipe(recipe_data)
                            if success:
                                imported_count += 1
                            else:
                                failed_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        failed_count += 1
                        errors.append(f"解析文件 {recipe_file} 时出错: {str(e)}")

            return {
                "success": True,
                "imported_count": imported_count,
                "failed_count": failed_count,
                "errors": errors
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"导入ZIP文件时出错: {str(e)}"
            }

    def _find_recipe_files(self, zip_ref: zipfile.ZipFile) -> List[str]:
        """
        从ZIP中找到所有菜谱文件
        """
        recipe_files = []
        for file_info in zip_ref.filelist:
            file_path = file_info.filename
            # 检查是否是 Markdown 文件，且路径包含菜谱分类目录
            if file_path.endswith('.md') and (
                '/aquatic/' in file_path.lower() or
                '/breakfast/' in file_path.lower() or
                '/condiment/' in file_path.lower() or
                '/dessert/' in file_path.lower() or
                '/drink/' in file_path.lower() or
                '/meat_dish/' in file_path.lower() or
                '/semi-finished/' in file_path.lower() or
                '/soup/' in file_path.lower() or
                '/staple/' in file_path.lower() or
                '/vegetable_dish/' in file_path.lower()
            ):
                recipe_files.append(file_path)

        return recipe_files

    def _parse_recipe_file(self, zip_ref: zipfile.ZipFile, file_path: str) -> Optional[Dict]:
        """
        解析单个菜谱文件
        """
        try:
            # 读取文件内容
            content = zip_ref.read(file_path).decode('utf-8')

            # 如果是 Markdown 文件，使用专门的方法解析
            if file_path.lower().endswith('.md'):
                return self._parse_markdown_recipe(content, file_path)
            else:
                # 其他格式暂时返回 None
                return None
        except Exception as e:
            print(f"解析菜谱文件 {file_path} 失败: {str(e)}")
            return None

    def _parse_markdown_recipe(self, content: str, file_path: str) -> Optional[Dict]:
        """
        解析 Markdown 格式的菜谱文件
        """
        try:
            import re

            # 提取菜谱名称（从标题）
            title_match = re.search(r'^#\s+(.+?)的做法', content, re.MULTILINE)
            if title_match:
                name = title_match.group(1).strip()
            else:
                # 从文件名提取
                name = Path(file_path).stem

            # 提取难度星级
            difficulty_stars = 0
            difficulty_match = re.search(r'预估烹饪难度：([★☆]+)', content)
            if difficulty_match:
                difficulty_str = difficulty_match.group(1)
                difficulty_stars = len([char for char in difficulty_str if char == '★'])

            difficulty_map = {0: 'simple', 1: 'simple', 2: 'easy', 3: 'medium', 4: 'hard', 5: 'expert'}
            difficulty = difficulty_map.get(difficulty_stars, 'medium')

            # 提取预计时间
            time_match = re.search(r'大约\s*(\d+)\s*分钟可以完成制作', content)
            total_time_minutes = int(time_match.group(1)) if time_match else None

            # 提取描述信息
            description = ""
            # 找到标题和第一个二级标题之间的文本
            header_end = content.find('\n', content.find('#'))
            if header_end != -1:
                section_header_pos = content.find('\n## ', header_end)
                desc_section = content[header_end:section_header_pos] if section_header_pos != -1 else content[header_end:]
                # 找到非标题、非列表的简短描述
                lines = desc_section.split('\n')
                desc_parts = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#') and not line.startswith('- ') and not line.startswith('* '):
                        if not line.startswith('预估') and '难度' not in line and '分钟' not in line:
                            desc_parts.append(line)
                    elif line.startswith('##'):  # 遇到下一个标题停止
                        break
                description = ' '.join(desc_parts[:3])

            # 提取食材信息
            ingredients = self._extract_ingredients_from_markdown(content)

            # 提取步骤信息
            steps = self._extract_steps_from_markdown(content)

            # 提取分类信息（从文件路径）
            category = Path(file_path).parent.name.lower()
            if category in ['aquatic', 'breakfast', 'condiment', 'dessert', 'drink', 'meat_dish', 'semi-finished', 'soup', 'staple', 'vegetable_dish']:
                tags = [category]
            else:
                tags = []

            # 返回标准化的菜谱数据
            recipe_data = {
                'name': name,
                'ingredients': ingredients,
                'cooking_steps': steps,
                'source': f"howtocook:{category}",
                'tags': tags,
                'total_time_minutes': total_time_minutes,
                'difficulty': difficulty,
                'servings': 1,
                'tips': [description] if description else []
            }

            return recipe_data
        except Exception as e:
            print(f"解析 Markdown 菜谱文件 {file_path} 失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def _extract_ingredients_from_markdown(self, content: str) -> List[Dict]:
        """
        从 Markdown 菜谱中提取食材信息
        """
        ingredients = []

        # 查找"计算"部分的内容（通常包含用量信息）
        calc_section_match = re.search(r'## 计算\s*\n((?:- .*\n?)*?(?=\n## |\Z))', content, re.IGNORECASE)
        if not calc_section_match:
            # 如果找不到"计算"部分，尝试"必备原料和工具"部分
            calc_section_match = re.search(r'## 必备原料和工具\s*\n((?:- .*\n?)*?(?=\n## |\Z))', content, re.IGNORECASE)

        if calc_section_match:
            calc_content = calc_section_match.group(1)
            lines = calc_content.split('\n')

            for line in lines:
                line = line.strip()
                if line.startswith('- '):
                    ingredient_line = line[2:]  # 移除"- "前缀
                    parsed_ing = self._parse_ingredient_from_line(ingredient_line)
                    if parsed_ing:
                        ingredients.append(parsed_ing)

        return ingredients

    def _parse_ingredient_from_line(self, ingredient_line: str) -> Optional[Dict]:
        """
        从单行解析食材信息
        """
        import re

        # 移除注释部分（括号内的内容）
        clean_line = re.sub(r'\([^)]*\)', '', ingredient_line).strip()

        # 提取食材名称和数量信息
        # 尝试匹配 "食材名 数量 单位" 的模式
        # 如："土豆 2 个（每个土豆大约重 120g，共约 240g）" -> 食材名:土豆, 数量:2, 单位:个
        match = re.match(r'^([^(]+?)\s+([\d\.]+)\s*([^\s\d\(\)]+)', clean_line)

        if match:
            name = match.group(1).strip()
            quantity = match.group(2).strip()
            unit = match.group(3).strip()
            return {
                'ingredient_name': name,
                'quantity': quantity,
                'unit': unit
            }
        else:
            # 如果上述模式不匹配，尝试其他模式
            # 例如："海盐（研磨装）" 或 "阿根廷红虾 2-3 只"
            parts = clean_line.split()
            if len(parts) >= 2:
                name = parts[0]
                # 查找数量和单位
                quantity = ""
                unit = ""

                for part in parts[1:]:
                    num_match = re.search(r'(\d+\.?\d*)', part)
                    if num_match:
                        quantity = num_match.group(1)

                    # 查找单位
                    unit_match = re.search(r'(g|kg|mg|ml|l|个|只|块|片|条|根|瓣|勺|杯|碗|克|升|毫升|斤|两|枚|段|瓣|把|棵|颗|粒|条|支|盒|袋|瓶|包|罐)', part)
                    if unit_match:
                        unit = unit_match.group(1)

                if quantity and unit:
                    return {
                        'ingredient_name': name,
                        'quantity': quantity,
                        'unit': unit
                    }

            # 如果仍然无法解析，至少返回名称
            name = clean_line.split()[0] if clean_line.split() else clean_line
            return {
                'ingredient_name': name,
                'quantity': "",
                'unit': ""
            }

    def _extract_steps_from_markdown(self, content: str) -> List[Dict]:
        """
        从 Markdown 菜谱中提取步骤信息
        """
        steps = []

        # 查找"操作"部分的内容
        steps_section_match = re.search(r'## 操作\s*\n((?:- .*\n?)*?(?=\n## |\Z))', content, re.IGNORECASE)
        if steps_section_match:
            steps_content = steps_section_match.group(1)
            lines = steps_content.split('\n')

            for idx, line in enumerate(lines):
                line = line.strip()
                if line.startswith('- '):
                    step_content = line[2:].strip()  # 移除"- "前缀
                    if step_content:
                        steps.append({
                            'step': idx + 1,
                            'content': step_content
                        })

        return steps

    def _normalize_recipe_data(self, raw_data: Dict, source_file: str) -> Optional[Dict]:
        """
        标准化菜谱数据格式
        """
        try:
            # 根据可能的数据结构进行标准化
            normalized = {}

            # 尝试不同的键名来获取菜谱名称
            name_keys = ['name', 'title', 'dish_name', 'recipe_name']
            for key in name_keys:
                if key in raw_data:
                    normalized['name'] = raw_data[key]
                    break
            else:
                # 如果找不到名称，使用文件名作为名称
                normalized['name'] = Path(source_file).stem.replace('_', ' ').replace('-', ' ')

            # 获取原料信息
            ingredients_list = []

            # 尝试不同的原料键名
            ingredients_keys = ['ingredients', 'materials', 'materials_list', 'items', 'steps']
            ingredients_raw = None
            for key in ingredients_keys:
                if key in raw_data:
                    ingredients_raw = raw_data[key]
                    break

            if ingredients_raw and isinstance(ingredients_raw, list):
                for ingredient_item in ingredients_raw:
                    if isinstance(ingredient_item, str):
                        # 如果是字符串，尝试分离数量和名称
                        ingredient_parsed = self._parse_ingredient_from_string(ingredient_item)
                        if ingredient_parsed:
                            ingredients_list.append(ingredient_parsed)
                    elif isinstance(ingredient_item, dict):
                        # 如果是字典，尝试提取相关信息
                        ingredient_parsed = self._parse_ingredient_from_dict(ingredient_item)
                        if ingredient_parsed:
                            ingredients_list.append(ingredient_parsed)
            # 如果在顶层直接有ingredients字段，也尝试处理
            elif 'ingredients' in raw_data and isinstance(raw_data['ingredients'], list):
                for ingredient_item in raw_data['ingredients']:
                    if isinstance(ingredient_item, str):
                        ingredient_parsed = self._parse_ingredient_from_string(ingredient_item)
                        if ingredient_parsed:
                            ingredients_list.append(ingredient_parsed)
                    elif isinstance(ingredient_item, dict):
                        ingredient_parsed = self._parse_ingredient_from_dict(ingredient_item)
                        if ingredient_parsed:
                            ingredients_list.append(ingredient_parsed)

            normalized['ingredients'] = ingredients_list

            # 获取步骤信息
            steps_list = []

            # 尝试不同的步骤键名
            steps_keys = ['steps', 'instructions', 'procedure', 'methods', 'cooking_steps']
            steps_raw = None
            for key in steps_keys:
                if key in raw_data:
                    steps_raw = raw_data[key]
                    break

            if steps_raw and isinstance(steps_raw, list):
                for idx, step_item in enumerate(steps_raw):
                    if isinstance(step_item, str):
                        steps_list.append({
                            'step': idx + 1,
                            'content': step_item
                        })
                    elif isinstance(step_item, dict) and 'content' in step_item:
                        steps_list.append({
                            'step': step_item.get('step', idx + 1),
                            'content': step_item.get('content', ''),
                            'duration_minutes': step_item.get('duration_minutes')
                        })
            # 如果在顶层直接有cooking_steps字段，也尝试处理
            elif 'cooking_steps' in raw_data and isinstance(raw_data['cooking_steps'], list):
                for idx, step_item in enumerate(raw_data['cooking_steps']):
                    if isinstance(step_item, str):
                        steps_list.append({
                            'step': idx + 1,
                            'content': step_item
                        })
                    elif isinstance(step_item, dict) and 'content' in step_item:
                        steps_list.append({
                            'step': step_item.get('step', idx + 1),
                            'content': step_item.get('content', ''),
                            'duration_minutes': step_item.get('duration_minutes')
                        })

            normalized['cooking_steps'] = steps_list

            # 其他字段
            normalized['source'] = f"howtocook:{Path(source_file).parent.name or 'unknown'}"
            normalized['tags'] = raw_data.get('tags', [])
            if 'category' in raw_data:
                normalized['tags'].append(raw_data['category'])
            elif 'type' in raw_data:
                normalized['tags'].append(raw_data['type'])

            normalized['total_time_minutes'] = raw_data.get('time', raw_data.get('total_time_minutes', raw_data.get('totalTime')))
            normalized['difficulty'] = raw_data.get('difficulty', raw_data.get('level', raw_data.get('difficulty', 'simple')))
            normalized['servings'] = raw_data.get('servings', raw_data.get('people', raw_data.get('yield', 1)))
            normalized['tips'] = raw_data.get('tips', raw_data.get('notes', raw_data.get('remark', [])))

            return normalized
        except Exception as e:
            print(f"标准化菜谱数据失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def _parse_ingredient_from_string(self, ingredient_str: str) -> Optional[Dict]:
        """
        从字符串解析原料信息
        """
        try:
            # 简单的字符串解析，例如："盐 5克" 或 "500g 鸡腿"
            parts = ingredient_str.strip().split()
            if len(parts) >= 2:
                # 假设最后一个部分是单位，前面的是名称
                quantity = parts[-2] if len(parts) >= 3 else parts[0]
                unit = parts[-1]
                name_parts = parts[:-2] if len(parts) >= 3 else parts[1:]
                name = ' '.join(name_parts) if name_parts else parts[0]
            else:
                name = parts[0] if parts else ingredient_str
                quantity = ""
                unit = ""

            # 尝试从数量中分离数值和单位
            import re
            match = re.search(r'(\d+(?:\.\d+)?)\s*([a-zA-Z\u4e00-\u9fa5]*)', quantity)
            if match:
                quantity = match.group(1)
                if not unit:  # 如果之前没有提取到单位，使用这里提取的
                    unit = match.group(2)

            return {
                'ingredient_name': name.strip(),
                'quantity': quantity,
                'unit': unit
            }
        except Exception:
            # 如果解析失败，返回基本结构
            return {
                'ingredient_name': ingredient_str.strip(),
                'quantity': "",
                'unit': ""
            }

    def _parse_ingredient_from_dict(self, ingredient_dict: Dict) -> Optional[Dict]:
        """
        从字典解析原料信息
        """
        try:
            name_keys = ['name', 'ingredient', 'item', 'material']
            quantity_keys = ['quantity', 'amount', 'qty', 'num']
            unit_keys = ['unit', 'measure_unit']

            name = ""
            for key in name_keys:
                if key in ingredient_dict:
                    name = ingredient_dict[key]
                    break

            quantity = ""
            for key in quantity_keys:
                if key in ingredient_dict:
                    quantity = str(ingredient_dict[key])
                    break

            unit = ""
            for key in unit_keys:
                if key in ingredient_dict:
                    unit = ingredient_dict[key]
                    break

            return {
                'ingredient_name': name,
                'quantity': quantity,
                'unit': unit
            }
        except Exception:
            return None

    def _import_single_recipe(self, recipe_data: Dict) -> bool:
        """
        导入单个菜谱
        """
        try:
            # 检查是否已存在同名菜谱
            existing_recipe = self.db.query(Recipe).filter(
                Recipe.name == recipe_data['name'],
                Recipe.source.like('howtocook:%')
            ).first()

            if existing_recipe:
                print(f"菜谱 {recipe_data['name']} 已存在，跳过导入")
                return True  # 视为成功，因为已存在

            # 构建菜谱对象
            recipe_create = RecipeCreate(
                name=recipe_data['name'],
                source=recipe_data['source'],
                tags=recipe_data.get('tags', []),
                cooking_steps=[
                    CookingStep(
                        step=item.get('step', idx + 1),
                        content=item['content'],
                        duration_minutes=item.get('duration_minutes')
                    ) for idx, item in enumerate(recipe_data.get('cooking_steps', []))
                ],
                ingredients=[
                    RecipeIngredientCreate(
                        ingredient_name=self._match_or_create_ingredient(item['ingredient_name']),
                        quantity=item.get('quantity', ''),
                        unit=item.get('unit', '')
                    ) for item in recipe_data.get('ingredients', [])
                ],
                total_time_minutes=recipe_data.get('total_time_minutes'),
                difficulty=recipe_data.get('difficulty', 'simple'),
                servings=recipe_data.get('servings', 1),
                tips=recipe_data.get('tips', [])
            )

            # 创建菜谱
            db_recipe = Recipe(
                name=recipe_create.name,
                source=recipe_create.source,
                user_id=1,  # 使用默认用户ID，稍后可以根据需要调整
                tags=recipe_create.tags,
                cooking_steps=[s.model_dump() for s in recipe_create.cooking_steps],
                total_time_minutes=recipe_create.total_time_minutes,
                difficulty=recipe_create.difficulty,
                servings=recipe_create.servings,
                tips=recipe_create.tips
            )

            self.db.add(db_recipe)
            self.db.flush()

            # 添加原料
            for ingredient_data in recipe_create.ingredients:
                # 查找原料
                ingredient = self.db.query(Ingredient).filter(
                    Ingredient.name == ingredient_data.ingredient_name
                ).first()

                if ingredient:
                    recipe_ingredient = RecipeIngredient(
                        recipe_id=db_recipe.id,
                        ingredient_id=ingredient.id,
                        quantity=ingredient_data.quantity,
                        unit=ingredient_data.unit
                    )
                    self.db.add(recipe_ingredient)
                else:
                    print(f"警告: 未找到原料 {ingredient_data.ingredient_name}")

            self.db.commit()
            print(f"成功导入菜谱: {recipe_data['name']}")
            return True

        except IntegrityError:
            self.db.rollback()
            print(f"菜谱 {recipe_data.get('name', 'Unknown')} 已存在")
            return True  # 视为成功，因为已存在
        except Exception as e:
            self.db.rollback()
            print(f"导入菜谱失败 {recipe_data.get('name', 'Unknown')}: {str(e)}")
            return False

    def _match_or_create_ingredient(self, ingredient_name: str) -> str:
        """
        匹配现有原料或创建新原料
        """
        # 尝试精确匹配（去除首尾空格并标准化大小写）
        clean_name = ingredient_name.strip()

        ingredient = self.db.query(Ingredient).filter(
            Ingredient.name == clean_name
        ).first()

        if ingredient:
            return ingredient.name

        # 如果没有找到，创建新的原料
        try:
            new_ingredient = Ingredient(
                name=clean_name,
                aliases=[]
            )
            self.db.add(new_ingredient)
            self.db.flush()  # 确保插入但不提交事务
            return clean_name
        except IntegrityError:
            # 如果在并发情况下另一个事务已经添加了相同的原料，则回滚并查询
            self.db.rollback()
            ingredient = self.db.query(Ingredient).filter(
                Ingredient.name == clean_name
            ).first()
            if ingredient:
                return ingredient.name
            else:
                # 如果仍然没有找到，返回原始清洁后的名称
                return clean_name


def check_and_import_initial_recipes(db: Session) -> Dict[str, any]:
    """
    检查是否需要导入初始菜谱
    """
    # 检查是否有任何菜谱来自 howtocook 源
    recipe_exists = db.query(Recipe).filter(
        Recipe.source.like('howtocook:%')
    ).first() is not None

    if not recipe_exists:
        print("未发现 HowToCook 菜谱，开始导入...")
        import_service = RecipeImportService(db)
        return import_service.import_recipes_from_cook_repo()
    else:
        print("HowToCook 菜谱已存在，跳过导入")
        return {
            "success": True,
            "message": "HowToCook 菜谱已存在，跳过导入"
        }