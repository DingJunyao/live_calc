# 设计文档：原料/商品匹配 USDA 营养素数据

## 一、功能概述

### 背景

现有系统已有一套「USDA 标准化数据」导入机制（`nutrition_import_service.py`），但它消费的是 HowToCook_json 仓库里**别人整理好的精简中文化版** `nutritions.json`，属于批量自动导入，无法应对「给某个新增原料/商品精准匹配 USDA 原始数据」的场景。

本功能新增一条独立链路：下载 **USDA FoodData Central 原始全量数据**（Foundation Foods + SR Legacy）入库，翻译食材名称（支持 AI 与机器翻译多后端），在前端营养编辑处提供「匹配 USDA」对话框，让用户搜索 USDA 食材、预览营养素、确认后写入原料/商品。

### 目标

- 原料/商品可手动匹配 USDA 食材，写入其营养数据。
- USDA 原始数据本地化存储，支持下载与手动上传两种入库方式。
- 食材名称全量预翻译（增量、断点续传），支持 6 种翻译后端。
- 后台提供 AI 配置、机器翻译配置、USDA 数据配置三个管理页面。
- 全程与现有营养逻辑解耦，复用现有框架。

### 范围（YAGNI）

- 第一版只做**手动匹配**，不做 AI 自动匹配推荐。
- 只翻译食材 `description`；营养素名称走预设映射表，不消耗 AI。
- 不做 USDA 数据的定时自动更新（手动触发下载/上传）。

---

## 二、与现有系统的关系

- **并存**：新链路与现有 `nutrition_import_service.py`（HowToCook 精简版批量导入）互不干扰。两套数据、两个目的——一个批量自动导入，一个全量可搜索 + 手动精准匹配。
- **复用**：
  - 后端 [admin.py](backend/app/api/admin.py) 后台框架、`MapConfiguration` 配置表模式、APScheduler（异步任务）。
  - 前端 `/admin` 路由与 `AdminDashboard.vue` 布局、`MapSettingsView.vue` 配置表单写法、`PasteImportDialog.vue` 的搜索 autocomplete 交互、现有营养编辑组件（`IngredientDetail.vue` / `ProductDetail.vue`）。
  - 营养数据写入复用现有 `NutritionData`（原料，JSON 三层结构）与 `custom_nutrition_data`（商品）结构，只是数据来源换成 USDA。

---

## 三、架构总览与数据流

三个新层挂在现有系统旁：

| 层 | 职责 |
|---|---|
| USDA 数据层 | 下载/上传原始数据 → 去重 → 入库 → 翻译 → 建内存索引 |
| 翻译服务层 | 抽象 `Translator` 接口，AI/机翻各后端实现 |
| 匹配交互层 | 搜索 USDA → 预览营养 → 确认匹配 → 写入原料/商品 |

**数据流：**

```
[后台]触发下载/上传 → 拉 Foundation+SR Legacy → 解析去重 → 写 usda_food / usda_food_nutrient
   ↓
[后台]触发翻译（6选1后端）→ 批量译 description（增量、断点续传）→ 写回 description_zh
   ↓
应用启动/数据变更 → 构建内存索引（fdc_id, 原文, 译文）
   ↓
[前端]原料/商品营养编辑点「匹配 USDA」→ 搜索（空格分词 OR 子串）→ 预览 → 确认
   ↓
后端写入 service：清空 → (商品额外：复制原料骨架设0) → 写 USDA 营养 → 标记 source + usda_id
```

---

## 四、USDA 数据层

### 4.1 表结构（独立 USDA 仓库，不碰现有营养表）

**`usda_food`（食材主表）**

| 字段 | 说明 |
|---|---|
| `id` | PK |
| `fdc_id` | USDA 唯一 ID，唯一索引 |
| `data_type` | `foundation` / `sr_legacy`（去重排序用） |
| `description` | 原文，如 `Chicken, breast, meat and skin, raw` |
| `description_zh` | 译文，nullable（未翻译为空） |
| `translate_status` | String，翻译状态（`pending`/`done`/`error`），增量用 |
| `publication_date` | 数据集发布日期 |
| `created_at` / `updated_at` | 时间戳 |

**`usda_food_nutrient`（营养素表）**

| 字段 | 说明 |
|---|---|
| `id` | PK |
| `fdc_id` | 关联 `usda_food`，建索引 |
| `nutrient_no` | USDA 营养素编号（映射用） |
| `name` | 原文名，如 `Energy` |
| `name_zh` | 映射后的中文名，如 `能量`（导入时查预设映射表填） |
| `amount` | 数值 |
| `unit_name` | `kcal` / `g` / `mg` / `µg` 等 |

**`usda_task`（任务进度）**

| 字段 | 说明 |
|---|---|
| `id` | PK |
| `task_type` | `download` / `upload` / `translate` |
| `status` | `pending` / `running` / `success` / `failed` |
| `progress` | 进度（已处理/总数等，JSON 或字段） |
| `provider` | 翻译任务用的后端名 |
| `error_log` | 错误信息 |
| `created_at` / `updated_at` | 时间戳 |

数据量预估：Foundation ≈ 4000~5000 + SR Legacy ≈ 7800，去重后约 1 万条食材，营养素行百万级。SQLite/PostgreSQL 均可承载。

### 4.2 下载流程（异步任务）

1. 抓 USDA 下载页拿最新 zip 直链（链接带日期版本，动态抓取，借鉴参考项目 `build_usda_data.py`）。
2. 流式下载 zip → 解析 JSON。
3. **去重**：相同 `description` 只留一条，优先级 `foundation > sr_legacy`，其次营养素更全者胜出。去重在内存里做，保证展示无重复。
4. 入库：按 `fdc_id` upsert（新增插、变更改），支持增量。

> 去重策略已确认：**同 description 去重只留最优一条**，被丢弃的 fdc_id 不入库、不可搜。

### 4.3 手动上传

USDA 数据配置页支持手动上传 zip（Foundation / SR Legacy 官方包）。后端复用与「下载」相同的「解析 → 去重 → upsert 入库」管线，仅数据来源不同（用户上传文件 vs URL 下载）。适用于服务器网络受限、无法直接拉取 USDA 的场景。

### 4.4 翻译增量

`translate_status = 'pending'` 的才翻译，已译跳过——天然断点续传，中断后重跑不浪费。

### 4.5 内存索引

应用启动时（及数据下载/翻译变更后）把所有 `usda_food` 的 `(fdc_id, description, description_zh)` 载入内存，英文小写化预处理，供搜索服务使用。

---

## 五、翻译服务与配置

### 5.1 分工

- **翻译对象**：仅食材 `description`（为搜索匹配服务）。
- **营养素 `name`**：走预设映射表（不消耗 AI）。

### 5.2 Translator 抽象接口

```python
class Translator(Protocol):
    async def translate_batch(self, texts: list[str]) -> list[str]: ...   # 批量译
    async def health_check(self) -> bool: ...                              # 配置页"测试连接"用
```

### 5.3 六个后端实现

| 后端 | 类型 | 关键配置 |
|---|---|---|
| Claude Code | AI | 调本机 `claude` CLI 子进程（需环境装了 claude） |
| OpenAI 兼容 | AI | `base_url` + `api_key` + `model`（兼容 DeepSeek/Ollama/各种代理） |
| Anthropic 兼容 | AI | `base_url` + `api_key` + `model`（base_url 默认官方、可填兼容端点） |
| 百度翻译 | 机翻 | `appid` + `secret` |
| 阿里云 | 机翻 | `access_key_id` + `access_key_secret` |
| DeepL | 机翻 | `auth_key`（free/pro） |

- AI 后端复用参考项目的**食材描述专用 prompt**（要求简洁、括号补细节，如 `Chicken, breast, ..., raw` → `鸡胸肉（生）`）。
- 机翻后端按各自官方签名实现，注意 QPS 限速（阿里云 50、百度/DeepL 按各自 plan）。
- 批大小与并发数可配（默认 AI 每批 ~50、机翻按 QPS 限速）。

### 5.4 营养素映射表

静态 `NUTRIENT_TRANSLATIONS`（200+ 条，从参考项目迁移）+ 现有 `CORE_DISPLAY_MAP`。导入 USDA 营养素时 `name → name_zh` 查表。**查不到的保留英文 `name`**，并记进后台一份「未映射营养素」清单，便于后续补表（不阻塞流程）。

### 5.5 配置存储

新增 `translation_config` 表（JSON 字段，按 `ai` / `machine` 两区分存各 provider 配置 + 各区 `default_provider`）。**密钥存储沿用现有 `MapConfiguration`（地图 API key）的约定**，保持一致。

配置结构示意：

```json
{
  "ai": {
    "providers": {
      "claude_code": {"enabled": true},
      "openai": {"enabled": true, "base_url": "...", "api_key": "...", "model": "..."},
      "anthropic": {"enabled": false, "base_url": "...", "api_key": "...", "model": "..."}
    }
  },
  "machine": {
    "providers": {
      "baidu": {"enabled": false, "appid": "...", "secret": "..."},
      "aliyun": {"enabled": false, "access_key_id": "...", "access_key_secret": "..."},
      "deepl": {"enabled": false, "auth_key": "..."}
    }
  }
}
```

### 5.6 超时

翻译/AI 的 HTTP 客户端单独走 **3600s** 超时（通用 API 仍是 10s），作为后端配置项 `TRANSLATE_HTTP_TIMEOUT = 3600`。AI 批量翻译、Claude Code CLI 子进程耗时长，10s 必爆。

### 5.7 测试连接

每个 provider 配置后可点「测试连接」，调用 `health_check()` 即时验证配置有效。测试连接不通过的 provider，禁止用作翻译任务的后端。

### 5.8 翻译任务执行

USDA 数据配置页点「翻译」时，从 6 个已配置后端中**选一个**（6 选 1）启动异步任务，批量译 `description`：
- 只处理 `translate_status = 'pending'` 的（增量/断点续传）。
- 进度 = 已译/总数，写 `usda_task`，前端轮询。
- 单条失败重试 3 次，最终失败标 `translate_status = 'error'`，不拖垮整批。

---

## 六、搜索服务

### 6.1 内存索引 + OR 召回

严格按需求：**空格分词 → OR 子串匹配**——只要原文或译文命中任意一个子项，都查出来。

```
query = "鸡 胸 raw"  →  tokens = [鸡, 胸, raw]
对每条食材：description 或 description_zh 包含「任意一个」token → 命中入选（宽召回）
排序分：精确匹配 > 前缀 > 包含；命中 token 数越多分越高 → 取 top N（默认 50）
```

- 万级数据内存遍历，毫秒级，先不上 FTS5（YAGNI；数据涨到十万级再考虑倒排索引）。
- 英文大小写不敏感（小写化预处理），中文无此问题。
- 数据下载/翻译变更后重建索引。

---

## 七、匹配写入逻辑

复用现有营养数据结构（原料走 `NutritionData` JSON 外键，商品走 `custom_nutrition_data` JSON），数据源换成 USDA。匹配后记录 `usda_id` 便于将来 USDA 更新时提示重新同步：原料写入 `NutritionData` 的 `usda_id` 字段（模型已有），商品写入 `custom_nutrition_data` JSON 内的 `usda_id`/`source` 字段。

### 7.1 原料匹配（简单）

```
1. 清空原料现有营养数据
2. 取该 fdc_id 的 usda_food_nutrient → 构造 NutritionData（core/all/details 三层，复用现有分层规则）→ 关联到原料
3. source = usda_manual_match（新增枚举值，区别于批量 usda_import），写 usda_id
```

### 7.2 商品匹配

```
1. 清空商品 custom_nutrition_data（如有）
2. 取商品所属原料的营养素「名称集合」→ 在商品 `custom_nutrition_data` 中创建同名营养素条目，值全设 0（骨架，保证维度与原料对齐）
3. 遍历 USDA 营养素：匹配到骨架键的 → 用 USDA 值覆盖；USDA 有但骨架没有的 → 追加
4. source = usda_manual_match，写 usda_id
```

**设计意图**：让商品的营养素维度跟所属原料对齐，实际值优先取 USDA，USDA 没有的留 0。

### 7.3 边界处理

- 商品无所属原料（独立商品）→ 跳过第 2 步骨架，直接写 USDA 数据。
- 所属原料无营养数据 → 同上，骨架为空，等价直接写 USDA。
- `fdc_id` 不存在 → 404。
- 无写权限 → 403。

---

## 八、前后端交互

### 8.1 后台管理页（三个独立页面）

| 页面 | 路由 | 内容 |
|---|---|---|
| AI 配置页 | `/admin/ai-config` | Claude Code / OpenAI 兼容 / Anthropic 兼容 三 provider 的表单（启用、base_url、api_key、model）+ 测试连接 |
| 翻译配置页 | `/admin/mt-config` | 百度 / DeepL / 阿里云 三 provider 的表单（启用、各自密钥）+ 测试连接 |
| USDA 数据配置页 | `/admin/usda-data` | 统计概览（食材总数/已译/未译/营养素数/未映射数）+ 下载按钮 + 手动上传 + 翻译按钮（6 选 1 后端）+ 任务进度条/日志 + 未映射营养素清单 |

复用 `AdminDashboard.vue` 布局与 `MapSettingsView.vue` 配置表单写法。侧边栏导航新增对应菜单项。

### 8.2 前端匹配对话框（可复用组件 `UsdaMatchDialog.vue`，原料/商品共用）

入口：原料/商品营养编辑区，紧挨现有「编辑」按钮加一个「匹配 USDA」按钮。

```
点按钮 → 打开 v-dialog
  ├─ 搜索框（防抖）→ 实时调搜索 API → 结果列表
  │     每条：description 原文 / description_zh 译文 / data_type 标签 / 营养素数
  ├─ 点某条 → 展开营养素预览表（名/值/单位）
  └─ 「确认匹配」→ 二次确认（提示"将清空现有营养数据"）→ 调写入 API → 关闭 → 营养区刷新
```

搜索交互参照 `PasteImportDialog.vue` 的 autocomplete 写法。组件接收 `entityType`（ingredient/product）+ `entityId`。

### 8.3 后端 API 端点

```
# USDA 搜索/详情（登录用户）
GET  /api/v1/usda/search?q=                    → top N 结果
GET  /api/v1/usda/{fdc_id}                     → 食材完整营养素（预览用）

# 匹配写入（校验对原料/商品的写权限）
POST /api/v1/usda/match/ingredient/{id}        body: {fdc_id}
POST /api/v1/usda/match/product/{id}           body: {fdc_id}

# 后台管理（admin only）
GET/PUT /api/v1/admin/translation-config       → 配置读写（含 ai/machine 两区）
POST    /api/v1/admin/translation-config/test  → 测试连接（传 provider+配置）
POST    /api/v1/admin/usda/download            → 触发下载
POST    /api/v1/admin/usda/upload              → 手动上传 zip
POST    /api/v1/admin/usda/translate           → 触发翻译（传 provider，6选1）
GET     /api/v1/admin/usda/task                → 任务进度查询
GET     /api/v1/admin/usda/unmapped-nutrients  → 未映射营养素清单
GET     /api/v1/admin/usda/statistics          → 统计概览
```

### 8.4 权限

- 配置读写 / 下载 / 上传 / 翻译 / 任务查询：**admin only**。
- USDA 搜索 / 食材详情 / 匹配写入：**登录用户**；匹配写入复用现有原料/商品的写权限校验。

---

## 九、数据库迁移与 SQL 脚本

- 提供 alembic 迁移：新增 `usda_food`、`usda_food_nutrient`、`translation_config`、`usda_task` 四张表；`source` 枚举新增 `usda_manual_match` 值。
- 按 CLAUDE.md 要求，本功能**与 PostGIS 无关**，提供 **3 套 SQL 脚本**：SQLite / MySQL / PostgreSQL（PG+PostGIS 与 PG 相同，省略）。

---

## 十、错误处理与边界

- 下载/上传失败 → 任务标 `failed` + 错误日志，可重试。
- 翻译：单条重试 3 次仍败标 `error`，不中断整批；provider 测试连接不过 → 阻止启动翻译任务。
- 匹配写入：`fdc_id` 不存在 → 404；无写权限 → 403；商品无所属原料/原料无营养数据 → 跳过骨架步直接写 USDA。
- USDA 数据未就绪（未下载/未翻译）时，匹配对话框提示「请先在后台下载 USDA 数据」。
- 搜索：空 query 返回空，超长截断。
- 全程保证无语法错误、构建/编译通过。

---

## 十一、测试

- **后端**：
  - Translator 各后端的 mock 测试（不真实调用外部 API）。
  - 搜索 OR 召回 + 排序测试。
  - 去重逻辑测试（同 description、foundation 优先、营养素数优先）。
  - 原料/商品匹配写入测试（含边界：商品无所属原料、原料无营养数据）。
  - 下载/上传解析的单元测试（用小样本 fixture，不真实下载）。
- **前端**：`UsdaMatchDialog` 组件与搜索交互测试。
- 复用现有测试框架（后端 pytest）。

---

## 十二、分阶段实施

每阶段可独立交付：

| 阶段 | 内容 | 产出 |
|---|---|---|
| **① 数据层** | 4 张表 + 迁移 + 3 套 SQL 脚本 + 营养素映射表 + 下载/上传/去重/入库 + 内存索引 + 搜索/详情 API + 统计 API | 能用原文搜 USDA |
| **② 翻译层** | `translation_config` + Translator 抽象 + 6 后端 + 测试连接 + 增量翻译任务（进度）+ 超时配置 | 能批量译、能测连接 |
| **③ 匹配交互** | 匹配写入 service（原料/商品）+ 匹配 API + 前端 `UsdaMatchDialog` + 营养编辑入口 | 核心功能闭环 |
| **④ 后台三页** | AI 配置页 + 翻译配置页 + USDA 数据配置页（统计/下载/上传/翻译 6 选 1/进度/未映射清单） | 管理闭环 |

> 阶段 ② 的翻译配置 API 会先做最小可用页面让阶段跑通，完整三页样式留到 ④ 打磨——实施计划阶段再细化。

---

## 十三、关键决策记录

| 决策点 | 选择 | 理由 |
|---|---|---|
| 数据源 | Foundation + SR Legacy | 覆盖更全（用户选定） |
| 翻译策略 | 全量预翻译 | 搜索体验最佳，支持增量 |
| 营养素名 | 预设映射表对齐 | 零 AI 成本，与现有体系一致 |
| 存储 + 搜索 | 数据库存储 + 内存索引搜索 | 与现有架构一致；OR 子串匹配内存遍历最契合需求 |
| 去重 | 同 description 留最优一条 | 展示无重复，匹配更精准 |
| Anthropic 后端 | 带 base_url | 支持兼容 API 端点 |
| 翻译/AI 超时 | 3600s | 批量翻译与 CLI 子进程耗时长 |
| 后台页面 | AI / 机翻 / USDA 三页独立 | 用户选定 |
