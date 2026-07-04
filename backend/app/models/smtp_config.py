from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class SmtpConfig(Base):
    """SMTP 发送配置（单行表，固定 id=1）。"""
    __tablename__ = "smtp_config"

    id = Column(Integer, primary_key=True, default=1)
    host = Column(String(255), nullable=False, default="")
    port = Column(Integer, nullable=False, default=587)
    username = Column(String(255), nullable=False, default="")
    password = Column(String(255), nullable=False, default="")
    use_tls = Column(Boolean, nullable=False, default=True)
    from_address = Column(String(255), nullable=False, default="")
    from_name = Column(String(100), nullable=False, default="LiveCalc")
    enabled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
