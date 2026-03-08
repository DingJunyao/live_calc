from app.core.database import SessionLocal
from app.models.unit import Unit

db = SessionLocal()
units = db.query(Unit).order_by(Unit.unit_type, Unit.display_order).all()

print(f'总共有 {len(units)} 个单位:')
current_type = None
for u in units:
    if u.unit_type != current_type:
        current_type = u.unit_type
        print(f'\n【{u.unit_type}】')
    common_mark = '是' if u.is_common else '否'
    print(f'  ID:{u.id:2d} | {u.name:6s} | {u.abbreviation:8s} | SI因子:{u.si_factor:8.6f} | 常用:{common_mark}')

db.close()
