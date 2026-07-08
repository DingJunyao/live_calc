"""API 公共依赖。"""
from typing import Optional

from fastapi import Header, HTTPException
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def get_timezone(x_timezone: Optional[str] = Header(None, alias="X-Timezone")) -> str:
    """校验请求头 X-Timezone 为合法 IANA 时区名。

    缺失或非法均返回 400（非 422）。前端拦截器统一注入，正常流程不会触发。
    """
    if not x_timezone:
        raise HTTPException(status_code=400, detail="缺少 X-Timezone 请求头")
    try:
        ZoneInfo(x_timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(status_code=400, detail=f"无效时区: {x_timezone}")
    return x_timezone
