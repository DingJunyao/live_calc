"""USDA 营养数据相关模型（独立仓库，与现有 nutrition_data 并存）"""
from sqlalchemy import Column, Integer, String, Float, JSON, Text, DateTime
from sqlalchemy.ext.mutable import MutableDict
from datetime import datetime
from app.core.database import Base


class UsdaFood(Base):
    """USDA 食材主表"""
    __tablename__ = "usda_foods"

    id = Column(Integer, primary_key=True, index=True)
    fdc_id = Column(Integer, unique=True, nullable=False, index=True)
    data_type = Column(String(32), nullable=False, index=True)  # foundation / sr_legacy
    description = Column(String(512), nullable=False, index=True)
    description_zh = Column(String(512), nullable=True, index=True)
    translate_status = Column(String(16), nullable=False, default="pending")  # pending/done/error
    publication_date = Column(String(32), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, **kwargs):
        kwargs.setdefault("translate_status", "pending")
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<UsdaFood(fdc_id={self.fdc_id}, {self.description})>"


class UsdaFoodNutrient(Base):
    """USDA 食材营养素"""
    __tablename__ = "usda_food_nutrients"

    id = Column(Integer, primary_key=True, index=True)
    fdc_id = Column(Integer, nullable=False, index=True)
    nutrient_no = Column(String(16), nullable=True)
    name = Column(String(255), nullable=False)
    name_zh = Column(String(255), nullable=True)
    amount = Column(Float, nullable=False)
    unit_name = Column(String(32), nullable=False)

    def __repr__(self):
        return f"<UsdaFoodNutrient(fdc_id={self.fdc_id}, {self.name}={self.amount}{self.unit_name})>"


class TranslationConfig(Base):
    """翻译配置（单行，JSON 存 ai/machine 两区各 provider 配置）"""
    __tablename__ = "translation_configs"

    id = Column(Integer, primary_key=True, index=True)
    config = Column(MutableDict.as_mutable(JSON), nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "ai": (self.config or {}).get("ai", {"providers": {}}),
            "machine": (self.config or {}).get("machine", {"providers": {}}),
        }


class UsdaTask(Base):
    """USDA 数据任务（下载/上传/翻译）进度记录"""
    __tablename__ = "usda_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String(32), nullable=False, index=True)  # download/upload/translate
    status = Column(String(16), nullable=False, default="pending")  # pending/running/success/failed
    progress = Column(MutableDict.as_mutable(JSON), nullable=True)  # {done, total, ...}
    provider = Column(String(32), nullable=True)
    error_log = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, **kwargs):
        kwargs.setdefault("status", "pending")
        super().__init__(**kwargs)

    def __repr__(self):
        return f"<UsdaTask({self.task_type}, {self.status})>"
