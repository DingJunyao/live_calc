#!/usr/bin/env python3
"""
检查数据库中的用户数据
"""

import sqlite3
import sys
from pathlib import Path

def check_users_table():
    # 数据库路径
    db_path = Path("./backend/data/livecalc.db")

    if not db_path.exists():
        print(f"数据库文件不存在: {db_path}")
        return

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        print("=== 检查用户表数据 ===")
        # 查询用户表的所有记录
        cursor.execute("SELECT id, username, email, is_admin, is_active FROM users ORDER BY id;")
        records = cursor.fetchall()

        if len(records) > 0:
            print("所有用户记录:")
            for record in records:
                print(f"  ID: {record[0]}, 用户名: {record[1]}, 邮箱: {record[2]}, 管理员: {record[3]}, 激活: {record[4]}")
        else:
            print("用户表中没有数据")

        # 统计每个用户拥有的地点数量
        print("\n=== 每个用户的地点数量 ===")
        cursor.execute("""
            SELECT u.id, u.username, COUNT(l.id) as location_count
            FROM users u
            LEFT JOIN locations l ON u.id = l.user_id
            GROUP BY u.id, u.username
            ORDER BY u.id;
        """)
        user_stats = cursor.fetchall()
        for stat in user_stats:
            print(f"  用户ID: {stat[0]}, 用户名: {stat[1]}, 地点数量: {stat[2]}")

        conn.close()

    except Exception as e:
        print(f"检查数据库时出错: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_users_table()