# 营养贡献溯源中计数单位无 piece_weight 导致高估

## 问题

菜谱分析页「营养贡献溯源」中，使用计数单位（如花椒 20 颗、蒜 2 瓣、姜 2 片等）的食材营养贡献值异常偏高。例如花椒蛋白质贡献显示 10.4g，超过其实际用量数倍。

## 根因

`backend/app/services/recipe_service.py` 的 `calculate_recipe_nutrition` 函数中有两层问题：

1. **主因**：计数单位（`unit_type == "count"`）未设 `ingredient.piece_weight` 时 ratio 回退为 `Decimal("1.0")`，把计数数量当作营养基准量（通常 100g）计算贡献。
   - 花椒 20 颗，营养数据蛋白质 10.4g/100g → 贡献 = 10.4 × 1.0 = **10.4g**（荒谬）
   - 实际上 1 颗花椒约 0.2g，20 颗约 4g，合理贡献应为 10.4 × 4/100 = 0.416g

2. **遗漏**：代码只查 `ingredient.piece_weight`，不查 `entity_unit_overrides` 表——而用户可以在原料详情页「自定义单位」中维护每件标准重量（如 1 颗=0.2g）。该表已有 258 条记录，但营养计算从未使用。

## 影响范围

- Recipe 351（麻婆豆腐）大部分食材使用计数单位（内酯豆腐/盒、咸鸭蛋/枚、蒜/瓣、姜/片、小米辣/根、花椒/颗）
- `nutrition_calculator.py` 无此问题（不含相同的 ratio 回退逻辑）
- 成本计算不影响（走不同的流程）

## 修复

`recipe_service.py:1821-1854`：计数单位无 `piece_weight` 时，先查 `entity_unit_overrides` 获取用户维护的每件标准重量；有则计算比例，无则 ratio=0。

```python
# 改前
else:
    # 没有设置标准重量，假设比例是1:1
    ratio = Decimal("1.0")

# 改后
else:
    # 查 entity_unit_overrides 自定义单位表
    from app.models.entity_unit_override import EntityUnitOverride
    entity_override = db.query(EntityUnitOverride).filter(
        EntityUnitOverride.entity_type == "ingredient",
        EntityUnitOverride.entity_id == ingredient.id,
        EntityUnitOverride.unit_name == recipe_ingredient.unit.abbreviation,
        EntityUnitOverride.weight_per_unit.isnot(None),
        EntityUnitOverride.weight_unit_id.isnot(None)
    ).first()
    if entity_override and entity_override.weight_per_unit:
        # 使用自定义单位中维护的每件标准重量
        weight_unit = db.query(Unit).filter(Unit.id == entity_override.weight_unit_id).first()
        if weight_unit:
            converted_weight, converted_unit = convert_to_standard(
                Decimal(str(entity_override.weight_per_unit)),
                weight_unit.abbreviation
            )
            total_weight = quantity * converted_weight
            if converted_unit.lower() == reference_unit.lower():
                ratio = total_weight / reference_amount
            else:
                weight_unit_obj = db.query(Unit).filter(Unit.abbreviation == converted_unit).first()
                if weight_unit_obj and weight_unit_obj.unit_type == "mass":
                    ratio = total_weight / reference_amount
                else:
                    ratio = Decimal("0")
        else:
            ratio = Decimal("0")
    else:
        # 没有维护每件标准重量，无法将计数单位换算为质量
        ratio = Decimal("0")
```

## 后续建议

推荐为常用食材在原料详情页继续维护自定义单位的每件标准重量。当前 fix 会优先使用这些数据，没有再回退 0。

## 关联记忆
- [[成本计算单位转换 & substitutable 回退]]
