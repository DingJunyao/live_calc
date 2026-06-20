# backend/tests/translate/test_nutrient_task_agent.py
"""Task 8：TranslateNutrientsTask.run 引擎替换（translate_batch → run_agent_loop）。

用 ``FakeMultiTurnRunner``（参照 ``test_translate_task_agent.py``）注入含
````sql```` UPDATE usda_food_nutrients 的 text_delta 事件流，monkeypatch
``runner_factory.build_runner`` 返回该 FakeRunner，跑
``TranslateNutrientsTask.run``，断言：

- 库内对应 ``usda_food_nutrients.name_zh`` 被更新。
- 原 name_zh 非空的行不动（守卫 ``AND name_zh IS NULL``）。
- 建 ``[后台]`` AgentSession（task_type=unmapped_nutrient_translate）+
  UsdaTask（task_type=translate_nutrients）。
- 返回 ``{translated, total}`` 合理。
"""
from __future__ import annotations

from typing import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.agent_session import AgentSession
from app.models.usda import UsdaFoodNutrient, UsdaTask
from app.services.agent.runner import AgentEvent
from app.services.translate.nutrient_task import TranslateNutrientsTask


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
# 内存库 fixture：monkeypatch app.core.database.SessionLocal。
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
def seed_nutrients(mem_db):
    """塞 4 行 usda_food_nutrients：

    - 2 行 Energy（name_zh 空，待翻译）。
    - 1 行 Protein（name_zh 空，待翻译）。
    - 1 行 Calcium（name_zh 已有「钙」，不应被覆盖）。
    """
    db = mem_db()
    try:
        db.add_all(
            [
                UsdaFoodNutrient(
                    fdc_id=1,
                    name="Energy",
                    name_zh=None,
                    amount=100.0,
                    unit_name="kcal",
                ),
                UsdaFoodNutrient(
                    fdc_id=2,
                    name="Energy",
                    name_zh=None,
                    amount=200.0,
                    unit_name="kcal",
                ),
                UsdaFoodNutrient(
                    fdc_id=1, name="Protein", name_zh=None, amount=10.0, unit_name="g"
                ),
                UsdaFoodNutrient(
                    fdc_id=2,
                    name="Calcium",
                    name_zh="钙",
                    amount=50.0,
                    unit_name="mg",
                ),
            ]
        )
        db.commit()
    finally:
        db.close()
    return mem_db


@pytest.fixture()
def patch_runner_factory(monkeypatch):
    """monkeypatch runner_factory.build_runner 返回 FakeMultiTurnRunner。"""
    from app.services.agent import runner_factory

    holder: "dict[str, FakeMultiTurnRunner]" = {}

    def _fake_build_runner(task_type, db_url, **kwargs):
        assert task_type == "unmapped_nutrient_translate"
        runner = holder["runner"]
        return runner

    monkeypatch.setattr(runner_factory, "build_runner", _fake_build_runner)
    return holder


# --------------------------------------------------------------------------- #
# 测试
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_nutrient_task_run_via_agent_loop(seed_nutrients, patch_runner_factory):
    """TranslateNutrientsTask.run 走 run_agent_loop：

    Agent 输出 UPDATE usda_food_nutrients SET name_zh=... WHERE name=... AND
    name_zh IS NULL → 自动执行 → name_zh 写回；原 name_zh 非空行不动；
    建 [后台] AgentSession（unmapped_nutrient_translate）+ UsdaTask
    （translate_nutrients）。
    """
    # 第 1 轮：Agent 翻译 Energy/Protein，输出两条 UPDATE。
    turn1 = [
        AgentEvent(
            kind="text_delta",
            text=(
                "翻译完毕：\n"
                "```sql\n"
                "UPDATE usda_food_nutrients SET name_zh='能量' "
                "WHERE name='Energy' AND name_zh IS NULL;\n"
                "```\n"
                "```sql\n"
                "UPDATE usda_food_nutrients SET name_zh='蛋白质' "
                "WHERE name='Protein' AND name_zh IS NULL;\n"
                "```\n"
            ),
        ),
        AgentEvent(kind="done", cost_usd=0.02),
    ]
    # 第 2 轮：复核后无 SQL → 完成。
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

    db = seed_nutrients()
    try:
        result = await TranslateNutrientsTask(db).run(
            provider="openai", config_dict=config_dict
        )
    finally:
        db.close()

    # total = 2（Energy、Protein 两个 distinct name 待翻译）；translated = 2。
    assert result["total"] == 2
    assert result["translated"] == 2

    # 库内 name_zh 被更新；原非空行不动。
    db = seed_nutrients()
    try:
        energy_rows = (
            db.query(UsdaFoodNutrient).filter(UsdaFoodNutrient.name == "Energy").all()
        )
        assert len(energy_rows) == 2
        for r in energy_rows:
            assert r.name_zh == "能量"

        protein = (
            db.query(UsdaFoodNutrient).filter(UsdaFoodNutrient.name == "Protein").one()
        )
        assert protein.name_zh == "蛋白质"

        # 守卫：Calcium 原本 name_zh='钙' 不被覆盖。
        calcium = (
            db.query(UsdaFoodNutrient).filter(UsdaFoodNutrient.name == "Calcium").one()
        )
        assert calcium.name_zh == "钙"

        # 建 [后台] AgentSession（task_type=unmapped_nutrient_translate）。
        sessions = db.query(AgentSession).order_by(AgentSession.id.desc()).all()
        assert len(sessions) >= 1
        bg = sessions[0]
        assert bg.task_type == "unmapped_nutrient_translate"
        assert bg.runner_type == "openai"
        assert bg.title is not None and bg.title.startswith("[后台]")
        assert bg.status == "success"

        # 建 UsdaTask（task_type=translate_nutrients）。
        tasks = (
            db.query(UsdaTask).filter(UsdaTask.task_type == "translate_nutrients").all()
        )
        assert len(tasks) >= 1
        assert tasks[0].provider == "openai"
        assert tasks[0].status == "success"
    finally:
        db.close()
