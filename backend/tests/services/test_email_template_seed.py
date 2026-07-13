"""邮件模板 seed 服务测试。"""
import pytest

from app.models.email_template import EmailTemplate
from app.services.email_template_seed import (
    EMAIL_TEMPLATES,
    ensure_email_templates,
)


def _clean_templates(db):
    """清空 email_templates，隔离测试。"""
    db.query(EmailTemplate).delete()
    db.commit()


@pytest.fixture()
def clean_db(db_session):
    """每个测试前后清空模板表（db_session 是共享内存库，须自隔离）。"""
    _clean_templates(db_session)
    yield db_session
    _clean_templates(db_session)


def test_ensure_creates_templates_when_empty(clean_db):
    db = clean_db

    ensure_email_templates(db)

    assert db.query(EmailTemplate).count() == len(EMAIL_TEMPLATES)
    keys = {t.key for t in db.query(EmailTemplate).all()}
    assert keys == {t["key"] for t in EMAIL_TEMPLATES}
    # 抽查内容正确（subject 含 string.Template 占位符）
    submitted = db.query(EmailTemplate).filter(
        EmailTemplate.key == "proposal_submitted"
    ).first()
    assert submitted is not None
    assert "${proposal_id}" in submitted.subject


def test_ensure_preserves_existing_and_fills_missing(clean_db):
    """已有 key 不覆盖（保护管理员编辑），缺失 key 才补齐。"""
    db = clean_db
    db.add(EmailTemplate(
        key="proposal_submitted",
        name="被管理员改过的名字",
        subject="EDITED",
        body_html="<p>edited</p>",
        description="edited",
    ))
    db.commit()

    ensure_email_templates(db)

    assert db.query(EmailTemplate).count() == len(EMAIL_TEMPLATES)
    submitted = db.query(EmailTemplate).filter(
        EmailTemplate.key == "proposal_submitted"
    ).first()
    assert submitted.subject == "EDITED"  # 未被覆盖


def test_ensure_idempotent_on_double_call(clean_db):
    db = clean_db

    ensure_email_templates(db)
    first = db.query(EmailTemplate).count()

    ensure_email_templates(db)

    assert db.query(EmailTemplate).count() == first
    assert first == len(EMAIL_TEMPLATES)
