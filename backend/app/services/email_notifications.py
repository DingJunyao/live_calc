"""邮件通知：提议提交/审核通过/驳回时发送邮件。

从 proposals.py 提取，消除直接调用 proposal_service.submit() 绕过通知的问题。
"""
import logging
from string import Template
from typing import Optional

logger = logging.getLogger(__name__)


# 与前端 entityTypeLabel / actionLabel 保持一致的翻译映射
_ENTITY_TYPE_LABELS: dict[str, str] = {
    "ingredient": "原料",
    "ingredient_merge": "原料合并",
    "ingredient_split": "原料拆分",
    "nutrition": "营养数据",
    "unit": "单位",
    "hierarchy": "食材层级关系",
    "merchant": "商家",
    "merchant_merge": "商家合并",
    "product_split": "商品拆分",
    "product_merge": "商品合并",
    "product": "商品",
    "recipe": "菜谱",
    "recipe_edit": "菜谱编辑",
    "entity_unit_override": "实体单位覆盖",
    "entity_density": "实体密度",
    "usda_ingredient_match": "USDA 原料匹配",
    "usda_product_match": "USDA 商品匹配",
    "product_nutrition": "商品营养",
}

_ACTION_LABELS: dict[str, str] = {
    "create": "创建",
    "update": "更新",
    "delete": "删除",
    "merge": "合并",
    "publish": "发布",
}


def _entity_label_for_email(db, proposal) -> str:
    """获取实体的可读标签用于邮件。"""
    from app.services.proposals.registry import ExecutorRegistry
    executor = ExecutorRegistry.get(proposal.entity_type)
    if executor is not None:
        try:
            label = executor.entity_label(db, proposal)
            if label:
                return label
        except Exception:
            pass
    return (f"{proposal.entity_type}#{proposal.entity_id}"
            if proposal.entity_id else proposal.entity_type)


def _build_variables(db, proposal, extra_vars: Optional[dict] = None) -> dict:
    """构造邮件模板变量。"""
    from app.models.user import User
    proposer = db.query(User).filter(User.id == proposal.proposer_id).first()
    variables = {
        "proposer_name": f"#{proposal.proposer_id}" if proposer is None else (proposer.username or f"#{proposal.proposer_id}"),
        "proposal_id": str(proposal.id),
        "entity_type_label": _ENTITY_TYPE_LABELS.get(proposal.entity_type, proposal.entity_type),
        "action_label": _ACTION_LABELS.get(proposal.action, proposal.action),
        "entity_label": _entity_label_for_email(db, proposal),
    }
    if extra_vars:
        variables.update(extra_vars)
    return variables


def _get_email_service(db):
    """按当前 SMTP 配置构造 EmailService。"""
    from app.models.smtp_config import SmtpConfig
    from app.services.email_service import EmailService
    config = db.query(SmtpConfig).first()
    return EmailService(config)


def notify_admins_on_submit(db, proposal) -> None:
    """有新的 manual 提议时通知所有管理员。在 submit 后调用。"""
    from app.models.user import User
    service = _get_email_service(db)
    if not service.ready:
        return
    admins = db.query(User).filter(User.is_admin.is_(True)).all()
    if not admins:
        return
    variables = _build_variables(db, proposal)
    for admin in admins:
        if admin.email:
            service.send_template_async("proposal_submitted", admin.email, variables, db)


def notify_proposer(db, proposal, template_key: str, extra_vars: Optional[dict] = None) -> None:
    """审核完成后通知提议发起者。在 review 后调用。"""
    from app.models.user import User
    service = _get_email_service(db)
    if not service.ready:
        return
    proposer = db.query(User).filter(User.id == proposal.proposer_id).first()
    if not proposer or not proposer.email:
        return
    variables = _build_variables(db, proposal, extra_vars)
    service.send_template_async(template_key, proposer.email, variables, db)
