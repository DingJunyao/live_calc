#!/usr/bin/env python3
"""
测试地图配置数据库操作
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import get_db
from app.api.admin import get_stored_map_config, update_stored_map_config, DEFAULT_MAP_CONFIG
from app.models.map_config import MapConfiguration


def test_map_config_db_operations():
    """测试地图配置数据库操作"""
    print("Testing map configuration database operations...")

    # 获取数据库会话
    db_gen = get_db()
    db = next(db_gen)

    try:
        # 1. 测试获取配置（首次获取，应该创建默认配置）
        print("\n1. Testing get_stored_map_config (first time)...")
        config = get_stored_map_config(db)
        print(f"✓ Retrieved config with ID: {config.id}")
        print(f"  Available maps: {config.available_maps}")
        print(f"  Default map: {config.default_map}")

        # 2. 测试更新配置
        print("\n2. Testing update_stored_map_config...")
        new_config_data = {
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

        updated_config = update_stored_map_config(db, new_config_data)
        print(f"✓ Updated config with ID: {updated_config.id}")
        print(f"  Available maps: {updated_config.available_maps}")
        print(f"  Default map: {updated_config.default_map}")

        # 3. 再次获取配置，验证更改
        print("\n3. Testing get_stored_map_config (after update)...")
        config_after_update = get_stored_map_config(db)
        print(f"✓ Retrieved updated config with ID: {config_after_update.id}")
        print(f"  Available maps: {config_after_update.available_maps}")
        print(f"  Default map: {config_after_update.default_map}")

        # 4. 验证数据正确性
        print("\n4. Verifying data correctness...")
        assert config_after_update.default_map == "baidu"
        assert "baidu" in config_after_update.available_maps
        assert config_after_update.map_api_keys["amap"] == "test_amap_key"
        print("✓ All data correctness tests passed!")

        # 5. 测试转换为字典
        print("\n5. Testing to_dict conversion...")
        config_dict = config_after_update.to_dict()
        print(f"✓ Converted to dict: {type(config_dict)} with keys {list(config_dict.keys())}")

        print("\n✓ All tests passed! Database operations work correctly.")

    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 关闭数据库会话
        db.close()

    return True


if __name__ == "__main__":
    success = test_map_config_db_operations()
    if not success:
        exit(1)
    print("\n🎉 All tests completed successfully!")