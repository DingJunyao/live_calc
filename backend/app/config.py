from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Literal, Optional


class Settings(BaseSettings):
    # 数据库配置
    database_url: str = "sqlite:///./data/livecalc.db"

    # 应用配置
    debug: bool = True
    app_host: str = "0.0.0.0"  # uvicorn 监听地址（python -m app.main 启动时生效）
    app_port: int = 8000       # uvicorn 监听端口（python -m app.main 启动时生效）

    # JWT 配置
    jwt_secret_key: str = "dev-jwt-secret-change-in-production"  # 开发环境默认值，生产环境必须修改
    jwt_access_token_expire_minutes: int = 10080  # 7天 (7 * 24 * 60 分钟)
    jwt_refresh_token_expire_days: int = 7

    # 注册配置
    invite_code_length: int = 8

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

    # Agent 子进程超时（秒）——运行 Agent CLI 或 LangChain 任务
    agent_idle_timeout: int = 120       # 两行输出之间最大间隔
    agent_total_timeout: int = 600      # Agent 整个任务墙钟上限
    agent_approval_timeout: int = 3600  # 危险 SQL 审批等待超时

    # 导入下载超时（秒）
    import_download_timeout: int = 300  # git clone / ZIP 下载

    # 日志配置
    log_level: str = "INFO"
    log_dir: str = "./logs"

    # 首次启动配置
    first_run_init_recipes: bool = False

    # 数据仓库配置（用于导入菜谱、原料、营养数据）
    data_repo_url: str = "https://github.com/DingJunyao/HowToCook_json.git"
    data_repo_branch: str = "main"
    data_repo_dir: str = "out"

    # 本地数据路径（如设置，启动时自动从该路径导入菜谱/食材等）
    data_local_path: Optional[str] = None

    # 图片存储（仅初始化 / 首次启动 / DB 未配置时生效；后台「图片存储」页配置后优先级更高）
    bootstrap_storage_backend: Literal["local", "s3"] = "local"
    bootstrap_s3_endpoint: str = ""  # OSS/COS/MinIO 等 S3 兼容端点
    bootstrap_s3_access_key: str = ""
    bootstrap_s3_secret_key: str = ""
    bootstrap_s3_bucket: str = ""
    bootstrap_s3_region: str = ""
    # S3 URL 风格：
    #   path     → <endpoint>/<bucket>/<key>（MinIO / 多数自建）
    #   virtual  → <scheme>://<bucket>.<host>[:<port>]/<key>（OSS / AWS S3）
    # OSS 实际为 virtual-hosted 风格，配 OSS 时设 virtual；默认 path 兼容 MinIO
    bootstrap_s3_url_style: Literal["path", "virtual"] = "path"
    # PicGo 风格：S3 key 前缀、自定义域名、网址后缀
    bootstrap_s3_base_path: str = ""         # 如 "livecalc/"（自动加首尾斜杠）
    bootstrap_s3_custom_domain: str = ""     # 如 "https://cdn.example.com"（CDN 域名）
    bootstrap_s3_url_suffix: str = ""       # 如 "?imageslim"（七牛云图片处理参数）

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 创建全局settings实例
settings = get_settings()
