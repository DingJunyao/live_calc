# 菜谱详情页 - 几人份快速切换

## 实现日期
2026-06-12

## 概述
在菜谱详情页的原料列表卡片中，于原料表格上方添加了"几人份"展示与快速切换功能。

## 修改文件
- `frontend/src/components/recipes/RecipeIngredientCard.vue` — 添加 servings 切换栏 UI 和逻辑
- `frontend/src/views/recipes/RecipeDetail.vue` — 添加 `@update:display-servings` 事件监听

## 功能详情
在原料列表标题与原料表格之间，使用 chips 组实现份数快捷切换：
- 左侧标签「份数」，右侧 chip 组：`1人份` `2人份` `4人份` `8人份` ...
- chip 根据配方默认份数智能生成（1、2、默认、双倍、半份）
- 当前选中 chip 为 primary tonal 高亮，其余为轻量 text 样式
- 原料数量和成本随份数动态缩放