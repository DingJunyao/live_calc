# 生活成本计算器 - 营养分析功能实施计划

**创建日期:** 2026-03-09
**最后更新:** 2026-03-11
**版本:** 2.0
**项目名称:** LiveCalc - Nutrition Feature Implementation

**架构变更说明 (v2.0):**
- 营养数据源从独立的 `HowToCook_nutrition_json` 仓库改为 `HowToCook_json` 仓库
- 数据文件路径: `out/nutritions.json`（与菜谱导入使用同一仓库）
- 数据格式适配 USDA 标准化营养数据（含 NRV 百分比）
- 食材匹配情况: 712/902 匹配 (约79%)

---

## 目录

1. [项目概述](#项目概述)
2. [功能需求](#功能需求)
3. [整体架构设计](#整体架构设计)
4. [实施阶段规划](#实施阶段规划)
5. [数据模型设计](#数据模型设计)
6. [API端点设计](#api端点设计)
7. [前端组件设计](#前端组件设计)
8. [测试策略](#测试策略)
9. [风险评估](#风险评估)
10. [时间估算](#时间估算)

---

## 项目概述

### 项目背景

生活成本计算器（LiveCalc）是一个全栈的生活成本管理应用，核心功能包括商品价格记录、菜谱成本计算、地点管理等。现在需要添加完整的营养数据分析功能，提升应用的健康管理和用户指导能力。

### 目标

为 LiveCalc 添加完整的营养数据分析系统，包括：

1. **营养数据导入** - 支持从外部文件导入标准化营养数据
2. **营养数据编辑** - 支持商品和食材的营养数据编辑（Mixin机制）
3. **营养数据展示** - 改进现有的营养展示，支持层级营养素和NRV百分比
4. **营养规划分析** - 提供营养缺口分析、智能推荐、趋势分析等功能

### 设计原则

- **渐进式实施**：分阶段实施，降低风险
- **向后兼容**：保持现有功能稳定，新增功能不影响现有功能
- **数据驱动**：基于营养数据进行计算，确保准确性
- **用户体验**：直观的可视化展示，便于用户理解和使用
- **性能优化**：合理使用缓存，避免重复计算
- **可扩展性**：模块化设计，便于未来功能扩展

---

## 功能需求

### 1. 营养数据导入功能

**功能描述：**
- 从 `HowToCook_json` 仓库的 `out/nutritions.json` 导入 USDA 标准化营养数据
- 支持增量更新和全量导入
- 提供导入进度反馈和错误处理
- 自动创建 AI 匹配关系

**用户价值：**
- 快速建立营养数据库基础
- 减少手动录入工作
- 提供完整的中文食材营养数据

### 2. 营养数据编辑功能

**功能描述：**
- 商品营养数据编辑：支持商品自定义营养数据，可覆盖默认食材营养
- 食材营养数据编辑：编辑食材的基础营养数据和别名
- Mixin机制：智能选择营养数据源（商品自定义 > 食材默认 > AI匹配）
- 编辑历史和审计追踪

**用户价值：**
- 支持特殊商品的营养数据（如减盐版、有机版）
- 允许用户纠正不准确的营养数据
- 灵活的数据管理方式

### 3. 营养数据展示功能

**功能描述：**
- 改进菜谱详情页的营养展示
- 支持层级营养素展示（主营养素+子营养素）
- NRV/DV百分比可视化（彩色进度条）
- 响应式设计，适配移动端
- 数据源指示器

**用户价值：**
- 清晰的营养数据展示，便于理解
- 可视化的营养充足度，指导健康饮食
- 优化的移动端体验

### 4. 营养规划与数据展示功能

**功能描述：**
- **营养缺口分析**：分析用户营养摄入与标准的差距
- **智能推荐系统**：性价比推荐、目标导向推荐、替代建议
- **趋势分析**：多时间段营养摄入趋势，支持图表展示
- **历史快照**：保存和加载重要分析结果

**用户价值：**
- 个性化的营养建议和指导
- 营养摄入趋势监控
- 智能的食谱推荐
- 历史数据回顾和对比

---

## 整体架构设计

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    LiveCalc 主系统架构                     │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────┐   │
│  │          前端层 (Vue 3 + Vite)         │   │
│  │  ┌────────────────────────────────────┐        │   │
│  │  │  页面组件                     │        │   │
│  │  ├─ RecipeDetail.vue          │        │   │
│  │  ├─ ProductDetail.vue          │        │   │
│  │  ├─ NutritionPlan.vue        │        │   │
│  │  └─ NutritionDisplay.vue    │        │   │
│  │  ┌────────────────────────────┐        │   │
│  │  │  图表组件                │        │   │
│  │  ├─ NutritionRadarChart.vue    │        │   │
│  │  ├─ TrendLineChart.vue         │        │   │
│  │  └─ ComparisonBarChart.vue  │        │   │
│  │  └────────────────────────────┘        │   │
│  └─────────────────────────────────────┘        │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                  ↓ HTTP/WebSocket
┌─────────────────────────────────────────────────────┐
│               后端层 (FastAPI)                     │
├─────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────┐        │   │
│  │          API 路由                    │        │   │
│  │  ├─ nutrition.py                │        │   │
│  │  ├─ products.py                │        │   │
│  │  └─ recipes.py                 │        │   │
│  │  ┌────────────────────────────┐        │   │
│  │  │  服务层                     │        │   │
│  │  ├─ nutrition_import_service.py   │        │   │
│  │  ├─ nutrition_calculator.py     │        │   │
│  │  ├─ nutrition_planner.py       │        │   │
│  │  ├─ nutrition_data_editor.py    │        │   │
│  │  └─ nutrition_analyzer.py     │        │   │
│  │  └────────────────────────────┘        │   │
│  │  ┌────────────────────────────┐        │   │
│  │  │  数据层                     │        │   │
│  │  ├─ NutritionData             │        │   │
│  │  ├─ Ingredient                │        │   │
│  │  ├─ Product                  │        │   │
│  │  └─ Recipe                   │        │   │
│  │  └────────────────────────────┘        │   │
│  └─────────────────────────────────────┘        │   │
│  ┌─────────────────────────────────────┤        │
│  │          数据库 (SQLite/PostgreSQL)      │        │
│  │          nutrition_data              │        │   │
│  │          ingredient_nutrition_mapping  │        │   │
│  │          nutrition_trend_snapshots   │        │   │
│  └─────────────────────────────┤        │   │
└─────────────────────────────────────────────┘        │
                    ↓ 文件导入
┌─────────────────────────────────────────────────────┐
│         HowToCook_nutrition_json            │
│  ┌────────────────────────────────────┐        │
│  │  输出: nutrition_data.json       │        │   │
│  └─────────────────────────────────────┘        │
└─────────────────────────────────────────────┘        │
```

### 数据流图

```
营养数据导入流程：
1. 运行 HowToCook_nutrition_json → 生成 nutrition_data.json
2. 用户手动上传 nutrition_data.json 或管理员导入
3. 后端解析和验证数据
4. 批量插入/更新数据库
5. 创建 AI 匹配关系
6. 生成导入报告

营养数据展示流程：
1. 前端选择商品/食材/菜谱
2. 后端计算营养数据（支持自定义数量）
3. 前端展示层级营养素和 NRV 百分比
4. 用户可自定义营养数据
5. 更新营养数据到数据库

营养规划分析流程：
1. 用户选择时间周期和目标
2. 后端分析营养摄入数据
3. 计算营养缺口和趋势
4. 生成智能推荐
5. 前端可视化展示和保存
```

---

## 实施阶段规划

### 阶段一：基础设施准备（预计3-5天）

#### 目标
- 准备必要的数据模型和服务基础
- 确保数据结构支持新功能
- 搭建基础的服务框架

#### 任务清单

- [ ] **T1.1** 分析现有数据模型，确定需要修改的字段
- [ ] **T1.2** 增强数据库模型（Product表支持custom_nutrition_data）
- [ ] **T1.3** 创建新的数据模型（营养趋势快照表）
- [ ] **T1.4** 编写数据库迁移脚本（Alembic）
- [ ] **T1.5** 测试数据库迁移并回滚脚本
- [ ] **T1.6** 创建基础服务框架文件
- [ ] **T1.7** 编写单元测试基础框架

#### 验收标准
- [ ] 所有数据库迁移脚本成功执行
- [ ] 新增数据模型可以通过 SQLAlchemy ORM 正常操作
- [ ] 单元测试框架可运行
- [ ] 数据库外键关系正确建立

### 阶段二：营养数据导入功能（预计4-6天）

#### 目标
- 实现营养数据从外部文件的导入功能
- 支持增量更新和全量导入
- 实现进度反馈和错误处理

#### 任务清单

- [ ] **T2.1** 创建营养数据导入服务 (`nutrition_import_service.py`)
- [ ] **T2.2** 实现JSON数据解析和验证
- [ ] **T2.3** 实现批量数据插入逻辑
- [ ] **T2.4** 实现AI匹配关系创建
- [ ] **T2.5** 实现冲突检测和处理策略
- [ ] **T2.6** 编写导入API端点 (`/nutrition/import`)
- [ ] **T2.7** 实现导入进度反馈机制
- [ ] **T2.8** 编写导入单元测试
- [ ] **T2.9** 测试导入功能的边界情况
- [ ] **T2.10** 编写导入功能文档

#### 验收标准
- [ ] 可以成功解析和导入 nutrition_data.json
- [ ] 批量导入支持1000+营养数据
- [ ] 导入过程中提供实时进度反馈
- [ ] 错误处理覆盖所有异常情况
- [ ] 生成详细的导入报告

### 阶段三：营养计算引擎（预计5-7天）

#### 目标
- 实现营养数据的标准化计算
- 支持单个食材、商品、菜谱的营养计算
- 支持自定义数量和单位的计算

#### 任务清单

- [ ] **T3.1** 创建营养计算器基础框架 (`nutrition_calculator.py`)
- [ ] **T3.2** 实现营养素标准化计算（值+单位+NRV%）
- [ ] **T3.3** 实现单个食材营养计算
- [ ] **T3.4** 实现菜谱营养汇总计算
- [ ] **T3.5** 实现自定义数量计算支持
- [ ] **T3.6** 实现缓存机制（常用营养数据缓存）
- [ ] **T3.7** 编写计算API端点
- [ ] **T3.8** 编写计算器单元测试
- [ ] **T3.9** 测试各种计算场景和边界条件

#### 验收标准
- [ ] 单个食材营养计算准确
- [ ] 菜谱营养汇总正确
- [ ] NRV百分比计算符合中国标准
- [ ] 自定义数量计算结果与固定数量成比例
- [ ] 缓存机制有效提升性能
- [ ] 计算结果符合预期格式

### 阶段四：营养数据编辑功能（预计4-5天）

#### 目标
- 实现商品和食材的营养数据编辑
- 支持Mixin机制的数据源选择
- 实现编辑历史和审计

#### 任务清单

- [ ] **T4.1** 创建营养数据编辑服务 (`nutrition_data_editor.py`)
- [ ] **T4.2** 实现商品自定义营养数据编辑
- [ ] **T4.3** 实现自定义营养数据清除
- [ ] **T4.4** 实现食材营养数据编辑
- [ ] **T4.5** 实现食材别名编辑
- [ ] **T4.6** 实现智能数据源选择器
- [ ] **T4.7** 编写编辑API端点
- [ ] **T4.8** 实现编辑历史记录
- [ ] **T4.9** 编写编辑功能单元测试
- [ ] **T4.10** 测试Mixin机制和数据源选择

#### 验收标准
- [ ] 商品可以设置和清除自定义营养数据
- [ ] 食材营养数据和别名可以编辑
- [ ] 智能数据源选择逻辑正确
- [ ] 编辑操作有完整的审计日志
- [ ] 数据修改事务正确处理

### 阶段五：营养数据展示优化（预计5-7天）

#### 目标
- 改进现有营养展示
- 实现层级营养素展示
- 实现NRV百分比可视化
- 优化响应式设计

#### 任务清单

- [ ] **T5.1** 创建营养展示组件 (`NutritionDisplay.vue`)
- [ ] **T5.2** 创建NRV进度条组件 (`NutritionProgressBar.vue`)
- [ ] **T5.3** 增强菜谱详情页的营养展示
- [ ] **T5.4** 实现层级营养素展示（主+子）
- [ ] **T5.5** 实现NRV百分比可视化
- [ ] **T5.6** 添加数据源指示器
- [ ] **T5.7** 优化移动端响应式设计
- [ ] **T5.8** 编写展示API端点（如需要新增）
- [ ] **T5.9** 组件单元测试和UI测试
- [ ] **T5.10** 测试不同设备和屏幕尺寸

#### 验收标准
- [ ] 营养数据组件展示完整正确
- [ ] 层级营养素展示结构清晰
- [ ] NRV百分比准确显示
- [ ] 数据源指示器正确反映数据来源
- [ ] 移动端展示优化，触摸友好

### 阶段六：营养规划分析功能（预计7-10天）

#### 目标
- 实现营养缺口分析
- 实现智能推荐系统
- 实现趋势分析功能
- 实现历史快照管理

#### 任务清单

- [ ] **T6.1** 创建营养规划服务 (`nutrition_planner.py`)
- [ ] **T6.2** 实现营养缺口分析逻辑
- [ ] **T6.3** 实现性价比推荐算法
- [ ] **T6.4** 实现目标导向推荐算法
- [ ] **T6.5** 实现替代食材推荐算法
- [ ] **T6.6** 创建趋势分析服务 (`nutrition_analyzer.py`)
- [ ] **T6.7** 实现营养摄入趋势分析
- [ ] **T6.8** 实现趋势洞察生成
- [ ] **T6.9** 实现历史快照创建和查询
- [ ] **T6.10** 编写推荐和趋势API端点
- [ ] **T6.11** 创建营养规划页面 (`NutritionPlan.vue`)
- [ ] **T6.12** 实现数据可视化组件（雷达图、趋势图等）
- [ ] **T6.13** 实现推荐功能展示
- [ ] **T6.14** 编写分析和推荐算法单元测试
- [ ] **T6.15** 测试推荐算法准确性

#### 验收标准
- [ ] 营养缺口分析准确，提供可行建议
- [ ] 推荐算法有效，结果合理
- [ ] 趋势分析正确，洞察有价值
- [ ] 历史快照可以正常创建和查询
- [ ] 所有推荐API响应格式正确
- [ ] 数据可视化组件准确美观

### 阶段七：集成测试和优化（预计3-4天）

#### 目标
- 端到端集成测试
- 跨模块功能测试
- 性能测试和优化
- 用户体验测试

#### 任务清单

- [ ] **T7.1** 编写端到端集成测试用例
- [ ] **T7.2** 测试营养数据导入完整流程
- [ ] **T7.3** 测试营养计算各种场景
- [ ] **T7.4** 测试营养数据编辑功能
- [ ] **T7.5** 测试营养展示组件
- [ ] **T7.6** 测试营养规划分析功能
- [ ] **T7.7** 性能测试（响应时间、并发处理）
- [ ] **T7.8** 优化数据库查询（索引、N+1查询）
- [ ] **T7.9** 优化缓存策略
- [ ] **T7.10** 移动端性能优化

#### 验收标准
- [ ] 所有新增功能集成测试通过
- [ ] 端到端响应时间在合理范围内（<1s）
- [ ] 移动端页面加载时间<2s
- [ ] 大数据量处理不会导致超时
- [ ] 内存使用在合理范围内
- [ ] 无内存泄漏，长时间运行稳定

### 阶段八：文档和培训（预计2-3天）

#### 目标
- 编写用户文档
- 编写开发者文档
- 准备用户培训材料

#### 任务清单

- [ ] **T8.1** 编写用户使用文档
- [ ] **T8.2** 编写开发者API文档
- [ ] **T8.3** 编写数据库变更文档
- [ ] **T8.4** 创建功能演示视频（可选）
- [ ] **T8.5** 准备常见问题解答
- [ ] **T8.6** 准备用户培训材料

#### 验收标准
- [ ] 用户文档清晰完整
- [ ] API文档符合OpenAPI规范
- [ ] 常见问题解答覆盖主要场景
- [ ] 培训材料内容易懂实用

---

## 数据模型设计

### 现有模型分析

**已有的营养相关模型：**
- `NutritionData` - 营养数据表
- `Ingredient` - 食材表
- `IngredientNutritionMapping` - 食材营养映射表

**需要增强的模型：**
- `Product` - 需要添加自定义营养数据支持

### 新增和修改的模型

#### Product 模型增强

```python
# backend/app/models/product.py

class Product(Base, AuditMixin):
    """商品记录表（增强版）"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"))

    # 商品基础信息
    product_name = Column(String(200), nullable=False)
    brand = Column(String(100))
    variant = Column(String(100))  # 变体信息（如"减盐版"、"有机版"）

    # 价格信息
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default="CNY")

    # 数量单位信息
    original_quantity = Column(Numeric(10, 2))
    original_unit = Column(String(20))
    standard_quantity = Column(Numeric(10, 2))
    standard_unit = Column(String(20))

    # ⭐ 新增：自定义营养数据支持
    custom_nutrition_data = Column(JSON, nullable=True)  # 自定义营养数据（Mixin机制）
    has_custom_nutrition = Column(Boolean, default=False, nullable=False)  # 是否有自定义营养数据

    # 记录类型
    record_type = Column(String(20), default="purchase")  # purchase/price
    recorded_at = Column(DateTime)
    notes = Column(Text)

    # 审计字段从 AuditMixin 继承
    # 关系
    ingredient = relationship("Ingredient", lazy="select")
    location = relationship("Location", lazy="select")
    user = relationship("User", back_populates="products")

# custom_nutrition_data 结构示例：
# {
#   "has_custom_data": true,
#   "override_reason": "减盐版本，钠含量降低30%",
#   "nutrition": {
#     "reference_base": {"amount": 100, "unit": "g"},
#     "nutrients": {
#       "calories": {
#         "standard_value": 252,
#         "standard_unit": "kcal",
#         "nrv_percent": 31.5
#       }
#     }
#   }
# }
```

#### 新增模型：营养趋势快照

```python
# backend/app/models/nutrition_trends.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.base_model import AuditMixin


class NutritionTrendSnapshot(Base, AuditMixin):
    """营养趋势快照表（持久化重要分析结果）"""
    __tablename__ = "nutrition_trend_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # 时间范围
    start_date = Column(DateTime, nullable=False, index=True)
    end_date = Column(DateTime, nullable=False, index=True)
    time_unit = Column(String(20), nullable=False)  # daily/weekly/monthly

    # 聚合数据
    aggregated_data = Column(JSON, nullable=False)  # 包含time_series_data, trend_analysis等

    # 元数据
    meal_count = Column(Integer, default=0)
    analysis_timestamp = Column(DateTime)

    # 审计字段从 AuditMixin 继承
    # 关系
    user = relationship("User", back_populates="nutrition_trend_snapshots")
```

---

## API端点设计

### 营养数据导入API

```
POST   /api/v1/nutrition/import
参数:
  - file: UploadFile - nutrition_data.json 文件
  - mode: "incremental" | "full" | "force" - 导入模式
  - overwrite: boolean - 是否覆盖已存在数据

返回:
  {
    "success": true,
    "message": "导入完成",
    "statistics": {
      "total_records": 150,
      "imported_records": 145,
      "updated_records": 5,
      "skipped_records": 0,
      "failed_records": 5,
      "errors": []
    }
  }
```

### 营养数据编辑API

```
PUT    /api/v1/products/{product_id}/nutrition
参数:
  - nutrition_data: dict - 标准化营养数据
  - override_reason: string - 覆盖原因
返回: {"success": true, "message": "更新成功"}

DELETE  /api/v1/products/{product_id}/nutrition
返回: {"success": true, "message": "已恢复使用原料营养数据"}

GET     /api/v1/products/{product_id}/nutrition
返回: ProductNutritionResult - 包含营养数据和数据源信息

PUT    /api/v1/ingredients/{ingredient_id}/nutrition
参数:
  - nutrition_data: dict - 标准化营养数据
返回: {"success": true, "message": "更新成功"}

PATCH   /api/v1/ingredients/{ingredient_id}/aliases
参数:
  - aliases: List[string] - 别名列表
返回: {"success": true, "message": "更新成功"}
```

### 营养计算API

```
GET     /api/v1/ingredients/{ingredient_id}/nutrition
参数:
  - quantity: number - 目标数量
  - unit: string - 目标单位
返回: IngredientNutritionResult - 计算后的营养值

GET     /api/v1/recipes/{recipe_id}/nutrition
参数:
  - servings: number - 份数
返回: RecipeNutritionResult - 菜谱总营养

GET     /api/v1/recipes/{recipe_id}/nutrition/summary
返回: NutritionSummary - 简化版总览数据（用于列表展示）
```

### 营养规划API

```
GET     /api/v1/nutrition/plans/gap-analysis
参数:
  - time_period: "daily" | "weekly" | "monthly"
  - start_date: datetime - 开始日期
  - end_date: datetime - 结束日期
返回: NutritionGapAnalysis - 营养缺口分析结果

GET     /api/v1/nutrition/plans/recommendations
参数:
  - recommendation_type: "cost_effective" | "goal_oriented" | "substitute"
  - budget_limit: number - 预算限制（性价比推荐）
  - nutrition_goal: string - 营养目标（goal_oriented推荐）
  - limit: number - 推荐数量限制
返回: RecommendationResult - 推荐结果列表

GET     /api/v1/nutrition/plans/trends
参数:
  - start_date: datetime
  - end_date: datetime
  - time_unit: "daily" | "weekly" | "monthly"
返回: NutritionTrendAnalysis - 趋势分析结果

POST    /api/v1/nutrition/plans/snapshots
参数:
  - request: dict - 快照创建请求
返回: {success: true, snapshot_id: int}

GET     /api/v1/nutrition/plans/snapshots
返回: List[TrendSnapshot] - 历史快照列表
```

---

## 前端组件设计

### 核心组件列表

1. **NutritionDisplay.vue** - 通用营养数据展示组件
2. **NutritionProgressBar.vue** - NRV百分比进度条组件
3. **NutritionPlan.vue** - 营养规划主页面
4. **NutritionRadarChart.vue** - 营养雷达图组件
5. **TrendLineChart.vue** - 趋势线图组件
6. **ComparisonBarChart.vue** - 营养对比柱状图组件

### 组件依赖关系

```
NutritionPlan.vue
├── NutritionDisplay.vue (复用)
├── NutritionProgressBar.vue (复用)
├── NutritionRadarChart.vue
├── TrendLineChart.vue
└── ComparisonBarChart.vue

RecipeDetail.vue (增强)
├── NutritionDisplay.vue (复用)
└── NutritionEditor.vue (新增)

ProductDetail.vue (增强)
└── NutritionDisplay.vue (复用)
```

### 组件设计原则

- **组件化开发**：功能独立，接口清晰
- **可复用性**：通用组件可被多个页面复用
- **响应式优先**：移动端优先，桌面端兼顾
- **类型安全**：完整的 TypeScript 类型定义
- **性能优化**：虚拟滚动、懒加载、防抖

---

## 测试策略

### 单元测试

#### 测试工具
- **后端**: pytest + pytest-asyncio
- **前端**: Vitest + @vue/test-utils

#### 测试重点

**后端测试:**
- [ ] 数据模型验证测试
- [ ] 服务层业务逻辑测试
- [ ] API端点集成测试
- [ ] 边界条件和异常处理测试
- [ ] 数据库操作事务测试
- [ ] Mixin机制功能测试

**前端测试:**
- [ ] 组件渲染测试
- [ ] 用户交互测试
- [ ] 响应式布局测试
- [ ] 数据可视化准确性测试
- [ ] 表单验证测试

### 集成测试

#### E2E 测试场景
1. **营养数据导入完整流程**
   - 上传标准 nutrition_data.json
   - 验证导入进度
   - 检查数据库结果
   - 测试错误处理

2. **营养数据编辑和展示**
   - 编辑商品自定义营养数据
   - 查看菜谱营养展示
   - 验证数据源选择器
   - 测试不同设备显示

3. **营养规划分析功能**
   - 查看营养缺口分析
   - 获取性价比推荐
   - 查看趋势分析
   - 创建和查看历史快照

---

## 风险评估

### 技术风险

#### 高风险
- **数据库迁移风险**: 现有数据结构变更可能影响现有功能
  - **缓解措施**: 充分测试、准备回滚方案、分阶段执行
- **性能影响**: 复杂营养计算可能影响性能
  - **缓解措施**: 缓存策略、异步处理、性能监控

#### 中风险
- **数据准确性**: 依赖外部AI仓库数据质量
  - **缓解措施**: 数据验证机制、用户可编辑纠正、版本管理
- **算法复杂性**: 推荐算法可能不准确
  - **缓解措施**: 多算法对比、置信度评分、用户反馈机制

### 业务风险

- **用户接受度**: 新增功能可能影响用户体验
  - **缓解措施**: 渐进式发布、用户培训、收集反馈
- **学习成本**: 复杂的营养概念需要用户学习
  - **缓解措施**: 完善帮助文档、提示说明、常见问题解答

### 项目风险

- **开发周期**: 总计35-44天，可能延期
  - **缓解措施**: 分阶段交付、优先核心功能、及时沟通进度

---

## 时间估算

### 详细时间分解

| 阶段 | 任务 | 乐观估计 | 保守估计 | 缓冲时间 |
|--------|------|------------|-----------|
| 阶段一: 基础设施 | 7项任务 | 3-5天 | 4-7天 | 5-7天 |
| 阶段二: 数据导入 | 10项任务 | 4-6天 | 5-8天 | 6-9天 |
| 阶段三: 营养计算 | 10项任务 | 5-7天 | 6-9天 | 7-10天 |
| 阶段四: 数据编辑 | 10项任务 | 4-5天 | 5-7天 | 6-9天 |
| 阶段五: 数据展示 | 10项任务 | 5-7天 | 6-9天 | 7-10天 |
| 阶段六: 营养规划 | 15项任务 | 7-10天 | 8-13天 | 10-15天 |
| 阶段七: 集成测试 | 10项任务 | 3-4天 | 4-6天 | 4-6天 |
| 阶段八: 文档培训 | 6项任务 | 2-3天 | 3-5天 | 3-5天 |
| **总计** | **78项任务** | **35-44天** | **41-57天** | **47-68天** |

### 关键路径

**关键路径（无并行依赖）:**
1. 基础设施 → 数据导入 → 营养计算 → 数据编辑 → 数据展示 → 营养规划
2. 数据展示优化可以与营养规划并行开发

**可并行任务:**
- 文档编写可在开发过程中同步进行
- 部分组件可在其他阶段提前开发

---

## 成功标准

### 功能完整性

- ✅ 营养数据可以从外部文件成功导入
- ✅ 商品和食材的营养数据可以编辑和查询
- ✅ 菜谱详情页展示完整的营养数据（层级+NRV%）
- ✅ 营养规划页面提供缺口分析、推荐和趋势
- ✅ 所有功能在移动端和桌面端正常运行

### 性能指标

- ✅ 营养数据导入1000+记录在30秒内完成
- ✅ 营养计算API响应时间<500ms
- ✅ 营养规划分析API响应时间<2s
- ✅ 页面首屏加载时间<2s
- ✅ 移动端页面滚动流畅

### 代码质量

- ✅ 所有新增代码通过 Pylint/Black 格式化
- ✅ 单元测试覆盖率≥80%
- ✅ 集成测试通过率100%
- ✅ 代码有完整的类型注解
- ✅ 无重大代码异味

### 用户体验

- ✅ 营养数据展示清晰直观
- ✅ NRV百分比可视化易于理解
- ✅ 响应式设计符合各设备尺寸
- ✅ 错误提示友好准确
- ✅ 用户文档完整易懂

---

## 后续优化方向

### 短期优化（3-6个月）

1. **性能优化**
   - 引入缓存机制，减少数据库查询
   - 优化营养计算算法性能
   - 实现数据预加载和懒加载

2. **功能增强**
   - 添加营养目标设定和跟踪功能
   - 实现智能饮食计划建议
   - 支持营养数据对比（不同版本数据对比）
   - 添加营养数据分享和导出功能

3. **用户体验优化**
   - 收集用户反馈并优化推荐算法
   - 增加营养知识库和帮助系统
   - 优化移动端手势操作和布局
   - 添加数据可视化交互和动画

4. **数据质量提升**
   - 建立营养数据质量监控机制
   - 定期更新外部AI仓库的数据
   - 实现用户反馈驱动的数据纠正机制

---

**文档版本:** 1.0
**最后更新:** 2026-03-09
**维护者:** Claude Code Agent
