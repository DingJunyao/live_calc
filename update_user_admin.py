#!/usr/bin/env python3
"""
修改数据库，将 billding 用户设置为管理员
"""

import sqlite3
import sys
from pathlib import Path

def make_billding_admin():
    # 数据库路径
    db_path = Path("./backend/data/livecalc.db")

    if not db_path.exists():
        print(f"数据库文件不存在: {db_path}")
        return False

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        print("=== 修改用户权限 ===")

        # 首先查询billding用户的信息
        cursor.execute("SELECT id, username, email, is_admin FROM users WHERE username = 'billding';")
        user = cursor.fetchone()

        if user:
            user_id, username, email, is_admin = user
            print(f"当前用户信息: ID={user_id}, 用户名={username}, 邮箱={email}, 管理员={bool(is_admin)}")

            if is_admin:
                print("billding已经是管理员，无需修改。")
                conn.close()
                return True

            # 更新用户权限
            cursor.execute("UPDATE users SET is_admin = 1 WHERE username = 'billding';")
            conn.commit()

            # 验证更改
            cursor.execute("SELECT id, username, email, is_admin FROM users WHERE username = 'billding';")
            updated_user = cursor.fetchone()
            updated_is_admin = updated_user[3]

            if updated_is_admin:
                print(f"✅ 成功将用户 {username} (ID: {user_id}) 设置为管理员")
                print(f"   更新后用户信息: ID={updated_user[0]}, 用户名={updated_user[1]}, 管理员={bool(updated_is_admin)}")
            else:
                print("❌ 更新失败")

        else:
            print("❌ 未找到用户名为 'billding' 的用户")

        conn.close()
        return True

    except Exception as e:
        print(f"修改数据库时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = make_billding_admin()
    if success:
        print("\n🎉 数据库更新完成！")
    else:
        print("\n❌ 数据库更新失败！")
        sys.exit(1)