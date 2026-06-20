# backend/tests/translate/test_translate_task_agent.py
"""Task 7：TranslateTask.run 引擎替换（translate_batch → run_agent_loop）集成测试。

用 ``FakeMultiTurnRunner``（参照 ``tests/agent/test_agent_loop.py``）注入含
````sql```` UPDATE usda_foods 的 text_delta 事件流，monkeypatch
``runner_factory.build_runner`` 返回该 FakeRunner，跑 ``TranslateTask.run``，断言：

- 库内对应 ``usda_foods.description_zh`` 被更新、``translate_status='done'``。
- 返回 ``{translated, total}`` 合理。
- 建 ``[后台]`` AgentSession + UsdaTask。
"""
from __future__ import annotations

from typing import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.agent_session import AgentSession
from app.models.usda import UsdaFood, UsdaTask
from app.services.agent.runner import AgentEvent
from app.services.translate.task import TranslateTask


# --------------------------------------------------------------------------- #
# FakeMultiTurnRunner：按 run 调用次数返回不同事件序列。
# --------------------------------------------------------------------------- #
class FakeMultiTurnRunner:
    """假 AgentRunner：每次 run() 按调用序号返回对应轮的事件列表。"""

    def __init__(self, turns: "list[list[AgentEvent]]"):
        self._turns = list(turns)
        self._call_count = 0
        self._last_sid: "str | None" = None

    @property
    def last_session_id(self) -> "str | None":
        return self._last_sid

    def run(
        self, prompt: str, *, resume_session_id: "str | None" = None
    ) -> "Iterator[AgentEvent]":
        self._call_count += 1
        idx = self._call_count - 1
        if idx >= len(self._turns):
            yield AgentEvent(kind="done")
            return
        self._last_sid = f"fake-sid-{self._call_count}"
        for ev in self._turns[idx]:
            yield ev


# --------------------------------------------------------------------------- #
# 内存库 fixture：monkeypatch app.core.database.SessionLocal，让 TranslateTask、
# run_agent_loop（独立 Session）、断言查询共享同一内存库。
# --------------------------------------------------------------------------- #
@pytest.fixture()
def mem_db(monkeypatch):
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    TestSession = sessionmaker(bind=eng, autoflush=False, autocommit=False)

    import app.core.database as dbmod

    monkeypatch.setattr(dbmod, "SessionLocal", TestSession)
    yield TestSession
    eng.dispose()


@pytest.fixture()
def seed_foods(mem_db):
    """塞 3 条 usda_foods：2 pending + 1 done。"""
    db = mem_db()
    try:
        db.add_all(
            [
                UsdaFood(
                    fdc_id=1,
                    data_type="foundation",
                    description="Apple, raw",
                    translate_status="pending",
                ),
                UsdaFood(
                    fdc_id=2,
                    data_type="foundation",
                    description="Beef, raw",
                    translate_status="pending",
                ),
                UsdaFood(
                    fdc_id=3,
                    data_type="foundation",
                    description="Chicken, raw",
                    translate_status="done",
                ),
            ]
        )
        db.commit()
    finally:
        db.close()
    return mem_db


@pytest.fixture()
def patch_runner_factory(monkeypatch):
    """monkeypatch runner_factory.build_runner 返回 FakeMultiTurnRunner。

    返回一个闭包，测试可塞入预设 turns。
    """
    from app.services.agent import runner_factory

    holder: "dict[str, FakeMultiTurnRunner]" = {}

    def _fake_build_runner(task_type, db_url, **kwargs):
        assert task_type == "usda_translate"
        runner = holder["runner"]
        return runner

    monkeypatch.setattr(runner_factory, "build_runner", _fake_build_runner)
    return holder


# --------------------------------------------------------------------------- #
# 测试
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_translate_task_run_via_agent_loop(seed_foods, patch_runner_factory):
    """TranslateTask.run 走 run_agent_loop：Agent 输出 UPDATE → 自动执行 →
    description_zh 写回 + translate_status=done，建 [后台] AgentSession + UsdaTask。

    第 1 轮：Agent 拉取 pending → 输出 UPDATE usda_foods ... SET description_zh=...,
    translate_status='done' WHERE fdc_id IN (1,2) AND translate_status='pending'。
    第 2 轮：Agent 复核后无 SQL → 完成。
    """
    # 预设 FakeRunner：第 1 轮产 safe UPDATE，第 2 轮无 SQL 完成。
    turn1 = [
        AgentEvent(
            kind="text_delta",
            text=(
                "翻译完毕：\n"
                "```sql\n"
                "UPDATE usda_foods SET description_zh = CASE "
                "WHEN fdc_id = 1 THEN '苹果（生）' "
                "WHEN fdc_id = 2 THEN '牛肉（生）' END, "
                "translate_status = 'done' "
                "WHERE fdc_id IN (1, 2) AND translate_status = 'pending';\n"
                "```\n"
            ),
        ),
        AgentEvent(kind="done", cost_usd=0.02),
    ]
    turn2 = [
        AgentEvent(kind="text_delta", text="已复核，全部翻译完毕。"),
        AgentEvent(kind="done", cost_usd=0.01),
    ]
    fake_runner = FakeMultiTurnRunner([turn1, turn2])
    patch_runner_factory["runner"] = fake_runner

    config_dict = {
        "ai": {
            "providers": {
                "openai": {
                    "enabled": True,
                    "base_url": "x",
                    "api_key": "y",
                    "model": "z",
                }
            }
        }
    }

    db = seed_foods()
    try:
        result = await TranslateTask(db).run(provider="openai", config_dict=config_dict)
    finally:
        db.close()

    # 返回 {translated, total} 合理：2 pending 被翻译，总共 2 条 pending。
    assert result["total"] == 2
    assert result["translated"] == 2

    # 库内 description_zh 被更新、translate_status=done。
    db = seed_foods()
    try:
        f1 = db.query(UsdaFood).filter(UsdaFood.fdc_id == 1).one()
        f2 = db.query(UsdaFood).filter(UsdaFood.fdc_id == 2).one()
        f3 = db.query(UsdaFood).filter(UsdaFood.fdc_id == 3).one()
        assert f1.description_zh == "苹果（生）"
        assert f1.translate_status == "done"
        assert f2.description_zh == "牛肉（生）"
        assert f2.translate_status == "done"
        # 原 done 行未被改动。
        assert f3.translate_status == "done"
        assert f3.description_zh is None

        # 建 [后台] AgentSession。
        sessions = db.query(AgentSession).order_by(AgentSession.id.desc()).all()
        assert len(sessions) >= 1
        bg = sessions[0]
        assert bg.task_type == "usda_translate"
        assert bg.runner_type == "openai"
        assert bg.title is not None and bg.title.startswith("[后台]")
        assert bg.status == "success"

        # 建 UsdaTask（USDA 维护页进度载体）。
        tasks = db.query(UsdaTask).filter(UsdaTask.task_type == "translate").all()
        assert len(tasks) >= 1
        assert tasks[0].provider == "openai"
        assert tasks[0].status == "success"
    finally:
        db.close()
