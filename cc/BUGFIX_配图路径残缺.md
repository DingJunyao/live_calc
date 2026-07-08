# 配图路径残缺修复（推荐页午餐瘦肉土豆片配图消失）

## 现象

推荐页（[DailyMealsView](frontend/src/views/meals/DailyMealsView.vue)）午餐「瘦肉土豆片」配图不显示，卡片退化为无图文字模式。早餐/晚餐因 images 本就为空，未被察觉。

## 根因

**关键认知偏差**：CLAUDE.md 写「数据库一般为 SQLite `backend/data/livecalc.db`」，但当前开发环境 [backend/.env](backend/.env) 实际指向 **PostgreSQL**（`postgresql://localhost:5432/livecalc`，见 [database.py](backend/app/core/database.py) engine.url）。前期按 SQLite 直查走弯路——SQLite 是早期正确导入的旧库（路径规范），PG 才是后端实际在用、且数据残缺的库。

**完整因果链**：

1. PG 里 recipe 188（瘦肉土豆片）`images = ['images/瘦肉土豆片_0.jpg']`——**残缺路径**，缺开头 `/`、`static/`、`recipes/` 三段。全库 177 条有图菜谱无一例外全部残缺（0 条规范）。
2. 前端 [MealCard.vue recipeImage computed](frontend/src/components/meals/MealCard.vue) 旧逻辑：`if (raw.startsWith('/'))` 才补 API 前缀；残缺路径不以 `/` 开头 → 走 `return raw` → 拿 `images/xxx.jpg` 当 src。
3. 浏览器请求 `http://localhost:5173/<当前路由>/images/xxx.jpg` → vite proxy 只认 `/api` → 404 → 图没了。

**导入 bug 出处**：[json_recipe_import_service.py _download_image](backend/app/services/json_recipe_import_service.py#L72) 成功返回 `/static/images/recipes/{filename}`（规范），失败（临时解压目录无图）返回 None；调用处 [:359-365](backend/app/services/json_recipe_import_service.py#L359) 在失败时 fallback `processed_images.append(normalized_path)`——`normalized_path` 就是仓库相对路径 `images/xxx.jpg`（残缺）。SQLite 早期导入走正确路径（或 _download_image 当时成功），PG 后来空库重导时临时目录无图、全走 fallback，致 177 条全残缺。

**额外发现（DRY 问题）**：前端有 5 处 `getImageUrl` 重复定义（RecipesView/RecipeDetail/ImageManager/RecipeEditDiff 各一 + MealCard 的 recipeImage computed），逻辑几乎一致且都含「拼到远程 GitHub 仓库」的第三条 fallback（`VITE_DATA_REPO_IMAGE_BASE`）。唯独 MealCard 的 recipeImage **缺这条远程 fallback**——这正是「菜谱详情/列表页遇残缺路径仍能从远程仓库加载、唯推荐页不行」的分野。

## 修复（三管齐下）

### 1. 数据修复（PG 批量 UPDATE）

`recipes.images` 数组中每个元素规范化：`http...` / `/static/images/...` 不动；其余取 basename 补全为 `/static/images/recipes/{filename}`。多图菜谱逐元素处理。

- 177 条全部修复，残缺路径归零
- 备份：[backend/data/recipe_images_backup_20260708.json](backend/data/recipe_images_backup_20260708.json)（177 条 before/after）
- 无表结构变更（纯数据值更新），无需 alembic/SQL 脚本

### 2. 导入 bug 修复

[json_recipe_import_service.py:359-365](backend/app/services/json_recipe_import_service.py#L359) `_download_image` 失败时**不再 append 残缺路径**，直接跳过。残缺的仓库相对路径前端永远解析不了，等于无效数据，不如不存。未来重导不再产生残缺。

### 3. 前端兜底（抽公共函数 + DRY）

新增 [frontend/src/utils/image.ts](frontend/src/utils/image.ts) `resolveImageUrl(path)`，统一三条分支：
1. `http(s)` 绝对 URL → 原样
2. `/static/images/...` → 补 `VITE_API_URL` 前缀走后端
3. 其它（仓库相对路径）→ 拼到 `VITE_DATA_REPO_IMAGE_BASE`（远程兜底）

5 处全部接入：MealCard（recipeImage computed 改用之，补齐原本缺失的远程兜底）、RecipesView/RecipeDetail/ImageManager/RecipeEditDiff（`const getImageUrl = resolveImageUrl`）。模板调用名不变，最小改动。

附带改进：原 4 处硬编码 `/api/v1`，公共函数统一用 `VITE_API_URL || '/api/v1'`，与项目自定义端口/API 地址配置对齐。

## 验证

- API 实测：`GET /meals/recommendations` lunch id=188 first_image = `/static/images/recipes/瘦肉土豆片_0.jpg`（规范）✓
- 图片直链 `GET /api/v1/static/images/recipes/瘦肉土豆片_0.jpg` = 200, 254333 字节 ✓
- 后端 `py_compile` 通过 ✓
- 前端 `npm run build` ✓ 32.34s（仅既有 chunk 体积警告）
- 全库残缺路径数：0 ✓

## 遗留

- **id=249 菜谱图片文件缺失**（某 `_3.jpeg`）：路径已补全为规范 `/static/images/recipes/xxx.jpeg`，但物理文件不在 `backend/static/images/recipes/` 盘上（177 条中唯一一条文件缺失）。路径规范后若补回文件即可显示，需重新获取该图片。
- 远程仓库兜底（`VITE_DATA_REPO_IMAGE_BASE`）依赖联网 + GitHub raw 可达，离线场景失效——但数据修复后路径都规范、走本地后端，远程兜底仅作未来防御。
- CLAUDE.md 索引所述「数据库一般为 SQLite」与当前实际（PG）不符，已在自动记忆补一条环境备忘，避免下次查错库。
