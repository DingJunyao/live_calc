"""
时区感知的日期范围工具

处理用户本地日期与UTC存储之间的转换
"""
from datetime import datetime, date, timedelta, timezone
from typing import Tuple, Optional


def local_date_to_utc_range(
    local_date: date,
    user_timezone_offset: Optional[int] = None
) -> Tuple[datetime, datetime]:
    """
    将用户本地日期转换为UTC时间范围

    Args:
        local_date: 用户本地日期（如 2026-03-29）
        user_timezone_offset: 用户时区偏移（秒），东八区为 28800（8*3600）
                            如果为 None，默认使用东八区

    Returns:
        (utc_start, utc_end) - UTC时间范围的起止时间

    Examples:
        >>> # 用户查询北京时间 2026-03-29 的数据
        >>> start, end = local_date_to_utc_range(date(2026, 3, 29))
        >>> # 返回: (2026-03-28 16:00:00, 2026-03-29 15:59:59)
        >>> # 对应北京时间的 2026-03-29 00:00:00 到 23:59:59
    """
    if user_timezone_offset is None:
        # 默认东八区（北京时间）
        user_timezone_offset = 8 * 3600

    # 本地日期的开始时间（00:00:00）
    local_start = datetime.combine(local_date, datetime.min.time())
    # 本地日期的结束时间（23:59:59.999999）
    local_end = datetime.combine(local_date, datetime.max.time())

    # 转换为UTC时间
    utc_start = local_start.replace(tzinfo=timezone(timedelta(seconds=user_timezone_offset))).astimezone(timezone.utc).replace(tzinfo=None)
    utc_end = local_end.replace(tzinfo=timezone(timedelta(seconds=user_timezone_offset))).astimezone(timezone.utc).replace(tzinfo=None)

    return utc_start, utc_end


def local_date_range_to_utc_range(
    start_date: date,
    end_date: date,
    user_timezone_offset: Optional[int] = None
) -> Tuple[datetime, datetime]:
    """
    将用户本地日期范围转换为UTC时间范围

    Args:
        start_date: 开始日期（本地）
        end_date: 结束日期（本地）
        user_timezone_offset: 用户时区偏移（秒）

    Returns:
        (utc_start, utc_end) - UTC时间范围的起止时间

    Examples:
        >>> # 用户查询北京时间 2026-03-01 到 2026-03-31 的数据
        >>> start, end = local_date_range_to_utc_range(date(2026, 3, 1), date(2026, 3, 31))
        >>> # 返回: (2026-02-28 16:00:00, 2026-03-30 15:59:59)
    """
    if user_timezone_offset is None:
        user_timezone_offset = 8 * 3600

    # 开始日期的 00:00:00
    local_start = datetime.combine(start_date, datetime.min.time())
    # 结束日期的 23:59:59.999999
    local_end = datetime.combine(end_date, datetime.max.time())

    # 转换为UTC
    utc_start = local_start.replace(tzinfo=timezone(timedelta(seconds=user_timezone_offset))).astimezone(timezone.utc).replace(tzinfo=None)
    utc_end = local_end.replace(tzinfo=timezone(timedelta(seconds=user_timezone_offset))).astimezone(timezone.utc).replace(tzinfo=None)

    return utc_start, utc_end


def utc_datetime_to_local_date(utc_dt: datetime, user_timezone_offset: Optional[int] = None) -> date:
    """
    将UTC datetime转换为用户本地日期

    Args:
        utc_dt: UTC时间
        user_timezone_offset: 用户时区偏移（秒）

    Returns:
        本地日期

    Examples:
        >>> utc_datetime_to_local_date(datetime(2026, 3, 28, 17, 0))
        date(2026, 3, 29)  # 北京时间
    """
    if user_timezone_offset is None:
        user_timezone_offset = 8 * 3600

    # 添加时区信息并转换
    utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    local_dt = utc_dt.astimezone(timezone(timedelta(seconds=user_timezone_offset)))
    return local_dt.date()
