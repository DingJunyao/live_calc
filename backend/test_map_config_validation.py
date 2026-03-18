#!/usr/bin/env python3
"""
验证地图配置功能是否正常工作
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.api.admin import MapConfig, MapApiKeys, GeocodingConfig
from app.schemas.auth import UserResponse
from app.core.database import get_db
from fastapi import HTTPException
from unittest.mock import Mock


def test_map_config_creation():
    """测试地图配置创建"""
    print("Testing map config creation...")

    # 创建一个测试配置
    config_data = {
        "available_maps": ["amap", "baidu", "osm"],
        "default_map": "baidu",
        "map_api_keys": {
            "amap": "test_amap_key",
            "baidu": "test_baidu_key",
            "tianditu": {"token": "test_tianditu_token", "type": "img"}
        },
        "geocoding": {
            "enabled_service": "baidu",
            "baidu_key": "test_geocoding_key"
        }
    }

    # 使用Pydantic模型验证数据结构
    map_api_keys = MapApiKeys(**config_data["map_api_keys"])
    geocoding = GeocodingConfig(**config_data["geocoding"])

    full_config = MapConfig(
        available_maps=config_data["available_maps"],
        default_map=config_data["default_map"],
        map_api_keys=map_api_keys,
        geocoding=geocoding
    )

    print("✓ MapConfig validation passed")
    print(f"  Available maps: {full_config.available_maps}")
    print(f"  Default map: {full_config.default_map}")
    print(f"  AMap key: {full_config.map_api_keys.amap}")
    print(f"  Geocoding service: {full_config.geocoding.enabled_service}")

    # 测试默认值
    default_config = MapConfig()
    print(f"✓ Default config created: {default_config.default_map}")

    return True


if __name__ == "__main__":
    success = test_map_config_creation()
    if not success:
        exit(1)
    print("\n🎉 Map configuration validation completed successfully!")