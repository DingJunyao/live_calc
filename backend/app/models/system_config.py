from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base


class SystemConfig(Base):
    """系统动态配置键值存储。

    数据库中存储的配置值优先级高于 .env 默认值，
    支持运行时通过管理接口动态修改，无需重启服务。
    """

    __tablename__ = "system_config"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
