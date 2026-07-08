"""
时区感知的日期范围工具

处理用户本地日期与 UTC 存储之间的转换。时区以 IANA 名表示（如 Asia/Shanghai）。
数据库存储 naive UTC datetime。
"""
from datetime import datetime, date, timezone
from typing import Tuple
from zoneinfo import ZoneInfo


def _zone(tz: str):
    """解析 IANA 时区名，空值回落 UTC。"""
    return ZoneInfo(tz if tz else "UTC")


def local_date_to_utc_range(local_date: date, tz: str = "UTC") -> Tuple[datetime, datetime]:
    """将用户本地日期转换为 UTC 时间范围（naive UTC，供 SQL 比较）。

    Args:
        local_date: 用户本地日期
        tz: IANA 时区名，默认 UTC

    Returns:
        (utc_start, utc_end) — 本地日 [00:00:00, 23:59:59.999999] 对应的 UTC 时刻

    Examples:
        >>> # 用户查询北京时间 2026-03-29 的数据
        >>> start, end = local_date_to_utc_range(date(2026, 3, 29), "Asia/Shanghai")
        >>> # 返回: (2026-03-28 16:00:00, 2026-03-29 15:59:59.999999)
    """
    zone = _zone(tz)
    local_start = datetime.combine(local_date, datetime.min.time(), tzinfo=zone)
    local_end = datetime.combine(local_date, datetime.max.time(), tzinfo=zone)
    utc_start = local_start.astimezone(timezone.utc).replace(tzinfo=None)
    utc_end = local_end.astimezone(timezone.utc).replace(tzinfo=None)
    return utc_start, utc_end


def local_date_range_to_utc_range(start_date: date, end_date: date, tz: str = "UTC") -> Tuple[datetime, datetime]:
    """将用户本地日期范围转换为 UTC 时间范围。

    Args:
        start_date: 开始日期（本地）
        end_date: 结束日期（本地）
        tz: IANA 时区名，默认 UTC

    Returns:
        (utc_start, utc_end) - UTC 时间范围的起止时间
    """
    _, end = local_date_to_utc_range(end_date, tz)
    start, _ = local_date_to_utc_range(start_date, tz)
    return start, end


def utc_datetime_to_local_date(utc_dt: datetime, tz: str = "UTC") -> date:
    """将 UTC datetime 转换为用户本地日期。naive datetime 视作 UTC。

    Args:
        utc_dt: UTC 时间（naive 视作 UTC）
        tz: IANA 时区名，默认 UTC

    Returns:
        本地日期

    Examples:
        >>> utc_datetime_to_local_date(datetime(2026, 3, 28, 17, 0, 0), "Asia/Shanghai")
        date(2026, 3, 29)  # 北京时间
    """
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(_zone(tz)).date()
