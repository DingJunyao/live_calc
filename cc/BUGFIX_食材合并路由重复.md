# 食材合并路由重复（Duplicate Operation ID）修复

## 症状

启动后端时报 FastAPI 警告：

```
UserWarning: Duplicate Operation ID merge_ingredients_api_v1_ingredients_merge_post
  for function merge_ingredients at .../backend/app/api/ingredient_merge.py
UserWarning: Duplicate Operation ID merge_ingredients_api_v1_ingredients_merge_post
  for function merge_ingredients at .../backend/app/api/ingredient_hierarchy.py
```

## 根因

两个文件都注册了完全相同的路由 `POST /api/v1/ingredients/merge`，且函数名都叫 `merge_ingredients`。FastAPI 按函数名自动生成 operation ID，同名函数 → 同一个 ID，撞车。

- `ingredient_merge.py:13` —— 整个文件只有这一个路由（孤立早期遗留）
- `ingredient_hierarchy.py:329` —— 含 hierarchy CRUD + merge-history + merge-status 一整套配套接口（更完整的实现）

更隐蔽的一层：`main.py` 中 `ingredient_merge.router` 先注册、`ingredient_hierarchy.router` 后注册。Starlette 按注册顺序匹配，**先注册的胜出** → 实际生效的是 `ingredient_merge.py` 的宽松版本（仅 `if not current_user` → 401），而 `ingredient_hierarchy.py` 后来加的 `is_admin` 管理员校验（403）形同虚设。

两份实现的差异仅权限校验：

| 文件 | 权限校验 |
|---|---|
| `ingredient_merge.py`（已删） | `if not current_user` → 401（登录即可） |
| `ingredient_hierarchy.py`（保留） | `if not current_user.is_admin` → 403（仅管理员） |

## 修复

KISS + DRY：删除孤立的早期遗留文件 `ingredient_merge.py`（整个文件就一个重复路由），保留 `ingredient_hierarchy.py` 的完整实现。同步清理 `main.py`：

- 删除 `from app.api import ingredient_merge  # 食材合并 API`（原第 24 行）
- 删除 `app.include_router(ingredient_merge.router, prefix="/api/v1", tags=["食材合并"])`（原第 565 行）

`schema` 文件 `app/schemas/ingredient_merge.py` 保留——它被 `nutrition.py` 引用，与本次路由冲突无关；`ingredient_hierarchy.py` 自身已重新定义了 `IngredientMergeRequest/Response`，不依赖该 schema 文件。

## 附带影响：权限规则细化（而非「仅管理员」）

删掉重复路由后，最初一度收紧为「仅管理员」。经需求澄清，合并食材应对普通用户开放，只是限定范围：

- **管理员**：可合并任意食材
- **普通用户**：只能把**自己创建的**源食材，合并进**自己创建的**目标食材（源与目标的 `created_by` 均须等于本人）

实现（`ingredient_hierarchy.py` 的 `merge_ingredients`）：去掉「一刀切 403」，改为在参数校验之后、调用 `IngredientMerger` 之前，对普通用户额外校验——把本轮涉及的源+目标 id 一次查出，凡 `created_by != current_user.id`（含系统/历史数据的 NULL）即 403，错误信息列出不由其创建的食材名称。`created_by` 字段由 `AuditMixin` 提供（`app/core/base_model.py`），无需表结构变更。

> 注：合并的固有行为是迁移该食材的所有引用（菜谱、商品、映射、层级关系），其中可能包含**他人**的菜谱引用——本次权限只卡食材所有权，不限制跨用户引用迁移，符合「合并」语义。

## 验证

- `python -m py_compile backend/app/main.py backend/app/api/ingredient_hierarchy.py` 通过，无语法错误
- 全仓库 grep 确认无 `from app.api import ingredient_merge` / `app.api.ingredient_merge` 遗留引用
- 无表结构变更，无需 SQL / alembic

## 涉及文件

- 删除：`backend/app/api/ingredient_merge.py`
- 修改：`backend/app/main.py`（去掉 import 与 include_router 各一行）
- 修改：`backend/app/api/ingredient_hierarchy.py`（`merge_ingredients` 权限校验改为细粒度所有权判定）
