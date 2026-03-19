# 价格计算逻辑统一化修复记录

## 问题描述
1. 原料管理页面和商品管理页面显示相同商品（如鸡蛋）的价格不一致
2. 原料管理页面未按价格记录数量正确排序
3. 后端不同API端点使用不同的价格计算逻辑

## 解决方案
1. 统一了后端API的价格计算逻辑，在所有端点使用平均单价计算方式
2. 修复了`/ingredients/{id}/latest-price`端点的排序逻辑
3. 修复了`/products/entity/{id}/latest-price`端点的价格计算逻辑
4. 更新了前端价格显示逻辑

## 修改文件
- `backend/app/api/nutrition.py` - 修复了原料端点的排序逻辑
- `backend/app/api/products_entity.py` - 修复了商品端点的价格计算逻辑
- `frontend/src/views/products/ProductManage.vue` - 更新了前端价格显示
- `frontend/src/api/client.ts` - 价格API接口定义

## 核心修复内容
- 后端统一使用单价计算：`unit_price = record.price / record.original_quantity`
- 原料管理页面现在正确按价格记录数量排序
- 所有端点返回一致的价格信息

## 验证结果
- 鸡蛋在原料管理页面和商品管理页面显示相同价格
- 原料管理页面按价格记录数量正确排序
- 价格趋势图表与列表价格显示一致