# 菜谱详情删除按钮禁用逻辑写反

## 现象

- 管理员在菜谱详情页点删除，按钮被禁用，tooltip 提示「已发布菜谱不可删除，请联系管理员」——管理员本应能删任意状态
- 普通用户看已发布菜谱，删除按钮反而没禁用（点了虽会被后端 403 拦截并提示）

## 根因

[RecipeDetail.vue:26](frontend/src/views/recipes/RecipeDetail.vue#L26) 删除按钮的 `v-if` 把「可用条件」写反：

```html
<!-- 改前：可用条件 = 未发布 或 非管理员（反了） -->
<v-btn v-if="!isPublished || !canManage" icon="mdi-delete" ... />
<v-tooltip v-else ...>已发布菜谱不可删除，请联系管理员</v-tooltip>
```

代入两个角色（都看「已发布」菜谱，isPublished=true）：

| 角色 | canManage | `!isPublished \|\| !canManage` | 分支 | 现象 |
|------|-----------|--------------------------------|------|------|
| 管理员 | true | `false \|\| false` = false | v-else（禁用） | ✅ 对上「管理员删不了」 |
| 普通用户 | false | `false \|\| true` = true | v-if（可用） | ✅ 对上「普通用户按钮亮着」 |

两个现象全中。管理员能走到 v-else，反证 `userStore.user?.is_admin` 在管理员侧取值正常（=true），不必担心 `is_admin` 字段缺失。

### 后端权限规则（正确，未动）

[recipes.py:618-647](backend/app/api/recipes.py#L618-L647) `delete_recipe` 三层拦截：

1. 不存在 → 404
2. `recipe.user_id != current_user.id and not is_admin` → 403「无权删除此菜谱」（别人的）
3. `is_public and not is_admin` → 403「已发布的菜谱不可删除/撤回，请联系管理员」（已发布，哪怕自己发的）

即：管理员任意删；普通用户删别人 / 删已发布（含自己发布的）都被拦，只有删自己未发布的才放行。后端与需求一致，纯前端判断反。

## 修复

`v-if` 翻正为「管理员，或未发布 → 可用按钮」：

```html
<v-btn v-if="canManage || !isPublished" icon="mdi-delete" ... />
<v-tooltip v-else ...>已发布菜谱不可删除，请联系管理员</v-tooltip>
```

修复后四种组合：

| 角色 | isPublished | `canManage \|\| !isPublished` | 分支 |
|------|-------------|-------------------------------|------|
| 管理员 | 已发布 | `true \|\| false` = true | v-if（可用）✅ |
| 普通用户 | 已发布 | `false \|\| false` = false | v-else（禁用+tooltip）✅ |
| 普通用户 | 未发布 | `false \|\| true` = true | v-if（可用，删别人由后端 403 提示）✅ |
| 管理员 | 未发布 | `true \|\| true` = true | v-if（可用）✅ |

附带把 [canManage](frontend/src/views/recipes/RecipeDetail.vue#L562) 的注释写实——该变量只反映「是否管理员」，原注释「是否可管理（删除/撤回）」容易让人误读成「能否删除」（正是本次 bug 的认知温床），改为「是否为管理员（可管理任意状态菜谱；普通用户仅未发布可管理，见删除按钮 v-if 的 `canManage || !isPublished`）」，把完整条件指向 v-if。

## 影响面

- `canManage` 在 RecipeDetail.vue 中仅此一处使用（grep 确认），改名与否都不影响别处；`isPublished` 另两处（chip 标签、canPublish）语义独立
- 没有独立「撤回」按钮（注释提及但实际不存在），无同款连带 bug
- 纯前端单文件，无表结构变更，无需 alembic / SQL 脚本

## 验证

- 静态推演四种组合全对（见上表）
- `npm run build` 通过（31.40s，RecipeDetail chunk 50.91 kB 正常）
