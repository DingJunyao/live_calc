"""AI 后处理：模糊量推测 + 密度推测。"""
import json
from typing import Optional, Callable

from sqlalchemy.orm import Session

from app.models.entity_density import EntityDensity
from app.models.nutrition import Ingredient
from app.models.recipe import RecipeIngredient
from app.services.importer.models import ImportResult


class AIInferrer:
    """用 AI 推测原料的模糊用量和密度。

    复用后端现有的 AI 配置，不直接发起 HTTP 请求。
    通过一个抽象的 _call_ai(prompt) 方法，让上层注入具体的 AI 调用实现。
    """

    def __init__(self, db: Session, ai_caller=None):
        self.db = db
        self.ai_caller = ai_caller

    def set_ai_caller(self, caller):
        """注入 AI 调用函数。接收 prompt 字符串，返回响应文本。"""
        self.ai_caller = caller

    # ----------------------------------------------------------------
    # 模糊量推测
    # ----------------------------------------------------------------

    def infer_fuzzy_quantities(self, force: bool = False,
                                progress_callback: Optional[Callable] = None) -> ImportResult:
        """推测菜谱原料的模糊量。

        扫描所有 RecipeIngredient，筛选出：
        1. 用量单位是计数单位（unit_system == 'count'）且原料没有 piece_weight
        2. 用量为 NULL 或 original_quantity 为"适量""少许"

        按 (ingredient_id, unit_id) 分组去重，每组问 AI 一次。
        """
        result = ImportResult()

        candidates = self._find_fuzzy_candidates(force)
        if not candidates:
            result.warnings.append("没有需要推测的模糊量条目")
            return result

        # 按 (ingredient_id, unit_id) 分组
        groups = {}
        for ri in candidates:
            key = (ri.ingredient_id, ri.unit_id)
            if key not in groups:
                groups[key] = {
                    "ingredient": self.db.query(Ingredient).get(ri.ingredient_id),
                    "unit_id": ri.unit_id,
                    "recipe_ingredients": [],
                }
            groups[key]["recipe_ingredients"].append(ri)

        total_groups = len(groups)
        inferred = 0
        for idx, ((ing_id, unit_id), group) in enumerate(groups.items(), 1):
            ingredient = group["ingredient"]
            if not ingredient:
                continue

            if progress_callback:
                progress_callback("模糊量推测", idx, total_groups,
                                  ingredient.name)

            recipes = [ri.recipe.name for ri in group["recipe_ingredients"]
                       if ri.recipe and ri.recipe.name]
            context = "、".join(set(recipes)) if recipes else "未知菜谱"
            prompt = self._build_quantity_prompt(
                ingredient.name, unit_id, context
            )

            try:
                response_text = self.ai_caller(prompt) if self.ai_caller else None
                if not response_text:
                    continue

                parsed = json.loads(response_text)
                piece_weight = parsed.get("piece_weight_g")
                default_quantity = parsed.get("default_quantity_g")

                # 如果有 piece_weight，更新原料
                if piece_weight is not None and ingredient.piece_weight is None:
                    ingredient.piece_weight = piece_weight
                    ingredient.ai_inferred = True
                    self.db.flush()

                # 如果有 default_quantity，更新各菜谱条目的 quantity_range
                if default_quantity is not None:
                    for ri in group["recipe_ingredients"]:
                        if ri.quantity is None and not ri.quantity_range:
                            ri.quantity_range = {"min": 0, "max": default_quantity}
                            ri.ai_inferred = True
                        ri.ai_inferred = True
                        self.db.flush()
                else:
                    for ri in group["recipe_ingredients"]:
                        ri.ai_inferred = True
                        self.db.flush()

                inferred += 1

            except (json.JSONDecodeError, Exception) as e:
                result.errors.append(
                    f"推测失败 {ingredient.name}(id={ing_id}): {str(e)}"
                )

        self.db.commit()
        result.stats["fuzzy_quantities"] = inferred
        return result

    def _find_fuzzy_candidates(self, force: bool = False):
        """筛选需要推测模糊量的 RecipeIngredient 条目。"""
        query = self.db.query(RecipeIngredient).join(Ingredient)

        if not force:
            query = query.filter(RecipeIngredient.ai_inferred == False)

        candidates = query.all()

        result = []
        for ri in candidates:
            ingredient = ri.ingredient
            if not ingredient:
                continue

            need_infer = False

            # 场景 1：计数单位但没有 piece_weight
            if ri.unit_id and ingredient.piece_weight is None:
                if self._is_countable_unit(ri.unit_id):
                    need_infer = True

            # 场景 2：用量为空或模糊文本
            if ri.quantity is None and not ri.quantity_range:
                need_infer = True
            elif ri.original_quantity:
                text = ""
                if isinstance(ri.original_quantity, dict):
                    text = ri.original_quantity.get("text", "")
                elif isinstance(ri.original_quantity, str):
                    text = ri.original_quantity
                if text in ("适量", "少许", "少量"):
                    need_infer = True

            if need_infer:
                result.append(ri)

        return result

    def _is_countable_unit(self, unit_id: int) -> bool:
        """判断单位是否为计数单位（unit_system == 'count'）。"""
        from app.models.unit import Unit
        unit = self.db.query(Unit).get(unit_id)
        return unit is not None and unit.unit_system == "count"

    def _build_quantity_prompt(self, ingredient_name: str,
                                unit_id: int, context: str) -> str:
        """构建模糊量推测的 AI Prompt。"""
        unit_name = ""
        if unit_id:
            from app.models.unit import Unit
            unit = self.db.query(Unit).get(unit_id)
            unit_name = unit.name if unit else ""
        return (
            f"请推测以下食材在常见菜谱中的典型用量：\n"
            f"- 食材：{ingredient_name}\n"
            f"- 单位：{unit_name or '无'}\n"
            f"- 出现于菜谱：{context}\n\n"
            f"请推测每个\"{unit_name or '份'}\"相当于多少克（piece_weight_g），"
            f"以及如果该食材用量为\"适量\"时大约是多少克（default_quantity_g，若无则为 null）。\n"
            f"返回 JSON：{{\"piece_weight_g\": 数值或null, "
            f"\"default_quantity_g\": 数值或null}}"
        )

    # ----------------------------------------------------------------
    # 密度推测
    # ----------------------------------------------------------------

    def infer_densities(self, force: bool = False,
                         progress_callback: Optional[Callable] = None) -> ImportResult:
        """推测没有密度值的原料的密度，写入 entity_densities 表（kg/m³）。"""
        result = ImportResult()

        # 找出缺少 density 的原料（与 entity_densities 左连接）
        from sqlalchemy import not_
        existing_ids = (
            self.db.query(EntityDensity.entity_id)
            .filter(EntityDensity.entity_type == 'ingredient', EntityDensity.condition.is_(None))
            .subquery()
        )
        query = self.db.query(Ingredient).filter(
            Ingredient.is_active == True,
            not_(Ingredient.id.in_(existing_ids)),
        )

        candidates = query.all()
        if not candidates:
            result.warnings.append("没有需要推测密度的原料（entity_densities 均已覆盖）")
            return result

        total = len(candidates)
        inferred = 0
        for idx, ingredient in enumerate(candidates, 1):
            if progress_callback:
                progress_callback("密度推测", idx, total,
                                  f"{ingredient.name} ({idx}/{total})")
            prompt = (
                f"请推测食材\"{ingredient.name}\"的密度（g/cm³），"
                f"即每毫升多少克。\n"
                f"常见参考：水=1.0，食用油≈0.92，蜂蜜≈1.4，面粉≈0.55。\n"
                f"返回 JSON：{{\"density_g_per_cm3\": 数值}}"
            )

            try:
                response_text = self.ai_caller(prompt) if self.ai_caller else None
                if not response_text:
                    continue

                parsed = json.loads(response_text)
                density = parsed.get("density_g_per_cm3")
                if density is not None:
                    # AI 返回 g/cm³，entity_densities 需 kg/m³（×1000）
                    ed = EntityDensity(
                        entity_type='ingredient',
                        entity_id=ingredient.id,
                        density=round(density * 1000, 6),
                        temperature=20.0,
                        source='ai_inferrer',
                        confidence=0.8,
                    )
                    self.db.add(ed)
                    inferred += 1

            except (json.JSONDecodeError, Exception) as e:
                result.errors.append(
                    f"密度推测失败 {ingredient.name}(id={ingredient.id}): {str(e)}"
                )

        self.db.commit()
        result.stats["densities"] = inferred
        return result
