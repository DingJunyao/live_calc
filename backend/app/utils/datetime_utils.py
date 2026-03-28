"""
时区处理工具

统一的时区处理方案：
- 数据库统一存储UTC时间（naive datetime）
- 序列化时标记为UTC时区
- 前端自动转换为用户本地时区显示
"""
from datetime import datetime, timezone
from typing import Union, Any
from pydantic import BaseModel
from pydantic.functional_serializers import field_serializer


def serialize_datetime(dt: Union[datetime, None]) -> Union[str, None]:
    """
    序列化 datetime 对象为 ISO 8601 格式字符串，包含时区信息

    规则：
    - 如果 datetime 对象没有时区信息，假设为 UTC 时间
    - 如果 datetime 对象已有 timezone，直接使用
    - 返回格式：2026-03-28T10:30:00+00:00

    Args:
        dt: datetime 对象，可能为 None

    Returns:
        ISO 8601 格式字符串，或 None（如果输入为 None）

    Examples:
        >>> serialize_datetime(datetime(2026, 3, 28, 10, 30))
        '2026-03-28T10:30:00+00:00'

        >>> serialize_datetime(None)
        None
    """
    if dt is None:
        return None

    if dt.tzinfo is None:
        # 数据库存储的 naive datetime 视为 UTC 时间
        dt = dt.replace(tzinfo=timezone.utc)

    # 返回 ISO 8601 格式字符串，包含时区信息
    return dt.isoformat()


def parse_datetime(dt_str: Union[str, None]) -> Union[datetime, None]:
    """
    解析 ISO 8601 格式字符串为 datetime 对象

    Args:
        dt_str: ISO 8601 格式字符串，可能为 None

    Returns:
        datetime 对象（可能带时区信息），或 None（如果输入为 None）

    Examples:
        >>> parse_datetime('2026-03-28T10:30:00+00:00')
        datetime.datetime(2026, 3, 28, 10, 30, tzinfo=datetime.timezone.utc)

        >>> parse_datetime(None)
        None
    """
    if dt_str is None:
        return None

    return datetime.fromisoformat(dt_str)


class TimeZoneAwareModel(BaseModel):
    """
    自动处理datetime字段的时区序列化的基类

    所有包含datetime字段的Response Schema都应该继承此类

    示例：
        class MerchantResponse(TimeZoneAwareModel):
            id: int
            name: str
            created_at: datetime
    """

    @field_serializer('*')
    def serialize_datetime_fields(self, value: Any, _info) -> Any:
        """
        自动序列化所有datetime字段

        如果字段是datetime类型，转换为带时区的ISO 8601格式
        """
        if isinstance(value, datetime):
            return serialize_datetime(value)
        return value
