from sqlalchemy import Column, Integer, DateTime, String, Boolean, ForeignKey
from sqlalchemy.sql import func


class AuditMixin:
    """审计字段混入类，包含创建时间、修改时间、创建者、修改者和有效性字段"""

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 创建者和修改者（外键关联到用户表）
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # 使用nullable=True避免现有数据问题
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # 使用nullable=True避免现有数据问题

    # 软删除标志
    is_active = Column(Boolean, default=True, nullable=False)


# 定义基础模型类
class BaseModel:
    """基础模型类，包含所有审计字段"""
    __abstract__ = True

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 创建者和修改者（外键关联到用户表）
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # 使用nullable=True避免现有数据问题
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # 使用nullable=True避免现有数据问题

    # 软删除标志
    is_active = Column(Boolean, default=True, nullable=False)