"""
跨数据库兼容性工具函数

提供针对不同数据库类型的兼容性支持，特别是 JSON 类型的处理。
"""
import json
from typing import Union, List


def get_database_type() -> str:
    """获取当前数据库类型"""
    import os
    from app.core.config import settings

    # 从 DATABASE_URL 提取数据库类型
    db_url = settings.DATABASE_URL
    if db_url.startswith('sqlite://'):
        return 'sqlite'
    elif db_url.startswith('mysql://'):
        return 'mysql'
    elif db_url.startswith('postgresql://'):
        return 'postgresql'
    elif db_url.startswith('postgresql+postgis://'):
        return 'postgresql-postgis'
    else:
        return 'sqlite'  # 默认使用 SQLite


def serialize_tags(tags: Union[List[str], None]) -> Union[str, None]:
    """将标签列表序列化为 JSON 字符串"""
    if not tags:
        return None
    return json.dumps(tags, ensure_ascii=False)


def deserialize_tags(tags_json: Union[str, None]) -> List[str]:
    """将 JSON 字符串反序列化为标签列表"""
    if not tags_json:
        return []
    try:
        return json.loads(tags_json)
    except json.JSONDecodeError:
        return []


def deserialize_tags_sqlite(tags_json: Union[str, None]) -> List[str]:
    """
    SQLite 的 JSON 反序列化，处理中文字符

    SQLite 的 TEXT 字段返回字符串，需要处理编码问题
    """
    if not tags_json:
        return []

    try:
        return json.loads(tags_json)
    except json.JSONDecodeError:
        return []


def validate_tags(tags: List[str]) -> List[str]:
    """
    验证标签格式，过滤空标签，去除重复

    Args:
        tags: 原始标签列表

    Returns:
        验证后的标签列表
    """
    if not tags:
        return []

    # 过滤空标签
    filtered = [tag for tag in tags if tag and tag.strip()]

    # 去除重复（保留首次出现的）
    seen = set()
    result = []
    for tag in filtered:
        if tag not in seen:
            result.append(tag)
            seen.add(tag)

    return result
