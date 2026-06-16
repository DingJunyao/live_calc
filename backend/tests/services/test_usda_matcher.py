"""USDA 匹配写入 service 测试。

注意：``Product.ingredient_id`` 在模型中是 nullable=False，
因此 "no_ingredient_direct_write" 用例改为：商品虽挂在原料下，
但原料无 NutritionData（无骨架可复制），验证 USDA 数据仍直接写入。
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.nutrition import Ingredient
from app.models.nutrition_data import NutritionData
from app.models.product_entity import Product
from app.models.usda import UsdaFood, UsdaFoodNutrient
from app.services.usda.matcher import match_ingredient, match_product


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    # Apple, raw — 含能量(52 kcal)与蛋白质(0.3 g)
    s.add(UsdaFood(fdc_id=100, data_type="foundation", description="Apple, raw"))
    s.add_all([
        UsdaFoodNutrient(fdc_id=100, name="Energy", name_zh="能量",
                         amount=52, unit_name="kcal"),
        UsdaFoodNutrient(fdc_id=100, name="Protein", name_zh="蛋白质",
                         amount=0.3, unit_name="g"),
    ])
    s.commit()
    yield s
    s.close()


def test_match_ingredient_clears_and_writes(db):
    ing = Ingredient(name="苹果", is_active=True)
    db.add(ing)
    db.commit()
    # 预置一条旧的 custom 营养数据
    db.add(NutritionData(
        ingredient_id=ing.id, source="custom",
        nutrients={"core_nutrients": {"旧": {"value": 1}}},
    ))
    db.commit()

    match_ingredient(db, ingredient_id=ing.id, fdc_id=100)

    nd = db.query(NutritionData).filter(
        NutritionData.ingredient_id == ing.id
    ).all()
    assert len(nd) == 1
    assert nd[0].source == "usda_manual_match"
    assert nd[0].usda_id == "100"
    assert "能量" in nd[0].nutrients["core_nutrients"]
    assert nd[0].nutrients["core_nutrients"]["能量"]["value"] == 52
    # all_nutrients 用英文 key
    assert nd[0].nutrients["all_nutrients"]["energy"]["value"] == 52


def test_match_product_skeleton_then_override(db):
    ing = Ingredient(name="苹果", is_active=True)
    db.add(ing)
    db.commit()
    # 原料营养含「钙」(9.0) 与「能量」(1.0)
    db.add(NutritionData(
        ingredient_id=ing.id, source="custom",
        nutrients={
            "core_nutrients": {
                "钙": {"value": 9.0, "unit": "mg", "key": "calcium"},
                "能量": {"value": 1.0, "unit": "kcal", "key": "energy"},
            },
        },
    ))
    db.commit()
    prod = Product(name="苹果", ingredient_id=ing.id, is_active=True)
    db.add(prod)
    db.commit()

    match_product(db, product_id=prod.id, fdc_id=100)
    db.refresh(prod)

    data = prod.custom_nutrition_data
    # 结构：三层 + 元数据
    assert set(["core_nutrients", "all_nutrients", "nutrient_details",
                "source"]).issubset(data.keys())
    assert data["source"] == "usda_manual_match"
    assert data["usda_id"] == "100"

    core = data["core_nutrients"]
    # 能量被 USDA 覆盖为 52（不是原料的 1.0）
    assert core["能量"]["value"] == 52
    # 钙：USDA 未命中，骨架保留为 0
    assert core["钙"]["value"] == 0

    # all_nutrients 覆盖校验
    assert data["all_nutrients"]["energy"]["value"] == 52
    # 钙骨架也应出现在 all_nutrients（key=calcium，值 0）
    assert data["all_nutrients"]["calcium"]["value"] == 0


def test_match_product_no_ingredient_direct_write(db):
    """商品挂在原料下但原料无 NutritionData：骨架为空，仅写 USDA 命中项。"""
    ing = Ingredient(name="独立原料", is_active=True)
    db.add(ing)
    db.commit()
    # 注意：不创建任何 NutritionData
    prod = Product(name="独立商品", ingredient_id=ing.id, is_active=True)
    db.add(prod)
    db.commit()

    match_product(db, product_id=prod.id, fdc_id=100)
    db.refresh(prod)

    data = prod.custom_nutrition_data
    # 无骨架，core 仅含 USDA 命中项（能量）
    assert "能量" in data["core_nutrients"]
    assert data["core_nutrients"]["能量"]["value"] == 52
    # 骨架为空：不应出现任意非 USDA 的项
    assert set(data["core_nutrients"].keys()) == {"能量", "蛋白质"}
