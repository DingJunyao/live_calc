# 数据导出功能

## 概述
个人中心「数据导出」：把当前用户可见的数据序列化为标准 JSON，连同图片打包成 zip，同步流式下载。菜谱/食材/营养/单位格式参考 HowToCook_json/out（兼容 + id 扩展），其余数据制定独立规格。

## 两档导出（scope）
- `full`：全量——我的 + 管理员/系统创建的所有数据。
- `mine`：仅我的——`user_id`/`created_by` 归属当前用户的数据，**加上可达性保证**（我引用到的管理员数据一并带上，避免导入后引用悬空）。

## 导出范围
- **核心三类（HowToCook 兼容 + id 扩展）**：菜谱（`recipes/*.json`，每菜一文件）、食材（`ingredients.json`，dict 聚合）、营养（`nutritions.json`，数组，嵌套→扁平 + raw_nutrients 保留）、单位（`units.json`，数组）。
- **扩展知识库**：unit_conversions、ingredient_categories、ingredient_hierarchy、entity_densities、products、product_barcodes、product_ingredient_links。
- **账户交易数据**：price_records、merchants、favorite_merchants。
- **不含**：地图配置/用户食材偏好/区域单位设置/实体单位覆盖等设置数据；菜谱成本历史/AI 匹配记录/营养编辑历史等派生数据。

所有外键冗余一个 `_name` 字段（如 `ingredient_id` + `ingredient_name`），便于人眼阅读与将来导入容错。

## 图片
菜谱图、商品本地图打包进 `images/`，json 内用相对路径（剥离 `/static/` 前缀）；外链 `http(s)://` 跳过并记入 `manifest.notes`。

## 顶层 manifest.json
记录 format_version、app_version、exported_at、scope、exported_by_user_id、schema（HowToCook 兼容 + 扩展分类）、counts（各表条数）、image_summary、errors（单表隔离）、notes。

## 架构
后端按职责拆分（`backend/app/services/export/` 包）：
- `serializers.py` — 13 个序列化纯函数 + 类型转换器（to_float/to_iso/convert_image_path）
- `reachability.py` — `ExportSet` dataclass + `collect_full_set`/`collect_mine_set` + `_collect_ingredient_closure`（不动点遍历，双向层级扩张）
- `packaging.py` — `build_export_zip` 编排（查询→名字映射→序列化→图片→zip），`_safe_build` 单表错误隔离，批量 name 预取避免 N+1
- `__init__.py` — `export_data(db, user, scope)` 主入口
- `backend/app/api/export.py` — `GET /data?scope=full|mine` 端点，`StreamingResponse` 流式返回 application/zip

前端：`ProfileView.vue` 数据导出对话框（全量/仅我的 radio + loading overlay），因 `api/client.ts` 拦截器无条件解包 response.data，下载用原生 axios 保留 Content-Disposition + Blob。

## API
`GET /api/v1/export/data?scope=full|mine`（JWT 鉴权，返回 application/zip，Content-Disposition 带 `export_YYYYMMDD_HHMMSS.zip`）

## 测试
- `tests/services/test_export_serializers.py`（30 单元测试）
- `tests/services/test_export_reachability.py`（2 集成测试）
- `tests/services/test_export_packaging.py`（2 服务层测试）
- `tests/test_export.py`（4 端点 + HowToCook 兼容性测试）
- 共 39 个，全绿。

## 设计/计划文档
- 设计 spec：[docs/superpowers/specs/2026-06-15-data-export-design.md](../docs/superpowers/specs/2026-06-15-data-export-design.md)
- 实现计划：[docs/superpowers/plans/2026-06-15-data-export.md](../docs/superpowers/plans/2026-06-15-data-export.md)

## 备注
- 本期只做导出，格式按可导入标准设计（带 id/外键映射），但**未实现导入功能**。
- `collect_full_set` 实际查询全表填充集合（而非返回空集），但 `packaging._query` 用 `full_mode` 标记判断（full 不加 id 过滤），二者兼容。
- 参考导入服务：`enhanced_recipe_import_service.py`（HowToCook 格式按名字匹配，导出格式与之对称）。
