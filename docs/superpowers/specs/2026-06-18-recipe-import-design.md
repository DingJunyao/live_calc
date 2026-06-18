# 设计文档：菜谱导入功能重做

## 一、功能概述

重做现有菜谱导入功能，将三代散落的导入服务整合为统一的分层管道。支持三种数据来源（git 仓库、本地目录、上传压缩包）、两种格式（HowToCook_json、系统导出格式），以及导入后的 AI 后处理（模糊量推测、密度推测）。

### 目标

- **统一**：将 `RecipeImportService`、`JsonRecipeImportService`、`EnhancedRecipeImportService` 三代服务整合为清晰的四层管道
- **扩展**：新增对系统导出格式的支持（含价格记录、商家等数据）
- **补全**：导入后通过 AI 推测原料的模糊用量和密度
- **权限**：管理员可导入全量数据，用户只能导入自己导出的数据

---

## 二、整体架构

```
输入源层 → 格式检测层 → 数据导入层 → AI 后处理层
```

每层职责单一、可独立测试：

| 层 | 职责 | 不做什么 |
|----|------|---------|
| 输入源层 | 获取原始文件集合 | 不关心文件内容格式 |
| 格式检测层 | 识别数据格式类型 | 不负责解析和写入 |
| 数据导入层 | 解析并写入数据库 | 不关心数据来源 |
| AI 后处理层 | 对已入库的数据做推测 | 和导入完全解耦，可重跑 |

### 项目结构

```
backend/app/services/
├── import/
│   ├── __init__.py
│   ├── base.py                   # DataSource / Importer 抽象基类
│   ├── sources/
│   │   ├── git_repo.py           # GitRepoSource
│   │   ├── local_dir.py          # LocalDirSource
│   │   └── upload_archive.py     # UploadArchiveSource
│   ├── detectors/
│   │   └── format_detector.py    # FormatDetector
│   ├── importers/
│   │   ├── howtocook.py          # HowToCookImporter
│   │   └── export.py             # ExportImporter
│   ├── ai_inference/
│   │   ├── __init__.py
│   │   ├── fuzzy_quantity.py     # 模糊量推测
│   │   └── density.py            # 密度推测
│   └── models.py                 # FileCollection / DataFile / ImportResult 等数据类
├── enhanced_recipe_import_service.py   # 保留，内部委托到新模块
└── export/                             # 已有导出模块不动
```

### 数据流

```
GitRepoSource ─┐
LocalDirSource ─┤→ FileCollection → FormatDetector → FormatType → Importer → DB
UploadArchive  ┘                                           ↓
                                               HowToCookImporter
                                               ExportImporter
                                               
DB ─→ AIInferrer (fuzzy_quantity / density) ─→ 回写 DB
```

---

## 三、输入源层

统一实现 `DataSource` 接口：

```python
class DataSource(ABC):
    @abstractmethod
    def collect_files(self) -> FileCollection:
        ...

@dataclass
class FileCollection:
    files: list[DataFile]
    temp_dir: Optional[str] = None
    cleanup: Optional[Callable] = None

@dataclass
class DataFile:
    relative_path: str
    absolute_path: str
    size: int
```

### GitRepoSource

- 从环境变量 `DATA_REPO_URL`、`DATA_REPO_BRANCH`、`DATA_REPO_DIR` 读取配置
- 优先 `git clone --depth 1 --branch <branch>`，失败则退回到 ZIP 下载（复用 `EnhancedRecipeImportService` 现有重试逻辑）
- 截取 `DATA_REPO_DIR` 子目录作为 `FileCollection`
- 设置 `cleanup` 清理临时 clone 目录

### LocalDirSource

- 直接扫描 `DATA_LOCAL_PATH` 目录
- 返回目录下所有文件的 `FileCollection`
- 无需清理

### UploadArchiveSource

- 接收上传的 ZIP 文件路径（已保存到临时目录）
- 解压到临时目录，递归扫描所有文件
- 支持两种压缩包：HowToCook_json 格式的 zip、系统导出格式的 zip
- 设置 `cleanup` 清理临时解压目录
- **权限控制**：管理员可上传任意格式；普通用户只能上传系统导出格式的压缩包

---

## 四、格式检测层

```python
class FormatDetector:
    @staticmethod
    def detect(collection: FileCollection) -> FormatType:
        # export → howtocook_json → unknown 优先级
        ...
```

### 检测规则

| 优先级 | 格式 | 判定条件 |
|--------|------|---------|
| 1 | `export` | 文件列表中存在 `manifest.json`，且包含 `version` 字段 |
| 2 | `howtocook_json` | 文件列表中存在 `ingredients.json`，且有至少一个菜谱 JSON |
| 3 | `unknown` | 均不匹配 |

**目录兼容**：同时检测根目录和 `DATA_REPO_DIR` 子目录，只要其中一层匹配即可。

---

## 五、数据导入层

```python
class Importer(ABC):
    def __init__(self, db: Session, user_id: int):
        ...

    @abstractmethod
    def import_all(self, collection: FileCollection) -> ImportResult:
        ...

@dataclass
class ImportResult:
    stats: dict[str, int]    # {"recipes": 5, "ingredients": 3, ...}
    errors: list[str]
    warnings: list[str]
```

### HowToCookImporter

复用 `EnhancedRecipeImportService` 的核心导入流程，不做大改：

1. 读 `units.json` → 导入单位（含别名）
2. 读 `ingredients.json` → 导入原料，自动创建对应商品
3. 读 `nutritions.json` / `matched_ingredients.json` → 关联营养数据
4. 扫描菜谱 JSON 文件 → 逐个导入
5. 下载/复制菜谱图片到 `backend/static/images/recipes/`

**主要变化**：从硬编码路径改为从 `FileCollection` 的文件路径自动推断 `DATA_REPO_DIR`。

### ExportImporter

按依赖顺序导入系统导出 zip 中的数据。**互斥规则**：以名称 + 来源匹配已有数据，匹配到则跳过。

```
导入顺序：
 1. units.json               → 单位
 2. unit_conversions.json    → 单位转换关系
 3. ingredient_categories.json → 原料分类
 4. ingredients.json         → 原料（匹配跳过） ← 含密度数据
 5. entity_densities.json    → 密度数据（匹配跳过）
 6. nutritions.json          → 营养数据（匹配跳过）
 7. ingredient_hierarchy.json → 原料层级关系（匹配跳过）
 8. recipes/*.json           → 菜谱（匹配跳过）
 9. products.json            → 商品（匹配跳过）
10. product_barcodes.json    → 条码
11. product_ingredient_links.json → 商品-原料关联
12. merchants.json           → 商家（按名称匹配跳过）
13. favorite_merchants.json  → 收藏商家
14. price_records.json       → 价格记录（全部写入，不做去重）
15. images/*                 → 图片文件
```

### 匹配与映射策略

| 实体 | 匹配键 | 匹配到则 | 导入时外键重映射 |
|------|--------|---------|----------------|
| 原料 | name | 跳过，用已有 ID | — |
| 菜谱 | name | 跳过，用已有 ID | ingredient_id 重映射 |
| 商品 | name + ingredient_id | 跳过，用已有 ID | ingredient_id 重映射 |
| 商家 | name | 跳过，用已有 ID | — |
| 价格记录 | — | 全部写入 | product_id、merchant_id 重映射 |
| 单位 | name + abbreviation | 跳过，用已有 ID | — |
| 单位转换 | — | 全部写入 | unit_id 重映射 |
| 营养数据 | ingredient_id | 跳过 | ingredient_id 重映射 |

**用户导入时的归属**：
- 新导入的菜谱、价格记录等可归属数据，`user_id` 设置为当前操作者
- 系统级数据（单位、单位转换关系、原料分类）不归属用户

---

## 六、AI 后处理层

独立于导入流程，用户可在导入完成后随时触发。复用现有 AI 配置（支持 Claude / OpenAI 兼容 / 百度 / 阿里云），用户选择一个提供方后批量处理。

### 模糊量推测

**处理对象**：对菜谱中用量为模糊值的 `RecipeIngredient` 条目做数值化推测。

**触发条件**（筛选候选）：
- 用量单位是计数单位（unit 表的 `is_countable` 标记）且原料没有 `piece_weight`
- 用量为 `null` 或内容为"适量""少许"等模糊文本

**处理流程**：
1. 遍历所有 `RecipeIngredient`，筛选候选
2. 按 `(ingredient_id, unit_id)` 分组去重——同一原料同一单位只问 AI 一次
3. 对每组构建 Prompt（原料名称 + 单位 + 上下文菜谱名），请求 AI 推测
4. 解析结果后：
   - 计数单位且推测出单件重量 → 回写 `Ingredient.piece_weight`（单位：克）
   - 模糊量且推测出合理范围 → 回写 `RecipeIngredient.quantity_range`
   - 已处理条目标记 `ai_inferred = True`，避免重复处理

**Prompt 示例**：
```
请推测以下食材在常见菜谱中的典型用量：
- 食材：鸡蛋，单位：个
- 出现于菜谱："西红柿炒鸡蛋、鸡蛋羹、韭菜炒鸡蛋"
请推测每个"个"相当于多少克（piece_weight_g），
以及如果该食材用量为"适量"时大约是多少克（default_weight_g）。
返回 JSON：{"piece_weight_g": 55, "default_weight_g": null}
```

### 密度推测

**处理对象**：`density IS NULL` 的原料。

**处理流程**：
1. 收集所有无密度值的原料
2. 按名称去重分批问 AI
3. 回写 `Ingredient.density`（单位：g/cm³）

### API

```
POST  /api/v1/import/ai-infer/quantities  → 触发模糊量推测（返回 job_id）
POST  /api/v1/import/ai-infer/densities    → 触发密度推测（返回 job_id）
GET   /api/v1/import/ai-infer/status       → 查询推测进度/结果
```

### 重跑机制

- 已推测的记录标记 `ai_inferred` 字段
- 重跑时自动跳过已处理记录，只处理新增的候选
- 用户可选择"强制重跑全部"清空标记重新处理

---

## 七、权限控制

| 功能 | 管理员 | 普通用户 |
|------|--------|---------|
| 配置 git repo / 本地目录导入 | ✅ 启动时 .env 配置 | ❌ |
| 上传 HowToCook_json 格式压缩包导入 | ✅ | ❌ |
| 上传系统导出格式压缩包导入 | ✅ 全量导入 | ✅ 归属自己 |
| 触发 AI 后处理（模糊量/密度） | ✅ | ✅ 从已有 AI 配置中选择提供方 |
| 查看导入日志/状态 | ✅ | 仅自己的导入记录 |

**用户导入导出数据的约束**：
- 上传 API 做格式检测，若为 `howtocook_json` 且非管理员 → 403
- 导入时关联的数据（菜谱、价格记录等）的 `user_id` 全部设置为当前操作者
- 系统中已有的数据（单位、原料等）不允许用户覆盖

---

## 八、前端变更

变化范围较小，主要是管理后台的配置入口：

### 新增页面/组件

- **导入管理页**（可选）：管理员查看导入状态、触发 AI 后处理的后台页面
  - 显示最近导入记录（时间、来源、统计数据）
  - AI 推测触发按钮 + 进度展示
  - 此页面可简化或延后实现（第一版可以只有 API，不上页面）

- **导入上传对话框**（用户端）：在已有界面上传导出压缩包
  - 文件选择 + 上传按钮
  - 上传后展示导入结果（成功 N 条，跳过 M 条，失败 K 条）
  - 可在"个人中心 - 数据导入"入口放置

### 现有页面修改

无。启动时导入保持现有行为，不需要前端介入。

---

## 九、错误处理与边界情况

| 场景 | 处理方式 |
|------|---------|
| 导入中途失败 | 事务回滚，记录失败日志，手动重试 |
| 格式无法识别 | 返回 400 + 错误信息，提示支持的格式 |
| 压缩包损坏 | 解压失败时返回具体错误信息 |
| git clone 超时 | 回退到 ZIP 下载 |
| 网络错误 | 按现有重试逻辑处理 |
| AI 调用失败 | 跳过当前条目，记录失败原因，继续处理剩余 |
| 用户上传非管理员格式 | 403 + 明确错误提示 |
| 重复导入同名菜谱 | 跳过已存在的，只导入新增的 |
| 部分导入失败 | 返回 PartialSuccess，列出成功/失败/跳过计数 |
| 菜谱引用了不存在的原料 | 记录 warning，跳过该菜谱 |

---

## 十、不做的事（YAGNI）

- ❌ 实时 WebSocket 进度推送（第一版用轮询或同步请求即可）
- ❌ 前端完整的管理后台页面（第一版只留 API 和最小化交互）
- ❌ 导入暂停/续传功能
- ❌ Git 仓库的 Webhook 自动同步
- ❌ AI 推测结果的版本管理
- ❌ 导入数据校验的自定义规则引擎
- ❌ 多语言导入支持
- ❌ 批量导出+导入的迁移工具

---

## 十一、与现有服务的集成

### 启动流程变化

`lifespan` 中的 `check_and_import_initial_recipes` 保持现有调用方式不变。内部实现改为委托到新的 `import/` 模块：

```python
# main.py（伪代码）
from app.services.import.sources.git_repo import GitRepoSource
from app.services.import.detectors.format_detector import FormatDetector
from app.services.import.importers.howtocook import HowToCookImporter

source = GitRepoSource(settings)
collection = source.collect_files()
format_type = FormatDetector.detect(collection)
importer = HowToCookImporter(db, user_id=1)
result = importer.import_all(collection)
```

### 导出模块不变

`backend/app/services/export/` 模块维持现状，导入器只读取其输出格式，不修改导出逻辑。

---

## 十二、数据库变更

### recipes 表

无结构变更。现有字段（`source`、`name`、`category` 等）足以标识和区分数据来源。

### ingredients 表

已有字段（不需新增）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `piece_weight` | Numeric(10,3), nullable | ✅ 已存在 |
| `piece_weight_unit_id` | Integer, FK, nullable | ✅ 已存在 |

新增字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `ai_inferred` | Boolean, default false | AI 是否已推测过此原料的模糊量/密度 |

### recipe_ingredients 表

已有字段（不需新增）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `original_quantity` | JSON, nullable | ✅ 已存在，可存 {"text": "适量"} 等格式 |

新增字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `ai_inferred` | Boolean, default false | AI 是否已推测过此条目的模糊量 |
