"""Hit the actual API endpoints to check live values"""
import sys
sys.path.insert(0, '.')
from app.core.database import get_db
from app.services.recipe_service import calculate_recipe_cost, calculate_recipe_cost_range_trend
import asyncio

db = next(get_db())

result = asyncio.run(calculate_recipe_cost(325, 1, db))
trend = calculate_recipe_cost_range_trend(325, 1, db, days=7)

print(f"Estimate total_cost: {float(result['total_cost'])}")
print(f"Trend today avg:     {trend[-1]['avg_cost'] if trend else 'N/A'}")
print(f"Match: {abs(float(result['total_cost']) - trend[-1]['avg_cost']) < 0.0001 if trend else False}")
