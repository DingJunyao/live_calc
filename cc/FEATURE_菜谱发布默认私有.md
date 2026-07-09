# 菜谱发布默认私有

## 需求

用户创建菜谱默认私有，只有点菜谱详情的「发布」按钮才发布；发布对作者不可逆；详情页导航栏对未发布菜谱提供发布按钮。发布仍走提议-审核框架（普通用户待审、管理员直写）。

## 根因（比表面深）

`source` 字段语义重载——既表「来源」（custom/json_repo/import/howtocook:xxx），又表「是否公共」。共享转型引入 `is_public` 本想分离，但没清理 `source` 的「公共」残留：

- [recipe.py:27](backend/app/schemas/recipe.py#L27) `RecipeCreate.source` 默认 `"custom"`（非空）
- 全系统把「source 非空」当「公共/已发布」：列表 [recipes.py:181](backend/app/api/recipes.py#L181) `or_(source != None, is_public)`、前端 [RecipeDetail.vue:559](frontend/src/views/recipes/RecipeDetail.vue#L559) `isPublished = is_public || !!source`
- 故自创菜谱 source='custom' 非空 → 立刻「已发布」、对所有人可见、发布按钮永不出现
- 叠加 [recipes.py:111-113](backend/app/api/recipes.py#L111) 管理员创建即 `is_public=True`
- 附带漏点：详情可见性只看 source 非空，别人自创私有菜谱详情其实能被看到

## 方案 A（已选定，非 B）

「公共/已发布」一律以 `is_public` 为唯一准绳，`source` 回归来源标识本职。未选方案 B（source 默认改 None），因其仍把公共语义挂在 source 上、治标不治本。

## 改动

**后端创建侧：**
- [create_recipe](backend/app/api/recipes.py#L111) 删管理员即发布，所有用户默认 `is_public=False`
- 5 处导入创建点补 `is_public=True`：[recipe_import_service:836](backend/app/services/recipe_import_service.py#L836)、[howtocook:207](backend/app/services/importer/importers/howtocook.py#L207)、[export:327](backend/app/services/importer/importers/export.py#L327)、[enhanced_recipe_import:671](backend/app/services/enhanced_recipe_import_service.py#L671)、[json_recipe_import:369](backend/app/services/json_recipe_import_service.py#L369)

**后端判断侧（source → is_public，9 处）：**
- 列表公共分支 181、详情可见性+fallback、update_recipe/upload_image 的 `is_public_or_source`、merchant-costs 807、配图/成本历史/区间成本 3 处可见性校验（recipes.py）
- [nutrition.py:839](backend/app/api/nutrition.py#L839) 批量菜谱可见性
- 顺带把变量名 `is_public_or_source` → `is_public_recipe`（方案 A 下不含 source，清 misnomer）

**数据迁移（必要）：**
判断只看 is_public 后，导入菜谱（source 非空但 is_public=False）会瞬间变私有，必须补 is_public=True：`UPDATE recipes SET is_public=true WHERE source IS NOT NULL AND source<>'custom' AND is_public=false`。alembic [20260709_0001](backend/alembic/versions/20260709_0001_recipe_import_default_public.py) + 三引擎 SQL。存量 custom 菜谱不动（靠 is_public 自动回归私有）。

**前端：**
- [RecipeDetail.vue:559](frontend/src/views/recipes/RecipeDetail.vue#L559) `isPublished` 去 `|| !!source`
- 状态 chip：删「已发布」chip；加「未发布」chip（`v-else-if="!isPublished"`，与「审核中」互斥）——已发布不显示状态，未发布才提醒
- 发布加二次确认 v-dialog（提示「发布后无法自行撤回」），`handlePublish` 拆成开对话框 + `confirmPublish` 提交
- [RecipesView.vue:83](frontend/src/views/recipes/RecipesView.vue#L83) 列表「未发布」chip：去 `&& !source`，再去 `user_id===me &&`（`RecipeResponse` 不返回 `user_id`，原条件恒 undefined → chip **从不显示**，这才是「列表页没状态」的真因）→ 只判 `!is_public`（列表里未发布必然自己的）
- 原料详情页「相关菜谱」列表项加未发布 chip：后端 [get_ingredient_recipes](backend/app/api/nutrition.py#L846) item 返回补 `is_public`，前端 Recipe interface + 列表项 `v-if="!recipe.is_public"` chip（相关菜谱可见性已是 `or_(user_id==me, is_public==True)`，列表里未发布即自己的）

**顺手修（既有 bug，被可见性测试撞破）：**
[get_recipe_detail](backend/app/api/recipes.py#L451) 的 `except Exception` 把 `raise HTTPException(404)` 也吞掉包成 500 → 加 `except HTTPException: raise` 透传，404 正常返回。

## 不可逆

作者侧无「取消发布」入口（天然不可逆）；执行器 [recipe_publish.py](backend/app/services/proposals/executors/recipe_publish.py) `revert` 保留（管理员审核台救场）。发布走审核框架不变。

## 验证

- 后端 5 新测试 passed（test_recipe_publish_private）：创建普通/管理员默认私有、5 导入含 is_public=True、私有 custom 对他人列表/详情不可见、公共对他人可见
- 相关套件 test_recipe_edit_proposals 全过（编辑提议链未坏）
- 前端 build 32.37s 通过；compileall 8 文件 OK
- 无表结构变更（纯数据 UPDATE 迁移）

## 遗留 / 注意

- **迁移待开发者执行**：开发库为 PG，跑 [postgresql 脚本](backend/scripts/sql/20260709_recipe_import_default_public_postgresql.sql) 或 `alembic upgrade head`（但项目不走 alembic 建库，建议直接跑 SQL）。**不跑则现有导入菜谱会变私有**。
- 回归中 5 个预存失败与本次无关（test_recipes 的 auth `password_hash` 登录 + `Ingredient(default_unit_id=)` 字段已删、test_usda_match 旧 forbidden 断言、test_merchant_executor），非本次范围。
- git 提交待开发者决定（项目规矩不主动提交）；本次在 master 主分支工作（开发者已同意）。
- subagent 本环境模型配置坏（API「模型不存在」），subagent-driven 回退 inline 执行。
- 设计 [spec](docs/superpowers/specs/2026-07-09-菜谱发布默认私有-design.md) + [plan](docs/superpowers/plans/2026-07-09-菜谱发布默认私有.md)。
