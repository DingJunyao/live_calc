"""SMTP 配置与邮件模板管理 API（仅管理员）。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models.user import User
from app.models.smtp_config import SmtpConfig
from app.models.email_template import EmailTemplate
from app.schemas.email_config import (
    SmtpConfigResponse,
    SmtpConfigUpdate,
    SmtpTestRequest,
    EmailTemplateResponse,
    EmailTemplateUpdate,
)
from app.services.email_service import EmailService

router = APIRouter()


def _get_or_create_smtp_config(db: Session) -> SmtpConfig:
    config = db.query(SmtpConfig).first()
    if not config:
        config = SmtpConfig(id=1)
        db.add(config)
        db.flush()
    return config


@router.get("/admin/email-config/smtp", response_model=SmtpConfigResponse)
def get_smtp_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    config = _get_or_create_smtp_config(db)
    return SmtpConfigResponse.model_validate(config)


@router.put("/admin/email-config/smtp", response_model=SmtpConfigResponse)
def update_smtp_config(
    body: SmtpConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    config = _get_or_create_smtp_config(db)
    update_data = body.model_dump(exclude_unset=True)
    if "password" in update_data and not update_data["password"]:
        del update_data["password"]
    for key, value in update_data.items():
        setattr(config, key, value)
    db.commit()
    db.refresh(config)
    return SmtpConfigResponse.model_validate(config)


@router.post("/admin/email-config/smtp/test")
def test_smtp_config(
    body: SmtpTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    config = _get_or_create_smtp_config(db)
    if not config.host or not config.enabled:
        raise HTTPException(status_code=400, detail="SMTP 未配置或未启用")
    service = EmailService(config)
    service.send_test_async(body.to_email)
    return {"message": f"测试邮件已异步发送至 {body.to_email}"}


@router.get("/admin/email-config/templates", response_model=List[EmailTemplateResponse])
def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    return db.query(EmailTemplate).order_by(EmailTemplate.key).all()


@router.get("/admin/email-config/templates/{key}", response_model=EmailTemplateResponse)
def get_template(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    tpl = db.query(EmailTemplate).filter(EmailTemplate.key == key).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="模板不存在")
    return tpl


@router.put("/admin/email-config/templates/{key}", response_model=EmailTemplateResponse)
def update_template(
    key: str,
    body: EmailTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    tpl = db.query(EmailTemplate).filter(EmailTemplate.key == key).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="模板不存在")
    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(tpl, k, v)
    db.commit()
    db.refresh(tpl)
    return tpl
