"""操作日志模型 - 记录所有数据变更"""
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class OperationLog(Base):
    """操作日志表 - 记录所有创建、更新、删除操作"""
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True)

    # 操作类型: create, update, delete, merge, restore 等
    action = Column(String(50), nullable=False, index=True)

    # 目标表名
    table_name = Column(String(100), nullable=False, index=True)

    # 目标记录ID
    record_id = Column(Integer, nullable=False, index=True)

    # 操作者ID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # 变更前的数据（JSON格式）
    old_data = Column(JSON, nullable=True)

    # 变更后的数据（JSON格式）
    new_data = Column(JSON, nullable=True)

    # 变更的字段列表
    changed_fields = Column(JSON, nullable=True)

    # 操作描述
    description = Column(Text, nullable=True)

    # IP地址
    ip_address = Column(String(50), nullable=True)

    # 操作时间
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<OperationLog(id={self.id}, action={self.action}, table={self.table_name}, record_id={self.record_id})>"