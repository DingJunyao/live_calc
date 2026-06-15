from decimal import Decimal
from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.export.serializers import (
    to_float,
    to_iso,
    convert_image_path,
    serialize_unit,
    serialize_ingredient,
    serialize_nutrition,
    serialize_recipe,
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


def _make_unit(**kw):
    base = dict(
        id=10, name="克", abbreviation="g", plural_form=None,
        unit_type="mass", si_factor=Decimal("0.001"), is_si_base=False,
        is_common=True, display_order=3, unit_system="market",
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
    assert out["unit_system"] == "market"


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
