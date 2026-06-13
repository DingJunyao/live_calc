"""List all ingredients with their current categories"""
import sqlite3, os

db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'livecalc.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute('''
    SELECT i.id, i.name, ic.display_name, ic.name
    FROM ingredients i
    LEFT JOIN ingredient_categories ic ON i.category_id = ic.id
    WHERE i.is_active = 1
    ORDER BY ic.sort_order, i.name
''')

print('All ingredients:')
for r in cur.fetchall():
    cat_display = r[2] if r[2] else '(未分类)'
    print(f'  [{r[0]:>4}] {r[1]:<20} <- {cat_display}')

conn.close()
