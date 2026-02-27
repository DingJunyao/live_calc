"""
添加食材密度数据的脚本
"""

from app.core.database import SessionLocal
from app.models.nutrition import Ingredient
from app.models.unit import Unit
from app.models.ingredient_density import IngredientDensity
from decimal import Decimal

def init_ingredient_densities():
    db = SessionLocal()

    try:
        # 首先创建一些常见的食材
        common_ingredients = [
            {"name": "water", "name_variants": {"aliases": ["水", "清水"]}},
            {"name": "flour", "name_variants": {"aliases": ["面粉", "小麦粉"]}},
            {"name": "rice", "name_variants": {"aliases": ["大米", "白米"]}},
            {"name": "milk", "name_variants": {"aliases": ["牛奶"]}},
            {"name": "oil", "name_variants": {"aliases": ["油", "食用油"]}},
            {"name": "sugar", "name_variants": {"aliases": ["糖", "白糖"]}},
        ]

        for ing_data in common_ingredients:
            existing = db.query(Ingredient).filter(Ingredient.name == ing_data["name"]).first()
            if not existing:
                ingredient = Ingredient(**ing_data)
                db.add(ingredient)

        db.commit()

        # 添加密度数据
        # 密度值：质量/体积，例如水的密度是1g/mL
        density_data = [
            {"ingredient_name": "water", "from_unit": "mL", "to_unit": "g", "density": 1.0, "condition": "room temperature"},
            {"ingredient_name": "flour", "from_unit": "mL", "to_unit": "g", "density": 0.57, "condition": "all-purpose flour"},
            {"ingredient_name": "rice", "from_unit": "mL", "to_unit": "g", "density": 0.75, "condition": "uncooked white rice"},
            {"ingredient_name": "milk", "from_unit": "mL", "to_unit": "g", "density": 1.03, "condition": "whole milk"},
            {"ingredient_name": "oil", "from_unit": "mL", "to_unit": "g", "density": 0.92, "condition": "cooking oil"},
            {"ingredient_name": "sugar", "from_unit": "mL", "to_unit": "g", "density": 0.85, "condition": "granulated sugar"},
        ]

        for density_info in density_data:
            ingredient = db.query(Ingredient).filter(Ingredient.name == density_info["ingredient_name"]).first()
            from_unit = db.query(Unit).filter(Unit.abbreviation == density_info["from_unit"]).first()
            to_unit = db.query(Unit).filter(Unit.abbreviation == density_info["to_unit"]).first()

            if ingredient and from_unit and to_unit:
                existing = db.query(IngredientDensity).filter(
                    IngredientDensity.ingredient_id == ingredient.id,
                    IngredientDensity.from_unit_id == from_unit.id,
                    IngredientDensity.to_unit_id == to_unit.id
                ).first()

                if not existing:
                    density = IngredientDensity(
                        ingredient_id=ingredient.id,
                        from_unit_id=from_unit.id,
                        to_unit_id=to_unit.id,
                        density_value=Decimal(str(density_info["density"])),
                        condition=density_info["condition"],
                        confidence=Decimal("1.00"),
                        source="standard reference"
                    )
                    db.add(density)

        db.commit()

        # 添加食材层级关系
        hierarchy_data = [
            {"parent": "flour", "child": "bread flour", "relationship_type": "includes", "confidence": 0.9},
            {"parent": "flour", "child": "cake flour", "relationship_type": "includes", "confidence": 0.9},
            {"parent": "flour", "child": "all-purpose flour", "relationship_type": "includes", "confidence": 1.0},
            {"parent": "rice", "child": "jasmine rice", "relationship_type": "includes", "confidence": 0.8},
            {"parent": "rice", "child": "sticky rice", "relationship_type": "includes", "confidence": 0.8},
        ]

        for hierarchy_info in hierarchy_data:
            parent_ing = db.query(Ingredient).filter(Ingredient.name == hierarchy_info["parent"]).first()
            child_ing = db.query(Ingredient).filter(Ingredient.name == hierarchy_info["child"]).first()

            if parent_ing and child_ing:
                # 先创建子食材（如果没有）
                if not child_ing:
                    child_ingredient = Ingredient(name=hierarchy_info["child"])
                    db.add(child_ingredient)
                    db.commit()
                    child_ing = db.query(Ingredient).filter(Ingredient.name == hierarchy_info["child"]).first()

                from app.models.ingredient_hierarchy import IngredientHierarchy
                existing = db.query(IngredientHierarchy).filter(
                    IngredientHierarchy.parent_id == parent_ing.id,
                    IngredientHierarchy.child_id == child_ing.id
                ).first()

                if not existing:
                    hierarchy = IngredientHierarchy(
                        parent_id=parent_ing.id,
                        child_id=child_ing.id,
                        relationship_type=hierarchy_info["relationship_type"],
                        confidence=hierarchy_info["confidence"]
                    )
                    db.add(hierarchy)

        db.commit()
        print("Ingredient densities and hierarchies initialized successfully!")

    finally:
        db.close()


if __name__ == "__main__":
    init_ingredient_densities()