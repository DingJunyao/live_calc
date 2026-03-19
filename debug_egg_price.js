// 测试鸡蛋价格计算逻辑
console.log("=== 鸡蛋价格显示问题调试 ===");

// 模拟鸡蛋价格记录数据
const eggPriceRecord = {
  id: 1,
  product_id: 1,
  product_name: "鸡蛋",
  merchant_name: "超市A",
  price: 16.35,           // 总价
  original_quantity: 1,   // 数量
  original_unit: "个",     // 单位
  recorded_at: "2026-03-19T10:30:00Z"
};

console.log("原始价格记录:");
console.log("- 产品:", eggPriceRecord.product_name);
console.log("- 总价:", eggPriceRecord.price, "元");
console.log("- 数量:", eggPriceRecord.original_quantity, eggPriceRecord.original_unit);

// 计算单位价格
function calculateUnitPrice(record) {
  if (record.original_quantity && record.original_quantity > 0) {
    return record.price / record.original_quantity;
  }
  return record.price;
}

const unitPrice = calculateUnitPrice(eggPriceRecord);
console.log("\n计算结果:");
console.log("- 单位价格:", unitPrice.toFixed(2), "元/" + eggPriceRecord.original_unit);

// 模拟另一个场景：一盒鸡蛋12个，总价16.35元
const eggBoxRecord = {
  id: 2,
  product_id: 1,
  product_name: "鸡蛋",
  merchant_name: "超市B",
  price: 16.35,           // 总价
  original_quantity: 12,  // 12个
  original_unit: "个",     // 单位
  recorded_at: "2026-03-19T10:30:00Z"
};

console.log("\n另一个例子（一盒12个鸡蛋）:");
console.log("- 产品:", eggBoxRecord.product_name);
console.log("- 总价:", eggBoxRecord.price, "元");
console.log("- 数量:", eggBoxRecord.original_quantity, eggBoxRecord.original_unit);

const unitPriceBox = calculateUnitPrice(eggBoxRecord);
console.log("- 单位价格:", unitPriceBox.toFixed(2), "元/" + eggBoxRecord.original_unit);

console.log("\n总结：");
console.log("- 以前价格列表显示的是总价（¥16.35），让人以为一个鸡蛋16.35元");
console.log("- 修复后价格列表将显示单价（¥16.35/个 或 ¥1.36/个 等）");
console.log("- 这样就能与价格趋势图表显示的单位价格保持一致");