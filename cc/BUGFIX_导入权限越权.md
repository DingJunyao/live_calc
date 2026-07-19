# 导入权限越权修复

- 日期：2026-07-19
- 关联设计：[docs/plans/2026-07-19-导入权限修复-design.md](../docs/plans/2026-07-19-导入权限修复-design.md)、[实现计划](../docs/plans/2026-07-19-导入权限修复.md)
- 测试：[backend/tests/services/test_export_importer_permissions.py](../backend/tests/services/test_export_importer_permissions.py)（21 例全过）

## 问题

多用户权限系统上线后，数据导出有 `full`（管理员全量）/`mine`（个人+可达共享字典）两档。但**导入通道完全没按角色收口**——管理员导出 full 包，普通用户导入后突破所有限制：

- 普通用户凭空创建管理员专属的黑名单分组定义
- 普通用户导入即获得 `is_public=True` 菜谱，绕过发布审核工作流
- 管理员的个人行为数据（价格记录、家/公司地点、个人黑名单、分组订阅）被克隆到普通用户名下，污染其成本计算与个人视图
- 共享字典（原料/商品/商家/营养）被普通用户身份裸写，绕过提议-审核框架

## 根因（三层缺口）

1. **入口** [import_api.py:33](../backend/app/api/import_api.py#L33) `POST /data/upload` 用 `get_current_user`——设计意图是保留普通用户导入「系统导出格式」的能力，但「系统导出格式」恰恰是最敏感的全量数据格式
2. **闸门** [api_service.py](../backend/app/services/importer/api_service.py) `import_from_upload_path` 只对 HowToCook 格式拦普通用户，EXPORT 格式完全放开
3. **漏洞主体** [export.py](../backend/app/services/importer/importers/export.py) `ExportImporter`：仅依赖 `self.user_id`，全文无 `is_admin` 判定；菜谱 `is_public=True` 硬编码；admin-only 数据（黑名单分组、单位换算、商品条码、营养）一律裸 `db.add`

## 修复方案

给 `ExportImporter` 注入 `is_admin` + 从 manifest 读 `scope`，导入时按「角色 × scope × 数据桶」三维分流。**入口不动**（保留普通用户导入迁移能力），权限收口放在 importer 内部。

### 分流矩阵（普通用户；管理员全量直写不变）

| 数据桶 | full 包 | mine 包 |
|---|---|---|
| admin-only·结构（黑名单分组定义/映射） | 跳过 | 跳过 |
| admin-only·字典（单位换算、商品条码） | 跳过 | 跳过 |
| 共享字典（单位/分类/层级/密度/原料/商品/商家） | 复用或新建（`created_by`=当前用户，auto 级） | 复用或新建 |
| 营养数据 | 复用或新建，`is_verified` 强制 False | 同左 |
| 菜谱 | 强制 `is_public=False`，作者=当前用户 | 恢复原 `is_public` |
| 价格记录 | 查重导入；非自己的 `purchase` 降为 `price`（不计支出） | 查重导入（同左降级规则） |
| 地点/个人黑名单/分组订阅 | 跳过（他人隐私） | 恢复（改归属） |

跳过不抛错、不中断，计入 `result.skipped` 字典（按桶计数）。管理员导入任意包维持现状（全量直写、`is_public`/`is_verified` 保留原值）。

**价格记录特殊处理**（2026-07-19 需求修正）：价格记录不再 full 跳过，改为查重导入——价格参考对所有用户有公开聚合价值。查重按「除 id/审计字段外业务字段全相同」判定（`recorded_at` 缺失时不参与，因 `server_default=now()` 不可预测），命中则跳过计入 `skipped.price_records_duplicate`。归属改当前用户；**非自己的购买记录**（原 `user_id` ≠ 当前用户 + `record_type=purchase`）**降为 `price`**（不计支出，避免把别人的支出算给自己）；自己的 purchase 保留。

### 关键决策（brainstorming 拍板）

1. 整体方向：**两者兼顾**——既堵越权又保留迁移能力，按权限逐桶精细处理（非简单拒绝）
2. 共享字典不存在时：**直写新建**（auto 级，数据源是管理员授权包，接受轻微越权；不爆审核台）
3. 私人数据 full 包：**跳过** / mine 包：**恢复**（价格记录会污染成本计算、地点含坐标隐私）
4. 营养 `is_verified`：普通用户导入**强制降级 False**（避免借导入自证核验）
5. mine 包菜谱：**恢复原 `is_public`**（自己的备份搬回来，本人发布的菜谱保持 public）

## 改动文件

- [models.py](../backend/app/services/importer/models.py)：`Importer.__init__` 加 `is_admin`、`ImportResult` 加 `skipped` 字典
- [export.py](../backend/app/services/importer/importers/export.py)：`__init__` 接收 `is_admin` + `self.scope`、加 `_skip()` 辅助、`import_all` 读 manifest scope、各 `_import_*` 按桶分流（黑名单分组/换算/条码跳过、营养降级、菜谱分 scope、个人数据 full 跳过）、商品字段补读、新增 `_import_entity_unit_overrides`、`tags` 序列化
- [api_service.py](../backend/app/services/importer/api_service.py)：四个入口透传 `is_admin`（upload/upload_path 用传入值，git/local 传 `True`）、`_run_import_task` 把 `result.skipped` 合进 `task.stats`
- [ImportUploadDialog.vue](../frontend/src/components/import/ImportUploadDialog.vue)：导入结果区分 `displayStats`（排除 skipped）与 `skippedItems` 摘要展示

## 附带修复（与权限无关，顺手）

- **商品字段补全**：`_import_products` 原只读 name/brand/aliases/tags，补读 `barcode`/`image_url`/`custom_nutrition_data`/`custom_nutrition_source`（对齐 [serializers.py:309-326](../backend/app/services/export/serializers.py#L309) 导出字段）
- **entity_unit_overrides 补导入**：导出端 [packaging.py:445](../backend/app/services/export/packaging.py#L445) 已含此表，importer 原完全不读取（数据丢失），新增 `_import_entity_unit_overrides` 方法 + import_all 注册
- **商品 tags 序列化**：`Product.tags` 是 `String(500)`（JSON 字符串列，对齐 API `serialize_tags`），但既有 `_import_products` 传 `tags=item.get("tags", [])`（list）——包里无 tags 时空 list 绑 String 列崩（被 import_all 的 try/except 吞，商品静默建不出来）。改为 `serialize_tags` 序列化（兼容包里已是字符串的情况）。这是既有潜伏 bug，agent 报告曾提及「Product.tags 缺字段时 list 绑 SQLite 崩」，本次 Task 7 触发并修复

## 验证

- 权限分流测试 21 例全过（[test_export_importer_permissions.py](../backend/tests/services/test_export_importer_permissions.py)）：含 is_admin/scope 基建、admin-only 三项跳过、营养降级、菜谱分 scope、个人数据 full 跳过/mine 恢复、商品字段、entity_unit_overrides、端到端综合（full 包普通用户一次导入所有越权点）+ mine 包 roundtrip
- 后端 py_compile + compileall importer 通过
- 前端 build 通过（48.86s，precache 128 entries 不变）
- `test_import_api.py` 回归：3 过 1 预存失败（`test_upload_rejects_non_zip` 卡在 `_admin_token()` 登录 401，真实库用户状态问题，与本次改动无关）
- TDD 全程红→绿，每个 task 先写失败测试再实现

## 不在本次范围

- HowToCook 格式导入（本就 admin-only）
- 导出端（导出权限已正确）
- change_proposals 框架本身
- 用户偏好类表（`UserProductWeightOverride`/`UserMerchantFavorite`/`UserMerchantProductOrder`）导入——导出/导入当前均未涵盖
- `Product.barcode` unique 撞约束（导出包本身问题，保留既有 db.flush 兜底）

## 教训

- **旁路通道要和正门同一套权限**：UI 上权限收得再紧，导入/导出/批量 API 这类旁路漏一个就全破。权限审计要覆盖所有数据写入路径，不只 CRUD 端点
- **try/except 吞异常是隐形 bug 温床**：`import_all` 的整体 try/except 把 `_import_products` 的 tags 崩吞掉，商品静默建不出。批量导入的子步骤异常应尽量暴露到 skipped/errors，而非整体 rollback
- **`String` 列存 JSON 要序列化**：`Product.tags=String` 注释「JSON 字符串」，但导入传 list 崩——存 JSON 用 `serialize_tags`/JSON 列二选一，别混
- **TDD 红绿逼出潜伏 bug**：Task 7 写测试才发现商品建不出来（tags 崩），若直接改实现不写测试，这个既有 bug 会继续潜伏
