"""操作日志服务 - 自动记录所有数据变更"""
from typing import Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import inspect
import json

from app.models.operation_log import OperationLog


class OperationLogService:
    """操作日志服务"""

    @staticmethod
    def log_operation(
        db: Session,
        action: str,
        table_name: str,
        record_id: int,
        user_id: Optional[int] = None,
        old_data: Optional[dict] = None,
        new_data: Optional[dict] = None,
        changed_fields: Optional[List[str]] = None,
        description: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> OperationLog:
        """
        记录操作日志

        Args:
            db: 数据库会话
            action: 操作类型 (create, update, delete, merge, restore)
            table_name: 表名
            record_id: 记录ID
            user_id: 操作者ID
            old_data: 变更前的数据
            new_data: 变更后的数据
            changed_fields: 变更的字段列表
            description: 操作描述
            ip_address: IP地址

        Returns:
            OperationLog: 创建的日志记录
        """
        log = OperationLog(
            action=action,
            table_name=table_name,
            record_id=record_id,
            user_id=user_id,
            old_data=old_data,
            new_data=new_data,
            changed_fields=changed_fields,
            description=description,
            ip_address=ip_address
        )
        db.add(log)
        # 注意：调用方需要负责 commit
        return log

    @staticmethod
    def serialize_model(model: Any, exclude_fields: Optional[List[str]] = None) -> dict:
        """
        将SQLAlchemy模型序列化为字典

        Args:
            model: SQLAlchemy模型实例
            exclude_fields: 要排除的字段列表

        Returns:
            dict: 序列化后的字典
        """
        if model is None:
            return None

        exclude = set(exclude_fields or [])

        result = {}
        mapper = inspect(model)

        for column in mapper.attrs:
            key = column.key
            if key in exclude:
                continue

            value = getattr(model, key)

            # 处理特殊类型
            if hasattr(value, 'isoformat'):
                # datetime 类型
                result[key] = value.isoformat() if value else None
            elif isinstance(value, (list, dict)):
                # JSON 类型
                result[key] = value
            else:
                result[key] = value

        return result

    @staticmethod
    def get_changed_fields(old_data: dict, new_data: dict) -> List[str]:
        """
        获取变更的字段列表

        Args:
            old_data: 变更前的数据
            new_data: 变更后的数据

        Returns:
            List[str]: 变更的字段列表
        """
        changed = []
        all_keys = set(old_data.keys()) | set(new_data.keys())

        for key in all_keys:
            old_value = old_data.get(key)
            new_value = new_data.get(key)

            if old_value != new_value:
                changed.append(key)

        return changed

    @staticmethod
    def log_create(
        db: Session,
        model: Any,
        user_id: Optional[int] = None,
        description: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> OperationLog:
        """记录创建操作"""
        table_name = model.__tablename__
        record_id = model.id

        new_data = OperationLogService.serialize_model(model)

        return OperationLogService.log_operation(
            db=db,
            action='create',
            table_name=table_name,
            record_id=record_id,
            user_id=user_id,
            new_data=new_data,
            description=description or f'创建 {table_name} 记录 #{record_id}',
            ip_address=ip_address
        )

    @staticmethod
    def log_update(
        db: Session,
        model: Any,
        old_data: dict,
        user_id: Optional[int] = None,
        description: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> OperationLog:
        """记录更新操作"""
        table_name = model.__tablename__
        record_id = model.id

        new_data = OperationLogService.serialize_model(model)
        changed_fields = OperationLogService.get_changed_fields(old_data, new_data)

        return OperationLogService.log_operation(
            db=db,
            action='update',
            table_name=table_name,
            record_id=record_id,
            user_id=user_id,
            old_data=old_data,
            new_data=new_data,
            changed_fields=changed_fields,
            description=description or f'更新 {table_name} 记录 #{record_id}: {", ".join(changed_fields)}',
            ip_address=ip_address
        )

    @staticmethod
    def log_delete(
        db: Session,
        model: Any,
        user_id: Optional[int] = None,
        description: Optional[str] = None,
        ip_address: Optional[str] = None,
        hard_delete: bool = False
    ) -> OperationLog:
        """记录删除操作"""
        table_name = model.__tablename__
        record_id = model.id

        old_data = OperationLogService.serialize_model(model)
        action = 'hard_delete' if hard_delete else 'delete'

        return OperationLogService.log_operation(
            db=db,
            action=action,
            table_name=table_name,
            record_id=record_id,
            user_id=user_id,
            old_data=old_data,
            description=description or f'删除 {table_name} 记录 #{record_id}',
            ip_address=ip_address
        )

    @staticmethod
    def log_merge(
        db: Session,
        source_table: str,
        source_id: int,
        target_id: int,
        user_id: Optional[int] = None,
        description: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> OperationLog:
        """记录合并操作"""
        return OperationLogService.log_operation(
            db=db,
            action='merge',
            table_name=source_table,
            record_id=source_id,
            user_id=user_id,
            new_data={'merged_into_id': target_id},
            description=description or f'合并 {source_table} #{source_id} 到 #{target_id}',
            ip_address=ip_address
        )

    @staticmethod
    def log_restore(
        db: Session,
        model: Any,
        user_id: Optional[int] = None,
        description: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> OperationLog:
        """记录恢复操作"""
        table_name = model.__tablename__
        record_id = model.id

        new_data = OperationLogService.serialize_model(model)

        return OperationLogService.log_operation(
            db=db,
            action='restore',
            table_name=table_name,
            record_id=record_id,
            user_id=user_id,
            new_data=new_data,
            description=description or f'恢复 {table_name} 记录 #{record_id}',
            ip_address=ip_address
        )