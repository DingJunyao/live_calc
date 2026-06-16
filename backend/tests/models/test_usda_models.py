from app.models.usda import UsdaFood, UsdaFoodNutrient, TranslationConfig, UsdaTask


def test_usda_food_fields():
    food = UsdaFood(fdc_id=123456, data_type="foundation", description="Chicken, raw")
    assert food.fdc_id == 123456
    assert food.data_type == "foundation"
    assert food.translate_status == "pending"  # 默认值
    assert food.description_zh is None


def test_translation_config_to_dict():
    cfg = TranslationConfig()
    d = cfg.to_dict()
    assert "ai" in d and "machine" in d


def test_usda_task_defaults():
    task = UsdaTask(task_type="download")
    assert task.status == "pending"
