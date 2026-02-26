#!/usr/bin/env python3
"""
检查数据库中的地点数据
"""

import sqlite3
import sys
from pathlib import Path

def check_locations_table():
    # 数据库路径
    db_path = Path("./backend/data/livecalc.db")

    if not db_path.exists():
        print(f"数据库文件不存在: {db_path}")
        return

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 检查表结构
        print("=== 检查表结构 ===")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"数据库中存在的表: {[table[0] for table in tables]}")

        if 'locations' in [table[0] for table in tables]:
            print("\n=== 检查地点表结构 ===")
            cursor.execute("PRAGMA table_info(locations);")
            columns = cursor.fetchall()
            print("地点表列结构:")
            for col in columns:
                print(f"  {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULL'}")

            print("\n=== 检查地点表数据 ===")
            # 查询地点表的所有记录
            cursor.execute("SELECT COUNT(*) FROM locations;")
            total_count = cursor.fetchone()[0]
            print(f"总地点数量: {total_count}")

            if total_count > 0:
                print("\n所有地点记录:")
                cursor.execute("SELECT id, user_id, name, address, latitude, longitude, created_at FROM locations ORDER BY created_at DESC;")
                records = cursor.fetchall()
                for record in records:
                    print(f"  ID: {record[0]}, 用户ID: {record[1]}, 名称: {record[2]}, 地址: {record[3]}, 纬度: {record[4]}, 经度: {record[5]}, 创建时间: {record[6]}")
            else:
                print("地点表中没有数据")

        else:
            print("\n警告: 没有找到 'locations' 表")

        conn.close()

    except Exception as e:
        print(f"检查数据库时出错: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_locations_table()