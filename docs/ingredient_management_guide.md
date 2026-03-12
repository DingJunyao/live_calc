# 食材层级关系与合并功能使用指南

## 概述

本系统实现了食材的层级关系管理与合并功能，解决了以下问题：
- 食材不当分立（如"米"和"大米"被认为是不同食材）
- 处理层级关系（如"鸡肉"、"鸡胸肉"、"鸡翅"等）
- 实现食材合并功能，将多个相似食材合并为一个
- 支持回退机制，在计算成本和营养值时找不到精确食材时向上查找
- 数据操作层面的合并，将相关记录（菜谱、价格记录等）自动重定向到合并后的食材

## API 接口使用说明

### 1. 食材层级关系管理

#### 1.1 创建层级关系
```
POST /api/v1/ingredients/hierarchy
Authorization: Bearer <your_token>

请求体：
{
  "parent_id": 1,           # 父食材ID（如：鸡肉）
  "child_id": 2,            # 子食材ID（如：鸡胸肉）
  "relation_type": "contains",  # 关系类型：contains/substitutable/fallback
  "strength": 80            # 关系强度（0-100，默认50）
}
```

关系类型说明：
- `contains`: 包含关系（如"鸡肉"包含"鸡胸肉"）
- `substitutable`: 可替代关系（如"精盐"可替代"盐"）
- `fallback`: 回退关系（如找不到"鸡胸肉"时可用"鸡肉"替代）

#### 1.2 获取食材的所有层级关系
```
GET /api/v1/ingredients/{ingredient_id}/hierarchy
Authorization: Bearer <your_token>

响应：
{
  "parent_relations": [     # 作为子节点的关系
    {
      "id": 1,
      "parent_id": 1,
      "parent_name": "鸡肉",
      "child_id": 2,
      "child_name": "鸡胸肉",
      "relation_type": "contains",
      "strength": 80,
      "created_at": "2026-03-12T10:00:00Z"
    }
  ],
  "child_relations": [      # 作为父节点的关系
    {
      "id": 2,
      "parent_id": 2,
      "parent_name": "鸡胸肉",
      "child_id": 3,
      "child_name": "鸡胸肉块",
      "relation_type": "contains",
      "strength": 90,
      "created_at": "2026-03-12T10:01:00Z"
    }
  ]
}
```

#### 1.3 删除层级关系
```
DELETE /api/v1/ingredients/hierarchy/{relation_id}
Authorization: Bearer <your_token>
```

### 2. 食材合并功能

#### 2.1 合并食材（需要管理员权限）
```
POST /api/v1/ingredients/merge
Authorization: Bearer <your_token>

请求体：
{
  "source_ingredient_ids": [2, 3],  # 源食材ID列表（如：[长粒米, 茉莉香米]）
  "target_ingredient_id": 1         # 目标食材ID（如：米）
}
```

响应：
```
{
  "success": true,
  "message": "成功将 2 个食材合并到目标食材 1",
  "merged_count": 2,
  "updated_recipes_count": 5,      # 更新的菜谱数量
  "updated_products_count": 3,     # 更新的价格记录数量
  "updated_mappings_count": 2,     # 更新的营养数据映射数量
  "updated_hierarchies_count": 1,  # 更新的层级关系数量
  "merged_nutrition_count": 0,     # 合并的营养数据数量
  "stats_change": {
    "before": {
      "total_ingredients": 3,
      "total_recipes": 10,
      "total_products": 5,
      "total_nutrition_mappings": 8
    },
    "after": {
      "total_ingredients": 1,
      "total_recipes": 10,
      "total_products": 5,
      "total_nutrition_mappings": 6
    }
  }
}
```

#### 2.2 查询合并历史
```
GET /api/v1/ingredients/merge-history
Authorization: Bearer <your_token>

响应：
{
  "records": [
    {
      "id": 1,
      "source_ingredient_id": 2,
      "source_ingredient_name": "长粒米",
      "target_ingredient_id": 1,
      "target_ingredient_name": "米",
      "merged_by_user_id": 1,
      "merged_by_username": "admin",
      "created_at": "2026-03-12T10:00:00Z"
    }
  ]
}
```

#### 2.3 检查食材合并状态
```
GET /api/v1/ingredients/{ingredient_id}/merge-status
Authorization: Bearer <your_token>

响应：
{
  "is_merged": true,
  "merged_into_id": 1,
  "merged_into_name": "米",
  "original_name": "长粒米"
}
```

## 实际使用场景

### 场景1：解决食材不当分立问题
1. 发现"米"、"大米"、"泰国香米"被当作不同食材
2. 决定将"大米"、"泰国香米"合并到"米"
3. 调用合并API：
```javascript
fetch('/api/v1/ingredients/merge', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer your_token_here'
  },
  body: JSON.stringify({
    source_ingredient_ids: [dami_id, xiangmi_id],  // "大米"和"泰国香米"的ID
    target_ingredient_id: mi_id                   // "米"的ID
  })
})
.then(response => response.json())
.then(data => {
  if (data.success) {
    console.log('食材合并成功！');
  }
});
```

### 场景2：建立层级关系
1. 建立"鸡肉"包含"鸡胸肉"、"鸡腿"的层级关系
2. 调用层级关系API：
```javascript
fetch('/api/v1/ingredients/hierarchy', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer your_token_here'
  },
  body: JSON.stringify({
    parent_id: chicken_id,    // "鸡肉"ID
    child_id: breast_id,      // "鸡胸肉"ID
    relation_type: "contains",
    strength: 80
  })
});
```

### 场景3：利用回退机制
当菜谱需要"鸡胸肉"但未找到精确数据时，系统会根据层级关系自动回退到"鸡肉"的数据进行计算。

## 注意事项

### 合并操作注意事项
1. **合并非可逆操作** - 合并操作是不可逆的，请谨慎操作
2. **权限要求** - 食材合并功能需要管理员权限
3. **目标食材选择** - 合并前请确认目标食材是合适的聚合目标
4. **历史数据保留** - 合并后原食材会被标记为已合并状态，但仍可在历史记录中查询
5. **数据重定向** - 所有相关数据（菜谱、价格记录、营养数据等）会自动重定向到目标食材

### 层级关系注意事项
1. **权限要求** - 层级关系管理需要管理员或高级用户权限
2. **关系合理性** - 请确保层级关系合理，避免循环依赖
3. **关系强度** - 根据实际相关性设置合适的强度值（0-100）

## 前端集成建议

### 1. 食材选择组件增强
在食材选择下拉框中，当检测到食材已被合并时，自动显示合并到的目标食材，并给出提示。

### 2. 食材管理页面
提供层级关系和合并功能的管理界面，允许管理员进行食材组织管理。

### 3. 菜谱编辑增强
在菜谱编辑时，如果食材存在层级关系，提供智能补全和回退建议。

## 性能考虑

1. **批量操作** - 建议批量处理食材合并，减少API调用次数
2. **缓存机制** - 建议对层级关系和合并状态进行适当缓存
3. **事务安全** - 所有操作都在数据库事务中执行，确保数据一致性

## 错误处理

常见错误码：
- `400`: 参数错误或业务逻辑错误
- `401`: 未授权访问
- `403`: 权限不足
- `404`: 资源不存在
- `500`: 服务器内部错误

## 维护建议

1. **定期检查** - 定期检查食材数据的重复情况
2. **审核合并** - 建立食材合并的审核流程
3. **备份数据** - 重要操作前备份数据
4. **用户培训** - 对管理员进行功能培训