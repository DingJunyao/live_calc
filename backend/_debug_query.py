import sqlite3
conn = sqlite3.connect(r'data/livecalc.db')
cur = conn.cursor()
cur.execute("SELECT id, hex(original_quantity), original_quantity FROM recipe_ingredients WHERE original_quantity IS NOT NULL AND original_quantity != '' AND original_quantity != ' ' LIMIT 5")
for row in cur.fetchall():
    print(row)
cur.execute("SELECT COUNT(*) FROM recipe_ingredients WHERE original_quantity LIKE '%\\u9002%'")
print("LIKE with backslash:", cur.fetchone())
cur.execute("SELECT COUNT(*) FROM recipe_ingredients WHERE instr(original_quantity, '\\u9002') > 0")
print("INSTR with backslash:", cur.fetchone())
conn.close()
