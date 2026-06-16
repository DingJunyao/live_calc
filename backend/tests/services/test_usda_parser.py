from app.services.usda.parser import parse_usda_food, dedupe_foods


def test_parse_food():
    raw = {
        "fdcId": 123456,
        "description": "Chicken, breast, raw",
        "publicationDate": "2024-04",
        "foodNutrients": [
            {"nutrient": {"name": "Energy", "number": "208"}, "amount": 110.0, "unitName": "kcal"},
            {"nutrient": {"name": "Protein", "number": "203"}, "amount": 23.0, "unitName": "g"},
        ],
    }
    food = parse_usda_food(raw, data_type="foundation")
    assert food["fdc_id"] == 123456
    assert food["description"] == "Chicken, breast, raw"
    assert food["data_type"] == "foundation"
    assert len(food["nutrients"]) == 2
    assert food["nutrients"][0]["name"] == "Energy"
    assert food["nutrients"][0]["name_zh"] == "能量"  # 映射命中


def test_dedupe_same_description_keeps_foundation():
    a = {"fdc_id": 1, "description": "Apple, raw", "data_type": "sr_legacy", "nutrients": [{"name": "Energy"}]}
    b = {"fdc_id": 2, "description": "Apple, raw", "data_type": "foundation", "nutrients": [{"name": "Energy"}]}
    out = dedupe_foods([a, b])
    assert len(out) == 1
    assert out[0]["data_type"] == "foundation"  # foundation 优先


def test_dedupe_same_type_keeps_more_nutrients():
    a = {"fdc_id": 1, "description": "Apple, raw", "data_type": "foundation", "nutrients": [{"name": "Energy"}]}
    b = {"fdc_id": 2, "description": "Apple, raw", "data_type": "foundation", "nutrients": [{"name": "Energy"}, {"name": "Protein"}]}
    out = dedupe_foods([a, b])
    assert len(out) == 1
    assert len(out[0]["nutrients"]) == 2  # 营养素更多者胜


def test_parse_food_null_nutrient():
    # USDA 数据中 foodNutrients 项的 nutrient 可能为 null，项本身也可能为 null，不应崩
    raw = {
        "fdcId": 1,
        "description": "Test, raw",
        "foodNutrients": [
            {"nutrient": None, "amount": 0, "unitName": "g"},  # nutrient=null
            {"nutrient": {"name": "Energy", "number": "208"}, "amount": 50, "unitName": "kcal"},
            None,  # 项本身为 null
        ],
    }
    food = parse_usda_food(raw, data_type="foundation")
    assert food["fdc_id"] == 1
    # null 项被跳过，有效项保留
    assert len(food["nutrients"]) == 1
    assert food["nutrients"][0]["name"] == "Energy"
