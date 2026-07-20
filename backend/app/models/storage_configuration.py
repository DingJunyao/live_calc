import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.core.database import Base


class StorageConfiguration(Base):
    """图片存储配置（单行）。DB 字段非空则覆盖 .env BOOTSTRAP_*。"""
    __tablename__ = "storage_configurations"

    id = Column(Integer, primary_key=True, index=True)
    backend = Column(String(10), nullable=False, default="local")        # local | s3
    storage_base_url = Column(String(255), nullable=True)
    s3_endpoint = Column(String(255), nullable=True)
    s3_access_key = Column(String(255), nullable=True)
    s3_secret_key = Column(String(255), nullable=True)
    s3_bucket = Column(String(255), nullable=True)
    s3_region = Column(String(64), nullable=True)
    s3_url_style = Column(String(10), nullable=False, default="path")    # path | virtual
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典格式以供 API 使用"""
        return {
            "backend": self.backend,
            "storage_base_url": self.storage_base_url,
            "s3_endpoint": self.s3_endpoint,
            "s3_access_key": self.s3_access_key,
            "s3_secret_key": self.s3_secret_key,
            "s3_bucket": self.s3_bucket,
            "s3_region": self.s3_region,
            "s3_url_style": self.s3_url_style,
        }
