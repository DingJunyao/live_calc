"""
时区数据迁移脚本

将旧的价格记录时间（存储为本地时间）转换为UTC时间

问题：
- 旧数据（created_at 不为空）：recorded_at 存储的是本地时间
- 新数据（created_at 为空）：recorded_at 存储的是UTC时间

解决方案：
- 将旧数据的 recorded_at 时间减8小时，转换为UTC时间
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


def migrate_to_utc(db_path: str, dry_run: bool = True):
    """
    将旧数据的 recorded_at 从本地时间转换为UTC时间

    Args:
        db_path: 数据库文件路径
        dry_run: 是否为试运行（不实际修改数据）
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 查找需要迁移的记录
    cursor.execute("""
        SELECT id, product_name, recorded_at
        FROM product_records
        WHERE created_at IS NOT NULL
        ORDER BY recorded_at
    """)

    records = cursor.fetchall()
    print(f"找到 {len(records)} 条需要迁移的记录\n")

    if dry_run:
        print("=== 试运行模式（不会实际修改数据）===\n")
        print("前10条记录预览：")
        print("-" * 80)
        for i, (record_id, name, old_time_str) in enumerate(records[:10], 1):
            old_dt = datetime.fromisoformat(old_time_str.replace(' ', 'T'))
            new_dt = old_dt - timedelta(hours=8)
            print(f"{i}. [{record_id}] {name}")
            print(f"   旧时间（本地）: {old_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   新时间（UTC）  : {new_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            print()

        if len(records) > 10:
            print(f"... 还有 {len(records) - 10} 条记录")
            print("\n范围：")
            first_time = datetime.fromisoformat(records[0][2].replace(' ', 'T'))
            last_time = datetime.fromisoformat(records[-1][2].replace(' ', 'T'))
            print(f"  最早: {first_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  最晚: {last_time.strftime('%Y-%m-%d %H:%M:%S')}")

        print("\n" + "=" * 80)
        print("如需执行迁移，请运行：python migrate_old_records_to_utc.py --execute")
        return

    # 实际执行迁移
    print("=== 开始迁移 ===\n")

    success_count = 0
    error_count = 0

    for record_id, name, old_time_str in records:
        try:
            old_dt = datetime.fromisoformat(old_time_str.replace(' ', 'T'))
            new_dt = old_dt - timedelta(hours=8)
            new_time_str = new_dt.strftime('%Y-%m-%d %H:%M:%S.%f')

            cursor.execute("""
                UPDATE product_records
                SET recorded_at = ?
                WHERE id = ?
            """, (new_time_str, record_id))

            success_count += 1

            if success_count % 50 == 0:
                print(f"已处理 {success_count} 条记录...")

        except Exception as e:
            error_count += 1
            print(f"错误：记录 {record_id} ({name}) 迁移失败: {e}")

    conn.commit()
    conn.close()

    print(f"\n=== 迁移完成 ===")
    print(f"成功: {success_count} 条")
    print(f"失败: {error_count} 条")
    print("\n请刷新页面验证时间显示是否正确")


if __name__ == "__main__":
    import sys

    db_path = "data/livecalc.db"

    # 检查数据库文件是否存在
    if not Path(db_path).exists():
        print(f"错误：数据库文件不存在: {db_path}")
        sys.exit(1)

    # 检查是否有 --execute 参数
    execute = "--execute" in sys.argv or "-e" in sys.argv

    if execute:
        print("⚠️  警告：即将修改数据库数据！")
        print("建议先备份数据库文件\n")

        confirm = input("确认执行迁移？(yes/no): ")
        if confirm.lower() != "yes":
            print("已取消")
            sys.exit(0)

    migrate_to_utc(db_path, dry_run=not execute)
