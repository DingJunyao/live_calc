"""执行器注册表 + 按 entity_type/action 的审核策略配置。"""
from typing import Dict, Optional, Tuple
from app.services.proposals.base import ProposalExecutor


class ExecutorRegistry:
    """全局执行器与策略注册表（类变量持有，进程级）。"""

    _executors: Dict[str, ProposalExecutor] = {}
    _policies: Dict[Tuple[str, str], str] = {}   # (entity_type, action) -> policy
    _risk_levels: Dict[Tuple[str, str], str] = {}

    @classmethod
    def register(cls, executor: ProposalExecutor, default_policy: str = "manual",
                 default_risk: str = "mid") -> ProposalExecutor:
        if not executor.entity_type:
            raise ValueError("执行器必须声明 entity_type")
        cls._executors[executor.entity_type] = executor
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
        if policy not in ("auto_approve", "auto_review", "manual"):
            raise ValueError(f"非法策略: {policy}")
        cls._policies[(entity_type, action)] = policy

    @classmethod
    def set_risk(cls, entity_type: str, action: str, risk: str) -> None:
        if risk not in ("low", "mid", "high"):
            raise ValueError(f"非法风险等级: {risk}")
        cls._risk_levels[(entity_type, action)] = risk

    @classmethod
    def reset(cls) -> None:
        """测试用：清空注册表。"""
        cls._executors.clear()
        cls._policies.clear()
        cls._risk_levels.clear()
