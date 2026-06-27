"""执行器基类、apply 结果、自动审核协议。"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol


@dataclass
class ApplyResult:
    """执行器 apply 的返回：变更前快照 + 逆向操作 + 摘要。"""
    snapshot: dict
    revert_payload: dict
    summary: str = ""


class ProposalExecutor(ABC):
    """每种 entity_type 注册一个执行器。

    apply 是唯一执行核心：管理员直写与提议审核通过后都调它，差别只在「是否先审」。
    """
    entity_type: str = ""

    @abstractmethod
    def validate(self, db, proposal) -> None:
        """校验提议合法性（含待审互斥检查）。失败 raise HTTPException(400)。"""

    @abstractmethod
    def preview(self, db, proposal) -> dict:
        """返回影响预览（如合并会影响多少引用）。"""

    @abstractmethod
    def apply(self, db, proposal) -> ApplyResult:
        """事务内执行变更，返回快照与逆向操作。调用方负责 commit。"""

    @abstractmethod
    def revert(self, db, proposal) -> None:
        """用 proposal.snapshot 与 proposal.revert_payload 原路还原。调用方负责 commit。"""


class ProposalAutoReviewer(Protocol):
    """自动审核接口（预留）。本期默认实现全部 escalate。"""

    def review(self, db, proposal) -> "AutoReviewResult": ...


@dataclass
class AutoReviewResult:
    decision: str   # "approve" / "escalate" / "reject"
    reason: str = ""
