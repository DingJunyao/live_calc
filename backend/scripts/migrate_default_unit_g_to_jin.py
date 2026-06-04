"""
迁移脚本：将原料的默认单位从「克(g)」改为「斤」

根据 units 表中的数据：
- g (克) 的 abbreviation = 'g'
- 斤 的 abbreviation = '斤'

使用 abbreviation 查找，避免硬编码 ID。
"""

import sqlite3
import sys
import os


def get_db_path():
    """获取数据库路径"""
    # 默认路径
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "livecalc.db")


def main():
    db_path = get_db_path()
    print(f"数据库路径: {db_path}")

    if not os.path.exists(db_path):
        print(f"错误: 数据库文件不存在 - {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 查找克和斤的 ID
    cur.execute("SELECT id, abbreviation FROM units WHERE abbreviation IN ('g', '斤')")
    units = {row[1]: row[0] for row in cur.fetchall()}

    g_id = units.get("g")
    jin_id = units.get("斤")

    if not g_id:
        print("错误: 未找到单位「克(g)」")
        sys.exit(1)
    if not jin_id:
        print("错误: 未找到单位「斤」")
        sys.exit(1)

    print(f"克(g) 的 ID: {g_id}")
    print(f"斤 的 ID: {jin_id}")

    # 统计需要更新的记录
    cur.execute(
        "SELECT COUNT(*) FROM ingredients WHERE default_unit_id = ?",
        (g_id,)
    )
    count = cur.fetchone()[0]
    print(f"需要更新的原料数量: {count}")

    if count == 0:
        print("没有需要更新的记录。")
        conn.close()
        return

    # 显示将要更新的原料（前 20 条）
    cur.execute(
        "SELECT id, name FROM ingredients WHERE default_unit_id = ? LIMIT 20",
        (g_id,)
    )
    print("\n将要更新的原料（前 20 条）:")
    for row in cur.fetchall():
        print(f"  ID={row[0]}, 名称={row[1]}")

    if count > 20:
        print(f"  ... 及其他共 {count} 条")

    # 确认更新
    print(f"\n将把 {count} 条原料的默认单位从「克」改为「斤」")

    # 执行更新
    cur.execute(
        "UPDATE ingredients SET default_unit_id = ? WHERE default_unit_id = ?",
        (jin_id, g_id)
    )
    conn.commit()

    affected = cur.rowcount
    print(f"更新完成，共修改 {affected} 条记录。")

    # 验证
    cur.execute(
        "SELECT COUNT(*) FROM ingredients WHERE default_unit_id = ?",
        (g_id,)
    )
    remaining = cur.fetchone()[0]
    print(f"剩余默认单位为「克」的原料: {remaining}")

    conn.close()


if __name__ == "__main__":
    main()
