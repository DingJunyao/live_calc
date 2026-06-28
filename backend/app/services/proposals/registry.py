"""执行器注册表 + 按 entity_type/action 的审核策略配置。"""
from typing import Dict, List, Optional, Tuple
from app.services.proposals.base import ProposalExecutor

# 持久化键前缀：proposal_policy:{entity_type}:{action}
_POLICY_KEY_PREFIX = "proposal_policy:"
# 合法策略与风险等级
_VALID_POLICIES = ("auto_approve", "auto_review", "manual")
_VALID_RISKS = ("low", "mid", "high")
# 注册时枚举的全部 action（与 register() 保持一致）
_KNOWN_ACTIONS = ("create", "update", "delete", "merge", "publish")


class ExecutorRegistry:
    """全局执行器与策略注册表（类变量持有，进程级）。"""

    _executors: Dict[str, ProposalExecutor] = {}
    _policies: Dict[Tuple[str, str], str] = {}   # (entity_type, action) -> policy
    _risk_levels: Dict[Tuple[str, str], str] = {}
    _defaults: Dict[str, str] = {}   # entity_type -> 注册时的 default_policy（用于 is_default 判定）

    @classmethod
    def register(cls, executor: ProposalExecutor, default_policy: str = "manual",
                 default_risk: str = "mid") -> ProposalExecutor:
        if not executor.entity_type:
            raise ValueError("执行器必须声明 entity_type")
        cls._executors[executor.entity_type] = executor
        cls._defaults[executor.entity_type] = default_policy
        # 注册时不覆盖已设置的 policy（允许后续 set_policy 定制）
        for action in ("create", "update", "delete", "merge", "publish"):
            cls._policies.setdefault((executor.entity_type, action), default_policy)
            cls._risk_levels.setdefault((executor.entity_type, action), default_risk)
        return executor

    @classmethod
    def get(cls, entity_type: str) -> Optional[ProposalExecutor]:
        return cls._executors.get(entity_type)

    @classmethod
    def policy_for(cls, entity_type: str, action: str) -> str:
        return cls._policies.get((entity_type, action), "manual")

    @classmethod
    def risk_for(cls, entity_type: str, action: str) -> str:
        return cls._risk_levels.get((entity_type, action), "mid")

    @classmethod
    def set_policy(cls, entity_type: str, action: str, policy: str) -> None:
        if policy not in _VALID_POLICIES:
            raise ValueError(f"非法策略: {policy}")
        cls._policies[(entity_type, action)] = policy

    @classmethod
    def set_risk(cls, entity_type: str, action: str, risk: str) -> None:
        if risk not in _VALID_RISKS:
            raise ValueError(f"非法风险等级: {risk}")
        cls._risk_levels[(entity_type, action)] = risk

    # ---------------- 持久化（system_config） ----------------

    @staticmethod
    def _policy_key(entity_type: str, action: str) -> str:
        return f"{_POLICY_KEY_PREFIX}{entity_type}:{action}"

    @classmethod
    def list_all_policies(cls) -> List[dict]:
        """返回所有已注册的 (entity_type, action) 策略 + 风险，供配置 API 读取。"""
        result: List[dict] = []
        # 以 _risk_levels 为准（register 时它与 _policies 同步初始化）
        for (entity_type, action), risk in cls._risk_levels.items():
            policy = cls._policies.get((entity_type, action), "manual")
            default = cls._defaults.get(entity_type, "manual")
            result.append({
                "entity_type": entity_type,
                "action": action,
                "policy": policy,
                "risk_level": risk,
                "is_default": policy == default,
            })
        return result

    @classmethod
    def load_persisted_policies(cls, db) -> int:
        """从 system_config 读取已持久化的策略覆盖当前 registry。

        返回被覆盖的条目数。仅在 register_all() 之后调用。
        """
        from app.models.system_config import SystemConfig  # 局部导入避免循环
        rows = db.query(SystemConfig).filter(
            SystemConfig.key.like(f"{_POLICY_KEY_PREFIX}%")
        ).all()
        n = 0
        for row in rows:
            # key 形如 proposal_policy:ingredient:update
            body = row.key[len(_POLICY_KEY_PREFIX):]
            if ":" not in body:
                continue
            entity_type, action = body.split(":", 1)
            if action not in _KNOWN_ACTIONS:
                continue
            if row.value not in _VALID_POLICIES:
                continue
            cls._policies[(entity_type, action)] = row.value
            n += 1
        return n

    @classmethod
    def persist_policy(cls, db, entity_type: str, action: str, policy: str) -> None:
        """写 system_config 持久化一条策略（upsert）。不 commit，调用方负责。"""
        if policy not in _VALID_POLICIES:
            raise ValueError(f"非法策略: {policy}")
        from app.models.system_config import SystemConfig
        key = cls._policy_key(entity_type, action)
        row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if row:
            row.value = policy
        else:
            db.add(SystemConfig(key=key, value=policy))
        cls._policies[(entity_type, action)] = policy

    @classmethod
    def reset(cls) -> None:
        """测试用：清空注册表。"""
        cls._executors.clear()
        cls._policies.clear()
        cls._risk_levels.clear()
        cls._defaults.clear()
