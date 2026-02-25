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
    secret_key: str = "dev-secret-key-change-in-production"  # 开发环境默认值，生产环境必须修改
    debug: bool = True

    # JWT 配置
    jwt_secret_key: str = "dev-jwt-secret-change-in-production"  # 开发环境默认值，生产环境必须修改
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # 注册配置
    registration_require_invite_code: bool = False
    invite_code_length: int = 8

    # 地图服务配置
    default_map_provider: Optional[str] = None  # amap, baidu, tencent, tianditu
    amap_api_key: Optional[str] = None
    baidu_api_key: Optional[str] = None
    tencent_api_key: Optional[str] = None
    map_tile_url: str = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    map_attribution: str = "&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors"

    # 任务调度配置
    task_scheduler_type: str = "apscheduler"  # apscheduler, celery

    # 文件上传配置
    max_upload_size: int = 10485760  # 10MB
    upload_dir: str = "./data/uploads"

    # 日志配置
    log_level: str = "INFO"
    log_dir: str = "./logs"

    # 首次启动配置
    first_run_init_recipes: bool = False
    recipes_source_repo: Optional[str] = None

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 创建全局settings实例
settings = get_settings()
