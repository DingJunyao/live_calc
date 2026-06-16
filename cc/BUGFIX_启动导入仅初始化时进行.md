# 启动导入仅在数据库初始化时进行

## 背景

应用启动时（`main.py` 的 `lifespan`）会导入菜谱等初始数据，此前每次重启都会执行：

- `init_default_data`（单位/分类）—— 已有幂等检查（`Unit` 存在则跳过）
- 菜谱/原料/营养数据导入 —— **缺乏顶层"已初始化则跳过"判断**
- 批量建商品 —— 已有幂等检查（`product_count == 0` 才建）

其中菜谱导入分两条路径：

- 远程路径 `check_and_import_initial_recipes` 内部**有**短路（查到 `source=json_repo` 的菜谱就跳过）
- 本地路径 `import_from_local_dir` **没有**顶层短路——每次重启都会重新遍历几百个数据文件做检查、重复执行营养增量导入（`check_and_import_nutrition(mode="incremental")`）。虽子函数对单条记录幂等，但整体开销大且无意义。

## 方案

在 `main.py` 的 `lifespan` 导入流程**外层加统一判断**：若数据库已存在初始导入的菜谱（`Recipe.source == "json_repo"` 的记录数 > 0），视为已初始化，直接跳过整个导入块（本地/远程均跳过）。

判据选用 `source == "json_repo"`，与远程路径既有短路逻辑一致，两条路径行为统一；原料导入是菜谱导入的前置步骤，菜谱导入完成即视为初始化完成，中间态会在下次启动时自我修复（原料导入幂等跳过已有项）。

## 改动文件

- `backend/app/main.py`：`lifespan` 导入块外层加 `imported_count` 判断，已初始化则只打日志不导入；首次初始化逻辑（本地/远程分支）整体下移到 `else` 内。

## 如何重新导入

启动导入默认只在首次进行。如需重新导入初始数据：

- 通过管理接口触发（`check_and_import_initial_recipes(..., force_reimport=True)`）
- 或先清空 `source='json_repo'` 的菜谱后重启，启动时会重新进入导入流程
