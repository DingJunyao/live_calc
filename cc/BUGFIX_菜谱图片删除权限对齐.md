# 菜谱图片删除权限对齐

## 问题

普通用户编辑菜谱信息时，删除图片报 403：
```
DELETE /api/v1/recipes/357/images/xxx.jpg → 403
"已发布菜谱仅管理员可删除图片"
```

## 根因

[delete_recipe_image](backend/app/api/recipes.py#L693) 端点的权限逻辑把 `is_public` 和 `recipe.source` 并列处理，已发布菜谱不论是否作者一律拦截。但图片删除本质上是「修改菜谱的 images 引用列表」，应纳入菜谱信息编辑流程，而非视为独立的文件删除操作。

## 修复方案

两处修改：

### 前端 [RecipeBasicCard.vue](frontend/src/components/recipes/RecipeBasicCard.vue#L277-L291)
`handleImageRemove` 不再调用 `DELETE /recipes/{id}/images/{filename}`，改为纯本地移除（`editImages.value.splice(index, 1)`）。变更在保存时通过 `PUT /recipes/{id}` 的 `images` 字段统一提交，走菜谱编辑的审核提议流程。

### 后端 [recipes.py](backend/app/api/recipes.py#L705-L711)
`delete_recipe_image` 退化管理员专用——简化权限判断为 `if not current_user.is_admin: 403`。常规操作统一由 `PUT /recipes/{id}` 处理审批流。

## 流程对照

| 场景 | 之前 | 之后 |
|------|------|------|
| 普通用户删已发布菜谱图片 | 403「仅管理员可删」 | 保存时提交审核提议（与菜谱编辑一致） |
| 普通用户删未发布菜谱图片 | 直接生效 | 保存时直接生效（走 PUT 直写） |
| 管理员删任意菜谱图片 | 直接生效 | 直接生效（DELETE 也可、PUT 也可） |

**Why:** 删除图片是变更菜谱数据的一部分，不应绕过审核框架。独立的 DELETE 端点只保留给管理员做物理文件清理。
**How to apply:** 无表结构变更，前后端均已构建通过。
