from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.api import auth, products, merchants, nutrition, recipes, reports, admin, invite_codes
from app.api import ingredient_extended  # 新增的食材扩展API
from app.api import products_entity  # 商品实体 API
from app.api import user_preferences  # 用户偏好 API
from app.api import units  # 单位管理 API
from app.core.database import Base, engine
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.recipe_import_service import check_and_import_initial_recipes
from app.services.json_recipe_import_service import check_and_import_from_json_repo
import asyncio
import threading
import os


def init_default_data(db: Session):
    """
    初始化默认数据：单位、单位转换、食材分类
    """
    from app.models.unit import Unit, UnitConversion
    from app.models.region_unit_setting import RegionUnitSetting
    from app.models.ingredient_category import IngredientCategory

    # 检查是否已初始化
    if db.query(Unit).first() is not None:
        print("单位数据已存在，跳过初始化")
        return

    print("正在初始化默认数据...")

    # 添加国际单位制基本单位
    si_units = [
        {"name": "米", "abbreviation": "m", "unit_type": "length", "is_si_base": True},
        {"name": "千克", "abbreviation": "kg", "unit_type": "mass", "is_si_base": True},
        {"name": "克", "abbreviation": "g", "unit_type": "mass", "si_factor": 0.001},
        {"name": "升", "abbreviation": "L", "unit_type": "volume", "is_si_base": True},
        {"name": "毫升", "abbreviation": "mL", "unit_type": "volume", "si_factor": 0.001},
        {"name": "秒", "abbreviation": "s", "unit_type": "time", "is_si_base": True},
    ]

    for unit_data in si_units:
        unit = Unit(**unit_data)
        db.add(unit)

    # 添加常用单位（含中文单位）
    common_units = [
        # 质量单位
        {"name": "斤", "abbreviation": "jin", "unit_type": "mass", "si_factor": 0.5, "is_common": True},
        {"name": "两", "abbreviation": "liang", "unit_type": "mass", "si_factor": 0.05, "is_common": True},
        {"name": "英磅", "abbreviation": "lb", "unit_type": "mass", "si_factor": 0.453592, "is_common": True},
        {"name": "盎司", "abbreviation": "oz", "unit_type": "mass", "si_factor": 0.0283495, "is_common": True},

        # 体积单位
        {"name": "杯", "abbreviation": "cup", "unit_type": "volume", "si_factor": 0.24, "is_common": True},
        {"name": "汤匙", "abbreviation": "tbsp", "unit_type": "volume", "si_factor": 0.015, "is_common": True},
        {"name": "茶匙", "abbreviation": "tsp", "unit_type": "volume", "si_factor": 0.005, "is_common": True},
        {"name": "液盎司", "abbreviation": "fl oz", "unit_type": "volume", "si_factor": 0.03, "is_common": True},

        # 长度单位
        {"name": "厘米", "abbreviation": "cm", "unit_type": "length", "si_factor": 0.01, "is_common": True},
        {"name": "毫米", "abbreviation": "mm", "unit_type": "length", "si_factor": 0.001, "is_common": True},
        {"name": "英寸", "abbreviation": "in", "unit_type": "length", "si_factor": 0.0254, "is_common": True},

        # 计数单位
        {"name": "个", "abbreviation": "个", "unit_type": "count", "si_factor": 1.0, "is_common": True},
        {"name": "只", "abbreviation": "只", "unit_type": "count", "si_factor": 1.0, "is_common": True},
        {"name": "条", "abbreviation": "条", "unit_type": "count", "si_factor": 1.0, "is_common": True},
        {"name": "片", "abbreviation": "片", "unit_type": "count", "si_factor": 1.0, "is_common": True},
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
        {"from_unit": "jin", "to_unit": "g", "factor": 500.0},
        {"from_unit": "g", "to_unit": "jin", "factor": 0.002},
        {"from_unit": "jin", "to_unit": "kg", "factor": 0.5},
        {"from_unit": "kg", "to_unit": "jin", "factor": 2.0},
        {"from_unit": "liang", "to_unit": "g", "factor": 50.0},
        {"from_unit": "g", "to_unit": "liang", "factor": 0.02},
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
    jin_unit = db.query(Unit).filter(Unit.abbreviation == "jin").first()
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
        {"name": "seasoning", "display_name": "调味品", "description": "盐、糖、酱油、醋、香料等", "sort_order": 8},
        {"name": "oil", "display_name": "油脂", "description": "食用油、动物油等", "sort_order": 9},
        {"name": "nuts", "display_name": "坚果", "description": "核桃、花生、杏仁等", "sort_order": 10},
        {"name": "beverages", "display_name": "饮品", "description": "茶、咖啡、果汁等", "sort_order": 11},
        {"name": "others", "display_name": "其他", "description": "其他食材", "sort_order": 99},
    ]

    for cat_data in categories:
        category = IngredientCategory(**cat_data)
        db.add(category)

    db.commit()
    print("默认数据初始化完成！")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 应用启动时的事件处理
    print("应用正在启动...")

    # 检查并创建缺失的数据库表
    from app.core.database import Base, engine
    Base.metadata.create_all(bind=engine)

    # 获取数据库会话
    db_gen = get_db()
    db: Session = next(db_gen)

    try:
        # 初始化默认数据（单位、分类等）
        init_default_data(db)

        # 检查并导入初始菜谱（优先从 JSON 仓库导入）
        result = check_and_import_from_json_repo(db, user_id=1)  # 使用默认用户 ID 1
        print(f"JSON 仓库菜谱导入结果: {result}")

        # 检查是否需要为现有原料批量创建商品
        from app.models.nutrition import Ingredient
        from app.models.product_entity import Product

        ingredient_count = db.query(Ingredient).filter(Ingredient.is_active == True).count()
        product_count = db.query(Product).filter(Product.is_active == True).count()

        if ingredient_count > 0 and product_count == 0:
            print(f"检测到 {ingredient_count} 个原料但没有商品，开始批量创建...")
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
                            print(f"已创建 {created_count} 个商品...")
                except Exception as e:
                    print(f"创建商品失败 {ingredient.name}: {str(e)}")

            db.commit()
            print(f"批量创建商品完成：共创建 {created_count} 个商品")
        elif product_count > 0:
            print(f"商品已存在，跳过批量创建（原料: {ingredient_count}, 商品: {product_count}）")
    except Exception as e:
        print(f"初始化过程中发生错误: {str(e)}")
    finally:
        # 关闭数据库会话
        db.close()

    yield

    # 应用关闭时的事件处理
    print("应用正在关闭...")


# 创建 FastAPI 应用
app = FastAPI(
    title="生计 - 生活成本计算器 API",
    description="生活成本计算器后端 API",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False  # 禁用自动斜杠重定向，避免 307 重定向丢失 Authorization header
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
app.include_router(nutrition.router, prefix="/api/v1/nutrition", tags=["营养"])
app.include_router(recipes.router, prefix="/api/v1/recipes", tags=["菜谱"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["报告"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["管理员"])
app.include_router(invite_codes.router, prefix="/api/v1/invite-codes", tags=["邀请码"])
app.include_router(ingredient_extended.router, prefix="/api/v1/ingredients", tags=["食材扩展"])
# 商品实体路由必须在商品记录路由之前，避免 /products/entity 被 /products/{record_id} 匹配
app.include_router(products_entity.router, prefix="/api/v1", tags=["商品实体"])
app.include_router(products.router, prefix="/api/v1/products", tags=["商品"])
app.include_router(user_preferences.router, prefix="/api/v1", tags=["用户偏好"])
app.include_router(units.router, prefix="/api/v1", tags=["单位管理"])


@app.get("/")
async def root():
    """根路径"""
    return {"message": "欢迎使用生计 - 生活成本计算器 API"}


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}