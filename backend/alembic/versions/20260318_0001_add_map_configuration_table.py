"""Add map configuration table

Revision ID: 20260318_0001
Revises: 20260314_0001
Create Date: 2026-03-18 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import json


# revision identifiers, used by Alembic.
revision = '20260318_0001'
down_revision = '20260314_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 map_configurations 表
    op.create_table(
        'map_configurations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('available_maps', sa.JSON(), nullable=False),
        sa.Column('default_map', sa.String(), nullable=False),
        sa.Column('map_api_keys', sa.JSON(), nullable=False),
        sa.Column('geocoding', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # 添加索引
    op.create_index(op.f('ix_map_configurations_id'), 'map_configurations', ['id'], unique=False)

    # 插入默认地图配置
    default_config = {
        "available_maps": ["amap", "baidu", "tencent", "tianditu", "osm"],
        "default_map": "amap",
        "map_api_keys": {
            "amap": None,
            "amap_security": None,
            "baidu": None,
            "tencent": None,
            "tianditu": {"token": "", "type": "vec"}
        },
        "geocoding": {
            "enabled_service": "amap",
            "amap_key": None,
            "baidu_key": None,
            "tencent_key": None,
            "nominatim_url": "",
            "nominatim_email": None
        }
    }

    # 由于使用JSON字段，需要使用原生SQL插入默认数据
    conn = op.get_bind()
    conn.execute(
        sa.text("""
        INSERT INTO map_configurations (available_maps, default_map, map_api_keys, geocoding, created_at, updated_at)
        VALUES (:available_maps, :default_map, :map_api_keys, :geocoding, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """),
        {
            "available_maps": json.dumps(default_config["available_maps"]),
            "default_map": default_config["default_map"],
            "map_api_keys": json.dumps(default_config["map_api_keys"]),
            "geocoding": json.dumps(default_config["geocoding"])
        }
    )


def downgrade() -> None:
    # 删除 map_configurations 表
    op.drop_table('map_configurations')