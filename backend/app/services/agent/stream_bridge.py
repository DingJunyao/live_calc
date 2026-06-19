"""stream_bridge - 会话级事件广播桥。

后台线程（session_runner）通过 ``publish_sync`` 发布事件，SSE 端点（Task 5）
通过 ``subscribe`` 订阅。跨线程安全。

设计要点：
- 模块级 ``_subscribers: dict[session_id, set[asyncio.Queue]]``。
- ``subscribe`` / ``unsubscribe`` 在事件循环协程里调用（async），用
  ``threading.Lock`` 保护字典访问（而非 ``asyncio.Lock``——后者在 sync 的
  ``publish_sync`` 中无法使用）。
- ``publish_sync`` 从后台线程调用，通过 ``loop.call_soon_threadsafe(
  q.put_nowait, event)`` 跨线程把事件塞进订阅者 queue。
- queue 满时直接丢弃（``QueueFull``）。SSE 靠历史重放兜底，慢订阅者丢增量
  而非阻塞发布者。
- 事件 dict 字段与 ``AgentEvent`` 对应，全部 JSON 可序列化。

Task 5 SSE 端点约束（重要）：
- 订阅端必须在 ``finally`` 中调用 ``unsubscribe``，否则事件循环关闭后订阅者
  queue 不会被回收，造成内存泄漏（模块级 ``_subscribers`` 字典里残留死 queue）。
- ``done`` / ``error`` 等终态事件可能因订阅者 queue 满（``QueueFull``）被静默
  丢弃。单靠实时流不足以让客户端稳定感知会话结束——Task 5 SSE 端点需采用
  「轮询 ``session.status`` 兜底发 synthesized done」（方案 B），确保客户端
  即便错过实时终态事件也能正确收尾。
"""
from __future__ import annotations

import asyncio
import logging
import threading
from collections import defaultdict
from typing import Any

logger = logging.getLogger("app.agent.stream_bridge")

__all__ = [
    "subscribe",
    "unsubscribe",
    "publish_sync",
    "publish_history_done",
    "MAX_QUEUE_SIZE",
    "_subscribers",
]

# 单个订阅者 queue 的最大容量。超过则 publish 时丢弃新事件。
MAX_QUEUE_SIZE = 512

# session_id -> 订阅者 queue 集合。
_subscribers: "dict[int, set[asyncio.Queue[Any]]]" = defaultdict(set)

# 保护 _subscribers 的读写。threading.Lock 在 async 与 sync 上下文均可用，
# 且 publish_sync 从后台线程调用（必须用 threading.Lock 而非 asyncio.Lock）。
_lock = threading.Lock()


async def subscribe(session_id: int) -> "asyncio.Queue[Any]":
    """订阅指定会话的实时事件流。

    Returns:
        asyncio.Queue: 订阅者 queue，SSE 协程从中 await get() 取事件。
    """
    q: "asyncio.Queue[Any]" = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
    with _lock:
        _subscribers[session_id].add(q)
    return q


async def unsubscribe(session_id: int, q: "asyncio.Queue[Any]") -> None:
    """取消订阅。幂等：未订阅也安全。"""
    with _lock:
        subs = _subscribers.get(session_id)
        if subs is None:
            return
        subs.discard(q)
        if not subs:
            _subscribers.pop(session_id, None)


def publish_sync(
    session_id: int,
    event: dict,
    loop: asyncio.AbstractEventLoop,
) -> None:
    """从后台线程发布事件给指定会话的所有订阅者。

    用 ``loop.call_soon_threadsafe`` 跨线程调用 ``q.put_nowait``。
    queue 满（QueueFull）时丢弃该订阅者的这条事件，不阻塞发布者，也不影响
    其它订阅者。
    """
    with _lock:
        subs = list(_subscribers.get(session_id, ()))

    for q in subs:
        try:
            loop.call_soon_threadsafe(_safe_put, q, event)
        except RuntimeError:
            # loop 已关闭：放弃此订阅者。
            logger.debug("publish_sync: event loop closed, drop subscriber")


def _safe_put(q: "asyncio.Queue[Any]", event: dict) -> None:
    """在事件循环线程里执行：put_nowait，QueueFull 时静默丢弃。"""
    try:
        q.put_nowait(event)
    except asyncio.QueueFull:
        logger.debug(
            "stream_bridge: subscriber queue full (session dropped event)"
        )


def publish_history_done(session_id: int) -> None:
    """（可选）标记会话实时流结束。

    目前作为占位扩展点，供 SSE 端点在「历史回放完毕、转入实时」或
    「会话终态」时使用。4a 中无具体语义，保留接口稳定。
    """
    # 故意留空：4a 仅做骨架，具体策略由 Task 5 SSE 端点决定。
    return None
