import pytest
from app.schemas.recipe import RecipeCostRangeResponse


def test_recipe_cost_range_response():
    """测试 RecipeCostRangeResponse 响应模型"""
    data = {
        "id": 1,
        "recipe_id": 123,
        "recipe_name": "红烧肉",
        "date": "2024-03-15",
        "min_cost": 21.00,
        "max_cost": 25.60,
        "avg_cost": 23.30,
        "recorded_at": 1710460800
    }
    response = RecipeCostRangeResponse(**data)
    assert response.id == 1
    assert response.min_cost == 21.00
    assert response.max_cost == 25.60
    assert response.avg_cost == 23.30
