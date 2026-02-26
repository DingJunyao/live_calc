from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, products, locations, nutrition, recipes, reports, admin, invite_codes
from app.core.database import Base, engine
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.recipe_import_service import check_and_import_initial_recipes
import asyncio
import threading


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 应用启动时的事件处理
    print("应用正在启动...")

    # 创建数据库表
    Base.metadata.create_all(bind=engine)

    # 检查并导入初始菜谱
    try:
        # 获取数据库会话
        db_gen = get_db()
        db: Session = next(db_gen)

        # 检查并导入初始菜谱
        result = check_and_import_initial_recipes(db)
        print(f"初始菜谱导入结果: {result}")

        # 关闭数据库会话
        db.close()
    except Exception as e:
        print(f"导入初始菜谱时发生错误: {str(e)}")

    yield

    # 应用关闭时的事件处理
    print("应用正在关闭...")


# 创建 FastAPI 应用
app = FastAPI(
    title="生计 - 生活成本计算器 API",
    description="生活成本计算器后端 API",
    version="1.0.0",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(products.router, prefix="/api/v1/products", tags=["商品"])
app.include_router(locations.router, prefix="/api/v1/locations", tags=["地点"])
app.include_router(nutrition.router, prefix="/api/v1/nutrition", tags=["营养"])
app.include_router(recipes.router, prefix="/api/v1/recipes", tags=["菜谱"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["报告"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["管理员"])
app.include_router(invite_codes.router, prefix="/api/v1/invite-codes", tags=["邀请码"])


@app.get("/")
async def root():
    """根路径"""
    return {"message": "欢迎使用生计 - 生活成本计算器 API"}


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}