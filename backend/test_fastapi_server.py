#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""测试 FastAPI 环境下的 API 端点"""

import asyncio
import os
import sys

# 添加后端目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from fastapi import FastAPI
from app.api.nutrition import router as nutrition_router
from app.core.database import engine, Base

app = FastAPI(title="Test API for Debugging")
app.include_router(nutrition_router, prefix="/api/v1", tags=["nutrition"])

@app.on_event("startup")
async def startup_event():
    print("Startup event complete")

if __name__ == "__main__":
    import uvicorn
    # 在实际环境中运行测试
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")