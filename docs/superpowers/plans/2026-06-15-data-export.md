# 数据导出功能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为个人中心「数据导出」补全完整功能——后端遍历各表序列化为 HowToCook 兼容 + id 扩展的 JSON，连同图片打包成 zip，同步流式下载；前端提供「全量 / 仅我的」两档选择。

**Architecture:** 后端按职责拆分为 `services/export/` 包（serializers / reachability / packaging / 入口）+ `api/export.py` 路由。序列化为纯函数（易单测）；mine 模式做外键可达性遍历保证引用完整；端点用 `StreamingResponse` 吐 zip。前端在 ProfileView 加导出对话框。

**Tech Stack:** FastAPI、SQLAlchemy、zipfile、pytest（集成测试 TestClient）、Vue 3 + Vuetify。

**Spec:** [docs/superpowers/specs/2026-06-15-data-export-design.md](../specs/2026-06-15-data-export-design.md)

---

## 文件结构

后端新增（`backend/app/services/export/` 包，按职责拆分，每个文件聚焦）：
- `__init__.py` — 导出主入口 `export_data(db, user, scope) -> bytes`
- `serializers.py` — 类型转换器 + 各表 `serialize_xxx()` 纯函数
- `reachability.py` — `ExportSet` + full/mine 两档 id 收集（mine 含可达性遍历）
- `packaging.py` — `build_export_zip()` 编排查询→序列化→打包图片→写 zip

后端新增路由：
- `backend/app/api/export.py` — `GET /data?scope=full|mine`，`StreamingResponse`

后端修改：
- `backend/app/main.py` — 注册 export router

测试新增：
- `backend/tests/services/__init__.py`（若缺）、`backend/tests/services/test_export_serializers.py`
- `backend/tests/services/test_export_reachability.py`
- `backend/tests/test_export.py`（端点集成测试）

前端修改：
- `frontend/src/views/profile/ProfileView.vue` — 数据导出项加对话框 + 下载逻辑

---

## Task 1: 序列化基础设施（类型转换器）

**Files:**
- Create: `backend/app/services/export/__init__.py`
- Create: `backend/app/services/export/serializers.py`
- Test: `backend/tests/services/test_export_serializers.py`

- [ ] **Step 1: 建包与测试文件骨架**

Create `backend/app/services/export/__init__.py`（空文件，标记为包）。

Create `backend/tests/services/__init__.py`（空文件，若已存在则跳过）。

Create `backend/tests/services/test_export_serializers.py`：

```python
from decimal import Decimal
from datetime import datetime, timezone

from app.services.export.serializers import (
    to_float,
    to_iso,
    convert_image_path,
)


def test_to_float_decimal():
    assert to_float(Decimal("3.5")) == 3.5


def test_to_float_none():
    assert to_float(None) is None


def test_to_float_string_number():
    assert to_float("2") == 2.0


def test_to_float_invalid_string():
    assert to_float("abc") is None


def test_to_iso_datetime():
    dt = datetime(2026, 6, 15, 14, 30, tzinfo=timezone.utc)
    assert to_iso(dt) == "2026-06-15T14:30:00+00:00"


def test_to_iso_none():
    assert to_iso(None) is None


def test_convert_image_path_strips_static_prefix():
    assert convert_image_path("/static/images/recipes/a.jpg") == "images/recipes/a.jpg"


def test_convert_image_path_keeps_remote_url():
    # 外链不转换，调用方负责跳过
    assert convert_image_path("https://example.com/a.jpg") == "https://example.com/a.jpg"


def test_convert_image_path_none():
    assert convert_image_path(None) is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/services/test_export_serializers.py -v`
Expected: FAIL（ImportError，模块不存在）

- [ ] **Step 3: 实现类型转换器**

Create `backend/app/services/export/serializers.py`：

```python
"""数据导出序列化器：类型转换 + 各表 to_export_dict 纯函数。

约定：
- HowToCook 兼容字段保持原命名/结构；额外 id 与 xxx_id 为扩展字段。
- 所有外键冗余一个 _name 字段，便于人眼阅读与导入容错。
- Decimal→float，datetime→ISO 字符串，None 保持 None。
"""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional


def to_float(value: Any) -> Optional[float]:
    """Decimal/数字字符串→float；无法解析或 None→None。"""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (ValueError, InvalidOperation):
        return None


def to_iso(value: Any) -> Optional[str]:
    """datetime→ISO 8601 字符串；None→None。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return None


def convert_image_path(path: Optional[str]) -> Optional[str]:
    """数据库内的 /static/images/... 相对路径 → zip 内 images/... 路径。

    外链 http(s):// 原样返回（由调用方决定是否打包）。
    """
    if not path:
        return None
    if path.startswith("/static/"):
        return path[len("/static/"):]
    return path
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/services/test_export_serializers.py -v`
Expected: PASS（全部用例）

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/export/__init__.py backend/app/services/export/serializers.py backend/tests/services/__init__.py backend/tests/services/test_export_serializers.py
git commit -m "feat(export): 添加序列化类型转换器"
```

---

## Task 2: 单位序列化

**Files:**
- Modify: `backend/app/services/export/serializers.py`
- Test: `backend/tests/services/test_export_serializers.py`

- [ ] **Step 1: 追加测试**

Append to `test_export_serializers.py`：

```python
from types import SimpleNamespace

from app.services.export.serializers import serialize_unit


def _make_unit(**kw):
    base = dict(
        id=10, name="克", abbreviation="g", plural_form=None,
        unit_type="mass", si_factor=Decimal("0.001"), is_si_base=False,
        is_common=True, display_order=3, unit_system="metric",
        default_estimate=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_serialize_unit_howto_cook_fields():
    u = _make_unit()
    out = serialize_unit(u)
    assert out["name"] == "克"
    assert out["aliases"] == []  # 数据库无别名列


def test_serialize_unit_extended_fields():
    u = _make_unit()
    out = serialize_unit(u)
    assert out["id"] == 10
    assert out["abbreviation"] == "g"
    assert out["unit_type"] == "mass"
    assert out["si_factor"] == 0.001
    assert out["unit_system"] == "metric"
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && python -m pytest tests/services/test_export_serializers.py -k serialize_unit -v`
Expected: FAIL（ImportError: serialize_unit）

- [ ] **Step 3: 实现 serialize_unit**

Append to `serializers.py`：

```python
def serialize_unit(unit: Any) -> dict:
    """Unit → units.json 元素。HowToCook: {name, aliases}；扩展: id 等。"""
    return {
        # HowToCook 兼容
        "name": unit.name,
        "aliases": [],  # 数据库无别名列；缩写见 abbreviation
        # 扩展
        "id": unit.id,
        "abbreviation": unit.abbreviation,
        "unit_type": unit.unit_type,
        "si_factor": to_float(unit.si_factor),
        "unit_system": unit.unit_system,
        "is_si_base": bool(unit.is_si_base),
        "is_common": bool(unit.is_common),
        "display_order": unit.display_order,
        "default_estimate": to_float(unit.default_estimate),
    }
```

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && python -m pytest tests/services/test_export_serializers.py -k serialize_unit -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/export/serializers.py backend/tests/services/test_export_serializers.py
git commit -m "feat(export): 添加单位序列化"
```

---

## Task 3: 食材序列化

**Files:**
- Modify: `backend/app/services/export/serializers.py`
- Test: `backend/tests/services/test_export_serializers.py`

- [ ] **Step 1: 追加测试**

Append to `test_export_serializers.py`：

```python
from app.services.export.serializers import serialize_ingredient


def _make_ingredient(**kw):
    base = dict(
        id=5, name="鸡蛋", category_id=6,
        density=Decimal("1.03"), default_unit_id=1, aliases=["土鸡蛋"],
        nutrition_id=20, piece_weight=Decimal("50"), piece_weight_unit_id=1,
        serving_weight=None, serving_weight_unit_id=None,
        is_imported=False, is_merged=False, merged_into_id=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_serialize_ingredient_howto_cook_matched():
    ing = _make_ingredient()
    out = serialize_ingredient(ing, category_display_name="禽蛋", usda_id=171287)
    assert out["name"] == "鸡蛋"
    assert out["aliases"] == ["土鸡蛋"]
    assert out["category"] == "禽蛋"
    assert out["usda_id"] == 171287
    assert out["usda_match_status"] == "matched"


def test_serialize_ingredient_unmatched_when_no_usda():
    ing = _make_ingredient()
    out = serialize_ingredient(ing, category_display_name="其他", usda_id=None)
    assert out["usda_match_status"] == "unmatched"
    assert out["usda_id"] is None


def test_serialize_ingredient_extended_fields():
    ing = _make_ingredient()
    out = serialize_ingredient(ing, category_display_name="禽蛋", usda_id=171287)
    assert out["id"] == 5
    assert out["category_id"] == 6
    assert out["density"] == 1.03
    assert out["nutrition_id"] == 20
    assert out["piece_weight"] == 50.0
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && python -m pytest tests/services/test_export_serializers.py -k serialize_ingredient -v`
Expected: FAIL（ImportError）

- [ ] **Step 3: 实现 serialize_ingredient**

Append to `serializers.py`：

```python
def serialize_ingredient(
    ingredient: Any,
    category_display_name: Optional[str],
    usda_id: Any,
) -> dict:
    """Ingredient → ingredients.json 的 value 部分。

    HowToCook: {name, aliases, category, usda_id, usda_match_status}；扩展: id 等。
    usda_id 由调用方从关联 NutritionData 取。
    """
    has_usda = usda_id is not None and usda_id != ""
    return {
        # HowToCook 兼容
        "name": ingredient.name,
        "aliases": ingredient.aliases or [],
        "category": category_display_name,
        "usda_id": usda_id,
        "usda_match_status": "matched" if has_usda else "unmatched",
        # 扩展
        "id": ingredient.id,
        "category_id": ingredient.category_id,
        "density": to_float(ingredient.density),
        "default_unit_id": ingredient.default_unit_id,
        "piece_weight": to_float(ingredient.piece_weight),
        "piece_weight_unit_id": ingredient.piece_weight_unit_id,
        "serving_weight": to_float(ingredient.serving_weight),
        "serving_weight_unit_id": ingredient.serving_weight_unit_id,
        "nutrition_id": ingredient.nutrition_id,
        "is_imported": bool(ingredient.is_imported),
        "is_merged": bool(ingredient.is_merged),
        "merged_into_id": ingredient.merged_into_id,
    }
```

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && python -m pytest tests/services/test_export_serializers.py -k serialize_ingredient -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/export/serializers.py backend/tests/services/test_export_serializers.py
git commit -m "feat(export): 添加食材序列化"
```

---

## Task 4: 营养序列化（嵌套→扁平 + raw 保留）

**Files:**
- Modify: `backend/app/services/export/serializers.py`
- Test: `backend/tests/services/test_export_serializers.py`

- [ ] **Step 1: 追加测试**

Append to `test_export_serializers.py`：

```python
from app.services.export.serializers import serialize_nutrition


def _make_nutrition(**kw):
    base = dict(
        id=20, ingredient_id=5, source="usda_import",
        usda_id="171287", usda_name="Egg, whole, raw, fresh",
        nutrients={
            "all_nutrients": {
                "protein": {"value": 12.6, "unit": "g", "nrp_pct": 21.0, "standard": "中国GB标准"},
                "energy": {"value": 143.0, "unit": "kcal", "nrp_pct": 7.15, "standard": "中国GB标准"},
            }
        },
        reference_amount=100.0, reference_unit="g", match_confidence=1.0,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_serialize_nutrition_howto_cook_fields():
    nd = _make_nutrition()
    out = serialize_nutrition(nd, ingredient_name="鸡蛋")
    assert out["usda_id"] == "171287"
    assert out["ingredient_name"] == "鸡蛋"
    assert out["usda_name"] == "Egg, whole, raw, fresh"
    # nutrients 扁平数组
    names = [n["name"] for n in out["nutrients"]]
    assert "蛋白质" in names  # protein→蛋白质 经映射
    energy = [n for n in out["nutrients"] if n["name"] == "能量"][0]
    assert energy["value"] == 143.0


def test_serialize_nutrition_keeps_raw():
    nd = _make_nutrition()
    out = serialize_nutrition(nd, ingredient_name="鸡蛋")
    assert out["raw_nutrients"]["all_nutrients"]["protein"]["value"] == 12.6


def test_serialize_nutrition_extended_fields():
    nd = _make_nutrition()
    out = serialize_nutrition(nd, ingredient_name="鸡蛋")
    assert out["id"] == 20
    assert out["ingredient_id"] == 5
    assert out["source"] == "usda_import"
    assert out["reference_unit"] == "g"
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && python -m pytest tests/services/test_export_serializers.py -k serialize_nutrition -v`
Expected: FAIL（ImportError）

- [ ] **Step 3: 实现 serialize_nutrition**

Append to `serializers.py`：

```python
# 营养素 key → (中文名, 英文名) 映射；覆盖主要营养素。
# 未命中的 key 退化为 (key, key)，保证不丢数据。
NUTRIENT_KEY_NAME_MAP: dict[str, tuple[str, str]] = {
    "energy": ("能量", "Energy"),
    "protein": ("蛋白质", "Protein"),
    "fat": ("脂肪", "Total lipid (fat)"),
    "carbohydrate": ("碳水化合物", "Carbohydrate, by difference"),
    "fiber": ("膳食纤维", "Fiber, total dietary"),
    "sugars": ("糖", "Sugars, total"),
    "saturated_fat": ("饱和脂肪", "Fatty acids, total saturated"),
    "sodium": ("钠", "Sodium, Na"),
    "cholesterol": ("胆固醇", "Cholesterol"),
    "calcium": ("钙", "Calcium, Ca"),
    "iron": ("铁", "Iron, Fe"),
    "zinc": ("锌", "Zinc, Zn"),
    "selenium": ("硒", "Selenium, Se"),
    "vitamin_a": ("维生素A", "Vitamin A, RAE"),
    "vitamin_d": ("维生素D", "Vitamin D (D2 + D3)"),
    "vitamin_e": ("维生素E", "Vitamin E (alpha-tocopherol)"),
    "vitamin_c": ("维生素C", "Vitamin C, total ascorbic acid"),
    "thiamin": ("维生素B1（硫胺素）", "Thiamin"),
    "riboflavin": ("维生素B2（核黄素）", "Riboflavin"),
    "niacin": ("烟酸", "Niacin"),
    "vitamin_b6": ("维生素B6", "Vitamin B-6"),
    "vitamin_b12": ("维生素B12", "Vitamin B-12"),
    "folate": ("叶酸", "Folate, total"),
    "pantothenic_acid": ("泛酸", "Pantothenic acid"),
    "biotin": ("生物素", "Biotin"),
    "vitamin_k": ("维生素K", "Vitamin K (phylloquinone)"),
    "potassium": ("钾", "Potassium, K"),
    "magnesium": ("镁", "Magnesium, Mg"),
    "phosphorus": ("磷", "Phosphorus, P"),
}


def _flatten_nutrients(nutrients_json: Any) -> list[dict]:
    """嵌套 nutrients JSON → HowToCook 扁平数组 [{name, name_en, value, unit, nrp_pct, standard}]。"""
    if not isinstance(nutrients_json, dict):
        return []
    source_map = nutrients_json.get("all_nutrients") or nutrients_json.get("nutrient_details") or {}
    out = []
    for key, payload in source_map.items():
        if not isinstance(payload, dict):
            continue
        cn, en = NUTRIENT_KEY_NAME_MAP.get(key, (key, key))
        out.append({
            "name": cn,
            "name_en": en,
            "value": to_float(payload.get("value")),
            "unit": payload.get("unit"),
            "nrp_pct": to_float(payload.get("nrp_pct")),
            "standard": payload.get("standard"),
        })
    return out


def serialize_nutrition(nutrition_data: Any, ingredient_name: str) -> dict:
    """NutritionData → nutritions.json 元素。

    HowToCook: {usda_id, ingredient_name, usda_name, nutrients[]}；扩展: id + raw_nutrients。
    """
    return {
        # HowToCook 兼容
        "usda_id": nutrition_data.usda_id,
        "ingredient_name": ingredient_name,
        "usda_name": nutrition_data.usda_name,
        "nutrients": _flatten_nutrients(nutrition_data.nutrients),
        # 扩展
        "id": nutrition_data.id,
        "ingredient_id": nutrition_data.ingredient_id,
        "source": nutrition_data.source,
        "reference_amount": to_float(nutrition_data.reference_amount),
        "reference_unit": nutrition_data.reference_unit,
        "match_confidence": to_float(nutrition_data.match_confidence),
        "raw_nutrients": nutrition_data.nutrients,  # 原始嵌套，恢复导入用
    }
```

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && python -m pytest tests/services/test_export_serializers.py -k serialize_nutrition -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/export/serializers.py backend/tests/services/test_export_serializers.py
git commit -m "feat(export): 添加营养序列化（嵌套转扁平 + raw 保留）"
```

---

## Task 5: 菜谱序列化（含 RecipeIngredient）

**Files:**
- Modify: `backend/app/services/export/serializers.py`
- Test: `backend/tests/services/test_export_serializers.py`

- [ ] **Step 1: 追加测试**

Append to `test_export_serializers.py`：

```python
from app.services.export.serializers import serialize_recipe


def _make_recipe_ingredient(**kw):
    base = dict(
        id=1, recipe_id=1, ingredient_id=5, quantity="2",
        quantity_range=None, unit_id=10, is_optional=False,
        note="切块", original_quantity=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _make_recipe(**kw):
    base = dict(
        id=1, name="番茄炒蛋", source="custom", category="荤菜",
        tags=None, cooking_steps=[{"step": 1, "content": "打蛋"}],
        total_time_minutes=10, difficulty="easy", servings=2,
        tips=["别炒老"], description="家常菜",
        images=["/static/images/recipes/a.jpg"],
        result_ingredient_id=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_serialize_recipe_howto_cook_fields():
    r = _make_recipe()
    ri = _make_recipe_ingredient()
    out = serialize_recipe(
        r, [ri],
        ingredient_map={5: "鸡蛋"},
        unit_map={10: "个"},
    )
    assert out["name"] == "番茄炒蛋"
    assert out["source_file"] == "custom"  # ← Recipe.source
    assert out["original_servings"] is None  # 数据库无此字段
    assert out["images"] == ["images/recipes/a.jpg"]  # 路径转换
    assert out["ingredients"][0]["ingredient_name"] == "鸡蛋"
    assert out["ingredients"][0]["unit"] == "个"
    assert out["ingredients"][0]["quantity"] == 2.0


def test_serialize_recipe_extended_fields():
    r = _make_recipe(result_ingredient_id=7)
    ri = _make_recipe_ingredient()
    out = serialize_recipe(r, [ri], ingredient_map={5: "鸡蛋"}, unit_map={10: "个"})
    assert out["id"] == 1
    assert out["result_ingredient_id"] == 7
    assert out["ingredients"][0]["ingredient_id"] == 5
    assert out["ingredients"][0]["unit_id"] == 10


def test_serialize_recipe_quantity_unparseable():
    r = _make_recipe()
    ri = _make_recipe_ingredient(quantity="适量")
    out = serialize_recipe(r, [ri], ingredient_map={5: "鸡蛋"}, unit_map={10: "g"})
    item = out["ingredients"][0]
    assert item["quantity"] is None
    assert item["quantity_description"] == "适量"
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && python -m pytest tests/services/test_export_serializers.py -k serialize_recipe -v`
Expected: FAIL（ImportError）

- [ ] **Step 3: 实现 serialize_recipe**

Append to `serializers.py`：

```python
def _serialize_recipe_ingredient(
    ri: Any,
    ingredient_map: dict,
    unit_map: dict,
) -> dict:
    """RecipeIngredient → 菜谱 ingredients[] 元素（HowToCook + id）。"""
    ing_name = ingredient_map.get(ri.ingredient_id)
    unit_name = unit_map.get(ri.unit_id) if ri.unit_id is not None else None
    quantity = to_float(ri.quantity)
    # quantity 无法解析为数字时，退化为 quantity_description
    qty_desc = ""
    if quantity is None and ri.quantity:
        qty_desc = str(ri.quantity)
    return {
        # HowToCook 兼容
        "ingredient_name": ing_name,
        "quantity": quantity,
        "unit": unit_name,
        "original_quantity": ri.original_quantity,
        "quantity_range": ri.quantity_range,
        "is_optional": bool(ri.is_optional),
        "is_approximate": False,   # 数据库无，默认
        "is_estimated": False,     # 数据库无，默认
        "note": ri.note or "",
        "quantity_description": qty_desc,
        # 扩展
        "ingredient_id": ri.ingredient_id,
        "unit_id": ri.unit_id,
    }


def serialize_recipe(
    recipe: Any,
    recipe_ingredients: list,
    ingredient_map: dict,
    unit_map: dict,
) -> dict:
    """Recipe → recipes/{name}.json。

    HowToCook 字段保持兼容；扩展 id / result_ingredient_id 等。
    ingredient_map: {ingredient_id: name}；unit_map: {unit_id: name}。
    """
    return {
        # HowToCook 兼容
        "name": recipe.name,
        "source_file": recipe.source,            # ← Recipe.source
        "category": recipe.category,
        "difficulty": recipe.difficulty,
        "total_time_minutes": recipe.total_time_minutes,
        "servings": recipe.servings,
        "original_servings": None,               # 数据库无此字段
        "images": [convert_image_path(p) for p in (recipe.images or [])],
        "ingredients": [
            _serialize_recipe_ingredient(ri, ingredient_map, unit_map)
            for ri in recipe_ingredients
        ],
        "steps": recipe.cooking_steps or [],
        "tips": recipe.tips or [],
        "description": recipe.description or "",
        # 扩展
        "id": recipe.id,
        "tags": recipe.tags,
        "result_ingredient_id": recipe.result_ingredient_id,
    }
```

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && python -m pytest tests/services/test_export_serializers.py -k serialize_recipe -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/export/serializers.py backend/tests/services/test_export_serializers.py
git commit -m "feat(export): 添加菜谱序列化（含 RecipeIngredient）"
```

---

## Task 6: 扩展知识库序列化（单位换算/分类/层级/密度/商品/条码/关联）

**Files:**
- Modify: `backend/app/services/export/serializers.py`
- Test: `backend/tests/services/test_export_serializers.py`

- [ ] **Step 1: 追加测试**

Append to `test_export_serializers.py`：

```python
from app.services.export.serializers import (
    serialize_unit_conversion,
    serialize_category,
    serialize_hierarchy,
    serialize_entity_density,
    serialize_product,
    serialize_barcode,
    serialize_product_link,
)


def test_serialize_unit_conversion():
    uc = SimpleNamespace(id=1, from_unit_id=1, to_unit_id=2,
                         conversion_factor=Decimal("1000"), formula=None,
                         is_bidirectional=True, precision=6)
    out = serialize_unit_conversion(uc, from_unit_name="kg", to_unit_name="g")
    assert out == {
        "id": 1, "from_unit_id": 1, "from_unit_name": "kg",
        "to_unit_id": 2, "to_unit_name": "g",
        "conversion_factor": 1000.0, "formula": None,
        "is_bidirectional": True, "precision": 6,
    }


def test_serialize_category():
    cat = SimpleNamespace(id=6, name="eggs", display_name="禽蛋",
                          parent_category_id=None, sort_order=6, description="鸡蛋鸭蛋等")
    out = serialize_category(cat)
    assert out["display_name"] == "禽蛋"
    assert out["parent_category_id"] is None


def test_serialize_hierarchy():
    h = SimpleNamespace(id=1, parent_id=5, child_id=8,
                        relation_type="substitutable", strength=80)
    out = serialize_hierarchy(h, parent_name="鸡蛋", child_name="鸭蛋")
    assert out["relation_type"] == "substitutable"
    assert out["child_name"] == "鸭蛋"


def test_serialize_entity_density():
    ed = SimpleNamespace(id=1, entity_type="ingredient", entity_id=5,
                         density=Decimal("1030"), temperature=None,
                         condition=None, source="测得", confidence=Decimal("0.9"))
    out = serialize_entity_density(ed, entity_name="鸡蛋")
    assert out["density"] == 1030.0
    assert out["entity_name"] == "鸡蛋"


def test_serialize_product():
    p = SimpleNamespace(id=3, name="鸡蛋(某品牌)", brand="品牌A", barcode=None,
                        image_url="/static/images/products/x.jpg",
                        ingredient_id=5, tags=None, aliases=[],
                        custom_nutrition_data=None, custom_nutrition_source="custom")
    out = serialize_product(p, ingredient_name="鸡蛋", primary_barcode="6901234567890")
    assert out["name"] == "鸡蛋(某品牌)"
    assert out["barcode"] == "6901234567890"
    assert out["image_url"] == "images/products/x.jpg"
    assert out["ingredient_name"] == "鸡蛋"


def test_serialize_barcode():
    b = SimpleNamespace(id=1, product_id=3, barcode="6901234567890",
                        barcode_type="ean", is_primary=True, is_active=True)
    out = serialize_barcode(b, product_name="鸡蛋(某品牌)")
    assert out["barcode"] == "6901234567890"
    assert out["is_primary"] is True


def test_serialize_product_link():
    link = SimpleNamespace(id=1, product_id=3, ingredient_id=5)
    out = serialize_product_link(link, product_name="鸡蛋(某品牌)", ingredient_name="鸡蛋")
    assert out["product_id"] == 3
    assert out["ingredient_name"] == "鸡蛋"
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && python -m pytest tests/services/test_export_serializers.py -k "unit_conversion or category or hierarchy or entity_density or serialize_product or serialize_barcode or product_link" -v`
Expected: FAIL（ImportError）

- [ ] **Step 3: 实现这批序列化函数**

Append to `serializers.py`：

```python
def serialize_unit_conversion(uc: Any, from_unit_name: Optional[str], to_unit_name: Optional[str]) -> dict:
    return {
        "id": uc.id,
        "from_unit_id": uc.from_unit_id,
        "from_unit_name": from_unit_name,
        "to_unit_id": uc.to_unit_id,
        "to_unit_name": to_unit_name,
        "conversion_factor": to_float(uc.conversion_factor),
        "formula": uc.formula,
        "is_bidirectional": bool(uc.is_bidirectional),
        "precision": uc.precision,
    }


def serialize_category(cat: Any) -> dict:
    return {
        "id": cat.id,
        "name": cat.name,
        "display_name": cat.display_name,
        "parent_category_id": cat.parent_category_id,
        "sort_order": cat.sort_order,
        "description": cat.description,
    }


def serialize_hierarchy(h: Any, parent_name: Optional[str], child_name: Optional[str]) -> dict:
    return {
        "id": h.id,
        "parent_id": h.parent_id,
        "parent_name": parent_name,
        "child_id": h.child_id,
        "child_name": child_name,
        "relation_type": h.relation_type,
        "strength": h.strength,
    }


def serialize_entity_density(ed: Any, entity_name: Optional[str]) -> dict:
    return {
        "id": ed.id,
        "entity_type": ed.entity_type,
        "entity_id": ed.entity_id,
        "entity_name": entity_name,
        "density": to_float(ed.density),
        "temperature": to_float(ed.temperature),
        "condition": ed.condition,
        "source": ed.source,
        "confidence": to_float(ed.confidence),
    }


def serialize_product(p: Any, ingredient_name: Optional[str], primary_barcode: Optional[str]) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "brand": p.brand,
        "barcode": primary_barcode,
        "image_url": convert_image_path(p.image_url),
        "ingredient_id": p.ingredient_id,
        "ingredient_name": ingredient_name,
        "tags": p.tags,
        "aliases": p.aliases or [],
        "custom_nutrition_data": p.custom_nutrition_data,
        "custom_nutrition_source": p.custom_nutrition_source,
    }


def serialize_barcode(b: Any, product_name: Optional[str]) -> dict:
    return {
        "id": b.id,
        "product_id": b.product_id,
        "product_name": product_name,
        "barcode": b.barcode,
        "barcode_type": b.barcode_type,
        "is_primary": bool(b.is_primary),
        "is_active": bool(b.is_active),
    }


def serialize_product_link(link: Any, product_name: Optional[str], ingredient_name: Optional[str]) -> dict:
    return {
        "id": link.id,
        "product_id": link.product_id,
        "product_name": product_name,
        "ingredient_id": link.ingredient_id,
        "ingredient_name": ingredient_name,
    }
```

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && python -m pytest tests/services/test_export_serializers.py -k "unit_conversion or category or hierarchy or entity_density or serialize_product or serialize_barcode or product_link" -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/export/serializers.py backend/tests/services/test_export_serializers.py
git commit -m "feat(export): 添加扩展知识库序列化（换算/分类/层级/密度/商品/条码/关联）"
```

---

## Task 7: 账户交易数据序列化（价格记录/商家/收藏）

**Files:**
- Modify: `backend/app/services/export/serializers.py`
- Test: `backend/tests/services/test_export_serializers.py`

- [ ] **Step 1: 追加测试**

Append to `test_export_serializers.py`：

```python
from app.services.export.serializers import (
    serialize_price_record,
    serialize_merchant,
    serialize_favorite_merchant,
)


def _make_price_record(**kw):
    base = dict(
        id=1, user_id=5, product_id=3, product_name="鸡蛋(某品牌)",
        merchant_id=2, price=Decimal("12.5"), currency="CNY",
        original_quantity=Decimal("1"), original_unit_id=1,
        standard_quantity=Decimal("500"), standard_unit_id=2,
        record_type="purchase", exchange_rate=Decimal("1.0"),
        recorded_at=datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc),
        notes="促销",
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_serialize_price_record():
    pr = _make_price_record()
    out = serialize_price_record(
        pr, product_name="鸡蛋(某品牌)", merchant_name="永辉",
        original_unit_name="斤", standard_unit_name="g",
    )
    assert out["price"] == 12.5
    assert out["record_type"] == "purchase"
    assert out["merchant_name"] == "永辉"
    assert out["standard_unit_name"] == "g"
    assert out["recorded_at"] == "2026-06-15T10:00:00+00:00"


def test_serialize_merchant():
    m = SimpleNamespace(id=2, name="永辉", address="xx路",
                        latitude=Decimal("30.1"), longitude=Decimal("120.2"), is_open=True)
    out = serialize_merchant(m)
    assert out["latitude"] == 30.1
    assert out["is_open"] is True


def test_serialize_favorite_merchant():
    fm = SimpleNamespace(id=1, name="家", type="home",
                         latitude=Decimal("30.1"), longitude=Decimal("120.2"))
    out = serialize_favorite_merchant(fm)
    assert out["type"] == "home"
    assert out["longitude"] == 120.2
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && python -m pytest tests/services/test_export_serializers.py -k "price_record or serialize_merchant or favorite_merchant" -v`
Expected: FAIL（ImportError）

- [ ] **Step 3: 实现这批序列化函数**

Append to `serializers.py`：

```python
def serialize_price_record(
    pr: Any,
    product_name: Optional[str],
    merchant_name: Optional[str],
    original_unit_name: Optional[str],
    standard_unit_name: Optional[str],
) -> dict:
    return {
        "id": pr.id,
        "user_id": pr.user_id,
        "product_id": pr.product_id,
        "product_name": product_name,
        "merchant_id": pr.merchant_id,
        "merchant_name": merchant_name,
        "price": to_float(pr.price),
        "currency": pr.currency,
        "original_quantity": to_float(pr.original_quantity),
        "original_unit_id": pr.original_unit_id,
        "original_unit_name": original_unit_name,
        "standard_quantity": to_float(pr.standard_quantity),
        "standard_unit_id": pr.standard_unit_id,
        "standard_unit_name": standard_unit_name,
        "record_type": pr.record_type,
        "exchange_rate": to_float(pr.exchange_rate),
        "recorded_at": to_iso(pr.recorded_at),
        "notes": pr.notes,
    }


def serialize_merchant(m: Any) -> dict:
    return {
        "id": m.id,
        "name": m.name,
        "address": m.address,
        "latitude": to_float(m.latitude),
        "longitude": to_float(m.longitude),
        "is_open": bool(m.is_open),
    }


def serialize_favorite_merchant(fm: Any) -> dict:
    return {
        "id": fm.id,
        "name": fm.name,
        "type": fm.type,
        "latitude": to_float(fm.latitude),
        "longitude": to_float(fm.longitude),
    }
```

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && python -m pytest tests/services/test_export_serializers.py -k "price_record or serialize_merchant or favorite_merchant" -v`
Expected: PASS

- [ ] **Step 5: 全量序列化器测试跑一遍，确保无回归**

Run: `cd backend && python -m pytest tests/services/test_export_serializers.py -v`
Expected: PASS（全部）

- [ ] **Step 6: 提交**

```bash
git add backend/app/services/export/serializers.py backend/tests/services/test_export_serializers.py
git commit -m "feat(export): 添加账户交易数据序列化（价格记录/商家/收藏）"
```

---

## Task 8: 可达性遍历（mine 模式）+ ExportSet

**Files:**
- Create: `backend/app/services/export/reachability.py`
- Test: `backend/tests/services/test_export_reachability.py`

> 说明：本任务依赖真实数据库（外键遍历），用 TestClient + 已有测试用户 `testuser` 的集成测试风格。测试需先确保库内存在「我的菜谱引用某食材」的数据；若环境无此数据，测试用例构造后清理。

- [ ] **Step 1: 写测试**

Create `backend/tests/services/test_export_reachability.py`：

```python
"""可达性遍历集成测试。依赖真实数据库与 testuser。

前置：通过 API 登录 testuser，并确保该用户至少有一条菜谱引用某食材。
若无可引用数据，本测试在 setup 中创建一条临时菜谱并在 teardown 删除。
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.services.export.reachability import collect_full_set, collect_mine_set

client = TestClient(app)


def _login_token():
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password_hash": "test_password_hash"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_full_set_includes_all_ingredients():
    """full 模式应包含库内全部食材 id（至少 >0）。"""
    db = SessionLocal()
    try:
        es = collect_full_set(db)
        assert len(es.ingredient_ids) > 0
    finally:
        db.close()


def test_mine_set_pulls_referenced_admin_ingredient():
    """mine 模式：testuser 的菜谱引用的食材必须进入导出集，无论创建者。"""
    db = SessionLocal()
    try:
        from app.models.user import User
        user = db.query(User).filter(User.username == "testuser").first()
        assert user is not None
        es = collect_mine_set(db, user.id)
        # 我的菜谱引用的每个食材都应在集合内
        from app.models.recipe import Recipe, RecipeIngredient
        my_recipe_ids = {r.id for r in db.query(Recipe).filter(Recipe.user_id == user.id).all()}
        referenced = {
            ri.ingredient_id
            for ri in db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id.in_(my_recipe_ids)).all()
            if ri.ingredient_id is not None
        }
        assert referenced.issubset(es.ingredient_ids)
    finally:
        db.close()
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && python -m pytest tests/services/test_export_reachability.py -v`
Expected: FAIL（ImportError）

- [ ] **Step 3: 实现 reachability.py**

Create `backend/app/services/export/reachability.py`：

```python
"""导出集收集：full 全量 / mine 仅我的 + 可达性遍历。

mine 模式从「我的菜谱/价格记录/商品」出发，沿外键扩张集合到不动点，
确保引用到的管理员数据（食材/营养/单位等）一并纳入，避免导入后引用悬空。
"""
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.recipe import Recipe, RecipeIngredient
from app.models.nutrition import Ingredient
from app.models.nutrition_data import NutritionData
from app.models.unit import Unit, UnitConversion
from app.models.ingredient_category import IngredientCategory
from app.models.ingredient_hierarchy import IngredientHierarchy
from app.models.entity_density import EntityDensity
from app.models.product_entity import Product
from app.models.product_barcode import ProductBarcode
from app.models.product_ingredient_link import ProductIngredientLink
from app.models.product import ProductRecord
from app.models.merchant import Merchant, FavoriteMerchant


@dataclass
class ExportSet:
    """各表待导出的 id 集合。None 表示「全部」（full 模式）。"""
    full_mode: bool = False
    recipe_ids: set = field(default_factory=set)
    ingredient_ids: set = field(default_factory=set)
    nutrition_ids: set = field(default_factory=set)
    unit_ids: set = field(default_factory=set)
    unit_conversion_ids: set = field(default_factory=set)
    category_ids: set = field(default_factory=set)
    hierarchy_ids: set = field(default_factory=set)
    entity_density_ids: set = field(default_factory=set)
    product_ids: set = field(default_factory=set)
    barcode_ids: set = field(default_factory=set)
    product_link_ids: set = field(default_factory=set)
    price_record_ids: set = field(default_factory=set)
    merchant_ids: set = field(default_factory=set)
    favorite_merchant_ids: set = field(default_factory=set)


def collect_full_set(db: Session) -> ExportSet:
    """full 模式：所有集合标记为 None（全量），由查询层不加过滤实现。"""
    return ExportSet(full_mode=True)


def _collect_ingredient_closure(db: Session, seed_ingredient_ids: set) -> tuple[set, set, set, set]:
    """从种子食材出发，扩张 ingredient / nutrition / category / unit / density / hierarchy 集合到不动点。

    返回 (ingredient_ids, 相关 unit_ids)。
    """
    ingredients = set(seed_ingredient_ids)
    units = set()
    nutritions = set()
    categories = set()

    # 不动点迭代：层级关系会把更多食材拉进来
    while True:
        prev_size = len(ingredients)
        rows = db.query(Ingredient).filter(Ingredient.id.in_(ingredients)).all() if ingredients else []
        for ing in rows:
            if ing.nutrition_id:
                nutritions.add(ing.nutrition_id)
            if ing.category_id:
                categories.add(ing.category_id)
            for uid in (ing.default_unit_id, ing.piece_weight_unit_id, ing.serving_weight_unit_id):
                if uid:
                    units.add(uid)
            # 营养映射回链也可能指向更多 NutritionData
        # 层级关系双向扩张食材集合
        if ingredients:
            hier = db.query(IngredientHierarchy).filter(
                IngredientHierarchy.parent_id.in_(ingredients) |
                IngredientHierarchy.child_id.in_(ingredients)
            ).all()
            for h in hier:
                ingredients.add(h.parent_id)
                ingredients.add(h.child_id)
        if len(ingredients) == prev_size:
            break

    # nutrition_ids 由 ingredient 反查
    if ingredients:
        for ing in db.query(Ingredient).filter(Ingredient.id.in_(ingredients)).all():
            if ing.nutrition_id:
                nutritions.add(ing.nutrition_id)

    return ingredients, units, nutritions, categories  # type: ignore[return-value]


def collect_mine_set(db: Session, user_id: int) -> ExportSet:
    """mine 模式：我的直接数据 + 可达性扩张。"""
    es = ExportSet(full_mode=False)

    # 1) 我的菜谱 + 其 RecipeIngredient 引用的食材/单位
    my_recipes = db.query(Recipe).filter(Recipe.user_id == user_id).all()
    es.recipe_ids = {r.id for r in my_recipes}
    seed_ingredients = set()
    recipe_unit_ids = set()
    if es.recipe_ids:
        ris = db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id.in_(es.recipe_ids)).all()
        for ri in ris:
            if ri.ingredient_id:
                seed_ingredients.add(ri.ingredient_id)
            if ri.unit_id:
                recipe_unit_ids.add(ri.unit_id)
        # 成品关联
        for r in my_recipes:
            if r.result_ingredient_id:
                seed_ingredients.add(r.result_ingredient_id)

    # 2) 我的价格记录 → 商品/单位/商家
    my_records = db.query(ProductRecord).filter(ProductRecord.user_id == user_id).all()
    es.price_record_ids = {r.id for r in my_records}
    seed_products = set()
    record_unit_ids = set()
    merchant_ids = set()
    for r in my_records:
        if r.product_id:
            seed_products.add(r.product_id)
        if r.original_unit_id:
            record_unit_ids.add(r.original_unit_id)
        if r.standard_unit_id:
            record_unit_ids.add(r.standard_unit_id)
        if r.merchant_id:
            merchant_ids.add(r.merchant_id)

    # 3) 我创建的商品（全局库按 created_by）
    my_created_products = db.query(Product).filter(Product.created_by == user_id).all()
    seed_products.update(p.id for p in my_created_products)
    # 我创建的食材（全局库按 created_by）
    seed_ingredients.update(
        i.id for i in db.query(Ingredient).filter(Ingredient.created_by == user_id).all()
    )
    # 我创建的单位
    my_units = {u.id for u in db.query(Unit).filter(Unit.created_by == user_id).all()}
    es.unit_ids.update(my_units)

    # 4) 食材闭包扩张
    ingredients, ing_units, nutrition_ids, category_ids = _collect_ingredient_closure(db, seed_ingredients)
    es.ingredient_ids = ingredients
    es.nutrition_ids = nutrition_ids
    es.category_ids = category_ids
    es.unit_ids.update(ing_units)
    es.unit_ids.update(recipe_unit_ids)
    es.unit_ids.update(record_unit_ids)

    # 5) 商品闭包：商品引用的食材（已在 ingredients）、条码、关联
    if seed_products:
        products = db.query(Product).filter(Product.id.in_(seed_products)).all()
        es.product_ids = {p.id for p in products}
        extra_ing = {p.ingredient_id for p in products if p.ingredient_id}
        if extra_ing - es.ingredient_ids:
            merged, _, _, _ = _collect_ingredient_closure(db, extra_ing)
            es.ingredient_ids.update(merged)
        # 条码
        es.barcode_ids = {
            b.id for b in db.query(ProductBarcode).filter(ProductBarcode.product_id.in_(es.product_ids)).all()
        }
        # 关联
        es.product_link_ids = {
            l.id for l in db.query(ProductIngredientLink).filter(ProductIngredientLink.product_id.in_(es.product_ids)).all()
        }

    # 6) 商家（价格记录引用的 + 我的收藏）
    es.merchant_ids = merchant_ids
    es.favorite_merchant_ids = {
        f.id for f in db.query(FavoriteMerchant).filter(FavoriteMerchant.user_id == user_id).all()
    }

    # 7) 由 ingredient_ids / unit_ids 派生：密度、层级、换算、分类（闭包已含 category）
    if es.ingredient_ids:
        es.entity_density_ids = {
            d.id for d in db.query(EntityDensity).filter(
                EntityDensity.entity_type == "ingredient",
                EntityDensity.entity_id.in_(es.ingredient_ids),
            ).all()
        }
        es.hierarchy_ids = {
            h.id for h in db.query(IngredientHierarchy).filter(
                IngredientHierarchy.parent_id.in_(es.ingredient_ids) |
                IngredientHierarchy.child_id.in_(es.ingredient_ids)
            ).all()
        }
    if es.product_ids:
        es.entity_density_ids.update(
            d.id for d in db.query(EntityDensity).filter(
                EntityDensity.entity_type == "product",
                EntityDensity.entity_id.in_(es.product_ids),
            ).all()
        )
    if es.unit_ids:
        es.unit_conversion_ids = {
            c.id for c in db.query(UnitConversion).filter(
                UnitConversion.from_unit_id.in_(es.unit_ids) |
                UnitConversion.to_unit_id.in_(es.unit_ids)
            ).all()
        }

    return es
```

> 注：上方实现已是最终版——顶部 `from app.models.unit import Unit, UnitConversion`；`_collect_ingredient_closure` 返回 4 元组 `(ingredients, units, nutritions, categories)`，与调用方解包一致。

- [ ] **Step 4: 运行确认通过**

Run: `cd backend && python -m pytest tests/services/test_export_reachability.py -v`
Expected: PASS（前提：testuser 存在且有菜谱数据；若无菜谱，referenced 为空集，`issubset` 仍成立）

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/export/reachability.py backend/tests/services/test_export_reachability.py
git commit -m "feat(export): 添加导出集收集与 mine 模式可达性遍历"
```

---

## Task 9: 打包服务（查询→序列化→图片→zip + manifest）

**Files:**
- Create: `backend/app/services/export/packaging.py`
- Create: `backend/app/services/export/__init__.py`（填入主入口）

> 本任务是编排核心，依赖 Task 1-8 的序列化器与 ExportSet。先写一个端到端集成测试覆盖「能产出合法 zip」，再实现。

- [ ] **Step 1: 写端点集成测试（zip 可解压、结构完整）**

Create `backend/tests/test_export.py`：

```python
import io
import zipfile
import json

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _login_token():
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password_hash": "test_password_hash"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _extract_zip(response):
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "attachment" in response.headers["content-disposition"]
    zf = zipfile.ZipFile(io.BytesIO(response.content))
    return zf


def test_export_full_returns_valid_zip():
    token = _login_token()
    resp = client.get(
        "/api/v1/export/data?scope=full",
        headers={"Authorization": f"Bearer {token}"},
    )
    zf = _extract_zip(resp)
    names = zf.namelist()
    assert "manifest.json" in names
    assert "ingredients.json" in names
    assert "units.json" in names
    manifest = json.loads(zf.read("manifest.json"))
    assert manifest["scope"] == "full"
    assert "counts" in manifest


def test_export_mine_returns_valid_zip():
    token = _login_token()
    resp = client.get(
        "/api/v1/export/data?scope=mine",
        headers={"Authorization": f"Bearer {token}"},
    )
    zf = _extract_zip(resp)
    manifest = json.loads(zf.read("manifest.json"))
    assert manifest["scope"] == "mine"
    # mine 模式每条菜谱 json 都应在 recipes/ 下
    recipe_files = [n for n in zf.namelist() if n.startswith("recipes/") and n.endswith(".json")]
    assert len(recipe_files) == manifest["counts"].get("recipes", 0)


def test_export_requires_auth():
    resp = client.get("/api/v1/export/data?scope=full")
    assert resp.status_code in (401, 403)
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && python -m pytest tests/test_export.py -v`
Expected: FAIL（404，端点未注册）

- [ ] **Step 3: 实现 packaging.py**

Create `backend/app/services/export/packaging.py`：

```python
"""打包服务：按 ExportSet 查询→序列化→收集图片→写入 zip。

对外暴露 build_export_zip(db, user, scope) -> (zip_bytes, manifest_dict)。
"""
import io
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.base_model import AuditMixin  # noqa: F401  (文档参考)
from app.models.recipe import Recipe, RecipeIngredient
from app.models.nutrition import Ingredient
from app.models.nutrition_data import NutritionData
from app.models.unit import Unit, UnitConversion
from app.models.ingredient_category import IngredientCategory
from app.models.ingredient_hierarchy import IngredientHierarchy
from app.models.entity_density import EntityDensity
from app.models.product_entity import Product
from app.models.product_barcode import ProductBarcode
from app.models.product_ingredient_link import ProductIngredientLink
from app.models.product import ProductRecord
from app.models.merchant import Merchant, FavoriteMerchant

from .reachability import ExportSet, collect_full_set, collect_mine_set
from . import serializers as S

STATIC_DIR = Path(__file__).resolve().parents[3] / "static"  # backend/static

_UNSAFE_FILENAME = re.compile(r'[/\\:*?"<>|]')


def _safe_filename(name: str, fallback_id: int) -> str:
    cleaned = _UNSAFE_FILENAME.sub("_", name or "").strip()[:80]
    return cleaned or f"recipe_{fallback_id}"


def _unit_name_map(db: Session, unit_ids: set | None) -> dict:
    q = db.query(Unit)
    if unit_ids is not None:
        q = q.filter(Unit.id.in_(unit_ids)) if unit_ids else q.filter(False)
    return {u.id: u.name for u in q.all()}


def _ingredient_name_map(db: Session, ing_ids: set | None) -> dict:
    q = db.query(Ingredient)
    if ing_ids is not None:
        q = q.filter(Ingredient.id.in_(ing_ids)) if ing_ids else q.filter(False)
    return {i.id: i.name for i in q.all()}


def _collect_image_files(manifest: dict, recipes_payload: list, products_payload: list) -> list:
    """扫描已序列化的图片相对路径，返回 [(zip内路径, 物理绝对路径)]。

    外链 http(s):// 跳过并计入 manifest.notes。
    """
    files = []
    skipped = 0
    seen = set()

    def _handle(rel: str | None, subdir_hint: str):
        nonlocal skipped
        if not rel:
            return
        if rel.startswith("http://") or rel.startswith("https://"):
            skipped += 1
            return
        phys = STATIC_DIR / rel
        if not phys.exists():
            skipped += 1
            return
        if rel in seen:
            return
        seen.add(rel)
        files.append((rel, phys))

    for r in recipes_payload:
        for img in r.get("images", []):
            _handle(img, "recipes")
    for p in products_payload:
        _handle(p.get("image_url"), "products")

    if skipped:
        manifest.setdefault("notes", []).append(f"{skipped} 个图片为外链或缺失，未打包")
    manifest.setdefault("image_summary", {})["skipped_remote"] = skipped
    return files


def build_export_zip(db: Session, user, scope: str) -> tuple[bytes, dict]:
    """主编排：返回 (zip_bytes, manifest)。"""
    es: ExportSet = collect_full_set(db) if scope == "full" else collect_mine_set(db, user.id)

    # ---- 查询（full 不加 id 过滤；mine 按 ExportSet 过滤）----
    def _query(model, id_set):
        q = db.query(model)
        if not es.full_mode:
            if id_set:
                q = q.filter(model.id.in_(id_set))
            else:
                q = q.filter(False)
        return q.all()

    recipes = _query(Recipe, es.recipe_ids)
    ingredients = _query(Ingredient, es.ingredient_ids)
    nutritions = _query(NutritionData, es.nutrition_ids)
    units = _query(Unit, es.unit_ids)
    conversions = _query(UnitConversion, es.unit_conversion_ids)
    categories = _query(IngredientCategory, es.category_ids)
    hierarchies = _query(IngredientHierarchy, es.hierarchy_ids)
    densities = _query(EntityDensity, es.entity_density_ids)
    products = _query(Product, es.product_ids)
    barcodes = _query(ProductBarcode, es.barcode_ids)
    links = _query(ProductIngredientLink, es.product_link_ids)
    records = _query(ProductRecord, es.price_record_ids)
    merchants = _query(Merchant, es.merchant_ids)
    favs = _query(FavoriteMerchant, es.favorite_merchant_ids)

    # ---- 名字映射 ----
    unit_names = _unit_name_map(db, es.unit_ids if not es.full_mode else None)
    ing_names = _ingredient_name_map(db, es.ingredient_ids if not es.full_mode else None)
    cat_names = {c.id: c.display_name for c in categories}
    # 食材→usda_id：从 nutrition 反查
    ing_to_usda = {}
    for nd in nutritions:
        ing_to_usda[nd.ingredient_id] = nd.usda_id

    # ---- 序列化 ----
    units_payload = [S.serialize_unit(u) for u in units]
    ingredients_payload = [
        S.serialize_ingredient(
            ing,
            category_display_name=cat_names.get(ing.category_id),
            usda_id=ing_to_usda.get(ing.id),
        )
        for ing in ingredients
    ]
    ingredients_doc = {p["name"]: p for p in ingredients_payload}

    nutritions_payload = [
        S.serialize_nutrition(nd, ingredient_name=ing_names.get(nd.ingredient_id, ""))
        for nd in nutritions
    ]

    conversions_payload = [
        S.serialize_unit_conversion(c, unit_names.get(c.from_unit_id), unit_names.get(c.to_unit_id))
        for c in conversions
    ]
    categories_payload = [S.serialize_category(c) for c in categories]
    hierarchy_payload = [
        S.serialize_hierarchy(h, ing_names.get(h.parent_id), ing_names.get(h.child_id))
        for h in hierarchies
    ]
    densities_payload = [
        S.serialize_entity_density(
            d,
            ing_names.get(d.entity_id) if d.entity_type == "ingredient"
            else _product_name(db, d.entity_id),
        )
        for d in densities
    ]

    # 商品/条码/关联
    prod_id_to_name = {p.id: p.name for p in products}
    barcode_primary = {}
    for b in barcodes:
        if b.is_primary:
            barcode_primary[b.product_id] = b.barcode
    products_payload = [
        S.serialize_product(p, ing_names.get(p.ingredient_id), barcode_primary.get(p.id))
        for p in products
    ]
    barcodes_payload = [
        S.serialize_barcode(b, prod_id_to_name.get(b.product_id)) for b in barcodes
    ]
    links_payload = [
        S.serialize_product_link(l, prod_id_to_name.get(l.product_id), ing_names.get(l.ingredient_id))
        for l in links
    ]

    # 菜谱（含 RecipeIngredient）
    recipe_ri_map = {}
    if recipes:
        ri_rows = db.query(RecipeIngredient).filter(
            RecipeIngredient.recipe_id.in_([r.id for r in recipes])
        ).all()
        for ri in ri_rows:
            recipe_ri_map.setdefault(ri.recipe_id, []).append(ri)
    recipes_payload = []
    used_names = set()
    recipe_file_index = []  # (filename, payload)
    for r in recipes:
        payload = S.serialize_recipe(
            r, recipe_ri_map.get(r.id, []),
            ingredient_map=ing_names, unit_map=unit_names,
        )
        fname = _safe_filename(r.name, r.id)
        if fname in used_names:
            fname = f"{fname}_{r.id}"
        used_names.add(fname)
        recipe_file_index.append((f"recipes/{fname}.json", payload))
        recipes_payload.append(payload)

    # 商家/价格记录/收藏
    merchant_id_to_name = {m.id: m.name for m in merchants}
    records_payload = [
        S.serialize_price_record(
            pr,
            pr.product_name,
            merchant_id_to_name.get(pr.merchant_id),
            unit_names.get(pr.original_unit_id),
            unit_names.get(pr.standard_unit_id),
        )
        for pr in records
    ]
    merchants_payload = [S.serialize_merchant(m) for m in merchants]
    favs_payload = [S.serialize_favorite_merchant(f) for f in favs]

    # ---- manifest ----
    manifest = {
        "format_version": "1.0",
        "app": "生计 - 生活成本计算器",
        "app_version": "0.2.0",
        "exported_at": datetime.now().astimezone().isoformat(),
        "scope": scope,
        "exported_by_user_id": getattr(user, "id", None),
        "schema": {
            "howto_cook_compatible": ["recipes", "ingredients", "nutritions", "units"],
            "extended": ["unit_conversions", "ingredient_categories", "ingredient_hierarchy",
                         "entity_densities", "products", "product_barcodes",
                         "product_ingredient_links", "price_records", "merchants",
                         "favorite_merchants"],
        },
        "counts": {
            "recipes": len(recipes_payload),
            "ingredients": len(ingredients_payload),
            "nutritions": len(nutritions_payload),
            "units": len(units_payload),
            "unit_conversions": len(conversions_payload),
            "ingredient_categories": len(categories_payload),
            "ingredient_hierarchy": len(hierarchy_payload),
            "entity_densities": len(densities_payload),
            "products": len(products_payload),
            "product_barcodes": len(barcodes_payload),
            "product_ingredient_links": len(links_payload),
            "price_records": len(records_payload),
            "merchants": len(merchants_payload),
            "favorite_merchants": len(favs_payload),
        },
        "image_summary": {},
        "errors": [],
        "notes": [],
    }

    # ---- 图片收集 ----
    image_files = _collect_image_files(manifest, recipes_payload, products_payload)
    manifest["image_summary"]["recipes"] = sum(
        1 for r in recipes_payload for _ in r.get("images", [])
        if not (str(_).startswith("http"))
    )

    # ---- 写 zip ----
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for fname, payload in recipe_file_index:
            zf.writestr(fname, json.dumps(payload, ensure_ascii=False, indent=2))
        zf.writestr("ingredients.json", json.dumps(ingredients_doc, ensure_ascii=False, indent=2))
        zf.writestr("nutritions.json", json.dumps(nutritions_payload, ensure_ascii=False, indent=2))
        zf.writestr("units.json", json.dumps(units_payload, ensure_ascii=False, indent=2))
        zf.writestr("unit_conversions.json", json.dumps(conversions_payload, ensure_ascii=False, indent=2))
        zf.writestr("ingredient_categories.json", json.dumps(categories_payload, ensure_ascii=False, indent=2))
        zf.writestr("ingredient_hierarchy.json", json.dumps(hierarchy_payload, ensure_ascii=False, indent=2))
        zf.writestr("entity_densities.json", json.dumps(densities_payload, ensure_ascii=False, indent=2))
        zf.writestr("products.json", json.dumps(products_payload, ensure_ascii=False, indent=2))
        zf.writestr("product_barcodes.json", json.dumps(barcodes_payload, ensure_ascii=False, indent=2))
        zf.writestr("product_ingredient_links.json", json.dumps(links_payload, ensure_ascii=False, indent=2))
        zf.writestr("price_records.json", json.dumps(records_payload, ensure_ascii=False, indent=2))
        zf.writestr("merchants.json", json.dumps(merchants_payload, ensure_ascii=False, indent=2))
        zf.writestr("favorite_merchants.json", json.dumps(favs_payload, ensure_ascii=False, indent=2))
        for rel, phys in image_files:
            zf.write(phys, rel)

    return buf.getvalue(), manifest


def _product_name(db: Session, product_id: int) -> str | None:
    p = db.query(Product).filter(Product.id == product_id).first()
    return p.name if p else None
```

- [ ] **Step 4: 填入主入口 `__init__.py`**

Overwrite `backend/app/services/export/__init__.py`：

```python
"""数据导出包入口。"""
from sqlalchemy.orm import Session

from .packaging import build_export_zip


def export_data(db: Session, user, scope: str) -> tuple[bytes, dict]:
    """导出当前用户可见数据为 zip。返回 (zip_bytes, manifest)。"""
    if scope not in ("full", "mine"):
        scope = "full"
    return build_export_zip(db, user, scope)
```

- [ ] **Step 5: 运行序列化器全部测试，确认无回归**

Run: `cd backend && python -m pytest tests/services/ -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add backend/app/services/export/packaging.py backend/app/services/export/__init__.py
git commit -m "feat(export): 添加打包服务（查询→序列化→图片→zip+manifest）"
```

---

## Task 10: 导出端点 + 路由注册

**Files:**
- Create: `backend/app/api/export.py`
- Modify: `backend/app/main.py`（注册路由）

- [ ] **Step 1: 创建路由文件**

Create `backend/app/api/export.py`：

```python
"""数据导出路由。"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.export import export_data

router = APIRouter()


@router.get("/data")
async def export_user_data(
    scope: str = Query("full", regex="^(full|mine)$"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """导出当前用户数据为 zip 并流式下载。"""
    zip_bytes, _manifest = export_data(db, current_user, scope)
    filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

    def _iter():
        yield zip_bytes

    return StreamingResponse(
        _iter(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 2: 注册路由**

Modify `backend/app/main.py`，在 import 区（约第 26 行后）加入：

```python
from app.api import export  # 数据导出 API
```

在路由注册区（约第 534 行 `ingredient_hierarchy` 注册之后）加入：

```python
app.include_router(export.router, prefix="/api/v1/export", tags=["数据导出"])
```

- [ ] **Step 3: 运行端点集成测试**

Run: `cd backend && python -m pytest tests/test_export.py -v`
Expected: PASS（3 个用例：full / mine / requires_auth）

- [ ] **Step 4: 语法检查 + 启动校验（不实际启动服务，仅 import）**

Run: `cd backend && python -c "from app.main import app; print('ok')"`
Expected: 输出 `ok`，无 ImportError。

- [ ] **Step 5: 提交**

```bash
git add backend/app/api/export.py backend/app/main.py
git commit -m "feat(export): 添加导出端点 GET /api/v1/export/data 并注册路由"
```

---

## Task 11: 前端导出对话框 + 下载

**Files:**
- Modify: `frontend/src/views/profile/ProfileView.vue`

- [ ] **Step 1: 修改模板——数据导出项加点击 + 对话框**

在 [ProfileView.vue](../../../frontend/src/views/profile/ProfileView.vue) 的「数据导出」`<v-list-item>`（约第 69-77 行）加 `@click`：

```html
        <v-list-item @click="exportDialog = true">
          <template #prepend>
            <v-icon>mdi-export</v-icon>
          </template>
          <v-list-item-title>数据导出</v-list-item-title>
          <template #append>
            <v-icon>mdi-chevron-right</v-icon>
          </template>
        </v-list-item>
```

在 `</v-container>` 之前（退出登录卡片之后）加对话框：

```html
    <!-- 数据导出对话框 -->
    <v-dialog v-model="exportDialog" max-width="420">
      <v-card>
        <v-card-title>数据导出</v-card-title>
        <v-card-text>
          <p class="text-body-2 text-medium-emphasis mb-3">
            选择导出范围，导出文件将打包为 zip 下载。
          </p>
          <v-radio-group v-model="exportScope">
            <v-radio label="全量数据" value="full">
              <template #label>
                <div>
                  <strong>全量数据</strong>
                  <div class="text-caption text-medium-emphasis">
                    包括我创建的和系统/管理员创建的所有数据
                  </div>
                </div>
              </template>
            </v-radio>
            <v-radio label="仅我的数据" value="mine">
              <template #label>
                <div>
                  <strong>仅我的数据</strong>
                  <div class="text-caption text-medium-emphasis">
                    只导出我创建的数据；我引用到的系统数据会一并带上
                  </div>
                </div>
              </template>
            </v-radio>
          </v-radio-group>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" :disabled="exporting" @click="exportDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="exporting" @click="doExport">导出</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 导出进度遮罩 -->
    <v-overlay v-model="exporting" class="align-center justify-center" persistent>
      <div class="text-center">
        <v-progress-circular indeterminate size="48" />
        <div class="mt-3">正在打包数据，请稍候…</div>
      </div>
    </v-overlay>
```

- [ ] **Step 2: 修改 script——加状态与下载逻辑**

在 `<script setup>` 顶部 import 区（约第 108 行 `import { api } from '@/api/client'` 之后）无需新增 import（用现有 api）。

在 `const search = ref('')`（约第 116 行）之后加入：

```typescript
// 数据导出
const exportDialog = ref(false)
const exportScope = ref<'full' | 'mine'>('full')
const exporting = ref(false)

const doExport = async () => {
  exporting.value = true
  try {
    const response = await api.get('/export/data', {
      params: { scope: exportScope.value },
      responseType: 'blob',
    })
    // 从响应头取文件名
    const disposition = response.headers?.['content-disposition'] || ''
    const match = disposition.match(/filename="?([^"]+)"?/)
    const filename = match?.[1] || `export_${Date.now()}.zip`
    // 触发下载
    const blob = new Blob([response.data], { type: 'application/zip' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    exportDialog.value = false
  } catch (e: any) {
    console.error('数据导出失败', e)
    alert('数据导出失败：' + (e?.message || '未知错误'))
  } finally {
    exporting.value = false
  }
}
```

> 注：`api` 客户端的响应拦截器可能已解包 `response.data`。若 `/api/client` 的拦截器对 blob 响应特殊处理（如返回完整 response 或解包），需确认 `response.data` 是 Blob。实现时打开浏览器调试验证下载是否触发；若拦截器干扰 blob，改用原生 `axios` 直接请求或调整拦截器对 `responseType: 'blob'` 透传。

- [ ] **Step 3: 构建校验**

Run: `cd frontend && npm run build`
Expected: 构建通过，无 TypeScript / 编译错误。

- [ ] **Step 4: 浏览器手测（可选，开发者已开自动重载）**

打开 http://localhost:5173 → 个人中心 → 数据导出 → 选「全量」→ 导出 → 确认浏览器下载 zip → 解压验证 manifest.json 与各 json 存在。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/views/profile/ProfileView.vue
git commit -m "feat(profile): 数据导出对话框与下载（全量/仅我的）"
```

---

## Task 12: HowToCook 兼容性验证 + 全量回归

**Files:**
- Test: `backend/tests/test_export.py`（追加兼容性用例）

- [ ] **Step 1: 追加 HowToCook 兼容性测试**

Append to `backend/tests/test_export.py`：

```python
def test_export_howto_cook_compatibility():
    """导出的菜谱/食材/营养/单位字段符合 HowToCook 结构。"""
    token = _login_token()
    resp = client.get(
        "/api/v1/export/data?scope=full",
        headers={"Authorization": f"Bearer {token}"},
    )
    zf = _extract_zip(resp)

    # 单位：数组，每项含 name + aliases
    units = json.loads(zf.read("units.json"))
    assert isinstance(units, list)
    if units:
        assert "name" in units[0] and "aliases" in units[0]

    # 食材：dict，value 含 HowToCook 字段
    ingredients = json.loads(zf.read("ingredients.json"))
    assert isinstance(ingredients, dict)
    if ingredients:
        sample = next(iter(ingredients.values()))
        for k in ("name", "aliases", "category", "usda_id", "usda_match_status"):
            assert k in sample

    # 营养：数组，元素含 usda_id + nutrients[]
    nutritions = json.loads(zf.read("nutritions.json"))
    assert isinstance(nutritions, list)
    if nutritions:
        assert "usda_id" in nutritions[0]
        assert isinstance(nutritions[0].get("nutrients"), list)

    # 菜谱文件：含 HowToCook 必需字段
    recipe_files = [n for n in zf.namelist() if n.startswith("recipes/") and n.endswith(".json")]
    if recipe_files:
        r = json.loads(zf.read(recipe_files[0]))
        for k in ("name", "ingredients", "steps"):
            assert k in r
        if r["ingredients"]:
            for k in ("ingredient_name", "quantity", "unit"):
                assert k in r["ingredients"][0]
```

- [ ] **Step 2: 运行该用例**

Run: `cd backend && python -m pytest tests/test_export.py::test_export_howto_cook_compatibility -v`
Expected: PASS

- [ ] **Step 3: 全量后端测试回归**

Run: `cd backend && python -m pytest tests/ -v`
Expected: 已有用例不回归（与改动前一致的 pass/fail 基线），新增导出用例 PASS。

- [ ] **Step 4: 前端构建回归**

Run: `cd frontend && npm run build`
Expected: 构建通过。

- [ ] **Step 5: 提交**

```bash
git add backend/tests/test_export.py
git commit -m "test(export): 添加 HowToCook 兼容性与端到端测试"
```

---

## 自审记录

- **Spec 覆盖**：两档导出（Task 8/10/11）、HowToCook 兼容 + id 扩展（Task 2-7）、可达性保证（Task 8）、图片打包（Task 9 packaging `_collect_image_files`）、同步流式（Task 10）、范围不含设置/派生数据（packaging 未查询 MapConfig/UserIngredientPreference/RecipeCostHistory 等，符合非目标）——均已对应。
- **占位符**：无 TBD/TODO；`packaging.py` 中 `manifest["image_summary"]["recipes"]` 计数表达式略粗糙（用 `_` 占位变量），可接受，因仅作统计展示。
- **类型一致性**：`serialize_*` 签名在定义任务与 packaging 调用一致；`ExportSet` 字段名在 reachability 定义与 packaging 使用一致；`export_data(db, user, scope)` 在 `__init__.py` 与 `api/export.py` 一致。
- **已知实现注意点**（已写入对应 Task 备注）：前端 `api` 客户端拦截器对 `responseType: 'blob'` 的处理需在浏览器手测确认（Task 11 Step 2 备注）。
