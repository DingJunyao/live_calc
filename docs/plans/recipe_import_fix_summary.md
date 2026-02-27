# 菜谱导入服务修复摘要

## 问题描述
系统初始化和菜谱导入时出现错误：
- 导入菜谱失败 陕北熬豆角: 'aliases' is an invalid keyword argument for Ingredient
- 导入菜谱失败 雷椒皮蛋: 'aliases' is an invalid keyword argument for Ingredient
- 导入菜谱失败 鸡蛋火腿炒黄瓜: 'aliases' is an invalid keyword argument for Ingredient

## 根本原因
在之前的食品数据结构优化项目中，我们将Ingredient模型的`aliases`字段替换为了`name_variants`字段，但在`recipe_import_service.py`中的`_match_or_create_ingredient`方法仍在使用旧的参数名称。

## 修复措施

### 1. 更新 recipe_import_service.py
- 修改 `_match_or_create_ingredient` 方法中的Ingredient创建代码
- 将 `aliases=[]` 参数改为 `name_variants=[]`

### 2. 更新 nutrition.py API端点
- 修改所有与ingredient相关的API端点以使用`name_variants`字段
- 保持向后兼容性，将`name_variants`数据结构转换为原有的`aliases`格式返回
- 更新create, update, get等操作以处理新的数据结构

### 3. 更新 nutrition_service.py
- 修改服务函数以正确处理`name_variants`字段
- 确保所有别名和变体名称的检索和更新都使用新的字段名
- 保持对旧数据格式的兼容性

### 4. 数据迁移支持
- 添加了从旧的`aliases`格式到新的`name_variants`格式的数据迁移脚本
- 确保向后兼容性，新的数据结构可以容纳以前的别名数据

## 验证
- 创建了测试脚本验证修复
- 测试确认没有再出现`'aliases' is an invalid keyword argument`错误
- 确认`_match_or_create_ingredient`方法正常工作

## 结果
- 菜谱导入服务现在可以正常工作
- 所有与食材相关的API端点正常运行
- 保持了前后端的数据结构一致性
- 维护了向后兼容性，避免破坏现有功能