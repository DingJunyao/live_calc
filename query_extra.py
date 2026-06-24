import sqlite3, json

conn = sqlite3.connect('backend/data/livecalc.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

print('===== QUERY 4: Ingredient hierarchies for 花椒 =====')
c.execute("""
SELECT ih.id, ih.child_id, ci.name as child_name, ih.parent_id, pi.name as parent_name, ih.relation_type, ih.strength
FROM ingredient_hierarchies ih
JOIN ingredients ci ON ci.id = ih.child_id
JOIN ingredients pi ON pi.id = ih.parent_id
WHERE ci.name LIKE '%花椒%' OR pi.name LIKE '%花椒%'
""")
rows = c.fetchall()
for row in rows:
    print(dict(row))

# Products for 花椒 ingredients
print()
print('===== Products for ALL 花椒 ingredients =====')
c.execute("""
SELECT p.id, p.name, p.ingredient_id, i.name as ing_name
FROM products p
JOIN ingredients i ON i.id = p.ingredient_id
WHERE i.name LIKE '%花椒%'
ORDER BY p.id
""")
for row in c.fetchall():
    print(dict(row))

# Product records (price records) for 花椒 products
print()
print('===== Product records for 花椒 products =====')
c.execute("""
SELECT pr.id, pr.product_id, p.name, i.name as ing_name, pr.price, pr.original_quantity, pr.original_unit_id, u.abbreviation, pr.standard_quantity, pr.standard_unit_id
FROM product_records pr
JOIN products p ON p.id = pr.product_id
JOIN ingredients i ON i.id = p.ingredient_id
LEFT JOIN units u ON u.id = pr.original_unit_id
WHERE i.name LIKE '%花椒%'
ORDER BY pr.id
""")
for row in c.fetchall():
    print(dict(row))

# Unit 颗
print()
print('===== Unit "颗" =====')
c.execute("SELECT * FROM units WHERE abbreviation = '颗' OR name = '颗'")
for row in c.fetchall():
    print(dict(row))
print()
c.execute("SELECT * FROM units WHERE abbreviation = 'g'")
for row in c.fetchall():
    print(dict(row))

# Check piece_weight for 花椒 (ingredient_id=57)
print()
print('===== 花椒 ingredient (id=57) piece_weight =====')
c.execute("SELECT id, name, piece_weight, piece_weight_unit_id FROM ingredients WHERE id=57")
print(dict(c.fetchone()))

# Check unit_conversions for 颗
print()
print('===== Unit conversions for 颗 =====')
c.execute("""
SELECT uc.*, u_from.abbreviation as from_abbr, u_to.abbreviation as to_abbr
FROM unit_conversions uc
JOIN units u_from ON u_from.id = uc.from_unit_id
JOIN units u_to ON u_to.id = uc.to_unit_id
WHERE u_from.abbreviation = '颗'
""")
for row in c.fetchall():
    print(dict(row))

# Check what other units are used for 花椒 in recipe_ingredients
print()
print('===== All units used in recipe_ingredients for 花椒 ingredients =====')
c.execute("""
SELECT DISTINCT ri.unit_id, u.abbreviation, u.name, u.unit_type
FROM recipe_ingredients ri
JOIN ingredients i ON i.id = ri.ingredient_id
JOIN units u ON u.id = ri.unit_id
WHERE i.name LIKE '%花椒%'
""")
for row in c.fetchall():
    print(dict(row))

# Also check which specific recipes use 花椒 and how much
print()
print('===== All recipes using 花椒 ingredients =====')
c.execute("""
SELECT r.id as recipe_id, r.name as recipe_name, ri.id as ri_id, ri.quantity, ri.quantity_range, u.abbreviation, i.id as ing_id, i.name as ing_name
FROM recipes r
JOIN recipe_ingredients ri ON ri.recipe_id = r.id
JOIN ingredients i ON i.id = ri.ingredient_id
LEFT JOIN units u ON u.id = ri.unit_id
WHERE i.name LIKE '%花椒%'
ORDER BY r.id, ri.id
""")
for row in c.fetchall():
    d = dict(row)
    print(d)

conn.close()
