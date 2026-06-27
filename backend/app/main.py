import asyncio
import json
import logging
import threading
import time
import traceback
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import auth, products, merchants, nutrition, recipes, reports, admin, invite_codes
from app.api import ingredient_extended  # 新增的食材扩展API
from app.api import products_entity  # 商品实体 API
from app.api import user_preferences  # 用户偏好 API
from app.api import units  # 单位管理 API（含实体单位覆盖和密度路由）
from app.api import ingredient_hierarchy  # 食材层级关系 API
from app.api import sparklines  # 迷你图数据 API
from app.api import export  # 数据导出 API
from app.api import usda  # USDA 食材搜索/详情 API
from app.api import usda_admin  # USDA 管理 API（下载/上传/任务/统计，admin only）
from app.api import import_api  # 导入 API
from app.api import agent_api  # Agent 维护任务台 API
from app.api import places  # 用户常用地点 API
from app.api import meals  # 每日饮食推荐
from app.api import blacklist_groups  # 原料黑名单分组
from app.api import blacklist  # 用户原料黑名单
from app.api import proposals  # 通用提议-审核 API
from app.core.database import Base, engine, get_db
from app.core.exceptions import AppException
from app.core.logging_config import setup_logging


logger = logging.getLogger("app.main")


def init_default_data(db: Session):
    """
    初始化默认数据：单位、单位转换、食材分类
    """
    from app.models.unit import Unit, UnitConversion
    from app.models.region_unit_setting import RegionUnitSetting
    from app.models.ingredient_category import IngredientCategory

    # 检查是否已初始化
    if db.query(Unit).first() is not None:
        logger.info("单位数据已存在，跳过初始化")
        return

    logger.info("正在初始化默认数据...")

    # 添加国际单位制基本单位
    si_units = [
        {"name": "米", "abbreviation": "m", "unit_type": "length", "unit_system": "metric", "is_si_base": True},
        {"name": "千克", "abbreviation": "kg", "unit_type": "mass", "unit_system": "metric", "is_si_base": True},
        {"name": "克", "abbreviation": "g", "unit_type": "mass", "unit_system": "metric", "si_factor": 0.001},
        {"name": "升", "abbreviation": "L", "unit_type": "volume", "unit_system": "metric", "is_si_base": True},
        {"name": "毫升", "abbreviation": "mL", "unit_type": "volume", "unit_system": "metric", "si_factor": 0.001},
        {"name": "秒", "abbreviation": "s", "unit_type": "time", "unit_system": "metric", "is_si_base": True},
    ]

    for unit_data in si_units:
        unit = Unit(**unit_data)
        db.add(unit)

    # 添加常用单位（含中文单位）
    common_units = [
        # 质量单位
        {"name": "斤", "abbreviation": "斤", "unit_type": "mass", "unit_system": "market", "si_factor": 0.5, "is_common": True},
        {"name": "两", "abbreviation": "两", "unit_type": "mass", "unit_system": "market", "si_factor": 0.05, "is_common": True},
        {"name": "英磅", "abbreviation": "lb", "unit_type": "mass", "unit_system": "imperial", "si_factor": 0.453592, "is_common": True},
        {"name": "盎司", "abbreviation": "oz", "unit_type": "mass", "unit_system": "imperial", "si_factor": 0.0283495, "is_common": True},

        # 体积单位
        {"name": "杯", "abbreviation": "cup", "unit_type": "volume", "unit_system": "imperial", "si_factor": 0.24, "is_common": True},
        {"name": "汤匙", "abbreviation": "tbsp", "unit_type": "volume", "unit_system": "imperial", "si_factor": 0.015, "is_common": True},
        {"name": "茶匙", "abbreviation": "tsp", "unit_type": "volume", "unit_system": "imperial", "si_factor": 0.005, "is_common": True},
        {"name": "液盎司", "abbreviation": "fl oz", "unit_type": "volume", "unit_system": "imperial", "si_factor": 0.03, "is_common": True},

        # 长度单位
        {"name": "厘米", "abbreviation": "cm", "unit_type": "length", "unit_system": "metric", "si_factor": 0.01, "is_common": True},
        {"name": "毫米", "abbreviation": "mm", "unit_type": "length", "unit_system": "metric", "si_factor": 0.001, "is_common": True},
        {"name": "英寸", "abbreviation": "in", "unit_type": "length", "unit_system": "imperial", "si_factor": 0.0254, "is_common": True},

        # 计数单位
        {"name": "个", "abbreviation": "个", "unit_type": "count", "unit_system": "count", "si_factor": 1.0, "is_common": True},
        {"name": "只", "abbreviation": "只", "unit_type": "count", "unit_system": "count", "si_factor": 1.0, "is_common": True},
        {"name": "条", "abbreviation": "条", "unit_type": "count", "unit_system": "count", "si_factor": 1.0, "is_common": True},
        {"name": "片", "abbreviation": "片", "unit_type": "count", "unit_system": "count", "si_factor": 1.0, "is_common": True},
    ]

    for unit_data in common_units:
        unit = Unit(**unit_data)
        db.add(unit)

    db.commit()

    # 添加单位转换关系
    unit_conversions = [
        # 质量转换
        {"from_unit": "kg", "to_unit": "g", "factor": 1000.0},
        {"from_unit": "g", "to_unit": "kg", "factor": 0.001},
        {"from_unit": "斤", "to_unit": "g", "factor": 500.0},
        {"from_unit": "g", "to_unit": "斤", "factor": 0.002},
        {"from_unit": "斤", "to_unit": "kg", "factor": 0.5},
        {"from_unit": "kg", "to_unit": "斤", "factor": 2.0},
        {"from_unit": "两", "to_unit": "g", "factor": 50.0},
        {"from_unit": "g", "to_unit": "两", "factor": 0.02},
        {"from_unit": "lb", "to_unit": "kg", "factor": 0.453592},
        {"from_unit": "kg", "to_unit": "lb", "factor": 2.20462},
        {"from_unit": "oz", "to_unit": "g", "factor": 28.3495},
        {"from_unit": "g", "to_unit": "oz", "factor": 0.035274},

        # 体积转换
        {"from_unit": "L", "to_unit": "mL", "factor": 1000.0},
        {"from_unit": "mL", "to_unit": "L", "factor": 0.001},
        {"from_unit": "cup", "to_unit": "mL", "factor": 240.0},
        {"from_unit": "mL", "to_unit": "cup", "factor": 0.00416667},
        {"from_unit": "tbsp", "to_unit": "mL", "factor": 15.0},
        {"from_unit": "mL", "to_unit": "tbsp", "factor": 0.0666667},
        {"from_unit": "tsp", "to_unit": "mL", "factor": 5.0},
        {"from_unit": "mL", "to_unit": "tsp", "factor": 0.2},
        {"from_unit": "fl oz", "to_unit": "mL", "factor": 30.0},
        {"from_unit": "mL", "to_unit": "fl oz", "factor": 0.0333333},

        # 长度转换
        {"from_unit": "m", "to_unit": "cm", "factor": 100.0},
        {"from_unit": "cm", "to_unit": "m", "factor": 0.01},
        {"from_unit": "cm", "to_unit": "mm", "factor": 10.0},
        {"from_unit": "mm", "to_unit": "cm", "factor": 0.1},
        {"from_unit": "in", "to_unit": "cm", "factor": 2.54},
        {"from_unit": "cm", "to_unit": "in", "factor": 0.393701},
    ]

    for conv_data in unit_conversions:
        from_unit = db.query(Unit).filter(Unit.abbreviation == conv_data["from_unit"]).first()
        to_unit = db.query(Unit).filter(Unit.abbreviation == conv_data["to_unit"]).first()

        if from_unit and to_unit:
            conversion = UnitConversion(
                from_unit_id=from_unit.id,
                to_unit_id=to_unit.id,
                conversion_factor=conv_data["factor"],
                precision=6
            )
            db.add(conversion)

    db.commit()

    # 添加中国地区单位设置
    jin_unit = db.query(Unit).filter(Unit.abbreviation == "斤").first()
    g_unit = db.query(Unit).filter(Unit.abbreviation == "g").first()
    ml_unit = db.query(Unit).filter(Unit.abbreviation == "mL").first()

    region_setting = RegionUnitSetting(
        region_code="CN",
        region_name="中国",
        default_mass_unit=jin_unit.id if jin_unit else g_unit.id,
        default_volume_unit=ml_unit.id if ml_unit else None
    )
    db.add(region_setting)
    db.commit()

    # 添加食材分类
    categories = [
        {"name": "grains", "display_name": "谷物", "description": "各类谷物、面粉、大米等", "sort_order": 1},
        {"name": "vegetables", "display_name": "蔬菜", "description": "各类蔬菜", "sort_order": 2},
        {"name": "fruits", "display_name": "水果", "description": "各类水果", "sort_order": 3},
        {"name": "meat", "display_name": "肉类", "description": "各种肉类：猪肉、牛肉、鸡肉等", "sort_order": 4},
        {"name": "seafood", "display_name": "海鲜", "description": "鱼类、虾类、贝类等", "sort_order": 5},
        {"name": "eggs", "display_name": "蛋类", "description": "鸡蛋、鸭蛋等", "sort_order": 6},
        {"name": "dairy", "display_name": "乳制品", "description": "牛奶、奶酪、黄油等", "sort_order": 7},
        {"name": "soy", "display_name": "豆制品", "description": "豆腐、豆浆、豆皮、腐竹等", "sort_order": 8},
        {"name": "seasoning", "display_name": "调味品", "description": "盐、糖、酱油、醋、香料等", "sort_order": 9},
        {"name": "oil", "display_name": "油脂", "description": "食用油、动物油等", "sort_order": 10},
        {"name": "nuts", "display_name": "坚果", "description": "核桃、花生、杏仁等", "sort_order": 11},
        {"name": "beverages", "display_name": "饮品", "description": "茶、咖啡、果汁等", "sort_order": 12},
        {"name": "others", "display_name": "其他", "description": "其他食材", "sort_order": 99},
    ]

    for cat_data in categories:
        category = IngredientCategory(**cat_data)
        db.add(category)

    db.commit()
    logger.info("默认数据初始化完成！")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 应用启动时的事件处理
    setup_logging()
    logger.info("应用正在启动...")

    # 检查并创建缺失的数据库表
    from app.core.database import Base, engine
    Base.metadata.create_all(bind=engine)

    # 获取数据库会话
    db_gen = get_db()
    db: Session = next(db_gen)

    try:
        # 初始化默认数据（单位、分类等）
        init_default_data(db)

        # 启动时导入菜谱等初始数据：仅在首次初始化数据库时进行。
        # 若已存在初始导入的菜谱（source=json_repo），视为已初始化，直接跳过，
        # 避免每次重启都重复遍历数据文件、重复执行营养增量导入（开销大）。
        # 如需重新导入，请通过管理接口触发，或先清空 source=json_repo 的菜谱。
        # 若 FIRST_RUN_INIT_RECIPES=false，也跳过启动导入。
        from app.models.recipe import Recipe
        from app.config import settings

        if not settings.first_run_init_recipes:
            logger.info("FIRST_RUN_INIT_RECIPES=false，跳过启动导入")
        else:
            imported_count = db.query(Recipe).filter(Recipe.source == "json_repo").count()
            if imported_count > 0:
                logger.info(f"初始数据已导入（{imported_count} 条菜谱），跳过启动导入")
            else:
                # 首次初始化：配置了本地数据路径则从本地导入，否则从远程仓库导入
                if settings.data_local_path:
                    local_path = settings.data_local_path
                    logger.info(f"检测到本地数据路径配置: {local_path}")
                    if os.path.isdir(local_path):
                        from app.services.importer.api_service import import_from_local_dir as local_import
                        local_result = local_import(db, local_path, user_id=1)
                        logger.info(f"本地数据导入结果: {local_result.stats}")
                    else:
                        logger.warning(f"本地数据路径不存在或不是目录: {local_path}")
                else:
                    # 未配置本地路径时，从远程仓库导入初始数据
                    from app.services.importer.api_service import import_from_git_repo
                    result = import_from_git_repo(db, user_id=1)
                    logger.info(f"远程数据导入结果: {result.stats}")

        # 检查是否需要为现有原料批量创建商品
        from app.models.nutrition import Ingredient
        from app.models.product_entity import Product

        ingredient_count = db.query(Ingredient).filter(Ingredient.is_active == True).count()
        product_count = db.query(Product).filter(Product.is_active == True).count()

        if ingredient_count > 0 and product_count == 0:
            logger.info(f"检测到 {ingredient_count} 个原料但没有商品，开始批量创建...")
            created_count = 0
            ingredients = db.query(Ingredient).filter(Ingredient.is_active == True).all()

            for ingredient in ingredients:
                try:
                    # 检查是否已存在同名商品
                    existing_product = db.query(Product).filter(
                        Product.name == ingredient.name,
                        Product.is_active == True
                    ).first()

                    if not existing_product:
                        new_product = Product(
                            name=ingredient.name,
                            ingredient_id=ingredient.id,
                            created_by=1,
                            updated_by=1,
                            is_active=True
                        )
                        db.add(new_product)
                        created_count += 1
                        if created_count % 100 == 0:
                            db.flush()
                            logger.info(f"已创建 {created_count} 个商品...")
                except Exception as e:
                    logger.error(f"创建商品失败 {ingredient.name}: {str(e)}")

            db.commit()
            logger.info(f"批量创建商品完成：共创建 {created_count} 个商品")
        elif product_count > 0:
            logger.info(f"商品已存在，跳过批量创建（原料: {ingredient_count}, 商品: {product_count}）")

        # 加载 USDA 搜索索引（表可能尚未迁移或为空，容错处理）
        try:
            from app.services.usda.index_manager import build_usda_index
            build_usda_index(db)
            logger.info("USDA 搜索索引已加载")
        except Exception as e:
            logger.warning(f"USDA 索引加载失败（可能尚未迁移或为空）: {e}")
    except Exception as e:
        logger.error(f"初始化过程中发生错误: {str(e)}")
    finally:
        # 关闭数据库会话
        db.close()

    yield

    # 应用关闭时的事件处理
    logger.info("应用正在关闭...")


# 创建 FastAPI 应用
app = FastAPI(
    title="生计 - 生活成本计算器 API",
    description="生活成本计算器后端 API",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False  # 禁用自动斜杠重定向，避免 307 重定向丢失 Authorization header
)


# === 请求/响应日志中间件 ===
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    记录所有 HTTP 请求和响应的详细信息。

    请求记录：方法、URL、查询参数、路径参数、客户端 IP
    响应记录：状态码、耗时
    错误记录：请求详情 + 响应详情 + 错误堆栈
    """
    start_time = time.time()

    # 读取请求体用于日志记录
    # Starlette 的 Request.body() 缓存结果到 _body，下游可重复读取
    request_body = None
    if request.method in ("POST", "PUT", "PATCH"):
        try:
            body_bytes = await request.body()
            if body_bytes:
                try:
                    request_body = json.loads(body_bytes.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    request_body = f"<binary/non-JSON body: {len(body_bytes)} bytes>"
            # Starlette 的 Request.body() 已内置缓存机制（_body），下游代码
            # 再次调用 request.body() 会直接返回缓存内容，无需手动重建 _receive。
            # 替换 _receive 反而会导致 BaseHTTPMiddleware 的 wrapped_receive 在
            # StreamingResponse.listen_for_disconnect 中收到意外的 http.request 消息
        except Exception:
            request_body = "<无法读取请求体>"

    # 构造请求日志
    req_log = {
        "method": request.method,
        "path": request.url.path,
        "query_params": dict(request.query_params) if request.query_params else None,
        "client": f"{request.client.host}:{request.client.port}" if request.client else None,
    }
    if request_body is not None:
        req_log["body"] = request_body

    logger.debug(f"请求: {json.dumps(req_log, ensure_ascii=False, default=str)}")

    try:
        response = await call_next(request)
        elapsed_ms = (time.time() - start_time) * 1000

        # 正常响应
        log_data = {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "elapsed_ms": f"{elapsed_ms:.1f}",
        }

        if response.status_code >= 400:
            # 错误响应：记录详细信息
            log_data["query_params"] = req_log["query_params"]
            log_data["client"] = req_log["client"]
            if request_body is not None:
                log_data["request_body"] = request_body
            logger.warning(f"响应(错误): {json.dumps(log_data, ensure_ascii=False, default=str)}")
        else:
            logger.debug(f"响应: {json.dumps(log_data, ensure_ascii=False, default=str)}")

        return response
    except Exception:
        elapsed_ms = (time.time() - start_time) * 1000

        # 未捕获的异常：打印完整请求详情和堆栈
        logger.error("=" * 80)
        logger.error(f"未捕获异常: {request.method} {request.url.path}")
        logger.error(f"客户端: {req_log['client']}")
        if req_log["query_params"]:
            logger.error(f"查询参数: {json.dumps(req_log['query_params'], ensure_ascii=False, default=str)}")
        if request_body is not None:
            logger.error(f"请求体: {json.dumps(request_body, ensure_ascii=False, default=str)}")
        logger.error(f"耗时: {elapsed_ms:.1f} ms")
        logger.error(f"错误堆栈:\n{traceback.format_exc()}")
        logger.error("=" * 80)
        raise


# === 全局异常处理器 ===
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """处理应用自定义异常。"""
    logger.error(
        f"AppException: {request.method} {request.url.path} -> "
        f"{exc.status_code} {exc.detail}"
    )
    logger.debug(f"异常堆栈:\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """处理 HTTP 异常（包括 FastAPI 的 HTTPException）。"""
    # 读取请求体用于错误日志
    request_body = None
    if request.method in ("POST", "PUT", "PATCH"):
        try:
            body_bytes = await request.body()
            if body_bytes:
                try:
                    request_body = json.loads(body_bytes.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    request_body = f"<binary: {len(body_bytes)} bytes>"
        except Exception:
            pass

    log_data = {
        "method": request.method,
        "path": request.url.path,
        "status_code": exc.status_code,
        "detail": str(exc.detail),
        "query_params": dict(request.query_params) if request.query_params else None,
        "client": f"{request.client.host}:{request.client.port}" if request.client else None,
    }
    if request_body is not None:
        log_data["request_body"] = request_body

    logger.error(f"HTTP异常: {json.dumps(log_data, ensure_ascii=False, default=str)}")
    logger.debug(f"异常堆栈:\n{traceback.format_exc()}")

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求参数验证错误 (422)。"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error.get("loc", [])),
            "message": error.get("msg", ""),
            "type": error.get("type", ""),
        })

    # 读取请求体
    request_body = None
    try:
        body_bytes = await request.body()
        if body_bytes:
            try:
                request_body = json.loads(body_bytes.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                request_body = f"<binary: {len(body_bytes)} bytes>"
    except Exception:
        pass

    logger.error("=" * 60)
    logger.error(f"请求验证失败: {request.method} {request.url.path}")
    logger.error(f"客户端: {request.client.host}:{request.client.port}" if request.client else "客户端: unknown")
    logger.error(f"查询参数: {dict(request.query_params)}" if request.query_params else "查询参数: 无")
    if request_body is not None:
        logger.error(f"请求体: {json.dumps(request_body, ensure_ascii=False, default=str)}")
    logger.error(f"验证错误:\n{json.dumps(errors, ensure_ascii=False, indent=2)}")
    logger.error("=" * 60)

    return JSONResponse(
        status_code=422,
        content={
            "detail": "请求参数验证失败",
            "errors": errors,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """处理所有未捕获的通用异常 (500)。"""
    # 读取请求体
    request_body = None
    if request.method in ("POST", "PUT", "PATCH"):
        try:
            body_bytes = await request.body()
            if body_bytes:
                try:
                    request_body = json.loads(body_bytes.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    request_body = f"<binary: {len(body_bytes)} bytes>"
        except Exception:
            pass

    logger.error("=" * 80)
    logger.error(f"未处理异常: {request.method} {request.url.path}")
    logger.error(f"客户端: {request.client.host}:{request.client.port}" if request.client else "客户端: unknown")
    if request.query_params:
        logger.error(f"查询参数: {dict(request.query_params)}")
    if hasattr(request, "path_params") and request.path_params:
        logger.error(f"路径参数: {request.path_params}")
    if request_body is not None:
        logger.error(f"请求体: {json.dumps(request_body, ensure_ascii=False, default=str)}")
    logger.error(f"异常类型: {type(exc).__name__}")
    logger.error(f"异常详情: {str(exc)}")
    logger.error(f"错误堆栈:\n{traceback.format_exc()}")
    logger.error("=" * 80)

    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器内部错误: {str(exc)}" if str(exc) else "服务器内部错误"},
    )

# 配置静态文件目录
static_dir = Path(__file__).parent.parent / "static"
static_images_dir = static_dir / "images"

# 确保静态文件目录存在
static_dir.mkdir(exist_ok=True)
static_images_dir.mkdir(exist_ok=True)

# 挂载静态文件到 /api/v1/static 路径，与 API 路径保持一致
app.mount("/api/v1/static", StaticFiles(directory=str(static_dir)), name="static")

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
app.include_router(merchants.router, prefix="/api/v1/merchants", tags=["商家"])
app.include_router(places.router, prefix="/api/v1/places", tags=["常用地点"])
app.include_router(nutrition.router, prefix="/api/v1/nutrition", tags=["营养"])
app.include_router(recipes.router, prefix="/api/v1/recipes", tags=["菜谱"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["报告"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["管理员"])
app.include_router(invite_codes.router, prefix="/api/v1/invite-codes", tags=["邀请码"])
# 食材层级关系路由必须在食材扩展路由之前，避免 /ingredients/merge-history、
# /ingredients/hierarchy、/ingredients/{id}/hierarchy、/ingredients/{id}/merge-status
# 被 ingredient_extended 的 GET /{ingredient_id} 捕获（返回 422/404 而非命中层级端点）。
# 与上方「商品实体路由必须在商品记录路由之前」同模式（路径冲突按 include 顺序裁决）。
app.include_router(ingredient_hierarchy.router, prefix="/api/v1", tags=["食材层级"])
app.include_router(ingredient_extended.router, prefix="/api/v1/ingredients", tags=["食材扩展"])
# 商品实体路由必须在商品记录路由之前，避免 /products/entity 被 /products/{record_id} 匹配
app.include_router(products_entity.router, prefix="/api/v1", tags=["商品实体"])
app.include_router(products.router, prefix="/api/v1/products", tags=["商品"])
app.include_router(user_preferences.router, prefix="/api/v1", tags=["用户偏好"])
app.include_router(units.router, prefix="/api/v1", tags=["单位管理"])
# 迷你图数据 API（独立于主列表，避免超时）
app.include_router(sparklines.router, prefix="/api/v1", tags=["迷你图"])

# 注册实体单位覆盖和密度路由
app.include_router(units.entities_unit_router, prefix="/api/v1", tags=["实体单位覆盖"])
app.include_router(units.entities_density_router, prefix="/api/v1", tags=["实体密度"])
app.include_router(export.router, prefix="/api/v1/export", tags=["数据导出"])
app.include_router(import_api.router, prefix="/api/v1/import", tags=["数据导入"])
app.include_router(agent_api.router, prefix="/api/v1/agent", tags=["Agent任务台"])
app.include_router(usda.router, prefix="/api/v1/usda", tags=["USDA"])
app.include_router(usda_admin.router, prefix="/api/v1/admin", tags=["USDA管理"])
app.include_router(meals.router, prefix="/api/v1/meals", tags=["每日推荐"])
app.include_router(blacklist.router, prefix="/api/v1", tags=["黑名单"])
app.include_router(blacklist_groups.blacklist_group_admin_router, prefix="/api/v1/admin", tags=["原料黑名单分组管理"])
app.include_router(blacklist_groups.blacklist_group_public_router, prefix="/api/v1", tags=["原料黑名单分组"])
app.include_router(proposals.router, prefix="/api/v1", tags=["变更提议"])


@app.get("/")
async def root():
    """根路径"""
    return {"message": "欢迎使用生计 - 生活成本计算器 API"}


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}