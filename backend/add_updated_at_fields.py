#!/usr/bin/env python3
"""
为剩余表添加updated_at字段
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, text
from app.config import settings

def add_remaining_updated_at():
    """为剩余表添加updated_at字段"""
    print("开始为剩余表添加updated_at字段...")

    # 创建数据库引擎
    engine = create_engine(settings.database_url)

    try:
        with engine.connect() as conn:
            # 读取SQL脚本
            sql_file = Path(__file__).parent / "add_remaining_updated_at.sql"
            if not sql_file.exists():
                print(f"错误: SQL脚本文件不存在 {sql_file}")
                return False

            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_commands = f.read()

            # 执行SQL命令
            commands = [cmd.strip() for cmd in sql_commands.split(';') if cmd.strip()]

            for cmd in commands:
                if cmd and not cmd.strip().startswith('--'):  # 跳过注释
                    try:
                        conn.execute(text(cmd))
                        print(f"执行命令: {cmd[:50]}...")
                    except Exception as e:
                        print(f"执行命令时出错 (可能该列已存在): {e}")
                        continue

            conn.commit()
            print("为剩余表添加updated_at字段完成!")

    except Exception as e:
        print(f"添加updated_at字段失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    add_remaining_updated_at()