"""stream_bridge 单测：subscribe / unsubscribe / publish_sync 跨线程广播。"""
from __future__ import annotations

import asyncio

import pytest

from app.services.agent import stream_bridge


@pytest.fixture(autouse=True)
def _clear_subscribers():
    """每个测试前后清空模块级订阅者字典，避免互相污染。"""
    with stream_bridge._lock:
        stream_bridge._subscribers.clear()
    yield
    with stream_bridge._lock:
        stream_bridge._subscribers.clear()


def _drain(q: asyncio.Queue, timeout: float = 0.5):
    """非阻塞取出 queue 中所有现存事件。"""
    out = []
    while True:
        try:
            out.append(q.get_nowait())
        except asyncio.QueueEmpty:
            break
    return out


def test_subscribe_and_publish_sync_single():
    async def scenario():
        sid = 1
        q = await stream_bridge.subscribe(sid)
        loop = asyncio.get_event_loop()
        # 从「另一个线程」模拟——这里直接 sync 调（call_soon_threadsafe 在同
        # 线程也工作）。
        stream_bridge.publish_sync(
            sid, {"kind": "text_delta", "text": "hi"}, loop
        )
        # 让 call_soon_threadsafe 调度执行。
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert q.qsize() == 1
        ev = await asyncio.wait_for(q.get(), timeout=0.5)
        assert ev == {"kind": "text_delta", "text": "hi"}

    asyncio.new_event_loop().run_until_complete(scenario())


def test_multiple_subscribers_all_receive():
    async def scenario():
        sid = 2
        q1 = await stream_bridge.subscribe(sid)
        q2 = await stream_bridge.subscribe(sid)
        loop = asyncio.get_event_loop()
        stream_bridge.publish_sync(sid, {"kind": "done"}, loop)
        await asyncio.sleep(0)
        e1 = await asyncio.wait_for(q1.get(), timeout=0.5)
        e2 = await asyncio.wait_for(q2.get(), timeout=0.5)
        assert e1 == {"kind": "done"}
        assert e2 == {"kind": "done"}

    asyncio.new_event_loop().run_until_complete(scenario())


def test_slow_subscriber_full_queue_does_not_block_publisher():
    """满 queue 时 publish 不阻塞、不抛，丢弃新事件。"""
    async def scenario():
        sid = 3
        # 临时把 MAX_QUEUE_SIZE 调小，构造一个 1 容量的 queue。
        import asyncio as _a
        q: asyncio.Queue = _a.Queue(maxsize=1)
        with stream_bridge._lock:
            stream_bridge._subscribers[sid].add(q)
        loop = asyncio.get_event_loop()
        # 灌满（1 条）。
        stream_bridge.publish_sync(sid, {"kind": "text_delta", "text": "a"}, loop)
        await asyncio.sleep(0)
        assert q.qsize() == 1
        # 第 2 条应被丢弃，不应抛 QueueFull，不应阻塞。
        stream_bridge.publish_sync(sid, {"kind": "text_delta", "text": "b"}, loop)
        await asyncio.sleep(0)
        # 仍是 1（被丢弃）。
        assert q.qsize() == 1

    asyncio.new_event_loop().run_until_complete(scenario())


def test_unsubscribe_stops_receiving():
    async def scenario():
        sid = 4
        q = await stream_bridge.subscribe(sid)
        await stream_bridge.unsubscribe(sid, q)
        loop = asyncio.get_event_loop()
        stream_bridge.publish_sync(sid, {"kind": "done"}, loop)
        await asyncio.sleep(0)
        assert q.qsize() == 0
        # 幂等：再次 unsubscribe 不报错。
        await stream_bridge.unsubscribe(sid, q)

    asyncio.new_event_loop().run_until_complete(scenario())


def test_unsubscribe_cleans_up_dict():
    async def scenario():
        sid = 5
        q = await stream_bridge.subscribe(sid)
        await stream_bridge.unsubscribe(sid, q)
        assert sid not in stream_bridge._subscribers

    asyncio.new_event_loop().run_until_complete(scenario())


def test_publish_to_no_subscribers_is_noop():
    loop = asyncio.new_event_loop()
    # 无订阅者：不应抛错。
    stream_bridge.publish_sync(999, {"kind": "done"}, loop)
