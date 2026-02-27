"""
启动测试服务器来验证API端点
"""

import uvicorn
from fastapi import FastAPI
from app.api.ingredient_extended import router as ingredient_extended_router

# 创建测试应用
test_app = FastAPI(title="Test App for New Ingredients API")

# 包含新API路由器
test_app.include_router(ingredient_extended_router, prefix="/api/v1/ingredients", tags=["食材扩展"])

@test_app.get("/")
async def root():
    return {"message": "Test server for new ingredients API"}

if __name__ == "__main__":
    uvicorn.run(test_app, host="0.0.0.0", port=8001)