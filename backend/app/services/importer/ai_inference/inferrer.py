"""AI 后处理：模糊量推测 + 密度推测。"""

import asyncio
import json
import logging
from typing import Callable, Optional

from sqlalchemy.orm import Session

from app.models.entity_density import EntityDensity
from app.models.nutrition import Ingredient
from app.models.recipe import RecipeIngredient
from app.services.importer.models import ImportResult

logger = logging.getLogger(__name__)

# LangChainRunner Agent 路径启用的 provider（其余回退老 ai_caller 逐组逻辑）。
_AGENT_PROVIDERS = ("openai", "anthropic")

# infer_quantities 对应的 task_template 键。
_INFER_QUANTITIES_TASK_TYPE = "infer_quantities"

# infer_densities 对应的 task_template 键。
_INFER_DENSITIES_TASK_TYPE = "infer_densities"


class AIInferrer:
    """用 AI 推测原料的模糊用量和密度。

    复用后端现有的 AI 配置，不直接发起 HTTP 请求。
    通过一个抽象的 _call_ai(prompt) 方法，让上层注入具体的 AI 调用实现。

    Args:
        db: SQLAlchemy Session（调用方负责生命周期）。
        ai_caller: 可选的同步 callable(prompt: str) -> str（老逐组逻辑用）。
            provider 为 openai/anthropic 时不使用（走 LangChainRunner Agent）。
        provider: AI 提供方名称（``"openai"`` / ``"anthropic"`` / ``"claude_code"``
            / 其它）。``"openai"`` / ``"anthropic"`` 时走 LangChainRunner +
            ``run_agent_loop(unattended=True)``；其余回退老 ai_caller 逐组逻辑
            （向后兼容，不破坏现有调用方）。
    """

    def __init__(self, db: Session, ai_caller=None, provider: Optional[str] = None,
                 main_loop: "Optional[asyncio.AbstractEventLoop]" = None):
        self.db = db
        self.ai_caller = ai_caller
        self.provider = provider
        # 主事件循环（SSE 协程的 loop）：Agent 路径 stream_bridge.publish_sync 靠它
        # call_soon_threadsafe 把事件推到订阅者 queue。None 时 fallback 新建占位 loop
        #（不推实时，仅供无 SSE 场景/测试）。
        self.main_loop = main_loop

    def set_ai_caller(self, caller):
        """注入 AI 调用函数。接收 prompt 字符串，返回响应文本。"""
        self.ai_caller = caller

    # ----------------------------------------------------------------
    # 模糊量推测
    # ----------------------------------------------------------------

    def infer_fuzzy_quantities(
        self,
        force: bool = False,
        progress_callback: Optional[Callable] = None,
    ) -> ImportResult:
        """推测菜谱原料的模糊量。

        扫描所有 RecipeIngredient，筛选出：
        1. 用量单位是计数单位（unit_system == 'count'）且原料没有 piece_weight
        2. 用量为 NULL 或 original_quantity 为"适量""少许"

        分流：
        - provider=openai/anthropic → ``LangChainRunner`` + ``run_agent_loop``：
          Agent 自主「摸底 → 估值 → 输出 ````sql```` UPDATE ingredients.piece_weight
          + UPDATE recipe_ingredients.quantity_range（带守卫）→ 复核」，safe SQL
          自动执行（unattended=True：dangerous 跳过）。
        - 其它 provider（含 claude_code / ai_caller 注入）→ 回退老逻辑：按
          (ingredient_id, unit_id) 分组去重，每组调 ai_caller 一次。
        """
        if self.provider in _AGENT_PROVIDERS:
            return self._infer_fuzzy_quantities_via_agent(
                force=force, progress_callback=progress_callback
            )
        return self._infer_fuzzy_quantities_legacy(
            force=force, progress_callback=progress_callback
        )

    def _infer_fuzzy_quantities_via_agent(
        self,
        force: bool = False,
        progress_callback: Optional[Callable] = None,
    ) -> ImportResult:
        """LangChainRunner Agent 路径（provider=openai/anthropic）。

        参照 Task 7 ``TranslateTask.run``：建 [后台] AgentSession + 渲染
        ``infer_quantities`` 模板 + build_runner + run_agent_loop(unattended=True)。
        多表写回（ingredients.piece_weight + recipe_ingredients.quantity_range）
        由 Agent 在 ````sql```` 块里输出，经 sql_guard safe 自动执行。

        同步非 async——调用方（``import_api._run_ai_inference``）在后台线程里
        同步阻塞调用；``run_agent_loop`` 也是同步，无需 ``asyncio.to_thread``。
        """
        result = ImportResult()

        # 开始回调（Agent 批量，无法逐条回调）。
        if progress_callback is not None:
            try:
                progress_callback("模糊量推测", 0, 0, "启动 Agent 推测...")
            except Exception:  # noqa: BLE001
                logger.exception("progress_callback 开始回调异常")

        # 摸底：写前计数，用于统计净增量。
        ing_before = (
            self.db.query(Ingredient)
            .filter(Ingredient.piece_weight.isnot(None))
            .count()
        )
        ri_before = (
            self.db.query(RecipeIngredient)
            .filter(RecipeIngredient.quantity_range.isnot(None))
            .count()
        )

        try:
            from app.config import settings
            from app.models.agent_session import AgentSession
            from app.services.agent import runner_factory, session_runner
            from app.services.agent.task_templates import get_template

            tpl = get_template(_INFER_QUANTITIES_TASK_TYPE)
            initial_prompt = tpl["prompt"]
            if force:
                initial_prompt = (
                    "# 强制重推\n"
                    "本次为强制重推所有模糊量条目（含已 ai_inferred 的）。"
                    "忽略已有 piece_weight/quantity_range，对所有命中条件的行重新"
                    "估值并输出 UPDATE。\n\n" + initial_prompt
                )

            # 建 [后台] AgentSession。
            sess = AgentSession(
                task_type=_INFER_QUANTITIES_TASK_TYPE,
                title=f"[后台] {tpl['title']}",
                status="pending",
                runner_type=self.provider,
                initial_prompt=initial_prompt,
                user_id=None,
            )
            self.db.add(sess)
            self.db.commit()
            self.db.refresh(sess)
            session_id = sess.id

            # 即时把 agent_session_id 回传给 ImportTask（任务进行中前端就能点击跳转任务台）。
            if progress_callback is not None:
                try:
                    progress_callback(
                        "已启动 Agent", 0, 0, "Agent 会话已建立", agent_session_id=session_id
                    )
                except Exception:  # noqa: BLE001
                    pass

            # main_loop：优先用调用方传入的主 loop（SSE 协程的 loop，publish_sync 才能
            # 把事件 call_soon_threadsafe 到订阅者 queue）；None 时 fallback 新建占位 loop
            #（不 run，不推实时，仅供无 SSE/测试）。owns_loop 标记是否自建（仅自建的 close）。
            main_loop = self.main_loop if self.main_loop is not None else asyncio.new_event_loop()
            owns_loop = self.main_loop is None
            db_url = settings.database_url

            try:
                runner = runner_factory.build_runner(
                    _INFER_QUANTITIES_TASK_TYPE, db_url, provider=self.provider
                )
                session_runner.run_agent_loop(
                    session_id,
                    runner,
                    initial_prompt,
                    main_loop,
                    db_session_factory=_session_local_factory(),
                    unattended=True,
                )
            except Exception:  # noqa: BLE001
                logger.exception(
                    "infer_fuzzy_quantities run_agent_loop 异常 session=%s",
                    session_id,
                )
                self._mark_session_failed(session_id)
            finally:
                if owns_loop:
                    try:
                        main_loop.close()
                    except Exception:  # noqa: BLE001
                        pass

            # 统计净增量（写前/写后差）。
            self.db.expire_all()
            ing_after = (
                self.db.query(Ingredient)
                .filter(Ingredient.piece_weight.isnot(None))
                .count()
            )
            ri_after = (
                self.db.query(RecipeIngredient)
                .filter(RecipeIngredient.quantity_range.isnot(None))
                .count()
            )
            inferred = max(ing_after - ing_before, 0) + max(ri_after - ri_before, 0)
            result.stats["fuzzy_quantities"] = inferred
            # 关联 [后台] AgentSession，供前端 ImportTask 点击跳转任务台对话。
            result.stats["agent_session_id"] = session_id
        finally:
            # 结束回调。
            if progress_callback is not None:
                try:
                    progress_callback(
                        "模糊量推测",
                        1,
                        1,
                        f"Agent 推测完成，净更新 {result.stats.get('fuzzy_quantities', 0)} 条",
                    )
                except Exception:  # noqa: BLE001
                    logger.exception("progress_callback 结束回调异常")

        return result

    @staticmethod
    def _mark_session_failed(session_id: int) -> None:
        """Agent 后台异常兜底：把 AgentSession 置 failed。"""
        from app.core.database import SessionLocal
        from app.models.agent_session import AgentSession

        db = SessionLocal()
        try:
            s = db.query(AgentSession).get(session_id)
            if s is not None and s.status not in ("success", "failed"):
                s.status = "failed"
                s.error = f"AI 推测任务后台启动失败 session={session_id}（见日志）"
                db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("兜底置 failed 失败 session=%s", session_id)
        finally:
            db.close()

    def _infer_fuzzy_quantities_legacy(
        self,
        force: bool = False,
        progress_callback: Optional[Callable] = None,
    ) -> ImportResult:
        """老 ai_caller 逐组路径（向后兼容）。"""
        result = ImportResult()

        candidates = self._find_fuzzy_candidates(force)
        if not candidates:
            result.warnings.append("没有需要推测的模糊量条目")
            return result

        # 按 (ingredient_id, unit_id) 分组
        groups = {}
        for ri in candidates:
            key = (ri.ingredient_id, ri.unit_id)
            if key not in groups:
                groups[key] = {
                    "ingredient": self.db.query(Ingredient).get(ri.ingredient_id),
                    "unit_id": ri.unit_id,
                    "recipe_ingredients": [],
                }
            groups[key]["recipe_ingredients"].append(ri)

        total_groups = len(groups)
        inferred = 0
        for idx, ((ing_id, unit_id), group) in enumerate(groups.items(), 1):
            ingredient = group["ingredient"]
            if not ingredient:
                continue

            if progress_callback:
                progress_callback("模糊量推测", idx, total_groups, ingredient.name)

            recipes = [
                ri.recipe.name
                for ri in group["recipe_ingredients"]
                if ri.recipe and ri.recipe.name
            ]
            context = "、".join(set(recipes)) if recipes else "未知菜谱"
            prompt = self._build_quantity_prompt(ingredient.name, unit_id, context)

            try:
                response_text = self.ai_caller(prompt) if self.ai_caller else None
                if not response_text:
                    continue

                parsed = json.loads(response_text)
                piece_weight = parsed.get("piece_weight_g")
                default_quantity = parsed.get("default_quantity_g")

                # 如果有 piece_weight，更新原料
                if piece_weight is not None and ingredient.piece_weight is None:
                    ingredient.piece_weight = piece_weight
                    ingredient.ai_inferred = True
                    self.db.flush()

                # 如果有 default_quantity，更新各菜谱条目的 quantity_range
                if default_quantity is not None:
                    for ri in group["recipe_ingredients"]:
                        if ri.quantity is None and not ri.quantity_range:
                            ri.quantity_range = {"min": 0, "max": default_quantity}
                            ri.ai_inferred = True
                        ri.ai_inferred = True
                        self.db.flush()
                else:
                    for ri in group["recipe_ingredients"]:
                        ri.ai_inferred = True
                        self.db.flush()

                inferred += 1

            except (json.JSONDecodeError, Exception) as e:
                result.errors.append(
                    f"推测失败 {ingredient.name}(id={ing_id}): {str(e)}"
                )

        self.db.commit()
        result.stats["fuzzy_quantities"] = inferred
        return result

    def _find_fuzzy_candidates(self, force: bool = False):
        """筛选需要推测模糊量的 RecipeIngredient 条目。"""
        query = self.db.query(RecipeIngredient).join(Ingredient)

        if not force:
            query = query.filter(RecipeIngredient.ai_inferred == False)

        candidates = query.all()

        result = []
        for ri in candidates:
            ingredient = ri.ingredient
            if not ingredient:
                continue

            need_infer = False

            # 场景 1：计数单位但没有 piece_weight
            if ri.unit_id and ingredient.piece_weight is None:
                if self._is_countable_unit(ri.unit_id):
                    need_infer = True

            # 场景 2：用量为空或模糊文本
            if ri.quantity is None and not ri.quantity_range:
                need_infer = True
            elif ri.original_quantity:
                text = ""
                if isinstance(ri.original_quantity, dict):
                    text = ri.original_quantity.get("text", "")
                elif isinstance(ri.original_quantity, str):
                    text = ri.original_quantity
                if text in ("适量", "少许", "少量"):
                    need_infer = True

            if need_infer:
                result.append(ri)

        return result

    def _is_countable_unit(self, unit_id: int) -> bool:
        """判断单位是否为计数单位（unit_system == 'count'）。"""
        from app.models.unit import Unit

        unit = self.db.query(Unit).get(unit_id)
        return unit is not None and unit.unit_system == "count"

    def _build_quantity_prompt(
        self, ingredient_name: str, unit_id: int, context: str
    ) -> str:
        """构建模糊量推测的 AI Prompt。"""
        unit_name = ""
        if unit_id:
            from app.models.unit import Unit

            unit = self.db.query(Unit).get(unit_id)
            unit_name = unit.name if unit else ""
        return (
            f"请推测以下食材在常见菜谱中的典型用量：\n"
            f"- 食材：{ingredient_name}\n"
            f"- 单位：{unit_name or '无'}\n"
            f"- 出现于菜谱：{context}\n\n"
            f"请推测每个\"{unit_name or '份'}\"相当于多少克（piece_weight_g），"
            f'以及如果该食材用量为"适量"时大约是多少克（default_quantity_g，若无则为 null）。\n'
            f'返回 JSON：{{"piece_weight_g": 数值或null, '
            f'"default_quantity_g": 数值或null}}'
        )

    # ----------------------------------------------------------------
    # 密度推测
    # ----------------------------------------------------------------

    def infer_densities(
        self, force: bool = False, progress_callback: Optional[Callable] = None
    ) -> ImportResult:
        """推测没有密度值的原料的密度，写入 entity_densities 表（kg/m³）。

        分流：
        - provider=openai/anthropic → ``LangChainRunner`` + ``run_agent_loop``：
          Agent 自主「摸底 → 按 kg/m³ 估值 → 输出 ````sql```` INSERT INTO
          entity_densities（WHERE NOT EXISTS 防重，source='agent'）→ 复核」，
          safe SQL 自动执行（unattended=True）。**单位直接 kg/m³，不 ×1000。**
        - 其它 provider（含 claude_code / ai_caller 注入）→ 回退老逻辑：
          逐个原料调 ai_caller，AI 返 g/cm³ 再 ×1000 写回。
        """
        if self.provider in _AGENT_PROVIDERS:
            return self._infer_densities_via_agent(
                force=force, progress_callback=progress_callback
            )
        return self._infer_densities_legacy(
            force=force, progress_callback=progress_callback
        )

    def _infer_densities_via_agent(
        self, force: bool = False, progress_callback: Optional[Callable] = None
    ) -> ImportResult:
        """LangChainRunner Agent 路径（provider=openai/anthropic）。

        参照 ``_infer_fuzzy_quantities_via_agent`` 骨架，差异点：
        - 模板：``infer_densities``；
        - 写回表：``entity_densities``（INSERT，非 UPDATE）；
        - 单位：Agent 输出 SQL 直接是 kg/m³（不 ×1000）；
        - 统计：``entity_densities`` 行数净增量（Agent 只 INSERT 不清空）。
        """
        result = ImportResult()

        # 开始回调。
        if progress_callback is not None:
            try:
                progress_callback("密度推测", 0, 0, "启动 Agent 推测...")
            except Exception:  # noqa: BLE001
                logger.exception("progress_callback 开始回调异常")

        # 写前计数，用于统计净增量。
        ed_before = (
            self.db.query(EntityDensity)
            .filter(EntityDensity.entity_type == "ingredient")
            .count()
        )

        try:
            from app.config import settings
            from app.models.agent_session import AgentSession
            from app.services.agent import runner_factory, session_runner
            from app.services.agent.task_templates import get_template

            tpl = get_template(_INFER_DENSITIES_TASK_TYPE)
            initial_prompt = tpl["prompt"]
            if force:
                initial_prompt = (
                    "# 强制重推\n"
                    "本次为强制重推所有密度条目（含已 source='agent' 的）。"
                    "忽略 entity_densities 已有记录，对所有缺密度的原料重新估值"
                    "并输出 INSERT（注意 WHERE NOT EXISTS 守卫在 force 下不会触发"
                    "重复 INSERT，故无需特别调整）。\n\n" + initial_prompt
                )

            sess = AgentSession(
                task_type=_INFER_DENSITIES_TASK_TYPE,
                title=f"[后台] {tpl['title']}",
                status="pending",
                runner_type=self.provider,
                initial_prompt=initial_prompt,
                user_id=None,
            )
            self.db.add(sess)
            self.db.commit()
            self.db.refresh(sess)
            session_id = sess.id

            # 即时把 agent_session_id 回传给 ImportTask（任务进行中前端就能点击跳转任务台）。
            if progress_callback is not None:
                try:
                    progress_callback(
                        "已启动 Agent", 0, 0, "Agent 会话已建立", agent_session_id=session_id
                    )
                except Exception:  # noqa: BLE001
                    pass

            # main_loop：优先用主 loop（SSE 实时）；None 时 fallback 占位 loop（不推实时）。
            main_loop = self.main_loop if self.main_loop is not None else asyncio.new_event_loop()
            owns_loop = self.main_loop is None
            db_url = settings.database_url

            try:
                runner = runner_factory.build_runner(
                    _INFER_DENSITIES_TASK_TYPE, db_url, provider=self.provider
                )
                session_runner.run_agent_loop(
                    session_id,
                    runner,
                    initial_prompt,
                    main_loop,
                    db_session_factory=_session_local_factory(),
                    unattended=True,
                )
            except Exception:  # noqa: BLE001
                logger.exception(
                    "infer_densities run_agent_loop 异常 session=%s",
                    session_id,
                )
                self._mark_session_failed(session_id)
            finally:
                if owns_loop:
                    try:
                        main_loop.close()
                    except Exception:  # noqa: BLE001
                        pass

            # 统计净增量。
            self.db.expire_all()
            ed_after = (
                self.db.query(EntityDensity)
                .filter(EntityDensity.entity_type == "ingredient")
                .count()
            )
            inferred = max(ed_after - ed_before, 0)
            result.stats["densities"] = inferred
            # 关联 [后台] AgentSession，供前端 ImportTask 点击跳转任务台对话。
            result.stats["agent_session_id"] = session_id
        finally:
            # 结束回调。
            if progress_callback is not None:
                try:
                    progress_callback(
                        "密度推测",
                        1,
                        1,
                        f"Agent 推测完成，净新增 {result.stats.get('densities', 0)} 条",
                    )
                except Exception:  # noqa: BLE001
                    logger.exception("progress_callback 结束回调异常")

        return result

    def _infer_densities_legacy(
        self, force: bool = False, progress_callback: Optional[Callable] = None
    ) -> ImportResult:
        """老 ai_caller 逐个路径（向后兼容）。AI 返 g/cm³，×1000 写回 kg/m³。"""
        result = ImportResult()

        # force=True 时不跳过已有密度原料，重推所有缺条件原料；
        # 这里沿用历史实现——筛「缺密度原料」（force 不影响候选筛选，agent
        # 路径才有 force 语义差异）。
        from sqlalchemy import not_

        existing_ids = (
            self.db.query(EntityDensity.entity_id)
            .filter(
                EntityDensity.entity_type == "ingredient",
                EntityDensity.condition.is_(None),
            )
            .subquery()
        )
        query = self.db.query(Ingredient).filter(
            Ingredient.is_active == True,
            not_(Ingredient.id.in_(existing_ids)),
        )

        candidates = query.all()
        if not candidates:
            result.warnings.append(
                "没有需要推测密度的原料（entity_densities 均已覆盖）"
            )
            return result

        total = len(candidates)
        inferred = 0
        for idx, ingredient in enumerate(candidates, 1):
            if progress_callback:
                progress_callback(
                    "密度推测", idx, total, f"{ingredient.name} ({idx}/{total})"
                )
            prompt = (
                f'请推测食材"{ingredient.name}"的密度（g/cm³），'
                f"即每毫升多少克。\n"
                f"常见参考：水=1.0，食用油≈0.92，蜂蜜≈1.4，面粉≈0.55。\n"
                f'返回 JSON：{{"density_g_per_cm3": 数值}}'
            )

            try:
                response_text = self.ai_caller(prompt) if self.ai_caller else None
                if not response_text:
                    continue

                parsed = json.loads(response_text)
                density = parsed.get("density_g_per_cm3")
                if density is not None:
                    # AI 返回 g/cm³，entity_densities 需 kg/m³（×1000）。
                    ed = EntityDensity(
                        entity_type="ingredient",
                        entity_id=ingredient.id,
                        density=round(density * 1000, 6),
                        temperature=20.0,
                        source="ai_inferrer",
                        confidence=0.8,
                    )
                    self.db.add(ed)
                    inferred += 1

            except Exception as e:  # noqa: BLE001
                result.errors.append(
                    f"密度推测失败 {ingredient.name}(id={ingredient.id}): {str(e)}"
                )

        self.db.commit()
        result.stats["densities"] = inferred
        return result


def _session_local_factory():
    """返回 run_agent_loop 的 db_session_factory（懒求值 SessionLocal）。

    封一层函数避免在模块加载期强绑定 ``app.core.database.SessionLocal``——
    便于测试 monkeypatch 替换内存库（monkeypatch 生效在 infer 调用时）。
    """
    from app.core.database import SessionLocal

    return SessionLocal
