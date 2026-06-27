# 多用户权限系统设计

> 日期：2026-06-27 ｜ 状态：待 Review ｜ 作者：权限改造专项

## 1. 背景与目标

本系统（生计 - 生活成本计算器）需要支持多用户，但现有大量操作仍按「单用户（管理员）」心智编写，权限管控要么缺失、要么过松、要么对「共享数据」的归属含糊。

本设计的目标：

1. **排查**全部 API 操作的权限现状，定位漏洞与不一致；
2. **建立**一套清晰、可扩展的多用户权限模型，覆盖个人数据、共享知识库、公开内容、管理员专属四类场景；
3. **落地**一套通用的「提议—审核」框架治理共享数据写入，并预留自动审核扩展点。

设计原则：KISS（匿名化只做最低必要）、YAGNI（信誉体系等暂不做）、DRY（一套审核框架管全部共享写入）。

---

## 2. 现状审计：问题地图

> 基于对 `backend/app/api/` 全部 24 个路由文件的只读审计。个别端点细节在实现阶段需复核，但整体问题模式清晰。

### 2.1 🔴 完全裸奔（连登录都不要）

| 位置 | 问题 |
|---|---|
| `units.py` 整个模块 | 单位、换算关系、实体单位覆盖、密度的增删改查**全部无鉴权** |
| `products_entity.py` 部分 GET | 商品列表/详情/价格/autocomplete 等**无鉴权** |

### 2.2 🟠 写权限太松（任何人能改共享或他人数据）

| 位置 | 问题 |
|---|---|
| `nutrition.py` | `/{id}/nutrition`、`/correct` 任意用户可改任意原料/商品营养；`latest-price(-by-merchant)` 跨用户读价格 |
| `usda.py` | `/match/ingredient`、`/match/product` 任意用户可改任意食材/商品营养 |
| `ingredient_hierarchy.py` | 层级关系增删改任意用户可操作共享结构；`merge-history` 全员可见 |
| `ingredient_extended.py` | 硬删除任意用户可永久删共享食材 |
| `products_entity.py` | 商品条码、导入别名写操作无所有权校验 |

### 2.3 🟡 数据越权读取

| 位置 | 问题 |
|---|---|
| `export.py` `GET /data scope=full` | 普通用户可导出全库（含他人菜谱/支出），待复核是否已限管理员 |
| `recipes.py` `GET /{id}/images` | 无所有权/公开校验 |

### 2.4 ⚪ 技术债

管理员校验写法不统一：`Depends(get_current_admin_user)`（admin/invite_codes）vs 手动 `if not is_admin`（import_api / agent_api / usda_admin）。

### 2.5 ✅ 已合规（保持不动）

- **用户管理全链路**（`auth.py` 的 `/users/*`）：列表/详情/创建/改密/提权/禁用全部 `get_current_admin_user` + `_check_user_safety`（禁操作自己、禁动 id=1 初始管理员）。改密时 bump `token_version` 作废旧 token。
- **个人数据隔离范本**：价格记录、支出、常用地点、食材偏好、黑名单+订阅、商家排序、每日推荐——都正确按 `user_id` 隔离。
- **管理员专属正确**：邀请码、地图/系统配置、Agent 驱动（`_require_admin`）、全局导入、USDA 管理、报告/迷你图（用户隔离）。

---

## 3. 数据分类：六个权限桶

系统数据按「谁能看 / 谁能写」分为六桶，是全部权限规则的根分类。

| 桶 | 谁能看 | 谁能写 | 装的数据 |
|---|---|---|---|
| **① 个人私密** | 仅本人 | 仅本人 | 支出(Expense)、购买记录(PURCHASE)、常用地点、食材偏好、黑名单+订阅、商家排序、每日推荐、营养目标/预算、自己的任务/会话 |
| **② 价格·公开聚合** | 所有人 | 本人录原始价；对外只给去标识聚合 | ProductRecord·PRICE 与 PURCHASE 单价 → 聚合视图 |
| **③ 客观存在·共享池** | 所有人 | 提议→审核 | 商家、商品实体(含条码/别名)、食材、食材分类 |
| **④ 共享知识库** | 所有人 | 提议→审核 | 营养数据+映射、单位+换算、实体单位覆盖、密度、食材层级关系、食材合并 |
| **⑤ 公开内容** | 所有人 | 作者发布 / 发布后共建共编 | 公共导入菜谱(source)、自创菜谱(发布后) |
| **⑥ 管理员专属** | 管理员 | 管理员 | 用户管理、邀请码、系统/地图配置、Agent 驱动、全局导入、USDA 任务、操作日志、全量导出、标准单位维护 |

---

## 4. 已锁定的策略决策

| # | 决策 |
|---|---|
| 1 | **愿景**：全面社区共建。价格信息公开聚合，支出/购买记录私有且不可反推 |
| 2 | **菜谱**：自创默认私有；发布需管理员审核；发布后共建共编（任何人编辑都走审核）；**作者不可撤回/删除，管理员可删** |
| 3 | **商家**：转社区共享池，「收藏」替代原私有归属；新增自由、改/删走审核 |
| 4 | **审核者**：仅管理员 |
| 5 | **审核策略三档**（按 `entity_type + action` 可配）：`auto_approve` / `auto_review` / `manual`，预留 `ProposalAutoReviewer` 接口 |
| 6 | **合并**：人工审核 + 影响预览 + 待审互斥 + 回滚窗口 |
| 7 | **价格匿名化**：唯一硬约束——对外输出剥离 `record_type` 与 `user_id`；不引入 k-匿名/时间模糊等重武器 |
| 8 | **落地架构**：通用 `change_proposals` 表 + 类型执行器 |
| 9 | **管理员超级权限**：管理员的所有写操作（全层面 CRUD）直写生效，绕过提议-审核框架；菜谱创建即发布；可管理任意用户的个人数据。单用户场景下管理员即唯一用户，整套审核对自我操作纯属多余 |

---

## 5. 目标设计

### 5.1 个人数据与管理员专属修复（节 A）

**越权读取修复**

| 端点 | 修复 |
|---|---|
| `export.py` `GET /data scope=full` | `full` 限管理员；普通用户强制 `mine` |
| `nutrition.py` `latest-price(-by-merchant)` | 改读公开价格聚合视图（5.2 建成后）；过渡期加 `user_id` 过滤 |
| `ingredient_hierarchy.py` `merge-history` | 限管理员，或仅返回本人发起的 |
| `recipes.py` `GET /{id}/images` | 校验：本人 OR 公开菜谱 OR 管理员 |

**鉴权缺失与统一修复**

| 现状 | 修复 |
|---|---|
| `units.py` 全模块无鉴权 | GET 登录可读；写操作并入 5.3 提议框架；标准单位管理员直写 |
| `products_entity.py` 部分 GET 无鉴权 | 加 `get_current_user`（共享池登录可读） |
| 商品条码/别名写操作无所有权 | 并入 5.3 提议框架 |
| 手动 `if not is_admin`（import_api / agent_api / usda_admin） | 统一为 `Depends(get_current_admin_user)` |

### 5.2 价格公开聚合与匿名化（节 B）

**唯一硬约束**：所有社区可见的价格输出，**剥离 `record_type` 与 `user_id`**。其余字段（price / product / merchant / time）可公开。PURCHASE 单价与 PRICE 一样纳入聚合——去标识后两者无法区分，正满足「看不出是纯记录还是支出」的要求。

**物化汇总表** `product_merchant_price_summary`（写入价格记录时增量更新，定位为查询加速而非匿名）：

```
product_id, merchant_id, sample_count, recent_price, avg_price_30d,
min_price, max_price, last_updated_at   -- 不存任何 user/record_type 信息
```

**对外接口改造**：`products_entity.py` 与 `nutrition.py` 的 `latest-price` 系列改读汇总表；个人的「我的价格记录」仍走 `GET /products`（私有，带 `user_id` 过滤，本人可见全字段含 `record_type`）。

**PURCHASE 行为本身**（数量、购买事实）完全私有，仅本人可见；支出统计走 Expense + PURCHASE。

### 5.3 通用提议—审核框架（节 C）

一套通用表管所有共享数据的提议，每种数据挂一个执行器。

**通用提议表 `change_proposals`**

| 字段 | 说明 |
|---|---|
| `id` | 主键 |
| `entity_type` | ingredient / nutrition / unit / merchant / hierarchy / merge / recipe_publish / … |
| `entity_id` | 操作对象（新增时空） |
| `action` | create / update / delete / merge |
| `payload_json` | 变更内容 |
| `review_policy` | auto_approve / auto_review / manual（按 entity_type+action 默认值，可被管理员覆盖） |
| `status` | pending / auto_approved / approved / rejected / applied / reverted |
| `proposer_id` | 提议人 |
| `reviewer_id` | 审核人（人工时填；自动审核为 NULL） |
| `revert_payload` | apply 时生成的逆向操作（供回滚） |
| `revertable_until` | 回滚窗口截止时间（高风险专属，如 apply 后 7 天） |
| `created_at / reviewed_at / applied_at` | 时间戳 |

**类型执行器接口**（每种 `entity_type` 注册一个）

```
validate(proposal) → 合法性校验
preview(proposal)  → 影响预览（合并时列出「会影响 12 个菜谱、3 个是别人的」）
apply(proposal)    → 事务内执行，并生成 revert_payload
revert(proposal)   → 用 revert_payload 原路还原
```

**流转**

1. 用户提议 → 按 `entity_type + action` 查 `review_policy`：
   - `auto_approve` → 直接 apply，status=auto_approved
   - `auto_review` → 调 `ProposalAutoReviewer`：approve→apply；escalate→pending 转人工；reject→rejected
   - `manual` → pending 等管理员
2. 管理员在统一审核台审批 → approved 执行 apply / rejected 驳回
3. 高风险（合并/删除）apply 后进入回滚窗口（默认 7 天），窗口内管理员可一键 revert
4. 待审期间同类互斥：某食材已有 pending 合并，再提涉及它的合并被挡

**鉴权**

| 操作 | 权限 |
|---|---|
| 提交提议 `POST /proposals` | 任意登录用户 |
| 审核 `POST /proposals/{id}/review` | 仅管理员 |
| 回滚 `POST /proposals/{id}/revert` | 仅管理员 |
| 查看提议列表 | 管理员看全部；普通用户看自己提交的 |

**合并特殊处理**（套在通用框架上）：`manual` + 强制 `preview` + apply 时把每条迁移引用记进 `revert_payload`（回滚即照映射表逐条还原）+ 待审互斥。

**管理员超级权限（直写）**：管理员的**所有**写操作绕过提议-审核框架直接生效——涵盖共享数据 CRUD、菜谱创建即发布、以及对任意用户个人数据的管理（管理员=系统所有者，可信）。为避免逻辑分裂，共享写端点统一采用「分流」模式：管理员调用 → 直接 `执行器.apply()`；普通用户调用 → 生成 `change_proposal` 走审核，通过后再 `执行器.apply()`。**执行器的 apply 是唯一执行核心，差别只在「是否先审」**。Agent、全局导入、USDA 同理直写。框架只管「普通用户对共享数据的写入」。

**菜谱发布与发布后编辑**都走通用框架：发布 = `entity_type=recipe, action=publish`（manual，apply 时置 `is_public=true`）；发布后编辑 = `action=update`（manual，任何人含原作者均走审核）。作者无撤回权，故不向作者提供 unpublish 提议类型；管理员删除发布后菜谱走管理员直写，不经框架。发布前（私有态）的增删改仍是作者自由操作，不经框架。

### 5.4 审核策略层与预留接口

**预留接口** `ProposalAutoReviewer`（协议/抽象基类）：

```
review(proposal, context) → AutoReviewResult(
    decision: "approve" | "escalate" | "reject",
    reason: str
)
```

- **本期只留接口 + 默认实现（全部 escalate，等价 manual）**，具体判定逻辑（规则引擎 / AI / 库内比对）后续再填。
- 管理员在后台为每种 `entity_type + action` 选择三档之一。
- 这一抽象统一了「反垃圾兜底」与「选审核方式」——它们是同一策略层的不同配置值。

### 5.5 各类共享数据治理总表（节 D）

**自动** = auto_approve；**人工** = manual；**补空** = 营养数据特例；🔒 = 不走框架的硬规则。所有「人工」档都挂 auto_review 接口，管理员可切。**注：本表针对普通用户；管理员的所有操作直写生效，不受 auto/manual 约束（含菜谱创建即发布、可删任意发布后菜谱）。**

| 数据 | 新增 | 编辑 | 删除 | 特殊 |
|---|---|---|---|---|
| 食材 | 自动 | 人工 | 人工+回滚 | 合并：人工+预览+互斥+回滚；硬删除也升人工+回滚 |
| 营养数据 / 映射 | 补空自动 / 有数据人工 | 人工 | 人工 | USDA 匹配写入：有数据→人工 |
| 标准单位(公制/市制/英制)及换算 | 🔒管理员直写 | 🔒管理员直写 | 🔒管理员直写 | 不进框架 |
| 模糊量/自定义单位 | 自动 | 人工 | 人工 | 等同实体单位覆盖模型 |
| 实体单位覆盖/密度 | 自动 | 人工 | 人工 | — |
| 食材层级关系 | 人工 | 人工 | 人工 | 涉及成本，全审（含改强度） |
| 商家（转共享池后） | 自动 | 人工（坐标高危） | 人工+回滚 | 收藏：个人私有，不走框架 |
| 商品实体(条码/别名) | 自动 | 人工 | 人工+回滚 | 条码增删：人工 |
| 食材分类 | 人工 | 人工 | 人工 | — |
| 菜谱·发布前 | 私有 | 作者自由 | 作者自由 | — |
| 菜谱·发布 | — | 人工审核 | — | 通过后变公开共建 |
| 菜谱·发布后 | — | 人工（任何人，含原作者） | 🔒作者不可删/撤回；管理员可删 | 共建资产，引用断链需提示 |

**补充规则**

- **营养数据「补空 vs 覆盖」**：执行器在 validate 时检查目标字段/记录是否已有数据。无数据→新增走 auto_approve；有数据→覆盖走 manual。
- **标准单位 vs 模糊单位**：`Unit` 表加标识区分。标准单位（公制/市制/英制及其换算）仅管理员直写，不进框架；模糊量/计数单位（如「一把」「一勺」）走自定义单位模型，权限同实体单位覆盖。
- **公开菜谱被引用**：发布后菜谱被管理员删除、或其内容被编辑审核通过变更时，需检测「半成品成本链」引用并提示影响（与合并影响预览同理，不悄悄断链）。

### 5.6 迁移、鉴权统一与测试（节 E）

**数据迁移**

| 对象 | 迁移动作 |
|---|---|
| 商家 | `user_id` 保留改义为「录入者」；新建 `user_merchant_favorites(user_id, merchant_id)` 承载「常用」；现有「拥有」语义转成「收藏」 |
| 重复商家 | 同一超市被多人各录一份 → **全部保留进共享池 + 提供商家合并工具**（复用合并执行器），管理员手动清理。不做自动去重（误合风险） |
| 价格记录 | `ProductRecord` 表不动，对外查询改走去标识聚合 |
| 单位 | `Unit` 表加 `is_standard`/`unit_system` 标识，区分标准与模糊量；存量标准单位回填标记 |
| 菜谱 | `Recipe` 加 `is_public` 字段（`source` 保留作导入来源） |
| 新表 | `change_proposals`、`product_merchant_price_summary`、`user_merchant_favorites` |

按项目规范，每种表结构变更配 SQLite / MySQL / PostgreSQL / PostgreSQL+PostGIS 四套 SQL 脚本 + alembic 迁移。

**鉴权统一**

- 手动 `if not is_admin`（import_api / agent_api / usda_admin）→ `Depends(get_current_admin_user)`
- `units.py` 等无鉴权端点补 `get_current_user`（读）/ 提议框架（写）
- 所有共享数据写操作收口到 `POST /proposals`；管理员直写路径保留

**测试策略**

- **执行器单测**：每种 entity_type 的 validate/preview/apply/revert，尤其合并的回滚完整性（迁移的引用能全部还原）
- **权限矩阵**：参数化测试（匿名/普通用户/管理员 × 各端点）——匿名 401、越权 403、合法 200
- **关键场景**：
  - 合并影响预览准确 + 回滚全还原
  - 营养「补空自动/覆盖人工」分支
  - 价格聚合输出**断言不含 `record_type`/`user_id`**
  - 菜谱：发布后作者不能撤回/删除、管理员能删、发布后编辑走审核
  - 待审互斥
  - 审核策略三档切换 + auto_review 接口接入（默认 escalate）

---

## 6. 数据模型变更总览

**新增表**

- `change_proposals`：通用提议（字段见 5.3）
- `product_merchant_price_summary`：价格聚合汇总（字段见 5.2）
- `user_merchant_favorites`：用户商家收藏（user_id, merchant_id, created_at）

**新增字段**

- `Unit`：`is_standard`(Boolean) 与/或 `unit_system`(String: metric/market/imperial/custom)
- `Recipe`：`is_public`(Boolean, default=false)

**字段改义（不改结构）**

- `Merchant.user_id`：从「拥有者」改义为「录入者」；写入与可见性改由共享池规则决定

**代码层（非表）**

- `ProposalAutoReviewer` 协议 + 默认实现（全部 escalate）
- 各 entity_type 的执行器（ingredient / nutrition / unit / merchant / hierarchy / merge / recipe_publish）

---

## 7. 实现优先级建议

| 阶段 | 内容 | 价值 |
|---|---|---|
| **P0 堵漏** | units.py 补鉴权；export full 限管理员；商品/营养/usda 写权限补所有权或转提议；手动 is_admin 统一 | 消除现存安全洞，风险最高优先 |
| **P1 框架** | change_proposals 表 + 执行器注册机制 + 统一审核台 API + ProposalAutoReviewer 接口（默认 escalate） | 共享治理的底座 |
| **P2 共享转型** | 商家转共享池 + 收藏；价格聚合表 + 去标识输出；菜谱 is_public + 发布审核 | 兑现社区共建愿景 |
| **P3 增强** | 商家合并工具；auto_review 具体判定实现；反垃圾「一键回退某用户全部提议」 | 体验与治理增强 |

P0 与 P1 之间无强耦合，可并行；P2 依赖 P1 框架就绪；P3 为后续迭代。

---

## 8. 开放项与风险

- **`export.py scope=full` 现状待复核**：实现阶段需确认是否已限管理员；若已限则该条从 P0 移除。
- **管理员审核负担**：单管理员在用户量增长后可能成为瓶颈。`auto_review` 接口是为此后埋的扩展点；版主/社区投票机制明确列为 YAGNI，暂不做。
- **菜谱发布不可逆**：作者发布后失去独占控制，需在前端发布流程强提示。若后续需「转让所有权」或「作者退出署名」，另立设计。
- **价格聚合的增量更新一致性**：写入价格记录触发汇总更新时，需处理并发与失败重试，避免汇总表漂移。
- **历史数据中的「重复商家」**：迁移后共享池初始存在重复项，依赖管理员手动合并；在合并完成前，价格聚合会按「多个商家实体」分别统计，不影响正确性，仅影响聚合密度。
- **管理员直写无审核兜底**：超级权限下管理员误操作（误删共享食材、误合并等）无人工审核拦截，依赖执行器的 `revert_payload` 与回滚窗口兜底。这是单用户/少用户场景的有意取舍。
