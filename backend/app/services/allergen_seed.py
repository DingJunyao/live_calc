"""过敏原黑名单分组种子数据与服务。

将 GB 7718-2025 的 13 类过敏原分组接入数据库初始化流程：
- lifespan 启动时调 ``ensure_allergen_groups`` 幂等创建；
- 命令行脚本 ``scripts/seed_allergen_groups.py`` 复用本模块数据与逻辑，
  保留 destructive 清空重建行为。
"""
import logging

from sqlalchemy.orm import Session

from app.models.blacklist_group import BlacklistGroup, BlacklistGroupIngredient
from app.models.nutrition import Ingredient

logger = logging.getLogger(__name__)


# ── 13 个过敏原分组及其原料名称映射（GB 7718-2025）──────────────
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


def _create_groups(db: Session):
    """创建全部过敏原分组及原料映射（纯创建，不清理、不自开 session）。

    返回 ``(created_count, mapping_count, not_found)``。
    读取 ingredient_names 采用非破坏性 ``.get``，保证 ALLERGEN_GROUPS
    作为模块级常量可被反复调用（原脚本的 ``.pop`` 会破坏常量，已弃用）。
    """
    # 1) 构建 name → id 查找表（含别名）
    all_ings = db.query(Ingredient).filter(Ingredient.is_active == True).all()
    name_to_id = {}
    for ing in all_ings:
        name_to_id.setdefault(ing.name, ing.id)
        if ing.aliases:
            aliases = ing.aliases if isinstance(ing.aliases, list) else []
            for alias in aliases:
                if alias and alias not in name_to_id:
                    name_to_id[alias] = ing.id

    # 2) 逐组创建 + 映射
    created_count = 0
    mapping_count = 0
    not_found = []

    for group_data in ALLERGEN_GROUPS:
        ingredient_names = group_data.get("ingredient_names", [])  # 非破坏性读取
        found_ids = []
        for name in ingredient_names:
            ing_id = name_to_id.get(name)
            if ing_id:
                found_ids.append(ing_id)
            else:
                not_found.append(f"[{group_data['name']}] 未找到: {name}")
        found_ids = list(set(found_ids))  # 去重

        group = BlacklistGroup(
            name=group_data["name"],
            display_order=group_data["display_order"],
            is_active=True,
        )
        db.add(group)
        db.flush()

        for ing_id in found_ids:
            db.add(BlacklistGroupIngredient(
                group_id=group.id,
                ingredient_id=ing_id,
                is_ai_matched=False,
                is_active=True,
            ))
            mapping_count += 1
        created_count += 1

    db.commit()
    return created_count, mapping_count, not_found


def ensure_allergen_groups(db: Session) -> None:
    """幂等确保过敏原分组存在：空表才创建，有数据则跳过。"""
    existing = db.query(BlacklistGroup).count()
    if existing > 0:
        logger.info("过敏原分组已存在（%s 个），跳过初始化", existing)
        return
    created, mappings, not_found = _create_groups(db)
    logger.info(
        "过敏原分组初始化完成：%s 组，%s 条映射，未匹配 %s 条",
        created, mappings, len(not_found),
    )


def upsert_allergen_groups(db: Session) -> dict:
    """Upsert 过敏原分组及原料映射（幂等，支持补齐）。

    供管理页「快速导入过敏原」按钮调用。与 ``ensure_allergen_groups``（启动时
    空表才建的保守语义）互补——本函数主动补齐缺失/复活软删：
    - 分组按 name 查含软删（避免撞 name unique）：不存在则建；存在且软删则复活
      （**不改 display_order**，尊重管理员排序调整）。
    - 原料映射按 (group_id, ingredient_id) 查含软删：软删则复活，不存在才建。
    返回 ``{created, reactivated, mapped, not_found}``。
    """
    # name → id 查找表（含别名），复用 _create_groups 的构建方式
    all_ings = db.query(Ingredient).filter(Ingredient.is_active == True).all()
    name_to_id = {}
    for ing in all_ings:
        name_to_id.setdefault(ing.name, ing.id)
        if ing.aliases:
            for alias in (ing.aliases if isinstance(ing.aliases, list) else []):
                if alias and alias not in name_to_id:
                    name_to_id[alias] = ing.id

    created = 0
    reactivated = 0
    mapped = 0
    not_found = []

    for group_data in ALLERGEN_GROUPS:
        group_name = group_data["name"]
        group = db.query(BlacklistGroup).filter(BlacklistGroup.name == group_name).first()
        if not group:
            group = BlacklistGroup(
                name=group_name,
                display_order=group_data["display_order"],
                is_active=True,
            )
            db.add(group)
            db.flush()
            created += 1
        elif not group.is_active:
            # 软删分组复活（不改 display_order，尊重管理员排序调整）
            group.is_active = True
            reactivated += 1

        # 原料映射：name 匹配 → (group, ingredient) 查含软删 → 复活 or 新建
        found_ids = []
        for ing_name in group_data.get("ingredient_names", []):
            ing_id = name_to_id.get(ing_name)
            if ing_id:
                found_ids.append(ing_id)
            else:
                not_found.append(f"[{group_name}] 未找到: {ing_name}")
        for ing_id in set(found_ids):
            existing = db.query(BlacklistGroupIngredient).filter(
                BlacklistGroupIngredient.group_id == group.id,
                BlacklistGroupIngredient.ingredient_id == ing_id,
            ).first()
            if existing:
                if not existing.is_active:
                    existing.is_active = True
                    mapped += 1
            else:
                db.add(BlacklistGroupIngredient(
                    group_id=group.id,
                    ingredient_id=ing_id,
                    is_ai_matched=False,
                    is_active=True,
                ))
                mapped += 1

    db.commit()
    logger.info(
        "过敏原分组 upsert 完成：新建 %s 组，复活 %s 组，映射 %s 条，未匹配 %s 条",
        created, reactivated, mapped, len(not_found),
    )
    return {"created": created, "reactivated": reactivated, "mapped": mapped, "not_found": not_found}


def need_allergen_seed(db: Session) -> dict:
    """判断是否需要导入过敏原分组（供管理页按钮显隐）。

    以 ``is_active=True`` 的标准分组为准（软删算缺失）；任一缺失或映射数为 0
    → ``needed=True``。返回
    ``{needed, total, existing, with_mappings, missing_groups, empty_groups}``。
    """
    standard_names = [g["name"] for g in ALLERGEN_GROUPS]
    standard_set = set(standard_names)

    active_groups = db.query(BlacklistGroup).filter(
        BlacklistGroup.name.in_(standard_names),
        BlacklistGroup.is_active == True,
    ).all()
    active_names = {g.name for g in active_groups}
    missing_groups = sorted(standard_set - active_names)

    empty_groups = []
    with_mappings = 0
    for g in active_groups:
        cnt = db.query(BlacklistGroupIngredient).filter(
            BlacklistGroupIngredient.group_id == g.id,
            BlacklistGroupIngredient.is_active == True,
        ).count()
        if cnt == 0:
            empty_groups.append(g.name)
        else:
            with_mappings += 1

    return {
        "needed": bool(missing_groups) or bool(empty_groups),
        "total": len(ALLERGEN_GROUPS),
        "existing": len(active_groups),
        "with_mappings": with_mappings,
        "missing_groups": missing_groups,
        "empty_groups": sorted(empty_groups),
    }
