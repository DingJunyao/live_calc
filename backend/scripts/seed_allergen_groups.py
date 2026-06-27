"""
过敏原分组种子脚本
基于 GB 7718-2025《预包装食品标签通则》的 8 大类强制标识过敏原
+ 常见自愿标示类别，创建黑名单分组并映射现有原料。
用原料名称匹配来查找 ID，避免硬编码 ID 漂移问题。

执行方式: python -X utf8 scripts/seed_allergen_groups.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('DATABASE_URL', 'sqlite:///data/livecalc.db')

from app.core.database import SessionLocal
from app.models.blacklist_group import BlacklistGroup, BlacklistGroupIngredient
from app.models.nutrition import Ingredient


# ── 定义 13 个过敏原分组及其原料名称映射 ──────────────────────

ALLERGEN_GROUPS = [
    {
        "name": "含有麸质的谷物及其制品",
        "display_order": 1,
        "ingredient_names": [
            # 小麦面粉类
            "中筋面粉", "低筋面粉", "全麦面粉", "面粉", "高筋面粉",
            # 面筋/谷朊
            "面筋", "面筋块", "谷朊粉",
            # 面包/烘焙类（小麦粉制）
            "吐司", "面包片", "面包糠", "面包", "饼干", "饼干屑",
            "手指饼干", "奥利奥", "手抓饼", "小薄饼", "蛋挞皮",
            # 面条/面食类（小麦粉制）
            "干面条", "面条", "挂面", "方便面", "意大利面", "通心粉",
            "半成品意大利面", "热干面特有的碱水面", "面",
            "荞麦面", "凉皮", "牛筋面", "擀面皮",
            "饺子皮", "馄饨皮",
            # 中式面点（小麦粉制）
            "饺子", "速冻水饺", "速冻馄饨", "馒头", "烧卖皮",
            # 含麸质谷物
            "燕麦", "麦片", "燕麦片",
            # 大麦芽酿造
            "啤酒",
            # 小麦酿造酱油（含麸质）
            "酱油", "生抽", "老抽", "麦芽粉",
        ],
    },
    {
        "name": "甲壳纲类动物及其制品",
        "display_order": 2,
        "ingredient_names": [
            "大虾", "小龙虾", "活虾", "海虾", "罗氏虾",
            "虾", "虾仁", "虾皮", "阿根廷红虾", "开洋", "基围虾",
            "螃蟹", "肉蟹", "青蟹",
        ],
    },
    {
        "name": "鱼类及其制品",
        "display_order": 3,
        "ingredient_names": [
            "三文鱼", "剑骨鱼", "巴沙鱼", "草鱼", "翘嘴鱼",
            "鲈鱼", "鲤鱼", "鳊鱼", "鳜鱼", "鳝鱼", "黑鳕鱼",
            "水浸金枪鱼", "鱼", "鱼头", "鲮鱼罐头", "昂刺鱼",
            "白鱔", "鱼丸", "鱼露",
        ],
    },
    {
        "name": "蛋类及其制品",
        "display_order": 4,
        "ingredient_names": [
            "鸡蛋", "咸鸭蛋", "温泉蛋", "煎蛋", "熟蛋黄",
            "皮蛋", "蛋挞液", "蛋清", "蛋类", "蛋黄",
            "鹌鹑蛋", "鸡蛋皮", "日本豆腐",
            "蛋黄酱",
        ],
    },
    {
        "name": "花生及其制品",
        "display_order": 5,
        "ingredient_names": [
            "花生", "花生碎", "花生油", "花生酱",
        ],
    },
    {
        "name": "大豆及其制品",
        "display_order": 6,
        "ingredient_names": [
            "黄豆", "毛豆", "黑豆",
            "豆腐", "白豆腐", "老豆腐", "内酯豆腐",
            "千张", "豆皮", "百叶", "香干",
            "腐竹", "炸腐竹",
            "腐乳", "南乳", "腐乳汁", "豆母子",
            "豆制品", "素鸡",
            "黄豆酱",
            "豆芽",
            "豆油", "豆豉",
        ],
    },
    {
        "name": "乳及乳制品（含乳糖）",
        "display_order": 7,
        "ingredient_names": [
            "牛奶", "全脂牛奶", "奶粉", "全脂奶粉",
            "炼乳", "加糖炼乳",
            "原味酸奶",
            "奶油", "淡奶油", "重奶油", "奶油奶酪",
            "黄油", "无盐黄油", "有盐黄油",
            "奶酪", "芝士", "芝士片", "芝士碎", "马斯卡彭芝士",
            "帕马森干酪",
            "酥油",
        ],
    },
    {
        "name": "坚果及其果仁类制品",
        "display_order": 8,
        "ingredient_names": [
            "坚果", "坚果碎",
            "杏仁", "栗子", "核桃", "熟松子仁", "腰果",
        ],
    },
    {
        "name": "芝麻及其制品",
        "display_order": 9,
        "ingredient_names": [
            "芝麻", "白芝麻", "黑芝麻",
            "芝麻油", "香油", "麻油",
            "芝麻酱", "芝麻盐",
        ],
    },
    {
        "name": "芹菜及其制品",
        "display_order": 10,
        "ingredient_names": [
            "芹菜", "香芹", "欧芹",
        ],
    },
    {
        "name": "芥末及其制品",
        "display_order": 11,
        "ingredient_names": [
            "芥末", "青芥末", "芥末油",
        ],
    },
    {
        "name": "软体动物及其制品",
        "display_order": 12,
        "ingredient_names": [
            "大田螺", "生蚝", "蛏子",
        ],
    },
    {
        "name": "椰子及其制品",
        "display_order": 13,
        "ingredient_names": [
            "椰浆", "椰子水", "椰汁",
        ],
    },
]


def seed_allergen_groups():
    """创建过敏原分组并映射原料"""
    db = SessionLocal()
    try:
        # 1) 清理旧的错误数据
        existing_count = db.query(BlacklistGroup).count()
        if existing_count > 0:
            print(f"🧹 清理 {existing_count} 个旧分组及关联映射...")
            db.query(BlacklistGroupIngredient).delete()
            db.query(BlacklistGroup).delete()
            db.flush()
            print("   已清理完成")

        # 2) 构建名称→ID 的查找表
        all_ings = db.query(Ingredient).filter(Ingredient.is_active == True).all()
        name_to_id = {}
        for ing in all_ings:
            name_to_id[ing.name] = ing.id
            # 同时也用别名匹配
            if ing.aliases:
                for alias in (ing.aliases if isinstance(ing.aliases, list) else []):
                    if alias and alias not in name_to_id:
                        name_to_id[alias] = ing.id

        # 3) 创建分组并映射原料
        created_count = 0
        mapping_count = 0
        not_found = []

        for group_data in ALLERGEN_GROUPS:
            ingredient_names = group_data.pop("ingredient_names")

            # 按名称查找 ID
            found_ids = []
            for name in ingredient_names:
                ing_id = name_to_id.get(name)
                if ing_id:
                    found_ids.append(ing_id)
                else:
                    not_found.append(f"  [{group_data['name']}] 未找到: {name}")

            # 去重
            found_ids = list(set(found_ids))

            # 创建分组
            group = BlacklistGroup(
                name=group_data["name"],
                display_order=group_data["display_order"],
                is_active=True,
            )
            db.add(group)
            db.flush()

            # 添加原料映射
            for ing_id in found_ids:
                mapping = BlacklistGroupIngredient(
                    group_id=group.id,
                    ingredient_id=ing_id,
                    is_ai_matched=False,
                    is_active=True,
                )
                db.add(mapping)
                mapping_count += 1

            created_count += 1
            print(f"  ✅ {group_data['name']} → {len(found_ids)}/{len(ingredient_names)} 种原料")

        db.commit()

        print(f"\n🎉 完成！共创建 {created_count} 个分组，关联 {mapping_count} 条原料映射。")
        if not_found:
            print(f"\n⚠️  以下原料未找到（共 {len(not_found)} 条）：")
            for msg in not_found:
                print(msg)

    except Exception as e:
        db.rollback()
        print(f"❌ 发生错误：{e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("🌰  过敏原分组种子脚本 - GB 7718-2025")
    print("=" * 60)
    seed_allergen_groups()
