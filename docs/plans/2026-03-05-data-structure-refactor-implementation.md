# 数据结构重构实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 完成生计项目的数据结构重构，包括商品、食材、菜谱、价格之间的完整关联，以及前端缺失的功能。

**Architecture:** 采用分层重构策略：先建立后端数据模型，再实现 API 接口，最后实现前端界面。遵循 TDD 原则，每个功能先写测试再实现代码。

**Tech Stack:** FastAPI (后端), SQLAlchemy (ORM), Vue 3 + TypeScript (前端), Alembic (数据库迁移)

---

## 阶段 1: 后端数据模型

### Task 1: 创建 Product 模型

**Files:**
- Create: `backend/app/models/product_entity.py`
- Modify: `backend/app/models/__init__.py`

**Step 1: 创建模型文件**

创建 `backend/app/models/product_entity.py`:

```python
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.base_model import AuditMixin
from app.core.database import Base


class Product(Base, AuditMixin):
    """商品实体 - 代表可在商店购买的具体商品"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    brand = Column(String(100))
    barcode = Column(String(50), unique=True)
    image_url = Column(String(500))
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False, index=True)
    tags = Column(String(500))  # JSON 字符串存储标签列表

    # 关系
    ingredient = relationship("Ingredient", back_populates="products")
    price_records = relationship("ProductRecord", back_populates="product")
```

**Step 2: 导入新模型**

在 `backend/app/models/__init__.py` 中添加导入:

```python
from app.models.product_entity import Product
```

**Step 3: 更新 Ingredient 模型添加反向关系**

修改 `backend/app/models/nutrition.py` 中的 Ingredient 类:

```python
class Ingredient(Base, AuditMixin):
    # ... 现有代码 ...

    # 添加反向关系
    products = relationship("Product", back_populates="ingredient", lazy="select")
    product_links = relationship("ProductIngredientLink", back_populates="ingredient", lazy="select")
```

**Step 4: 创建数据库迁移脚本**

Run: `cd backend && alembic revision --autogenerate -m "add product table"`

**Step 5: 检查迁移脚本**

确认生成的迁移脚本在 `backend/alembic/versions/` 中，包含：
- 创建 `products` 表
- 添加正确的字段和约束

**Step 6: 提交**

```bash
git add backend/app/models/product_entity.py backend/app/models/__init__.py backend/app/models/nutrition.py backend/alembic/versions/
git commit -m "feat(product): add Product model with audit fields"
```

---

### Task 2: 创建 UserIngredientPreference 模型

**Files:**
- Create: `backend/app/models/user_ingredient_preference.py`
- Modify: `backend/app/models/__init__.py`

**Step 1: 创建模型文件**

创建 `backend/app/models/user_ingredient_preference.py`:

```python
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.base_model import AuditMixin
from app.core.database import Base


class UserIngredientPreference(Base, AuditMixin):
    """用户对食材的默认选择偏好设置"""
    __tablename__ = "user_ingredient_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False, index=True)
    default_product_id = Column(Integer, ForeignKey("products.id"))
    default_recipe_id = Column(Integer, ForeignKey("recipes.id"))
    preference_type = Column(String(20), default="product")
    is_favorite = Column(Boolean, default=False)

    # 唯一约束
    __table_args__ = (
        UniqueConstraint('user_id', 'ingredient_id', name='unique_user_ingredient'),
    )

    # 关系
    user = relationship("User")
    ingredient = relationship("Ingredient")
    default_product = relationship("Product")
    default_recipe = relationship("Recipe")
```

**Step 2: 导入新模型**

在 `backend/app/models/__init__.py` 中添加导入:

```python
from app.models.user_ingredient_preference import UserIngredientPreference
```

**Step 3: 创建数据库迁移脚本**

Run: `cd backend && alembic revision --autogenerate -m "add user_ingredient_preference table"`

**Step 4: 检查迁移脚本**

确认生成的迁移脚本包含：
- 创建 `user_ingredient_preferences` 表
- 包含唯一约束 `(user_id, ingredient_id)`

**Step 5: 提交**

```bash
git add backend/app/models/user_ingredient_preference.py backend/app/models/__init__.py backend/alembic/versions/
git commit -m "feat(preference): add UserIngredientPreference model with unique constraint"
```

---

### Task 3: 修改 Recipe 模型添加成品食材关联

**Files:**
- Modify: `backend/app/models/recipe.py`

**Step 1: 添加 result_ingredient_id 字段**

在 `backend/app/models/recipe.py` 中的 Recipe 类添加:

```python
class Recipe(Base, AuditMixin):
    # ... 现有字段 ...

    # 新增：成品对应食材
    result_ingredient_id = Column(Integer, ForeignKey("ingredients.id"))

    # 添加关系
    result_ingredient = relationship("Ingredient", foreign_keys=[result_ingredient_id], lazy="select")
```

**Step 2: 创建数据库迁移脚本**

Run: `cd backend && alembic revision --autogenerate -m "add result_ingredient_id to recipes"`

**Step 3: 检查迁移脚本**

确认迁移脚本在 `recipes` 表中添加了 `result_ingredient_id` 列和外键约束。

**Step 4: 提交**

```bash
git add backend/app/models/recipe.py backend/alembic/versions/
git commit -m "feat(recipe): add result_ingredient_id to link recipe to ingredient"
```

---

### Task 4: 修改 ProductRecord 模型添加商品关联

**Files:**
- Modify: `backend/app/models/product.py`

**Step 1: 添加 product_id 字段**

在 `backend/app/models/product.py` 中的 ProductRecord 类添加:

```python
class ProductRecord(Base):
    # ... 现有字段 ...

    # 新增：关联商品
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    # 添加关系
    product = relationship("Product", back_populates="price_records")
```

**Step 2: 创建数据库迁移脚本**

Run: `cd backend && alembic revision --autogenerate -m "add product_id to product_records"`

**Step 3: 检查迁移脚本**

确认迁移脚本：
- 在 `product_records` 表中添加了 `product_id` 列
- 添加了外键约束到 `products` 表
- **注意：** 由于现有数据可能违反 NOT NULL 约束，迁移脚本需要先允许 NULL，然后填充数据，最后改为 NOT NULL

**Step 4: 编辑迁移脚本处理现有数据**

打开迁移脚本，修改为：

```python
def upgrade():
    op.add_column('product_records', sa.Column('product_id', sa.Integer(), nullable=True))

    # 为现有记录创建临时商品（基于 ingredient 关联）
    connection = op.get_bind()
    # 执行 SQL 为现有记录创建 product_id
    # 这部分需要根据现有数据结构编写 SQL

    op.create_foreign_key('fk_product_records_product', 'product_records', 'products', ['product_id'], ['id'])
    op.alter_column('product_records', 'product_id', nullable=False)

def downgrade():
    op.drop_constraint('fk_product_records_product', 'product_records', type_='foreignkey')
    op.drop_column('product_records', 'product_id')
```

**Step 5: 提交**

```bash
git add backend/app/models/product.py backend/alembic/versions/
git commit -m "feat(product_record): add product_id foreign key"
```

---

### Task 5: 修改 ProductIngredientLink 模型

**Files:**
- Modify: `backend/app/models/product_ingredient_link.py`

**Step 1: 重构模型**

将 `backend/app/models/product_ingredient_link.py` 修改为:

```python
from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class ProductIngredientLink(Base):
    """商品与食材之间的映射关系"""
    __tablename__ = "product_ingredient_links"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)

    # 审计字段
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    product = relationship("Product")
    ingredient = relationship("Ingredient", back_populates="product_links")
```

**Step 2: 创建数据库迁移脚本**

Run: `cd backend && alembic revision --autogenerate -m "refactor product_ingredient_links"`

**Step 3: 检查迁移脚本**

确认迁移脚本：
- 删除旧的外键约束 `product_record_id`
- 添加新的外键约束 `product_id`
- 删除已废弃的字段（`match_confidence`, `match_method`, `verified_by_user`, `verification_notes`）

**Step 4: 提交**

```bash
git add backend/app/models/product_ingredient_link.py backend/alembic/versions/
git commit -m "refactor(product_ingredient_link): simplify and link to Product instead of ProductRecord"
```

---

### Task 6: 执行数据库迁移

**Files:**
- None (database only)

**Step 1: 备份现有数据库**

```bash
cp backend/data/livecalc.db backend/data/livecalc.db.backup
```

**Step 2: 运行迁移**

Run: `cd backend && alembic upgrade head`

**Step 3: 验证数据库结构**

```bash
sqlite3 backend/data/livecalc.db ".schema products"
sqlite3 backend/data/livecalc.db ".schema user_ingredient_preferences"
sqlite3 backend/data/livecalc.db ".schema recipes"  # 检查 result_ingredient_id
sqlite3 backend/data/livecalc.db ".schema product_records"  # 检查 product_id
```

Expected: 所有新表和新字段已创建

**Step 4: 提交**

```bash
git add backend/data/
git commit -m "chore: execute database migrations"
```

---

## 阶段 2: 后端 API 接口

### Task 7: 创建 Product Schema

**Files:**
- Create: `backend/app/schemas/product_entity.py`

**Step 1: 创建 Schema 文件**

创建 `backend/app/schemas/product_entity.py`:

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    brand: Optional[str] = Field(None, max_length=100)
    barcode: Optional[str] = Field(None, max_length=50)
    image_url: Optional[str] = Field(None, max_length=500)
    ingredient_id: int
    tags: Optional[List[str]] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    brand: Optional[str] = Field(None, max_length=100)
    barcode: Optional[str] = Field(None, max_length=50)
    image_url: Optional[str] = Field(None, max_length=500)
    ingredient_id: Optional[int] = None
    tags: Optional[List[str]] = None


class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True


class ProductWithDetails(ProductResponse):
    ingredient_name: Optional[str] = None
    latest_price: Optional[float] = None
    latest_price_date: Optional[datetime] = None
```

**Step 2: 提交**

```bash
git add backend/app/schemas/product_entity.py
git commit -m "feat(schemas): add Product schemas"
```

---

### Task 8: 创建 UserIngredientPreference Schema

**Files:**
- Create: `backend/app/schemas/user_preference.py`

**Step 1: 创建 Schema 文件**

创建 `backend/app/schemas/user_preference.py`:

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserPreferenceBase(BaseModel):
    ingredient_id: int
    default_product_id: Optional[int] = None
    default_recipe_id: Optional[int] = None
    preference_type: str = Field(default="product", pattern="^(product|recipe)$")
    is_favorite: bool = False


class UserPreferenceCreate(UserPreferenceBase):
    pass


class UserPreferenceUpdate(BaseModel):
    ingredient_id: Optional[int] = None
    default_product_id: Optional[int] = None
    default_recipe_id: Optional[int] = None
    preference_type: Optional[str] = Field(None, pattern="^(product|recipe)$")
    is_favorite: Optional[bool] = None


class UserPreferenceResponse(UserPreferenceBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True
```

**Step 2: 提交**

```bash
git add backend/app/schemas/user_preference.py
git commit -m "feat(schemas): add UserIngredientPreference schemas"
```

---

### Task 9: 创建 Product API 路由

**Files:**
- Create: `backend/app/api/products_entity.py`

**Step 1: 创建 API 路由文件**

创建 `backend/app/api/products_entity.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.product_entity import Product
from app.schemas.product_entity import ProductCreate, ProductUpdate, ProductResponse, ProductWithDetails
from sqlalchemy import desc

router = APIRouter(prefix="/products/entity", tags=["products"])


@router.post("/", response_model=ProductResponse)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建商品"""
    # 检查条码唯一性
    if product.barcode:
        existing = db.query(Product).filter(Product.barcode == product.barcode).first()
        if existing:
            raise HTTPException(status_code=400, detail="Barcode already exists")

    db_product = Product(**product.dict())
    db_product.created_by = current_user.id
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@router.get("/", response_model=List[ProductResponse])
def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    ingredient_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取商品列表"""
    query = db.query(Product).filter(Product.is_active == True)

    if ingredient_id:
        query = query.filter(Product.ingredient_id == ingredient_id)

    if search:
        query = query.filter(Product.name.contains(search))

    products = query.order_by(desc(Product.created_at)).offset(skip).limit(limit).all()
    return products


@router.get("/{product_id}", response_model=ProductWithDetails)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """获取商品详情"""
    product = db.query(Product).filter(Product.id == product_id, Product.is_active == True).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # 构建详细响应
    response = ProductWithDetails(
        **product.__dict__,
        ingredient_name=product.ingredient.name if product.ingredient else None,
        latest_price=None,  # TODO: 从 ProductRecord 获取最新价格
        latest_price_date=None
    )
    return response


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新商品"""
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product_update.dict(exclude_unset=True)

    # 检查条码唯一性
    if 'barcode' in update_data and update_data['barcode']:
        existing = db.query(Product).filter(
            Product.barcode == update_data['barcode'],
            Product.id != product_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Barcode already exists")

    for field, value in update_data.items():
        setattr(db_product, field, value)

    db_product.updated_by = current_user.id
    db.commit()
    db.refresh(db_product)
    return db_product


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """软删除商品"""
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    db_product.is_active = False
    db_product.updated_by = current_user.id
    db.commit()
    return {"message": "Product deleted successfully"}
```

**Step 2: 注册路由**

在 `backend/app/main.py` 中添加:

```python
from app.api.products_entity import router as products_entity_router

app.include_router(products_entity_router, prefix="/api/v1", tags=["products"])
```

**Step 3: 提交**

```bash
git add backend/app/api/products_entity.py backend/app/main.py
git commit -m "feat(api): add Product CRUD endpoints"
```

---

### Task 10: 创建 UserPreference API 路由

**Files:**
- Create: `backend/app/api/user_preferences.py`

**Step 1: 创建 API 路由文件**

创建 `backend/app/api/user_preferences.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.user_ingredient_preference import UserIngredientPreference
from app.schemas.user_preference import UserPreferenceCreate, UserPreferenceUpdate, UserPreferenceResponse

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.post("/", response_model=UserPreferenceResponse)
def set_preference(
    preference: UserPreferenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """设置用户食材偏好"""
    # 检查是否已存在
    existing = db.query(UserIngredientPreference).filter(
        UserIngredientPreference.user_id == current_user.id,
        UserIngredientPreference.ingredient_id == preference.ingredient_id
    ).first()

    if existing:
        # 更新现有偏好
        for field, value in preference.dict().items():
            setattr(existing, field, value)
        existing.updated_by = current_user.id
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # 创建新偏好
        db_preference = UserIngredientPreference(
            **preference.dict(),
            user_id=current_user.id,
            created_by=current_user.id
        )
        db.add(db_preference)
        db.commit()
        db.refresh(db_preference)
        return db_preference


@router.get("/", response_model=List[UserPreferenceResponse])
def list_preferences(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户偏好列表"""
    preferences = db.query(UserIngredientPreference).filter(
        UserIngredientPreference.user_id == current_user.id,
        UserIngredientPreference.is_active == True
    ).offset(skip).limit(limit).all()
    return preferences


@router.get("/{ingredient_id}", response_model=UserPreferenceResponse)
def get_preference(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户对特定食材的偏好"""
    preference = db.query(UserIngredientPreference).filter(
        UserIngredientPreference.user_id == current_user.id,
        UserIngredientPreference.ingredient_id == ingredient_id,
        UserIngredientPreference.is_active == True
    ).first()

    if not preference:
        raise HTTPException(status_code=404, detail="Preference not found")

    return preference


@router.delete("/{ingredient_id}")
def delete_preference(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除用户偏好"""
    preference = db.query(UserIngredientPreference).filter(
        UserIngredientPreference.user_id == current_user.id,
        UserIngredientPreference.ingredient_id == ingredient_id
    ).first()

    if not preference:
        raise HTTPException(status_code=404, detail="Preference not found")

    preference.is_active = False
    preference.updated_by = current_user.id
    db.commit()
    return {"message": "Preference deleted successfully"}
```

**Step 2: 注册路由**

在 `backend/app/main.py` 中添加:

```python
from app.api.user_preferences import router as user_preferences_router

app.include_router(user_preferences_router, prefix="/api/v1", tags=["preferences"])
```

**Step 3: 提交**

```bash
git add backend/app/api/user_preferences.py backend/app/main.py
git commit -m "feat(api): add UserPreference CRUD endpoints"
```

---

### Task 11: 修改现有 ProductRecord API 使用 Product

**Files:**
- Modify: `backend/app/api/products.py`

**Step 1: 修改创建价格记录端点**

在 `backend/app/api/products.py` 中，修改创建端点:

```python
# 找到 POST /api/v1/products/ 端点
# 修改为：

@router.post("/", response_model=ProductRecordResponse)
def create_product_record(
    product_record: ProductRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建商品价格记录"""
    # 验证 product_id
    product = db.query(Product).filter(Product.id == product_record.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # 设置标准单位
    standard_quantity, standard_unit = convert_to_standard_unit(
        product_record.original_quantity,
        product_record.original_unit
    )

    db_record = ProductRecord(
        **product_record.dict(exclude={'standard_quantity', 'standard_unit'}),
        user_id=current_user.id,
        standard_quantity=standard_quantity,
        standard_unit=standard_unit
    )
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record
```

**Step 2: 修改 Schema 添加 product_id**

在 `backend/app/schemas/product.py` 中修改:

```python
class ProductRecordCreate(BaseModel):
    product_id: int  # 改为必填的 product_id
    location_id: Optional[int] = None
    price: float
    currency: str = "CNY"
    original_quantity: float
    original_unit: str
    record_type: str = RecordType.PURCHASE
    exchange_rate: float = 1.0
    notes: Optional[str] = None
```

**Step 3: 提交**

```bash
git add backend/app/api/products.py backend/app/schemas/product.py
git commit -m "refactor(api): use product_id in ProductRecord instead of direct ingredient"
```

---

### Task 12: 创建 Recipe Schema 更新

**Files:**
- Modify: `backend/app/schemas/recipe.py`

**Step 1: 添加 result_ingredient_id 字段**

在 `backend/app/schemas/recipe.py` 的 `RecipeBase` 和相关 Schema 中添加:

```python
class RecipeBase(BaseModel):
    # ... 现有字段 ...
    result_ingredient_id: Optional[int] = None  # 新增


class RecipeCreate(RecipeBase):
    # ... 保持不变 ...


class RecipeUpdate(BaseModel):
    # ... 现有字段 ...
    result_ingredient_id: Optional[int] = None  # 新增
```

**Step 2: 提交**

```bash
git add backend/app/schemas/recipe.py
git commit -m "feat(schemas): add result_ingredient_id to Recipe schemas"
```

---

## 阶段 3: 前端页面

### Task 13: 创建 Product API 客户端

**Files:**
- Modify: `frontend/src/api/client.ts`

**Step 1: 添加商品 API 方法**

在 `frontend/src/api/client.ts` 中添加:

```typescript
// Product Entity APIs
export const productAPI = {
  // 创建商品
  create: async (data: ProductCreate) => {
    return api.post('/products/entity', data)
  },

  // 获取商品列表
  list: async (params?: {
    skip?: number
    limit?: number
    ingredient_id?: number
    search?: string
  }) => {
    return api.get('/products/entity', { params })
  },

  // 获取商品详情
  get: async (id: number) => {
    return api.get(`/products/entity/${id}`)
  },

  // 更新商品
  update: async (id: number, data: ProductUpdate) => {
    return api.put(`/products/entity/${id}`, data)
  },

  // 删除商品
  delete: async (id: number) => {
    return api.delete(`/products/entity/${id}`)
  }
}

// User Preference APIs
export const preferenceAPI = {
  // 设置偏好
  set: async (data: UserPreferenceCreate) => {
    return api.post('/preferences', data)
  },

  // 获取偏好列表
  list: async (params?: { skip?: number; limit?: number }) => {
    return api.get('/preferences', { params })
  },

  // 获取特定食材的偏好
  get: async (ingredientId: number) => {
    return api.get(`/preferences/${ingredientId}`)
  },

  // 删除偏好
  delete: async (ingredientId: number) => {
    return api.delete(`/preferences/${ingredientId}`)
  }
}
```

**Step 2: 添加 TypeScript 类型**

在 `frontend/src/api/client.ts` 中添加类型定义:

```typescript
// Product Types
export interface ProductCreate {
  name: string
  brand?: string
  barcode?: string
  image_url?: string
  ingredient_id: number
  tags?: string[]
}

export interface ProductUpdate {
  name?: string
  brand?: string
  barcode?: string
  image_url?: string
  ingredient_id?: number
  tags?: string[]
}

export interface ProductResponse {
  id: number
  name: string
  brand?: string
  barcode?: string
  image_url?: string
  ingredient_id: number
  tags?: string[]
  created_at: string
  updated_at?: string
  is_active: boolean
}

export interface ProductWithDetails extends ProductResponse {
  ingredient_name?: string
  latest_price?: number
  latest_price_date?: string
}

// User Preference Types
export interface UserPreferenceCreate {
  ingredient_id: number
  default_product_id?: number
  default_recipe_id?: number
  preference_type?: 'product' | 'recipe'
  is_favorite?: boolean
}

export interface UserPreferenceResponse {
  id: number
  user_id: number
  ingredient_id: number
  default_product_id?: number
  default_recipe_id?: number
  preference_type: string
  is_favorite: boolean
  created_at: string
  updated_at?: string
  is_active: boolean
}
```

**Step 3: 提交**

```bash
git add frontend/src/api/client.ts
git commit -m "feat(api): add Product and UserPreference API client methods"
```

---

### Task 14: 创建商品管理页面

**Files:**
- Create: `frontend/src/views/products/ProductManage.vue`

**Step 1: 创建商品管理页面**

创建 `frontend/src/views/products/ProductManage.vue`:

```vue
<template>
  <div class="product-manage">
    <PageHeader title="商品管理" :show-back="true">
      <template #extra>
        <button @click="showAddModal = true" class="btn-square add-btn" title="添加商品">
          <i class="mdi mdi-plus"></i>
        </button>
      </template>
    </PageHeader>

    <!-- 搜索和筛选 -->
    <div class="search-filter">
      <div class="search-box">
        <input
          v-model="searchTerm"
          placeholder="搜索商品名称、品牌、条码..."
          class="search-input"
          @input="debounceSearch"
        />
      </div>
      <button @click="loadProducts" class="btn-search">
        <i class="mdi mdi-magnify"></i> 搜索
      </button>
    </div>

    <!-- 商品列表 -->
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="products.length === 0" class="empty-state">
      <p>暂无商品数据</p>
      <button @click="showAddModal = true" class="btn-primary">添加商品</button>
    </div>
    <div v-else class="product-grid">
      <div
        v-for="product in products"
        :key="product.id"
        class="product-card"
        @click="viewProduct(product)"
      >
        <div class="product-image">
          <img
            v-if="product.image_url"
            :src="product.image_url"
            :alt="product.name"
          />
          <div v-else class="placeholder-image">
            <i class="mdi mdi-package-variant"></i>
          </div>
        </div>
        <h3>{{ product.name }}</h3>
        <div class="product-info">
          <p v-if="product.brand">
            <i class="mdi mdi-tag"></i> {{ product.brand }}
          </p>
          <p v-if="product.ingredient_name">
            <i class="mdi mdi-grain"></i> {{ product.ingredient_name }}
          </p>
          <p v-if="product.barcode">
            <i class="mdi mdi-barcode"></i> {{ product.barcode }}
          </p>
          <p v-if="product.tags && product.tags.length > 0">
            <span
              v-for="tag in product.tags"
              :key="tag"
              class="tag"
            >
              {{ tag }}
            </span>
          </p>
        </div>
        <div class="product-actions">
          <button
            @click.stop="editProduct(product)"
            class="btn-edit"
            title="编辑"
          >
            <i class="mdi mdi-pencil"></i>
          </button>
          <button
            @click.stop="addPriceRecord(product)"
            class="btn-add-price"
            title="添加价格记录"
          >
            <i class="mdi mdi-currency-cny"></i>
          </button>
          <button
            @click.stop="deleteProduct(product)"
            class="btn-delete"
            title="删除"
          >
            <i class="mdi mdi-delete"></i>
          </button>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <Pagination
      v-if="total > 0"
      :current-page="currentPage"
      :page-size="pageSize"
      :total="total"
      @change-page="handlePageChange"
      @change-page-size="handlePageSizeChange"
    />

    <!-- 添加/编辑商品模态框 -->
    <ProductModal
      v-if="showModal"
      :product="editingProduct"
      :show="showModal"
      @close="closeModal"
      @save="handleSaveProduct"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { productAPI, type ProductResponse, type ProductCreate } from '@/api/client'
import PageHeader from '@/components/PageHeader.vue'
import Pagination from '@/components/Pagination.vue'
import ProductModal from '@/components/ProductModal.vue'

const products = ref<ProductResponse[]>([])
const loading = ref(false)
const showModal = ref(false)
const editingProduct = ref<ProductResponse | null>(null)
const searchTerm = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

let searchTimeout: ReturnType<typeof setTimeout> | null = null

onMounted(() => {
  loadProducts()
})

async function loadProducts() {
  loading.value = true
  try {
    const response = await productAPI.list({
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
      search: searchTerm.value || undefined
    })
    products.value = response
    total.value = response.length // TODO: 需要后端支持返回总数
  } catch (error) {
    console.error('Failed to load products:', error)
  } finally {
    loading.value = false
  }
}

function debounceSearch() {
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    loadProducts()
  }, 300)
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadProducts()
}

function handlePageSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  loadProducts()
}

function viewProduct(product: ProductResponse) {
  // TODO: 跳转到商品详情页
  console.log('View product:', product)
}

function editProduct(product: ProductResponse) {
  editingProduct.value = product
  showModal.value = true
}

function addPriceRecord(product: ProductResponse) {
  // TODO: 打开添加价格记录模态框
  console.log('Add price record for product:', product)
}

async function deleteProduct(product: ProductResponse) {
  if (confirm(`确定要删除商品 "${product.name}" 吗？`)) {
    try {
      await productAPI.delete(product.id)
      await loadProducts()
    } catch (error) {
      console.error('Failed to delete product:', error)
      alert('删除失败')
    }
  }
}

async function handleSaveProduct(data: ProductCreate | ProductResponse) {
  try {
    if (editingProduct.value) {
      await productAPI.update(editingProduct.value.id, data as any)
    } else {
      await productAPI.create(data as ProductCreate)
    }
    closeModal()
    await loadProducts()
  } catch (error) {
    console.error('Failed to save product:', error)
    alert('保存失败')
  }
}

function closeModal() {
  showModal.value = false
  editingProduct.value = null
}
</script>

<style scoped>
/* 添加页面样式... */
</style>
```

**Step 2: 提交**

```bash
git add frontend/src/views/products/ProductManage.vue
git commit -m "feat(frontend): add product management page"
```

---

### Task 15: 创建 ProductModal 组件

**Files:**
- Create: `frontend/src/components/ProductModal.vue`

**Step 1: 创建商品模态框组件**

创建 `frontend/src/components/ProductModal.vue`:

```vue
<template>
  <div class="modal-overlay" @click="$emit('close')">
    <div class="modal-content" @click.stop>
      <h2>{{ product ? '编辑商品' : '添加商品' }}</h2>
      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label for="productName">商品名称 *</label>
          <input
            v-model="formData.name"
            type="text"
            id="productName"
            required
          />
        </div>
        <div class="form-group">
          <label for="productBrand">品牌</label>
          <input
            v-model="formData.brand"
            type="text"
            id="productBrand"
          />
        </div>
        <div class="form-group">
          <label for="productBarcode">条码</label>
          <input
            v-model="formData.barcode"
            type="text"
            id="productBarcode"
          />
        </div>
        <div class="form-group">
          <label for="productImage">图片URL</label>
          <input
            v-model="formData.image_url"
            type="text"
            id="productImage"
          />
        </div>
        <div class="form-group">
          <label for="productIngredient">关联食材 *</label>
          <select
            v-model="formData.ingredient_id"
            id="productIngredient"
            required
          >
            <option value="">请选择食材</option>
            <option
              v-for="ingredient in ingredients"
              :key="ingredient.id"
              :value="ingredient.id"
            >
              {{ ingredient.name }}
            </option>
          </select>
        </div>
        <div class="form-group">
          <label for="productTags">标签（用逗号分隔）</label>
          <input
            v-model="tagsText"
            type="text"
            id="productTags"
            placeholder="例如: 有机, 进口, 促销"
          />
        </div>
        <div class="form-actions">
          <button type="button" @click="$emit('close')" class="btn-secondary">取消</button>
          <button type="submit" class="btn-primary">{{ product ? '更新' : '添加' }}</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/api/client'
import type { ProductCreate, ProductResponse } from '@/api/client'

const props = defineProps<{
  product?: ProductResponse | null
  show: boolean
}>()

const emit = defineEmits(['close', 'save'])

const formData = ref<ProductCreate>({
  name: '',
  brand: '',
  barcode: '',
  image_url: '',
  ingredient_id: 0,
  tags: []
})

const tagsText = ref('')
const ingredients = ref<any[]>([])

onMounted(async () => {
  await loadIngredients()
  if (props.product) {
    formData.value = {
      name: props.product.name,
      brand: props.product.brand || '',
      barcode: props.product.barcode || '',
      image_url: props.product.image_url || '',
      ingredient_id: props.product.ingredient_id,
      tags: props.product.tags || []
    }
    tagsText.value = (formData.value.tags || []).join(', ')
  }
})

async function loadIngredients() {
  try {
    const response = await api.get('/ingredients')
    ingredients.value = response
  } catch (error) {
    console.error('Failed to load ingredients:', error)
  }
}

function handleSubmit() {
  // 解析标签
  if (tagsText.value) {
    formData.value.tags = tagsText.value.split(',').map(t => t.trim()).filter(t => t)
  } else {
    formData.value.tags = []
  }

  emit('save', formData.value)
}
</script>

<style scoped>
/* 添加模态框样式... */
</style>
```

**Step 2: 提交**

```bash
git add frontend/src/components/ProductModal.vue
git commit -m "feat(components): add ProductModal component"
```

---

### Task 16: 重构价格记录页面

**Files:**
- Modify: `frontend/src/views/products/ProductList.vue`

**Step 1: 修改价格记录页面**

将 `frontend/src/views/products/ProductList.vue` 修改为使用商品而非食材:

```vue
<!-- 主要修改：将原料选择器改为商品选择器 -->
<div class="form-group">
  <label for="productName">商品:</label>
  <div class="autocomplete-container">
    <input
      v-model="newProduct.product_name"
      type="text"
      id="productName"
      required
      @input="onProductInput"
      @focus="showProductSuggestions = true"
    />
    <ul v-if="showProductSuggestions && productSuggestions.length > 0" class="suggestions-list">
      <li
        v-for="(suggestion, index) in productSuggestions"
        :key="suggestion.id"
        @click="selectProduct(suggestion)"
      >
        {{ suggestion.name }}
        <span v-if="suggestion.brand" class="brand">({{ suggestion.brand }})</span>
      </li>
    </ul>
  </div>
</div>
```

```typescript
// 修改 TypeScript 代码
const newProduct = ref({
  product_id: 0,  // 改为 product_id
  price: 0,
  quantity: 1,
  unit: ''
})

const productSuggestions = ref<ProductResponse[]>([])
const showProductSuggestions = ref(false)

async function loadProducts() {
  try {
    const response = await productAPI.list({ limit: 100 })
    productSuggestions.value = response
  } catch (error) {
    console.error('Failed to load products:', error)
  }
}

function selectProduct(product: ProductResponse) {
  newProduct.value.product_id = product.id
  showProductSuggestions.value = false
}
```

**Step 2: 提交**

```bash
git add frontend/src/views/products/ProductList.vue
git commit -m "refactor(frontend): use Product instead of Ingredient in price records"
```

---

### Task 17: 增强食材管理页面

**Files:**
- Modify: `frontend/src/views/products/IngredientList.vue`

**Step 1: 添加关联商品展示**

在食材卡片中添加关联商品部分:

```vue
<div class="ingredient-card">
  <!-- ... 现有内容 ... -->

  <!-- 新增：关联商品 -->
  <div class="related-products" v-if="ingredient.related_products">
    <h4>关联商品 ({{ ingredient.related_products.length }})</h4>
    <div class="product-list">
      <div
        v-for="product in ingredient.related_products"
        :key="product.id"
        class="product-item"
      >
        {{ product.name }}
        <span v-if="product.brand">({{ product.brand }})</span>
      </div>
    </div>
  </div>
</div>
```

**Step 2: 添加设置偏好功能**

```typescript
async function setPreference(ingredient: Ingredient, product?: ProductResponse) {
  try {
    await preferenceAPI.set({
      ingredient_id: ingredient.id,
      default_product_id: product?.id,
      preference_type: 'product'
    })
    alert('偏好设置成功')
  } catch (error) {
    console.error('Failed to set preference:', error)
    alert('设置失败')
  }
}
```

**Step 3: 提交**

```bash
git add frontend/src/views/products/IngredientList.vue
git commit -m "feat(frontend): add related products and preference settings to ingredient page"
```

---

### Task 18: 更新路由配置

**Files:**
- Modify: `frontend/src/router/index.ts`

**Step 1: 添加新路由**

在路由配置中添加:

```typescript
{
  path: '/products/manage',
  name: 'ProductManage',
  component: () => import('@/views/products/ProductManage.vue'),
  meta: { requiresAuth: true }
},
{
  path: '/prices/records',
  name: 'PriceRecords',
  component: () => import('@/views/products/ProductList.vue'),
  meta: { requiresAuth: true }
}
```

**Step 2: 更新导航菜单**

在主导航组件中更新菜单项。

**Step 3: 提交**

```bash
git add frontend/src/router/index.ts
git commit -m "feat(router): add product management and price records routes"
```

---

## 阶段 4: 智能功能

### Task 19: 实现食谱成品自动匹配

**Files:**
- Create: `backend/app/services/recipe_matching.py`

**Step 1: 创建匹配服务**

创建 `backend/app/services/recipe_matching.py`:

```python
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from thefuzz import fuzz
from app.models.ingredient import Ingredient
from app.models.recipe import Recipe
import re


class RecipeMatchingService:
    """食谱成品自动匹配服务"""

    # 需要去除的前缀和后缀
    PREFIXES = ['自制', '家庭', '家常', '妈妈', '奶奶', '手工', '做法']
    SUFFIXES = ['做法', '制作', '秘方', '教程']

    @staticmethod
    def extract_candidates(recipe_name: str) -> List[str]:
        """从食谱名称提取候选名称"""
        candidates = [recipe_name]

        # 去除前缀
        cleaned = recipe_name
        for prefix in RecipeMatchingService.PREFIXES:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
                candidates.append(cleaned)

        # 去除后缀
        cleaned = cleaned
        for suffix in RecipeMatchingService.SUFFIXES:
            if cleaned.endswith(suffix):
                cleaned = cleaned[:-len(suffix)]
                candidates.append(cleaned)

        return candidates

    @staticmethod
    def match_ingredients(
        db: Session,
        candidates: List[str],
        threshold: int = 70
    ) -> List[Dict]:
        """匹配食材，返回按相似度排序的列表"""
        all_ingredients = db.query(Ingredient).filter(Ingredient.is_active == True).all()
        results = []

        for ingredient in all_ingredients:
            # 检查名称
            for candidate in candidates:
                name_similarity = fuzz.ratio(candidate, ingredient.name)

                if name_similarity >= threshold:
                    results.append({
                        'ingredient_id': ingredient.id,
                        'ingredient_name': ingredient.name,
                        'similarity': name_similarity,
                        'match_type': 'name'
                    })

                # 检查别名
                if ingredient.aliases:
                    for alias in ingredient.aliases:
                        alias_similarity = fuzz.ratio(candidate, alias)

                        if alias_similarity >= threshold:
                            results.append({
                                'ingredient_id': ingredient.id,
                                'ingredient_name': ingredient.name,
                                'similarity': alias_similarity,
                                'match_type': 'alias'
                            })

        # 去重并按相似度排序
        unique_results = {}
        for result in results:
            key = result['ingredient_id']
            if key not in unique_results or result['similarity'] > unique_results[key]['similarity']:
                unique_results[key] = result

        sorted_results = sorted(unique_results.values(), key=lambda x: -x['similarity'])

        return sorted_results

    @staticmethod
    def calculate_confidence(match_result: Dict) -> float:
        """计算匹配置信度"""
        similarity = match_result['similarity']
        match_type = match_result['match_type']

        if match_type == 'name':
            # 名称匹配权重更高
            confidence = (similarity * 0.6) / 100
        else:
            # 别名匹配权重较低
            confidence = (similarity * 0.4) / 100

        return round(confidence, 2)

    @staticmethod
    def suggest_ingredient_for_recipe(
        db: Session,
        recipe_name: str,
        threshold: int = 70
    ) -> Optional[Dict]:
        """为食谱建议食材"""
        candidates = RecipeMatchingService.extract_candidates(recipe_name)
        matches = RecipeMatchingService.match_ingredients(db, candidates, threshold)

        if not matches:
            return None

        # 返回最佳匹配
        best_match = matches[0]
        best_match['confidence'] = RecipeMatchingService.calculate_confidence(best_match)

        return best_match
```

**Step 2: 提交**

```bash
git add backend/app/services/recipe_matching.py
git commit -m "feat(service): add recipe ingredient matching service"
```

---

### Task 20: 添加自动匹配 API 端点

**Files:**
- Create: `backend/app/api/recipe_matching.py`

**Step 1: 创建匹配 API 端点**

创建 `backend/app/api/recipe_matching.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.recipe_matching import RecipeMatchingService

router = APIRouter(prefix="/recipe-matching", tags=["recipe-matching"])


class IngredientSuggestionResponse(BaseModel):
    ingredient_id: int
    ingredient_name: str
    similarity: int
    match_type: str
    confidence: float


@router.post("/suggest", response_model=IngredientSuggestionResponse)
def suggest_ingredient(
    recipe_name: str = Query(..., min_length=1),
    threshold: int = Query(70, ge=0, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """为食谱名称建议食材"""
    suggestion = RecipeMatchingService.suggest_ingredient_for_recipe(db, recipe_name, threshold)

    if not suggestion:
        raise HTTPException(status_code=404, detail="No matching ingredient found")

    return suggestion


@router.post("/candidates", response_model=List[IngredientSuggestionResponse])
def get_candidates(
    recipe_name: str = Query(..., min_length=1),
    threshold: int = Query(70, ge=0, le=100),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取多个候选食材"""
    candidates = RecipeMatchingService.extract_candidates(recipe_name)
    matches = RecipeMatchingService.match_ingredients(db, candidates, threshold)

    # 限制返回数量并计算置信度
    for match in matches[:limit]:
        match['confidence'] = RecipeMatchingService.calculate_confidence(match)

    return matches[:limit]
```

**Step 2: 注册路由**

在 `backend/app/main.py` 中添加:

```python
from app.api.recipe_matching import router as recipe_matching_router

app.include_router(recipe_matching_router, prefix="/api/v1", tags=["recipe-matching"])
```

**Step 3: 提交**

```bash
git add backend/app/api/recipe_matching.py backend/app/main.py
git commit -m "feat(api): add recipe ingredient matching endpoints"
```

---

### Task 21: 实现成本计算智能选择

**Files:**
- Create: `backend/app/services/cost_calculation.py`

**Step 1: 创建成本计算服务**

创建 `backend/app/services/cost_calculation.py`:

```python
from typing import Dict, Tuple, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from datetime import datetime, timedelta
from app.models.user_ingredient_preference import UserIngredientPreference
from app.models.product_entity import Product
from app.models.product_record import ProductRecord, RecordType
from app.models.recipe import Recipe


class CostCalculationService:
    """成本计算智能选择服务"""

    @staticmethod
    def get_default_cost_source(
        db: Session,
        user_id: int,
        ingredient_id: int
    ) -> Optional[Tuple[str, int, float]]:
        """
        获取默认成本来源
        返回: (source_type, id, cost)
        source_type: 'product' | 'recipe'
        """
        # 1. 查找用户偏好
        preference = db.query(UserIngredientPreference).filter(
            and_(
                UserIngredientPreference.user_id == user_id,
                UserIngredientPreference.ingredient_id == ingredient_id,
                UserIngredientPreference.is_active == True
            )
        ).first()

        if preference:
            if preference.preference_type == 'product' and preference.default_product_id:
                # 使用用户偏好的商品
                cost = CostCalculationService.get_product_cost(db, preference.default_product_id)
                if cost:
                    return ('product', preference.default_product_id, cost)
            elif preference.preference_type == 'recipe' and preference.default_recipe_id:
                # 使用用户偏好的食谱
                cost = CostCalculationService.get_recipe_cost(db, preference.default_recipe_id)
                if cost:
                    return ('recipe', preference.default_recipe_id, cost)

        # 2. 无偏好，使用默认策略
        # 优先查找商品
        product_cost = CostCalculationService.get_best_product_cost(db, user_id, ingredient_id)
        if product_cost:
            return product_cost

        # 备选查找食谱
        recipe_cost = CostCalculationService.get_best_recipe_cost(db, ingredient_id)
        if recipe_cost:
            return recipe_cost

        return None

    @staticmethod
    def get_product_cost(db: Session, product_id: int) -> Optional[float]:
        """获取商品成本（最新价格）"""
        record = db.query(ProductRecord).filter(
            and_(
                ProductRecord.product_id == product_id,
                ProductRecord.is_active == True
            )
        ).order_by(desc(ProductRecord.recorded_at)).first()

        return record.price if record else None

    @staticmethod
    def get_recipe_cost(db: Session, recipe_id: int) -> Optional[float]:
        """
        获取食谱成本（递归计算）
        注意：需要避免循环依赖
        """
        # TODO: 实现递归计算食谱成本
        # 需要传递已访问的食谱 ID 列表以避免循环
        return None

    @staticmethod
    def get_best_product_cost(
        db: Session,
        user_id: int,
        ingredient_id: int
    ) -> Optional[Tuple[str, int, float]]:
        """获取最佳商品成本（按优先级排序）"""
        # 查找该食材的所有商品
        products = db.query(Product).filter(
            and_(
                Product.ingredient_id == ingredient_id,
                Product.is_active == True
            )
        ).all()

        if not products:
            return None

        best_product = None
        best_score = -1

        for product in products:
            score = CostCalculationService.calculate_product_score(db, user_id, product.id)
            if score > best_score:
                best_score = score
                best_product = product

        if best_product:
            cost = CostCalculationService.get_product_cost(db, best_product.id)
            if cost:
                return ('product', best_product.id, cost)

        return None

    @staticmethod
    def calculate_product_score(db: Session, user_id: int, product_id: int) -> float:
        """
        计算商品得分（用于排序）
        评分标准：
        - 用户标记常用: +100
        - 最近购买（30天内）: +50
        - 价格越低分越高
        - 最近更新: +20
        """
        score = 0.0

        # 获取最新价格记录
        record = db.query(ProductRecord).filter(
            and_(
                ProductRecord.product_id == product_id,
                ProductRecord.user_id == user_id,
                ProductRecord.is_active == True
            )
        ).order_by(desc(ProductRecord.recorded_at)).first()

        if record:
            # 最近购买（30天内）
            if record.recorded_at >= datetime.now() - timedelta(days=30):
                score += 50

            # 最近更新
            if record.recorded_at >= datetime.now() - timedelta(days=7):
                score += 20

            # 价格（价格越低分越高，归一化处理）
            # 假设合理价格范围 0-1000元
            normalized_price = max(0, 1000 - record.price) / 1000 * 30
            score += normalized_price

        return score

    @staticmethod
    def get_best_recipe_cost(
        db: Session,
        ingredient_id: int
    ) -> Optional[Tuple[str, int, float]]:
        """获取最佳食谱成本"""
        # 查找以该食材为成品的食谱
        recipes = db.query(Recipe).filter(
            and_(
                Recipe.result_ingredient_id == ingredient_id,
                Recipe.is_active == True
            )
        ).all()

        if not recipes:
            return None

        # 简单返回第一个（TODO: 可以添加更复杂的评分逻辑）
        for recipe in recipes:
            cost = CostCalculationService.get_recipe_cost(db, recipe.id)
            if cost:
                return ('recipe', recipe.id, cost)

        return None

    @staticmethod
    def get_all_cost_options(
        db: Session,
        user_id: int,
        ingredient_id: int
    ) -> List[Dict]:
        """
        获取所有成本选项（用于展示）
        返回: [
            {type: 'product', id: 1, name: '某品牌薯条', cost: 8.5, source: '购买'},
            {type: 'recipe', id: 5, name: '自制薯条', cost: 5.2, source: '自制'}
        ]
        """
        options = []

        # 获取所有商品选项
        products = db.query(Product).filter(
            and_(
                Product.ingredient_id == ingredient_id,
                Product.is_active == True
            )
        ).all()

        for product in products:
            cost = CostCalculationService.get_product_cost(db, product.id)
            if cost:
                options.append({
                    'type': 'product',
                    'id': product.id,
                    'name': product.name,
                    'cost': cost,
                    'source': '购买'
                })

        # 获取所有食谱选项
        recipes = db.query(Recipe).filter(
            and_(
                Recipe.result_ingredient_id == ingredient_id,
                Recipe.is_active == True
            )
        ).all()

        for recipe in recipes:
            cost = CostCalculationService.get_recipe_cost(db, recipe.id)
            if cost:
                options.append({
                    'type': 'recipe',
                    'id': recipe.id,
                    'name': recipe.name,
                    'cost': cost,
                    'source': '自制'
                })

        # 按成本排序
        options.sort(key=lambda x: x['cost'])

        return options
```

**Step 2: 提交**

```bash
git add backend/app/services/cost_calculation.py
git commit -m "feat(service): add cost calculation service"
```

---

### Task 22: 添加成本计算 API 端点

**Files:**
- Create: `backend/app/api/cost_calculation.py`

**Step 1: 创建成本计算 API 端点**

创建 `backend/app/api/cost_calculation.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.cost_calculation import CostCalculationService

router = APIRouter(prefix="/cost-calculation", tags=["cost-calculation"])


@router.get("/default-source/{ingredient_id}")
def get_default_cost_source(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取食材的默认成本来源"""
    source = CostCalculationService.get_default_cost_source(db, current_user.id, ingredient_id)

    if not source:
        return {"message": "No cost source found"}

    return {
        "source_type": source[0],
        "source_id": source[1],
        "cost": source[2]
    }


@router.get("/options/{ingredient_id}")
def get_cost_options(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取食材的所有成本选项"""
    options = CostCalculationService.get_all_cost_options(db, current_user.id, ingredient_id)

    return {
        "ingredient_id": ingredient_id,
        "options": options
    }
```

**Step 2: 注册路由**

在 `backend/app/main.py` 中添加:

```python
from app.api.cost_calculation import router as cost_calculation_router

app.include_router(cost_calculation_router, prefix="/api/v1", tags=["cost-calculation"])
```

**Step 3: 提交**

```bash
git add backend/app/api/cost_calculation.py backend/app/main.py
git commit -m "feat(api): add cost calculation endpoints"
```

---

### Task 23: 前端集成智能匹配功能

**Files:**
- Modify: `frontend/src/views/recipes/RecipeForm.vue`

**Step 1: 添加食谱成品自动匹配**

在食谱表单中添加自动匹配功能:

```typescript
import { ref, watch } from 'vue'
import { api } from '@/api/client'

// 监听食谱名称变化
watch(() => formData.value.name, async (newName) => {
  if (newName && newName.length > 2) {
    await fetchIngredientSuggestions(newName)
  }
})

async function fetchIngredientSuggestions(recipeName: string) {
  try {
    const response = await api.post('/recipe-matching/suggest', null, {
      params: { recipe_name: recipeName }
    })

    if (response.confidence > 0.8) {
      // 高置信度，自动选中
      formData.value.result_ingredient_id = response.ingredient_id
      showMatchSuggestion.value = false
    } else if (response.confidence > 0.5) {
      // 中等置信度，提示确认
      suggestedIngredient.value = response
      showMatchSuggestion.value = true
    }
  } catch (error) {
    // 无匹配或错误，忽略
  }
}
```

**Step 2: 提交**

```bash
git add frontend/src/views/recipes/RecipeForm.vue
git commit -m "feat(frontend): add automatic ingredient matching for recipe results"
```

---

### Task 24: 前端集成成本计算功能

**Files:**
- Modify: `frontend/src/views/recipes/RecipeDetail.vue`

**Step 1: 添加成本选项展示**

在菜谱详情页面展示成本选项:

```vue
<template>
  <div class="recipe-cost">
    <h3>原料成本</h3>
    <div v-for="ingredient in recipe.ingredients" :key="ingredient.id" class="ingredient-cost">
      <h4>{{ ingredient.name }}</h4>

      <!-- 成本选项 -->
      <div class="cost-options" v-if="costOptions[ingredient.id]">
        <div
          v-for="option in costOptions[ingredient.id]"
          :key="`${option.type}-${option.id}`"
          class="cost-option"
          :class="{ active: selectedOption[ingredient.id] === option.id }"
          @click="selectCostOption(ingredient.id, option)"
        >
          <span class="source">{{ option.source }}</span>
          <span class="name">{{ option.name }}</span>
          <span class="cost">¥{{ option.cost.toFixed(2) }}</span>
        </div>
      </div>
    </div>

    <div class="total-cost">
      总成本: ¥{{ totalCost.toFixed(2) }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '@/api/client'

const costOptions = ref<Record<number, CostOption[]>>({})
const selectedOption = ref<Record<number, number>>({})

async function loadCostOptions(ingredientId: number) {
  try {
    const response = await api.get(`/cost-calculation/options/${ingredientId}`)
    costOptions.value[ingredientId] = response.options

    // 自动选择第一个
    if (response.options.length > 0) {
      selectedOption.value[ingredientId] = `${response.options[0].type}-${response.options[0].id}`
    }
  } catch (error) {
    console.error('Failed to load cost options:', error)
  }
}

const totalCost = computed(() => {
  let total = 0
  for (const [ingredientId, options] of Object.entries(costOptions.value)) {
    const selected = selectedOption.value[ingredientId]
    if (selected) {
      const option = options.find((opt: any) => `${opt.type}-${opt.id}` === selected)
      if (option) {
        total += option.cost
      }
    }
  }
  return total
})

function selectCostOption(ingredientId: number, option: any) {
  selectedOption.value[ingredientId] = `${option.type}-${option.id}`
}
</script>
```

**Step 2: 提交**

```bash
git add frontend/src/views/recipes/RecipeDetail.vue
git commit -m "feat(frontend): add cost calculation with multiple options display"
```

---

## 阶段 5: 测试和文档

### Task 25: 编写后端测试

**Files:**
- Create: `backend/tests/test_product_entity.py`
- Create: `backend/tests/test_user_preference.py`
- Create: `backend/tests/test_recipe_matching.py`
- Create: `backend/tests/test_cost_calculation.py`

**Step 1: 编写 Product 模型测试**

创建 `backend/tests/test_product_entity.py`:

```python
import pytest
from sqlalchemy.orm import Session
from app.models.product_entity import Product
from app.models.nutrition import Ingredient
from app.schemas.product_entity import ProductCreate


def test_create_product(db: Session, test_user):
    """测试创建商品"""
    # 先创建测试食材
    ingredient = Ingredient(name="测试食材")
    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)

    # 创建商品
    product = Product(
        name="测试商品",
        brand="测试品牌",
        barcode="123456789",
        ingredient_id=ingredient.id,
        created_by=test_user.id
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    assert product.id is not None
    assert product.name == "测试商品"
    assert product.brand == "测试品牌"
    assert product.barcode == "123456789"
    assert product.ingredient_id == ingredient.id


def test_product_barcode_unique(db: Session, test_user):
    """测试条码唯一性"""
    ingredient = Ingredient(name="测试食材2")
    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)

    # 创建第一个商品
    product1 = Product(
        name="商品1",
        barcode="999",
        ingredient_id=ingredient.id,
        created_by=test_user.id
    )
    db.add(product1)
    db.commit()

    # 创建第二个商品，条码相同
    product2 = Product(
        name="商品2",
        barcode="999",  # 相同条码
        ingredient_id=ingredient.id,
        created_by=test_user.id
    )
    db.add(product2)

    with pytest.raises(Exception):  # 应该抛出数据库异常
        db.commit()


def test_product_soft_delete(db: Session, test_user):
    """测试商品软删除"""
    ingredient = Ingredient(name="测试食材3")
    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)

    product = Product(
        name="测试商品3",
        ingredient_id=ingredient.id,
        created_by=test_user.id
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    # 软删除
    product.is_active = False
    db.commit()

    # 验证已删除
    assert not product.is_active
```

**Step 2: 编写其他测试文件**

类似地创建其他测试文件。

**Step 3: 提交**

```bash
git add backend/tests/
git commit -m "test: add backend tests for new features"
```

---

### Task 26: 编写前端测试

**Files:**
- Create: `frontend/tests/components/ProductModal.spec.ts`
- Create: `frontend/tests/views/ProductManage.spec.ts`

**Step 1: 编写组件测试**

```typescript
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ProductModal from '@/components/ProductModal.vue'
import { api } from '@/api/client'

describe('ProductModal', () => {
  it('renders correctly', () => {
    const wrapper = mount(ProductModal, {
      props: {
        product: null,
        show: true
      }
    })
    expect(wrapper.find('.modal-overlay').exists()).toBe(true)
  })

  it('emits save event with correct data', async () => {
    const wrapper = mount(ProductModal, {
      props: {
        product: null,
        show: true
      }
    })

    // 设置表单数据
    await wrapper.setData({
      formData: {
        name: '测试商品',
        ingredient_id: 1
      }
    })

    // 提交表单
    await wrapper.find('form').trigger('submit')

    // 验证事件
    expect(wrapper.emitted('save')).toBeTruthy()
    expect(wrapper.emitted('save')?.[0][0]).toEqual({
      name: '测试商品',
      ingredient_id: 1
    })
  })
})
```

**Step 2: 提交**

```bash
git add frontend/tests/
git commit -m "test: add frontend component tests"
```

---

### Task 27: 更新项目文档

**Files:**
- Modify: `CLAUDE.md`
- Modify: `backend/CLAUDE.md`
- Modify: `frontend/CLAUDE.md`
- Create: `docs/plans/2026-03-05-data-structure-refactor-summary.md`

**Step 1: 更新主 CLAUDE.md**

在 `/home/ding/code/live_calc/CLAUDE.md` 中添加:

```markdown
## 数据模型

### 核心实体
- **Product (商品)** - 可在商店购买的具体商品，关联食材
- **Ingredient (食材)** - 原料材料，可关联多个商品
- **Recipe (菜谱)** - 烹饪配方，可以以食材为成品
- **UserIngredientPreference (用户偏好)** - 用户对食材的默认选择偏好

### 关系说明
- Product → Ingredient: 一对一（一个商品对应一个食材）
- Ingredient → Product: 一对多（一个食材可对应多个商品）
- Recipe → Ingredient: 一对多（食谱中使用的食材）
- Recipe.result_ingredient_id → Ingredient: 一对一（食谱的成品食材）
```

**Step 2: 更新后端 CLAUDE.md**

添加新 API 端点说明。

**Step 3: 更新前端 CLAUDE.md**

添加新页面和组件说明。

**Step 4: 创建总结文档**

创建实施总结文档。

**Step 5: 提交**

```bash
git add CLAUDE.md backend/CLAUDE.md frontend/CLAUDE.md docs/plans/
git commit -m "docs: update project documentation after refactor"
```

---

## Task 28: 最终验证和清理

**Files:**
- None

**Step 1: 运行所有测试**

```bash
cd backend && pytest tests/ -v
cd frontend && npm test
```

**Step 2: 启动开发服务器验证**

```bash
cd backend && python -m uvicorn app.main:app --reload
cd frontend && npm run dev
```

**Step 3: 手动测试关键功能**

- 创建商品
- 添加价格记录
- 设置用户偏好
- 创建食谱（自动匹配）
- 查看成本计算

**Step 4: 代码审查**

检查代码是否符合项目规范。

**Step 5: 最终提交**

```bash
git add .
git commit -m "chore: final cleanup and verification"
```

---

## 附录: 实施检查清单

### 阶段 1: 后端数据模型
- [ ] Task 1: 创建 Product 模型
- [ ] Task 2: 创建 UserIngredientPreference 模型
- [ ] Task 3: 修改 Recipe 模型
- [ ] Task 4: 修改 ProductRecord 模型
- [ ] Task 5: 修改 ProductIngredientLink 模型
- [ ] Task 6: 执行数据库迁移

### 阶段 2: 后端 API 接口
- [ ] Task 7: 创建 Product Schema
- [ ] Task 8: 创建 UserIngredientPreference Schema
- [ ] Task 9: 创建 Product API 路由
- [ ] Task 10: 创建 UserPreference API 路由
- [ ] Task 11: 修改现有 ProductRecord API
- [ ] Task 12: 创建 Recipe Schema 更新

### 阶段 3: 前端页面
- [ ] Task 13: 创建 Product API 客户端
- [ ] Task 14: 创建商品管理页面
- [ ] Task 15: 创建 ProductModal 组件
- [ ] Task 16: 重构价格记录页面
- [ ] Task 17: 增强食材管理页面
- [ ] Task 18: 更新路由配置

### 阶段 4: 智能功能
- [ ] Task 19: 实现食谱成品自动匹配
- [ ] Task 20: 添加自动匹配 API 端点
- [ ] Task 21: 实现成本计算智能选择
- [ ] Task 22: 添加成本计算 API 端点
- [ ] Task 23: 前端集成智能匹配功能
- [ ] Task 24: 前端集成成本计算功能

### 阶段 5: 测试和文档
- [ ] Task 25: 编写后端测试
- [ ] Task 26: 编写前端测试
- [ ] Task 27: 更新项目文档
- [ ] Task 28: 最终验证和清理

---

**计划完成日期:** 待定
**预计工作量:** 8-12 小时
