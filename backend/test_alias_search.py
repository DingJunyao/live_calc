"""测试别名搜索功能"""
from app.core.database import get_db
from app.models.nutrition import Ingredient
from app.models.product_entity import Product
from app.models.product import ProductRecord
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
import json

db = next(get_db())

def _make_alias_search_term(term: str) -> str:
    """生成用于搜索 JSON 别名数组的 Unicode 转义字符串"""
    return json.dumps(term)[1:-1]

print("=" * 60)
print("测试 1: 食材别名搜索")
print("=" * 60)

search_term = "西红柿"
alias_search = _make_alias_search_term(search_term)

query = db.query(Ingredient).filter(Ingredient.is_active == True).filter(
    or_(
        Ingredient.name.contains(search_term),
        Ingredient.aliases.contains(alias_search)
    )
)

results = query.all()
print(f"搜索 '{search_term}' (别名搜索: {alias_search})")
print(f"找到 {len(results)} 个食材:")
for ing in results:
    print(f"  - {ing.name} (别名: {ing.aliases})")

print("\n" + "=" * 60)
print("测试 2: 商品别名搜索（通过食材别名）")
print("=" * 60)

query = db.query(Product).options(
    joinedload(Product.ingredient)
).filter(Product.is_active == True).filter(
    or_(
        Product.name.contains(search_term),
        Product.ingredient.has(
            or_(
                Ingredient.name.contains(search_term),
                Ingredient.aliases.contains(alias_search)
            )
        )
    )
)

results = query.all()
print(f"搜索 '{search_term}'")
print(f"找到 {len(results)} 个商品:")
for p in results:
    ingredient_name = p.ingredient.name if p.ingredient else None
    print(f"  - {p.name} (关联食材: {ingredient_name})")

print("\n" + "=" * 60)
print("测试 3: 价格记录别名搜索（通过商品食材别名）")
print("=" * 60)

query = db.query(ProductRecord).filter(ProductRecord.user_id == 1).join(
    Product, ProductRecord.product_id == Product.id
).join(
    Ingredient, Product.ingredient_id == Ingredient.id
).filter(
    or_(
        ProductRecord.product_name.contains(search_term),
        Ingredient.name.contains(search_term),
        Ingredient.aliases.contains(alias_search)
    )
)

results = query.all()
print(f"搜索 '{search_term}'")
print(f"找到 {len(results)} 条价格记录:")
for r in results[:5]:  # 只显示前5条
    print(f"  - {r.product_name} (¥{r.price})")

db.close()
print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
