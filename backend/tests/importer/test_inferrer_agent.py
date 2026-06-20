# backend/tests/importer/test_inferrer_agent.py
"""Task 9 / Task 10：AIInferrer 引擎替换集成测试。

Task 9：``infer_fuzzy_quantities``（参照 Task 7
``tests/translate/test_translate_task_agent.py``）——用
``FakeMultiTurnRunner`` 注入含 ````sql```` UPDATE ingredients.piece_weight +
UPDATE recipe_ingredients.quantity_range 的 text_delta 事件流，monkeypatch
``runner_factory.build_runner`` 返回该 FakeRunner，跑 ``provider="openai"`` 的
``infer_fuzzy_quantities``，断言：

- ``ingredients.piece_weight`` 被写、``recipe_ingredients.quantity_range`` 被写。
- 建 ``[后台]`` AgentSession（task_type=infer_quantities）。
- progress_callback 接口保留（被调用不报错）。

Task 10：``infer_densities``——同 FakeRunner 模式，Agent 输出
````sql```` INSERT INTO entity_densities（density=1000 kg/m³，source='agent'），
断言 entity_densities 表写入、单位为 kg/m³（不 ×1000）。

回退路径（provider 非 openai/anthropic）走老 ai_caller 逐组逻辑——两条各测一条。
"""
from __future__ import annotations

from typing import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.agent_session import AgentSession
from app.models.entity_density import EntityDensity
from app.models.nutrition import Ingredient
from app.models.recipe import Recipe, RecipeIngredient
from app.models.unit import Unit
from app.services.agent.runner import AgentEvent
from app.services.importer.ai_inference.inferrer import AIInferrer


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
# 内存库 fixture
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
def seed_data(mem_db):
    """塞原料 / 单位 / 菜谱 / 菜谱原料（计数单位 + piece_weight 缺失 + 用量空）。"""
    db = mem_db()
    try:
        unit = Unit(
            name="个",
            abbreviation="个",
            unit_type="count",
            unit_system="count",
        )
        db.add(unit)
        db.commit()
        db.refresh(unit)

        ing = Ingredient(name="鸡蛋", is_active=True, piece_weight=None)
        db.add(ing)
        db.commit()
        db.refresh(ing)

        recipe = Recipe(name="番茄炒蛋", servings=2)
        db.add(recipe)
        db.commit()
        db.refresh(recipe)

        ri = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ing.id,
            unit_id=unit.id,
            quantity=None,
            quantity_range=None,
            ai_inferred=False,
        )
        db.add(ri)
        db.commit()
        db.refresh(ri)

        data = {
            "unit_id": unit.id,
            "ingredient_id": ing.id,
            "recipe_id": recipe.id,
            "ri_id": ri.id,
        }
    finally:
        db.close()
    return mem_db, data


@pytest.fixture()
def patch_runner_factory(monkeypatch):
    """monkeypatch runner_factory.build_runner 返回 FakeMultiTurnRunner。"""
    from app.services.agent import runner_factory

    holder: "dict[str, FakeMultiTurnRunner]" = {}

    def _fake_build_runner(task_type, db_url, **kwargs):
        assert task_type == "infer_quantities"
        return holder["runner"]

    monkeypatch.setattr(runner_factory, "build_runner", _fake_build_runner)
    return holder


# --------------------------------------------------------------------------- #
# 测试：Agent 路径
# --------------------------------------------------------------------------- #
def test_infer_fuzzy_quantities_via_agent(seed_data, patch_runner_factory, monkeypatch):
    """provider=openai → 走 LangChainRunner + run_agent_loop(unattended=True)。

    Agent 第 1 轮输出两条 UPDATE（ingredients.piece_weight +
    recipe_ingredients.quantity_range），safe 自动执行；第 2 轮无 SQL 完成。
    """
    TestSession, data = seed_data

    turn1 = [
        AgentEvent(
            kind="text_delta",
            text=(
                "推测完毕：\n"
                "```sql\n"
                "UPDATE ingredients SET piece_weight = 55, ai_inferred = 1 "
                f"WHERE id IN ({data['ingredient_id']}) "
                "AND (piece_weight IS NULL OR piece_weight = 100);\n"
                "```\n"
                "```sql\n"
                f"UPDATE recipe_ingredients SET quantity_range = "
                '\'{"min": 0, "max": 110}\', ai_inferred = 1 '
                f"WHERE id IN ({data['ri_id']}) "
                "AND quantity IS NULL;\n"
                "```\n"
            ),
        ),
        AgentEvent(kind="done", cost_usd=0.02),
    ]
    turn2 = [
        AgentEvent(kind="text_delta", text="已复核，全部处理完毕。"),
        AgentEvent(kind="done", cost_usd=0.01),
    ]
    patch_runner_factory["runner"] = FakeMultiTurnRunner([turn1, turn2])

    progress_log: "list[tuple]" = []

    def progress_callback(stage, current, total, message=""):
        progress_log.append((stage, current, total, message))

    db = TestSession()
    try:
        inferrer = AIInferrer(db, provider="openai")
        result = inferrer.infer_fuzzy_quantities(
            force=False, progress_callback=progress_callback
        )
    finally:
        db.close()

    # ingredients.piece_weight 被写、ai_inferred=True。
    db = TestSession()
    try:
        ing = db.query(Ingredient).get(data["ingredient_id"])
        assert float(ing.piece_weight) == 55.0
        assert ing.ai_inferred is True

        ri = db.query(RecipeIngredient).get(data["ri_id"])
        assert ri.quantity_range is not None
        assert ri.quantity_range.get("max") == 110
        assert ri.ai_inferred is True

        # 建 [后台] AgentSession。
        sessions = db.query(AgentSession).order_by(AgentSession.id.desc()).all()
        assert len(sessions) >= 1
        bg = sessions[0]
        assert bg.task_type == "infer_quantities"
        assert bg.runner_type == "openai"
        assert bg.title is not None and bg.title.startswith("[后台]")
        assert bg.status == "success"
    finally:
        db.close()

    # progress_callback 接口保留（至少被调用一次：开始/结束）。
    assert len(progress_log) >= 1
    # result.stats 至少含 fuzzy_quantities 键。
    assert "fuzzy_quantities" in result.stats


# --------------------------------------------------------------------------- #
# 测试：回退路径（provider 非 openai/anthropic + ai_caller 注入）
# --------------------------------------------------------------------------- #
def test_infer_fuzzy_quantities_fallback_to_ai_caller(seed_data):
    """provider=claude_code（非 openai/anthropic）→ 回退老逐组 ai_caller 逻辑。

    ai_caller 返回固定 JSON（piece_weight_g + default_quantity_g），断言
    老逻辑写回 piece_weight + quantity_range。
    """
    TestSession, data = seed_data

    def fake_ai_caller(prompt: str) -> str:
        return '{"piece_weight_g": 55, "default_quantity_g": 110}'

    db = TestSession()
    try:
        inferrer = AIInferrer(db, provider="claude_code")
        inferrer.set_ai_caller(fake_ai_caller)
        result = inferrer.infer_fuzzy_quantities(force=False)
    finally:
        db.close()

    db = TestSession()
    try:
        ing = db.query(Ingredient).get(data["ingredient_id"])
        assert float(ing.piece_weight) == 55.0
        assert ing.ai_inferred is True

        ri = db.query(RecipeIngredient).get(data["ri_id"])
        assert ri.quantity_range is not None
        assert ri.quantity_range.get("max") == 110
    finally:
        db.close()

    assert result.stats.get("fuzzy_quantities") == 1


# =========================================================================== #
# Task 10：infer_densities 引擎替换
# =========================================================================== #


@pytest.fixture()
def density_seed(mem_db):
    """塞两条无密度原料（鸡蛋 + 面粉）。"""
    db = mem_db()
    try:
        ings = [
            Ingredient(name="水", is_active=True),
            Ingredient(name="面粉", is_active=True),
        ]
        for ing in ings:
            db.add(ing)
        db.commit()
        for ing in ings:
            db.refresh(ing)
        data = {"water_id": ings[0].id, "flour_id": ings[1].id}
    finally:
        db.close()
    return mem_db, data


@pytest.fixture()
def patch_runner_factory_densities(monkeypatch):
    """monkeypatch runner_factory.build_runner 返回 densities FakeRunner。"""
    from app.services.agent import runner_factory

    holder: "dict[str, FakeMultiTurnRunner]" = {}

    def _fake_build_runner(task_type, db_url, **kwargs):
        assert task_type == "infer_densities"
        return holder["runner"]

    monkeypatch.setattr(runner_factory, "build_runner", _fake_build_runner)
    return holder


# --------------------------------------------------------------------------- #
# 测试：Agent 路径
# --------------------------------------------------------------------------- #
def test_infer_densities_via_agent(
    density_seed, patch_runner_factory_densities, monkeypatch
):
    """provider=openai → 走 LangChainRunner + run_agent_loop(unattended=True)。

    Agent 第 1 轮输出 INSERT entity_densities（水=1000、面粉=550 kg/m³，
    source='agent'），safe 自动执行；第 2 轮无 SQL 完成。
    单位验证：Agent 路径直接写 kg/m³（不 ×1000）。
    """
    TestSession, data = density_seed

    turn1 = [
        AgentEvent(
            kind="text_delta",
            text=(
                "推测完毕：\n"
                "```sql\n"
                "INSERT INTO entity_densities (entity_type, entity_id, density, "
                "temperature, `condition`, source, confidence, created_at, "
                "updated_at) "
                f"SELECT 'ingredient', id, 1000, 20.0, NULL, 'agent', 0.9, "
                "datetime('now'), datetime('now') "
                f"FROM ingredients WHERE id IN ({data['water_id']}) "
                "AND NOT EXISTS (SELECT 1 FROM entity_densities WHERE "
                "entity_type='ingredient' AND entity_id=ingredients.id AND "
                "`condition` IS NULL);\n"
                "```\n"
                "```sql\n"
                "INSERT INTO entity_densities (entity_type, entity_id, density, "
                "temperature, `condition`, source, confidence, created_at, "
                "updated_at) "
                f"SELECT 'ingredient', id, 550, 20.0, NULL, 'agent', 0.9, "
                "datetime('now'), datetime('now') "
                f"FROM ingredients WHERE id IN ({data['flour_id']}) "
                "AND NOT EXISTS (SELECT 1 FROM entity_densities WHERE "
                "entity_type='ingredient' AND entity_id=ingredients.id AND "
                "`condition` IS NULL);\n"
                "```\n"
            ),
        ),
        AgentEvent(kind="done", cost_usd=0.02),
    ]
    turn2 = [
        AgentEvent(kind="text_delta", text="已复核，全部处理完毕。"),
        AgentEvent(kind="done", cost_usd=0.01),
    ]
    patch_runner_factory_densities["runner"] = FakeMultiTurnRunner([turn1, turn2])

    progress_log: "list[tuple]" = []

    def progress_callback(stage, current, total, message=""):
        progress_log.append((stage, current, total, message))

    db = TestSession()
    try:
        inferrer = AIInferrer(db, provider="openai")
        result = inferrer.infer_densities(
            force=False, progress_callback=progress_callback
        )
    finally:
        db.close()

    db = TestSession()
    try:
        # entity_densities 两条记录写入、单位 kg/m³（水=1000 不 ×1000）。
        rows = (
            db.query(EntityDensity)
            .filter(EntityDensity.entity_type == "ingredient")
            .order_by(EntityDensity.entity_id)
            .all()
        )
        assert len(rows) == 2
        dens_by_id = {r.entity_id: float(r.density) for r in rows}
        # Agent 路径：直接写 kg/m³，1000 而非 1.0。
        assert dens_by_id[data["water_id"]] == 1000.0
        assert dens_by_id[data["flour_id"]] == 550.0
        # source 标记。
        for r in rows:
            assert r.source == "agent"
            assert float(r.confidence) == 0.9

        # 建 [后台] AgentSession。
        sessions = db.query(AgentSession).order_by(AgentSession.id.desc()).all()
        assert len(sessions) >= 1
        bg = sessions[0]
        assert bg.task_type == "infer_densities"
        assert bg.runner_type == "openai"
        assert bg.title is not None and bg.title.startswith("[后台]")
        assert bg.status == "success"
    finally:
        db.close()

    # progress_callback 被调用。
    assert len(progress_log) >= 1
    # result.stats 含 densities 键。
    assert "densities" in result.stats


# --------------------------------------------------------------------------- #
# 测试：回退路径（provider 非 openai/anthropic + ai_caller 注入）
# --------------------------------------------------------------------------- #
def test_infer_densities_fallback_to_ai_caller(density_seed):
    """provider=claude_code → 回退老 ai_caller 逻辑。

    ai_caller 返回 g/cm³ JSON（水=1.0、面粉=0.55），老逻辑 ×1000 写回 entity_densities。
    """
    TestSession, data = density_seed

    def fake_ai_caller(prompt: str) -> str:
        # legacy prompt: 请推测食材"<name>"的密度…（提取首个引号内食材名匹配）。
        name = prompt.split('"', 2)[1] if '"' in prompt else ""
        if "水" == name:
            return '{"density_g_per_cm3": 1.0}'
        return '{"density_g_per_cm3": 0.55}'

    db = TestSession()
    try:
        inferrer = AIInferrer(db, provider="claude_code")
        inferrer.set_ai_caller(fake_ai_caller)
        result = inferrer.infer_densities(force=False)
    finally:
        db.close()

    db = TestSession()
    try:
        rows = (
            db.query(EntityDensity)
            .filter(EntityDensity.entity_type == "ingredient")
            .order_by(EntityDensity.entity_id)
            .all()
        )
        assert len(rows) == 2
        dens_by_id = {r.entity_id: float(r.density) for r in rows}
        # legacy 路径：g/cm³ ×1000 = kg/m³。
        assert dens_by_id[data["water_id"]] == 1000.0
        assert dens_by_id[data["flour_id"]] == 550.0
        for r in rows:
            assert r.source == "ai_inferrer"
    finally:
        db.close()

    assert result.stats.get("densities") == 2
