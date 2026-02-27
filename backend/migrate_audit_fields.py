#!/usr/bin/env python3
"""
数据库审计字段迁移脚本
为所有相关表添加审计字段（created_by, updated_by, is_active）和软删除功能
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, text
from app.config import settings

def migrate_audit_fields():
    """执行审计字段迁移"""
    print("开始执行审计字段迁移...")

    # 创建数据库引擎
    engine = create_engine(settings.database_url)

    # 读取SQL脚本
    sql_file = Path(__file__).parent / "update_audit_fields_sqlite.sql"
    if not sql_file.exists():
        print(f"错误: SQL脚本文件不存在 {sql_file}")
        return False

    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_commands = f.read()

    try:
        # 执行SQL命令
        with engine.connect() as conn:
            # 分割SQL命令并逐个执行
            commands = [cmd.strip() for cmd in sql_commands.split(';') if cmd.strip()]

            for cmd in commands:
                if cmd:  # 确保命令不为空
                    conn.execute(text(cmd))

            conn.commit()

        print("数据库审计字段迁移成功完成!")
        return True

    except Exception as e:
        print(f"数据库迁移失败: {e}")
        return False

if __name__ == "__main__":
    migrate_audit_fields()