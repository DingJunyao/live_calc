"""临时脚本: 批量更新 ingredients.piece_weight"""
import sys
import os

# 使用 .env 中配置的数据库
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.core.config import settings
from sqlalchemy import text, create_engine

engine = create_engine(str(settings.database_url))

updates = [
    (0.002, [661]),
    (0.005, [115]),
    (0.05,  [641, 630, 442]),
    (0.1,   [502]),
    (0.3,   [53]),
    (0.5,   [412, 561]),
    (1,     [66]),
    (2,     [321]),
    (4,     [496]),
    (5,     [62, 459]),
    (10,    [580]),
    (15,    [569, 163, 186, 363]),
    (18,    [172]),
    (25,    [378, 47]),
    (30,    [158, 688, 725]),
    (35,    [702]),
    (40,    [282]),
    (60,    [279]),
    (120,   [49]),
    (184,   [434]),
    (200,   [673, 696, 283]),
    (250,   [714]),
    (300,   [165, 239]),
    (500,   [664]),
    (1500,  [150]),
]

with engine.connect() as conn:
    # 使用乐观事务模式（MySQL 需显式 BEGIN）
    with conn.begin():
        total = 0
        for pw, ids in updates:
            placeholders = ','.join([f':id{i}' for i in range(len(ids))])
            params = {'pw': pw, 'unit_abbr': 'g'}
            for i, id_val in enumerate(ids):
                params[f'id{i}'] = id_val
            sql = text(
                f'UPDATE ingredients SET piece_weight=:pw, '
                f'piece_weight_unit_id=(SELECT id FROM units WHERE abbreviation=:unit_abbr), '
                f'ai_inferred=1 WHERE id IN ({placeholders})'
            )
            result = conn.execute(sql, params)
            n = result.rowcount
            total += n
            print(f'OK: piece_weight={pw}g -> {n} rows (ids={ids})')
        print(f'\nTotal: {total} rows updated across {len(updates)} statements')

# 验证
with engine.connect() as conn:
    result = conn.execute(text(
        "SELECT COUNT(*) FROM ingredients WHERE id IN :ids AND piece_weight IS NOT NULL"
    ), {'ids': tuple([661,115,641,630,442,502,53,412,561,66,321,496,62,459,580,569,163,186,363,172,378,47,158,688,725,702,282,279,49,434,673,696,283,714,165,239,664,150])})
    count = result.fetchone()[0]
    print(f'Verified: {count}/38 ingredients now have piece_weight')

engine.dispose()
print('Done.')
