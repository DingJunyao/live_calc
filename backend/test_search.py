from app.core.database import get_db
from app.models.product import ProductRecord
from app.models.product_entity import Product
from app.models.nutrition import Ingredient
from sqlalchemy import or_

db = next(get_db())

def _make_alias_search_term(term: str) -> str:
    import json
    return json.dumps(term)[1:-1]

for search_term, desc in [("西红柿", "别名搜索"), ("番茄", "直接名称搜索")]:
    print(f"\n=== {desc}: {search_term} ===")

    query = db.query(ProductRecord).filter(ProductRecord.user_id == 1)
    alias_search = _make_alias_search_term(search_term)
    query = query.join(Product, ProductRecord.product_id == Product.id).join(
        Ingredient, Product.ingredient_id == Ingredient.id
    ).filter(
        or_(
            ProductRecord.product_name.contains(search_term),
            Ingredient.name.contains(search_term),
            Ingredient.aliases.contains(alias_search)
        )
    )

    total = query.count()
    print(f"找到记录数: {total}")
    for r in query.limit(3).all():
        print(f"  - {r.product_name} (商品ID: {r.product_id})")

db.close()
