from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, products, locations, nutrition, recipes, reports
from app.core.database import Base, engine

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建 FastAPI 应用
app = FastAPI(
    title="生计 - 生活成本计算器 API",
    description="生活成本计算器后端 API",
    version="1.0.0"
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


@app.get("/")
async def root():
    """根路径"""
    return {"message": "欢迎使用生计 - 生活成本计算器 API"}


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}
