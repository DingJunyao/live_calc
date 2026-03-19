# 原料管理页面排序功能修复记录

## 问题描述
原料管理页面未按价格记录数量排序，而是按默认顺序（通常是ID或创建时间）显示。

## 根本原因
前端调用的是 `/api/v1/ingredients` 端点（来自 ingredient_extended.py），而这个端点没有实现 `sort_by=price_records` 参数的处理逻辑。虽然 `nutrition.py` 中的端点有此功能，但前端实际上使用的是另一个端点。

## 解决方案
更新 `backend/app/api/ingredient_extended.py` 中的 `get_ingredients` 函数，添加对 `sort_by` 参数的支持，特别是 `price_records` 排序选项。

## 核心修改
- 添加了 `sort_by` 查询参数，默认值为 `"created_at"`
- 实现了 `sort_by="price_records"` 时的排序逻辑，与 `nutrition.py` 中的逻辑保持一致
- 使用子查询统计每个原料关联商品的价格记录数量，然后按此数量降序排序

## 验证结果
- 排序测试成功：青菜（ID: 81）有9条价格记录，排第1位
- 鸡蛋（ID: 2）有8条价格记录，排第10位
- 排序逻辑正确按价格记录数量从多到少排列

## 影响
- 前端原料管理页面现在可以正确使用 `/api/v1/ingredients?sort_by=price_records` 获取按价格记录数量排序的列表
- 保持了与其他排序选项（name, created_at）的兼容性