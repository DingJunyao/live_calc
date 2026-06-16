# backend/tests/services/test_nutrient_mapping.py
from app.services.usda.nutrient_mapping import map_nutrient_name, NUTRIENT_TRANSLATIONS


def test_known_nutrient():
    # live_calc 核心营养素用「能量」（见 nutrition_import_service.CORE_DISPLAY_MAP），
    # 参考项目原本用「热量」，此处已对齐到 live_calc 用词。
    assert map_nutrient_name("Energy") == "能量"
    assert map_nutrient_name("Protein") == "蛋白质"
    assert map_nutrient_name("Fiber, total dietary") == "膳食纤维"


def test_case_insensitive():
    assert map_nutrient_name("ENERGY") == "能量"


def test_unknown_returns_none():
    assert map_nutrient_name("Some Weird Nutrient XYZ") is None


def test_table_nonempty():
    assert len(NUTRIENT_TRANSLATIONS) >= 50
