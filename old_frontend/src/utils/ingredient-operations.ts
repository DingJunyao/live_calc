/**
 * 食材层级关系与合并功能测试
 * 以下代码片段展示了如何在前端使用这些新功能
 */

// 1. 合并食材
async function mergeIngredientsExample() {
  try {
    const response = await api.post('/ingredients/merge', {
      source_ingredient_ids: [2, 3],  // 源食材ID列表
      target_ingredient_id: 1         // 目标食材ID
    });
    console.log('合并成功:', response);
  } catch (error) {
    console.error('合并失败:', error);
  }
}

// 2. 获取食材层级关系
async function getIngredientHierarchy(ingredientId) {
  try {
    const response = await api.get(`/ingredients/${ingredientId}/hierarchy`);
    console.log('层级关系:', response);
    return response;
  } catch (error) {
    console.error('获取层级关系失败:', error);
  }
}

// 3. 创建层级关系
async function createHierarchyRelationExample() {
  try {
    const response = await api.post('/ingredients/hierarchy', {
      parent_id: 1,           // 父食材ID（如：鸡肉）
      child_id: 2,            // 子食材ID（如：鸡胸肉）
      relation_type: "contains",  // 关系类型：contains/substitutable/fallback
      strength: 80            // 关系强度（0-100，默认50）
    });
    console.log('层级关系创建成功:', response);
  } catch (error) {
    console.error('创建层级关系失败:', error);
  }
}

// 4. 获取合并历史
async function getMergeHistoryExample() {
  try {
    const response = await api.get('/ingredients/merge-history');
    console.log('合并历史:', response);
    return response;
  } catch (error) {
    console.error('获取合并历史失败:', error);
  }
}

// 5. 检查食材合并状态
async function checkMergeStatus(ingredientId) {
  try {
    const response = await api.get(`/ingredients/${ingredientId}/merge-status`);
    console.log('合并状态:', response);
    return response;
  } catch (error) {
    console.error('获取合并状态失败:', error);
  }
}