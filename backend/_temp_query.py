import sqlite3
import json

conn = sqlite3.connect('data/livecalc.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=== 1. 计数单位缺少合理 piece_weight 的原料 ===")
cursor.execute("""
SELECT i.id AS ingredient_id, i.name AS ingredient_name,
       u.name AS unit_name, u.unit_system,
       COUNT(DISTINCT ri.id) AS recipe_count,
       i.piece_weight, i.ai_inferred
FROM recipe_ingredients ri
JOIN ingredients i ON i.id = ri.ingredient_id
JOIN units u ON u.id = ri.unit_id
WHERE u.unit_system = 'count'
  AND (i.piece_weight IS NULL OR i.piece_weight = 100)
  AND i.is_active = 1
GROUP BY i.id
ORDER BY recipe_count DESC
""")
rows = cursor.fetchall()
print(f"共 {len(rows)} 条结果")
for r in rows:
    print(f"  id={r['ingredient_id']}, name={r['ingredient_name']}, unit={r['unit_name']}({r['unit_system']}), recipe_count={r['recipe_count']}, piece_weight={r['piece_weight']}, ai_inferred={r['ai_inferred']}")

print()
print("=== 2. 用量为空/模糊的条目统计 ===")
cursor.execute("""
SELECT i.id AS ingredient_id, i.name AS ingredient_name,
       COUNT(DISTINCT ri.id) AS recipe_count,
       ri.quantity, ri.quantity_range, ri.original_quantity,
       ri.ai_inferred
FROM recipe_ingredients ri
JOIN ingredients i ON i.id = ri.ingredient_id
WHERE (ri.quantity IS NULL AND ri.quantity_range IS NULL)
   OR ri.original_quantity IN ('适量', '少许', '少量')
GROUP BY i.id
ORDER BY recipe_count DESC
""")
rows = cursor.fetchall()
print(f"共 {len(rows)} 条结果")
for r in rows:
    print(f"  id={r['ingredient_id']}, name={r['ingredient_name']}, recipe_count={r['recipe_count']}, qty={r['quantity']}, qty_range={r['quantity_range']}, orig_qty={r['original_quantity']}, ai_inferred={r['ai_inferred']}")

print()
print("=== 3. 模糊用量条目的详细上下文 ===")
cursor.execute("""
SELECT ri.id, r.name AS recipe_name, i.name AS ingredient_name,
       u.name AS unit_name, u.unit_system,
       ri.quantity, ri.quantity_range, ri.original_quantity,
       i.piece_weight
FROM recipe_ingredients ri
JOIN recipes r ON r.id = ri.recipe_id
JOIN ingredients i ON i.id = ri.ingredient_id
LEFT JOIN units u ON u.id = ri.unit_id
WHERE (ri.quantity IS NULL AND ri.quantity_range IS NULL)
   OR ri.original_quantity IN ('适量', '少许', '少量')
ORDER BY i.name, r.name
""")
rows = cursor.fetchall()
print(f"共 {len(rows)} 条记录")
for r in rows:
    print(f"  ri_id={r['id']}, recipe={r['recipe_name']}, ingredient={r['ingredient_name']}, unit={r['unit_name']}({r['unit_system']}), qty={r['quantity']}, qty_range={r['quantity_range']}, orig_qty={r['original_quantity']}, piece_weight={r['piece_weight']}")

print()
print("=== 4. 计数单位缺失 piece_weight 的详细上下文 ===")
cursor.execute("""
SELECT ri.id, r.name AS recipe_name, i.name AS ingredient_name,
       u.name AS unit_name, ri.quantity, ri.original_quantity
FROM recipe_ingredients ri
JOIN recipes r ON r.id = ri.recipe_id
JOIN ingredients i ON i.id = ri.ingredient_id
JOIN units u ON u.id = ri.unit_id
WHERE u.unit_system = 'count'
  AND (i.piece_weight IS NULL OR i.piece_weight = 100)
  AND i.is_active = 1
ORDER BY i.name, r.name
""")
rows = cursor.fetchall()
print(f"共 {len(rows)} 条记录")
for r in rows:
    print(f"  ri_id={r['id']}, recipe={r['recipe_name']}, ingredient={r['ingredient_name']}, unit={r['unit_name']}, qty={r['quantity']}, orig_qty={r['original_quantity']}")

conn.close()
