"""导入任务模型——追踪后台导入/AI 推测任务的进度。"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.mutable import MutableDict

from app.core.database import Base


class ImportTask(Base):
    """导入/推测任务进度记录"""
    __tablename__ = "import_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String(32), nullable=False, index=True)
    # task_type: git_import / local_import / upload_import / ai_quantities / ai_densities
    status = Column(String(16), nullable=False, default="pending")
    # status: pending / running / success / failed
    progress = Column(MutableDict.as_mutable(JSON), nullable=True)
    # progress: {"stage": "克隆仓库", "current": 50, "total": 100, "message": "导入菜谱 50/395"}
    stats = Column(JSON, nullable=True)
    # stats: {"recipes": 362, "ingredients": 615} — 最终统计
    error = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, **kwargs):
        kwargs.setdefault("status", "pending")
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            "id": self.id,
            "task_type": self.task_type,
            "status": self.status,
            "progress": self.progress or {},
            "stats": self.stats or {},
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
