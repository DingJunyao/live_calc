"""
API 端点错误处理工具。

提供标准化的错误记录和响应构建辅助函数。
"""

import logging
import traceback
import sys
from fastapi import Request
from app.core.exceptions import AppException

logger = logging.getLogger("app.error")


def log_api_error(
    request: Request,
    exception: Exception,
    *,
    extra_info: str = "",
) -> None:
    """
    统一记录 API 错误的详细信息。

    打印：
    - 请求方法、URL、路径参数、查询参数
    - 请求体（如果有）
    - 错误类型、错误消息
    - 完整堆栈跟踪
    """
    lines = []
    lines.append("=" * 80)
    lines.append(f"API 错误: {request.method} {request.url.path}")

    # 查询参数
    if request.query_params:
        lines.append(f"查询参数: {dict(request.query_params)}")

    # 路径参数
    if hasattr(request, "path_params") and request.path_params:
        lines.append(f"路径参数: {request.path_params}")

    # 请求头（仅记录关键信息）
    headers = dict(request.headers)
    key_headers = {
        k: v
        for k, v in headers.items()
        if k.lower()
        in ("content-type", "authorization", "user-agent", "x-forwarded-for", "host")
    }
    if key_headers:
        lines.append(f"关键请求头: {key_headers}")

    # 客户端 IP
    client = request.client
    if client:
        lines.append(f"客户端: {client.host}:{client.port}")

    # 错误信息
    lines.append("-" * 40)
    lines.append(f"错误类型: {type(exception).__name__}")

    if isinstance(exception, AppException):
        lines.append(f"HTTP 状态码: {exception.status_code}")
        lines.append(f"错误详情: {exception.detail}")
    elif hasattr(exception, "status_code"):
        lines.append(f"HTTP 状态码: {exception.status_code}")
        lines.append(f"错误详情: {exception.detail if hasattr(exception, 'detail') else str(exception)}")
    else:
        lines.append(f"错误详情: {str(exception)}")

    if extra_info:
        lines.append(f"额外信息: {extra_info}")

    # 堆栈跟踪
    lines.append("-" * 40)
    lines.append("错误堆栈:")
    lines.append(traceback.format_exc())
    lines.append("=" * 80)

    # 输出到 logger
    error_msg = "\n".join(lines)
    logger.error(error_msg)


def extract_error_detail(exception: Exception) -> str:
    """
    从异常中提取用户可读的错误信息。

    优先级：
    1. AppException.detail
    2. HTTPException.detail
    3. str(exception)
    4. 通用错误消息
    """
    if isinstance(exception, AppException):
        return exception.detail
    if hasattr(exception, "detail"):
        return str(exception.detail)
    msg = str(exception)
    if msg and msg.strip():
        return msg
    return "服务器内部错误，请稍后重试"
