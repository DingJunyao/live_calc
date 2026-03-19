/**
 * 鸡蛋价格显示问题修复验证脚本
 *
 * 问题：在原料管理中，鸡蛋的价格显示为¥16.35/个，而在价格趋势图表中显示正常
 *
 * 原因分析：
 * 1. 价格趋势图表中：价格被转换为单位价格（price / quantity）
 * 2. 价格历史列表中：价格直接显示总价，没有转换为单位价格
 * 3. 用户看到价格列表中"¥16.35/个"就认为一个鸡蛋16.35元，这是错误的理解
 *
 * 修复方案：
 * 1. 在价格历史列表中显示单位价格（价格/数量）
 * 2. 同时显示总价以供参考
 */

console.log("=== 鸡蛋价格显示问题修复验证 ===\n");

// 模拟数据：鸡蛋价格记录
const priceRecords = [
  {
    id: 1,
    product_name: "鸡蛋",
    price: 16.35,           // 总价16.35元
    original_quantity: 10,    // 10个
    original_unit: "个",       // 单位是"个"
    merchant_name: "超市A",
    recorded_at: "2026-03-19T10:30:00Z"
  },
  {
    id: 2,
    product_name: "鸡蛋",
    price: 16.35,           // 总价16.35元
    original_quantity: 1,     // 1个
    original_unit: "个",       // 单位是"个"
    merchant_name: "超市B",
    recorded_at: "2026-03-19T11:00:00Z"
  },
  {
    id: 3,
    product_name: "鸡蛋",
    price: 16.35,           // 总价16.35元
    original_quantity: 12,    // 12个
    original_unit: "个",       // 单位是"个"
    merchant_name: "超市C",
    recorded_at: "2026-03-19T12:00:00Z"
  }
];

// 计算单位价格的函数（与修复后的前端代码一致）
function calculateUnitPrice(record) {
  if (record.original_quantity && record.original_quantity > 0) {
    return record.price / record.original_quantity;
  }
  return record.price;
}

console.log("修复前的价格显示（存在问题）：");
console.log("┌─────────────┬──────────┬──────────┬──────────┐");
console.log("│    商品     │   商家   │   价格   │   数量   │");
console.log("├─────────────┼──────────┼──────────┼──────────┤");
priceRecords.forEach(record => {
  console.log(`│   ${record.product_name.padEnd(8)}  │ ${record.merchant_name.padEnd(7)}  │ ¥${record.price.toFixed(2)}   │ ${record.original_quantity} ${record.original_unit}    │`);
});
console.log("└─────────────┴──────────┴──────────┴──────────┘");

console.log("\n修复后的价格显示（显示单位价格+总价参考）：");
console.log("┌─────────────┬──────────┬──────────────────────────┬──────────┐");
console.log("│    商品     │   商家   │         单价/总价        │   数量   │");
console.log("├─────────────┼──────────┼──────────────────────────┼──────────┤");
priceRecords.forEach(record => {
  const unitPrice = calculateUnitPrice(record);
  const unitPriceStr = `¥${unitPrice.toFixed(2)}/${record.original_unit}`;
  const totalPriceStr = `总计: ¥${record.price.toFixed(2)}`;
  console.log(`│   ${record.product_name.padEnd(8)}  │ ${record.merchant_name.padEnd(7)}  │ ${unitPriceStr} ${totalPriceStr.padEnd(15)} │ ${record.original_quantity} ${record.original_unit}    │`);
});
console.log("└─────────────┴──────────┴──────────────────────────┴──────────┘");

console.log("\n价格趋势图表显示（正常）：");
console.log("显示的是单位价格：");
priceRecords.forEach((record, index) => {
  const unitPrice = calculateUnitPrice(record);
  console.log(`${index + 1}. ${record.merchant_name}: ¥${unitPrice.toFixed(2)}/${record.original_unit}`);
});

console.log("\n结论：");
console.log("1. 修复后，价格历史列表和价格趋势图表都显示单位价格，保持一致");
console.log("2. 同时显示总价作为参考，用户可以清楚地知道购买的数量和总价");
console.log("3. 用户不会再误解为一个鸡蛋16.35元，而是看到真实的单位价格");
console.log("4. 比如10个鸡蛋16.35元，则单价为1.64元/个");
console.log("5. 比如1个鸡蛋16.35元，则单价为16.35元/个");
console.log("6. 比如12个鸡蛋16.35元，则单价为1.36元/个");

console.log("\n修复涉及的文件：");
console.log("- frontend/src/views/items/components/PriceHistoryList.vue");
console.log("- frontend/src/views/items/components/PriceChartSection.vue（已有一致的逻辑）");