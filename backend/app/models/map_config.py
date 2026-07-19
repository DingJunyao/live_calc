import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, JSON, Boolean, DateTime
from sqlalchemy.ext.mutable import MutableDict
from datetime import datetime
from app.core.database import Base


class MapConfiguration(Base):
    """
    地图配置模型 - 存储地图相关配置信息
    """
    __tablename__ = "map_configurations"

    id = Column(Integer, primary_key=True, index=True)
    # 地图功能总开关（False 时前端所有地图隐藏、商家经纬度不必填、常用地点写接口拒绝）
    map_enabled = Column(Boolean, nullable=False, default=True, server_default=sa.text("true"))
    # 可用地图列表
    available_maps = Column(JSON, nullable=False, default=list)
    # 默认地图
    default_map = Column(String(50), nullable=False, default='amap')
    # 地图 API 密钥配置
    map_api_keys = Column(MutableDict.as_mutable(JSON), nullable=False, default=dict)
    # 地理编码配置
    geocoding = Column(MutableDict.as_mutable(JSON), nullable=False, default=dict)
    # 创建时间
    created_at = Column(DateTime, default=datetime.utcnow)
    # 更新时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """转换为字典格式以供 API 使用"""
        return {
            "map_enabled": self.map_enabled,
            "available_maps": self.available_maps,
            "default_map": self.default_map,
            "map_api_keys": self.map_api_keys,
            "geocoding": self.geocoding
        }