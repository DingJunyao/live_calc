# 菜谱列表漏掉导入菜谱（NULL 三值逻辑缝隙）

## 现象

PG 上注册用户后，菜谱列表为空——但启动时明明导入了菜谱（`source='json_repo'`）。

## 根因

这是 [审计字段外键修复](BUGFIX_audit_field_pg_fk_violation.md) 的**连带头**：上关把 howtocook 导入的 `Recipe` 改成 `user_id=None`（避开 PG 空库外键违反，`Recipe.user_id` 外键保留），但菜谱列表查询没适配这个 NULL。

菜谱列表 [get_recipes](../backend/app/api/recipes.py#L152) 由两个子查询 `union_all` 合并（[:171-184](../backend/app/api/recipes.py#L171)）：

```python
user_recipes = ... filter(Recipe.user_id == current_user.id, is_active==True)        # 我的
public_imported_recipes = ... filter(
    or_(Recipe.source != None, Recipe.is_public == True),
    Recipe.user_id != current_user.id,    # ← 缝隙
    is_active==True
)
```

导入菜谱 `user_id=None, source='json_repo', is_public=False`：

- 「我的」分支：`None == current_user.id` → **False**
- 「公共」分支：`source != None` 是 True，但 `user_id != current_user.id` 对 NULL 求值是 **NULL（SQL 三值逻辑，非 True）**，整条 AND 塌成 NULL → **不命中**

`union_all` 两边都落空 → 列表为空。

## 修复

[recipes.py:179](../backend/app/api/recipes.py#L179) 公共分支显式接纳 NULL：

```python
# 原
Recipe.user_id != current_user.id,
# 改
or_(Recipe.user_id != current_user.id, Recipe.user_id.is_(None)),
```

## 验证

- `py_compile` 通过。
- 逻辑走查（修复后公共分支 `or_(source!=None, is_public==True) AND or_(user_id!=me, user_id IS NULL) AND is_active`）：
  - 导入菜谱（无主 + 有 source）：全 True → 命中 ✅
  - 别人的私有菜谱（user_id=他人, source=None, is_public=False）：`or_(source, is_public)` False → 不命中（不可见，正确）
  - 我的菜谱（user_id=me）：被 `user_recipes` 覆盖；公共分支 `or_(user_id!=me [False], IS NULL [False])` → False，排除（`union_all` 不重复，正确）
- 详情页 [get_recipe_detail:375-388](../backend/app/api/recipes.py#L375) 本就用 `or_(user_id==me, source!=None)` + source 兜底查询，导入菜谱（source 非空）本就可见，**无 NULL 缝隙**，无需改。

## 边界

- 只动列表的公共查询；详情/编辑权限（[:665](../backend/app/api/recipes.py#L665) `is_owner_or_admin`、[:1297](../backend/app/api/recipes.py#L1297)/[:1346](../backend/app/api/recipes.py#L1346)/[:1406](../backend/app/api/recipes.py#L1406) `user_id==me`）语义不变——导入菜谱本就不属于具体用户、不可编辑，只可查看。
- grep 确认全库仅此一处 `Recipe.user_id != current_user.id`，无同类缝隙。

## 影响

- 导入的公共菜谱对所有注册用户在列表可见。
- 三库一致受益：NULL 三值逻辑是 SQL 标准（PG/SQLite/MySQL 行为相同）。
- 运行时：uvicorn `--reload` 重启后，注册用户刷新菜谱列表即可看到导入菜谱；无需重新导入（菜谱数据已落库，只是查询漏了）。
