from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # 数据库配置
    database_url: str = "sqlite:///./data/livecalc.db"

    # Redis 配置
    redis_url: Optional[str] = None

    # 应用配置
    app_name: str = "生计"
    app_url: str = "http://localhost:8000"
    secret_key: str  # 必须从环境变量设置，无默认值
    debug: bool = True

    # JWT 配置
    jwt_secret_key: str  # 必须从环境变量设置，无默认值
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # 注册配置
    registration_require_invite_code: bool = False
    invite_code_length: int = 8

    # 地图服务配置
    map_tile_url: str = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    map_attribution: str = "&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 创建全局settings实例
settings = get_settings()
