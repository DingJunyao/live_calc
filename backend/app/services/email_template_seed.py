"""邮件模板默认种子数据与服务。

``email_templates`` 表由 ``create_all`` 建表，但 3 条默认模板的数据原本只写在
alembic 迁移（``20260704_0001``）和手动 SQL 脚本里——本项目走 ``create_all``、
不跑 alembic，故默认模板从未被插入，导致 ``email_service.send_template_async``
查不到模板而静默跳过所有审核通知邮件。

本模块作为默认模板的**唯一数据源**，供 lifespan 启动时幂等补齐缺失模板。
"""
import logging

from sqlalchemy.orm import Session

from app.models.email_template import EmailTemplate

logger = logging.getLogger(__name__)


# ── 默认邮件模板（与 alembic 20260704_0001 的 INSERT 保持一致）──────
# body_html 使用 string.Template 语法（${var}），与 EmailService.send_template_async
# 的 safe_substitute 对齐。注意：这里不能用 f-string，否则 ${} 会被误解析。
EMAIL_TEMPLATES = [
    {
        "key": "proposal_submitted",
        "name": "新提议通知（管理员）",
        "subject": "[LiveCalc] 新提议 #${proposal_id}",
        "body_html": (
            "<h2>新变更提议</h2>"
            "<p>用户 <strong>${proposer_name}</strong> 提交了一条新的变更提议，需要审核。</p>"
            "<table>"
            "<tr><td>提议编号</td><td>#${proposal_id}</td></tr>"
            "<tr><td>实体类型</td><td>${entity_type_label}</td></tr>"
            "<tr><td>操作</td><td>${action_label}</td></tr>"
            "<tr><td>目标</td><td>${entity_label}</td></tr>"
            "</table>"
        ),
        "description": "用户提交变更提议时通知所有管理员",
    },
    {
        "key": "proposal_approved",
        "name": "提议通过通知（发起者）",
        "subject": "[LiveCalc] 提议 #${proposal_id} 已通过",
        "body_html": (
            "<h2>提议已通过</h2>"
            "<p>您的变更提议已通过审核并生效。</p>"
            "<table>"
            "<tr><td>提议编号</td><td>#${proposal_id}</td></tr>"
            "<tr><td>实体类型</td><td>${entity_type_label}</td></tr>"
            "<tr><td>操作</td><td>${action_label}</td></tr>"
            "<tr><td>目标</td><td>${entity_label}</td></tr>"
            "</table>"
        ),
        "description": "提议审核通过时通知发起者",
    },
    {
        "key": "proposal_rejected",
        "name": "提议驳回通知（发起者）",
        "subject": "[LiveCalc] 提议 #${proposal_id} 未通过",
        "body_html": (
            "<h2>提议未通过</h2>"
            "<p>您的变更提议未通过审核。</p>"
            "<table>"
            "<tr><td>提议编号</td><td>#${proposal_id}</td></tr>"
            "<tr><td>实体类型</td><td>${entity_type_label}</td></tr>"
            "<tr><td>操作</td><td>${action_label}</td></tr>"
            "<tr><td>目标</td><td>${entity_label}</td></tr>"
            "</table>"
            "<p>审核备注：${review_note}</p>"
        ),
        "description": "提议审核驳回时通知发起者",
    },
]


def _create_templates(db: Session) -> int:
    """补齐缺失的默认模板（按 key 判断，已存在的 key 一律不动）。

    返回新增条数。采用「按 key 逐个补齐」而非「count>0 跳过」——模板可能被
    管理员经 ``PUT /admin/email-config/templates/{key}`` 编辑过，按 key 补齐
    既能保护管理员修改、又能在中途失败后重启补齐缺失项。
    """
    existing_keys = {key for (key,) in db.query(EmailTemplate.key).all()}
    created = 0
    for tpl in EMAIL_TEMPLATES:
        if tpl["key"] in existing_keys:
            continue
        db.add(EmailTemplate(**tpl))
        created += 1
    if created:
        db.commit()
    return created


def ensure_email_templates(db: Session) -> None:
    """幂等确保默认邮件模板存在：仅补缺失项，不覆盖已存在模板。"""
    created = _create_templates(db)
    if created:
        logger.info("邮件模板初始化完成：新增 %d 条", created)
    else:
        logger.info("默认邮件模板均已存在，跳过初始化")
