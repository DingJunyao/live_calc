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
    jwt_access_token_expire_minutes: int = 10080  # 7天 (7 * 24 * 60 分钟)
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

    # USDA FoodData Central 下载配置
    # 直连 USDA 的 TLS 握手会被网络按指纹概率性切断（SSL UNEXPECTED_EOF），
    # 单次成功率约 50%，故用「并发重试」拉高整体成功率：每轮并发 N 个握手，
    # 全失败则退避再来，最多 ceil(retries/concurrency) 轮。
    # 仍可配置 usda_http_proxy 走境外代理（默认留空，并兼容 HTTPS_PROXY 环境变量）。
    usda_http_proxy: Optional[str] = None
    usda_download_timeout: int = 600    # 单次请求读/写超时（秒）
    usda_connect_timeout: int = 8       # TLS 握手超时（秒），缩短以快速失败、快速重试
    usda_download_retries: int = 20     # 总尝试次数
    usda_download_concurrency: int = 5  # 每轮并发握手数

    # 翻译/AI HTTP 超时（秒）——批量翻译与 CLI 子进程耗时长，独立于通用 API 的短超时
    translate_http_timeout: int = 3600

    # 日志配置
    log_level: str = "INFO"
    log_dir: str = "./logs"

    # 首次启动配置
    first_run_init_recipes: bool = False
    recipes_source_repo: Optional[str] = None

    # 数据仓库配置（用于导入菜谱、原料、营养数据）
    data_repo_url: str = "https://github.com/DingJunyao/HowToCook_json.git"
    data_repo_branch: str = "main"
    data_repo_dir: str = "out"

    # 本地数据路径（如设置，启动时自动从该路径导入菜谱/食材等）
    data_local_path: Optional[str] = None

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 创建全局settings实例
settings = get_settings()
