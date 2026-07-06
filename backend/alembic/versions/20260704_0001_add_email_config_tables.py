"""add smtp_config and email_templates tables

Revision ID: 20260704_0001
Revises: c0e1d2f3a4b5
Create Date: 2026-07-04

为 SMTP 发送配置（smtp_config）和邮件模板（email_templates）建表，
并插入 3 条默认模板（新提议通知/提议通过通知/提议驳回通知）。
"""
from alembic import op
import sqlalchemy as sa

revision = "20260704_0001"
down_revision = "c0e1d2f3a4b5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "smtp_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("host", sa.String(255), nullable=False, server_default=""),
        sa.Column("port", sa.Integer(), nullable=False, server_default="587"),
        sa.Column("username", sa.String(255), nullable=False, server_default=""),
        sa.Column("password", sa.String(255), nullable=False, server_default=""),
        sa.Column("use_tls", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("from_address", sa.String(255), nullable=False, server_default=""),
        sa.Column("from_name", sa.String(100), nullable=False, server_default="LiveCalc"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "email_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(50), unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("description", sa.String(500), server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Insert default templates
    op.execute(
        "INSERT INTO email_templates (key, name, subject, body_html, description) VALUES "
        "('proposal_submitted', '新提议通知（管理员）', "
        "'[LiveCalc] 新提议 #{proposal_id}', "
        "'<h2>新变更提议</h2><p>用户 <strong>${proposer_name}</strong> 提交了一条新的变更提议，需要审核。</p>"
        "<table><tr><td>提议编号</td><td>#${proposal_id}</td></tr>"
        "<tr><td>实体类型</td><td>${entity_type_label}</td></tr>"
        "<tr><td>操作</td><td>${action_label}</td></tr>"
        "<tr><td>目标</td><td>${entity_label}</td></tr></table>', "
        "'用户提交变更提议时通知所有管理员')"
    )
    op.execute(
        "INSERT INTO email_templates (key, name, subject, body_html, description) VALUES "
        "('proposal_approved', '提议通过通知（发起者）', "
        "'[LiveCalc] 提议 #{proposal_id} 已通过', "
        "'<h2>提议已通过</h2><p>您的变更提议已通过审核并生效。</p>"
        "<table><tr><td>提议编号</td><td>#${proposal_id}</td></tr>"
        "<tr><td>实体类型</td><td>${entity_type_label}</td></tr>"
        "<tr><td>操作</td><td>${action_label}</td></tr>"
        "<tr><td>目标</td><td>${entity_label}</td></tr></table>', "
        "'提议审核通过时通知发起者')"
    )
    op.execute(
        "INSERT INTO email_templates (key, name, subject, body_html, description) VALUES "
        "('proposal_rejected', '提议驳回通知（发起者）', "
        "'[LiveCalc] 提议 #{proposal_id} 未通过', "
        "'<h2>提议未通过</h2><p>您的变更提议未通过审核。</p>"
        "<table><tr><td>提议编号</td><td>#${proposal_id}</td></tr>"
        "<tr><td>实体类型</td><td>${entity_type_label}</td></tr>"
        "<tr><td>操作</td><td>${action_label}</td></tr>"
        "<tr><td>目标</td><td>${entity_label}</td></tr></table>"
        "<p>审核备注：${review_note}</p>', "
        "'提议审核驳回时通知发起者')"
    )


def downgrade():
    op.drop_table("email_templates")
    op.drop_table("smtp_config")
