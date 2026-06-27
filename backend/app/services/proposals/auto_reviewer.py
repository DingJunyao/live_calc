"""默认自动审核器：全部 escalate（等价 manual）。

具体判定逻辑（规则引擎/AI/库内比对）后续实现，本期只留接口。
"""
from app.services.proposals.base import AutoReviewResult


class DefaultAutoReviewer:
    """默认实现：所有提议都转人工审核。"""

    def review(self, db, proposal) -> AutoReviewResult:
        return AutoReviewResult(
            decision="escalate",
            reason="默认自动审核未配置，转人工审核"
        )
