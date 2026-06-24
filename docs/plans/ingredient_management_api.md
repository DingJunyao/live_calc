# 食材层级关系与合并管理接口

## 食材层级关系管理

### 1. 创建层级关系
```
POST /api/v1/ingredients/hierarchy

请求体：
{
  "parent_id": 1,           # 父食材ID（如：鸡肉）
  "child_id": 2,            # 子食材ID（如：鸡胸肉）
  "relation_type": "contains"  # 关系类型：contains/substitutable/fallback
}
```

### 2. 获取食材的所有层级关系
```
GET /api/v1/ingredients/{ingredient_id}/hierarchy

响应：
{
  "parent_relations": [     # 作为子节点的关系
    {
      "id": 1,
      "parent_id": 1,
      "parent_name": "鸡肉",
      "relation_type": "contains",
      "strength": 80
    }
  ],
  "child_relations": [      # 作为父节点的关系
    {
      "id": 2,
      "child_id": 2,
      "child_name": "鸡胸肉",
      "relation_type": "contains",
      "strength": 80
    }
  ]
}
```

### 3. 删除层级关系
```
DELETE /api/v1/ingredients/hierarchy/{relation_id}
```

## 食材合并功能

### 1. 合并食材
```
POST /api/v1/ingredients/merge

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
  "updated_recipes_count": 5,
  "updated_products_count": 3,
  "updated_mappings_count": 2,
  "stats_change": {
    "before": {"total_ingredients": 3, "total_recipes": 10, ...},
    "after": {"total_ingredients": 1, "total_recipes": 10, ...}
  }
}
```

### 2. 查询合并记录
```
GET /api/v1/ingredients/merge-history

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

### 3. 检查食材是否已被合并
```
GET /api/v1/ingredients/{ingredient_id}/merge-status

响应：
{
  "is_merged": true,
  "merged_into_id": 1,
  "merged_into_name": "米",
  "original_name": "长粒米"
}
```

## 实际使用示例

### 场景1：处理食材不当分立问题
1. 发现"米"、"大米"、"泰国香米"被当作不同食材
2. 决定将"大米"、"泰国香米"合并到"米"
3. 调用合并API：
```javascript
// 合并相似食材
fetch('/api/v1/ingredients/merge', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    source_ingredient_ids: [dami_id, xiangmi_id],  // "大米"和"泰国香米"的ID
    target_ingredient_id: mi_id                   // "米"的ID
  })
})
```

### 场景2：建立层级关系
1. 建立"鸡肉"包含"鸡胸肉"、"鸡腿"的层级关系
2. 调用层级关系API：
```javascript
// 建立包含关系
fetch('/api/v1/ingredients/hierarchy', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    parent_id: chicken_id,    // "鸡肉"ID
    child_id: breast_id,      // "鸡胸肉"ID
    relation_type: "contains"
  })
})
```

### 场景3：处理计算时的回退机制
1. 当菜谱需要"鸡胸肉"但未找到精确数据时
2. 系统会根据层级关系自动回退到"鸡肉"的数据进行计算
3. 无需额外操作，系统自动处理

## 权限要求
- 食材合并功能需要管理员权限
- 层级关系管理需要管理员或高级用户权限
- 普通用户只能查看层级关系和合并状态

## 注意事项
1. 合并操作是不可逆的，请谨慎操作
2. 合并后原食材会被标记为已合并状态，但仍可在历史记录中查询
3. 所有相关数据（菜谱、价格记录、营养数据等）会自动重定向到目标食材
4. 合并前请确认目标食材是合适的聚合目标