# 原料详情页 TDZ 崩溃修复

## 现象
访问 `http://localhost:5173/data/ingredients/:id`（任意原料 id）页面白屏，控制台持续报：
```
IngredientDetail.vue:2093 Uncaught (in promise) ReferenceError: Cannot access 'priceUnitName' before initialization
    at setup (IngredientDetail.vue:2093:9)
```

## 根因
ES 模块 `const` 的暂时性死区（TDZ）。[IngredientDetail.vue](../frontend/src/views/ingredients/IngredientDetail.vue) 中：

- 声明点：原 2145 行 `const { energyUnit, priceUnitName, massUnitName } = useUserUnits()`
- 触发点：原 2093 行 `editPriceForm = ref({ ... unit: priceUnitName.value ... })`——`ref()` 的参数是普通对象字面量，setup 执行到此时**立即求值** `priceUnitName.value`，而 `priceUnitName` 此时还未声明 → TDZ ReferenceError，整个 setup 抛错 → 页面白屏。
- 侥幸点：原 1876 行 `overlaidDefaultUnitName = computed(() => priceUnitName.value)` 也引用了它，但 `computed` 是懒求值（只有访问 `.value` 才执行回调），setup 阶段不触发，故未炸；这也是为什么报错只在 2093 而非 1876。

对比 [ProductDetail.vue](../frontend/src/views/products/ProductDetail.vue) 同款改造里声明（1401）在使用（1529）之前，顺序正确，所以不报错——佐证是单纯的声明顺序问题。

属「用户级默认单位配置」feature（详见 [FEATURE_用户级默认单位配置.md](FEATURE_用户级默认单位配置.md)）手工替代失败 subagent 时遗漏的声明顺序——该 feature 备注里写「Phase F 原派 4 subagent 全因模型不存在 API 错误失败，改手工」，手工补的解构放到了营养定义区（2145），没注意到上面的 editPriceForm（2093）和 overlaidDefaultUnitName（1876）已经引用。

## 修复
把 `useUserUnits()` 解构前置到所有引用之前（修复根因，非症状）：

1. 在 `overlaidDefaultUnitName`（原 1876）之前插入：
```js
// 用户级单位偏好（能量/质量/记价单位）——须在 overlaidDefaultUnitName / editPriceForm 等引用前声明，否则触发 TDZ
const { energyUnit, priceUnitName, massUnitName } = useUserUnits()
```
2. 删除原 2145 行的重复声明，`NUTRIENT_DEFINITIONS`（原 2146）留原位——它依赖 `energyUnit`，声明前置后 `energyUnit` 早在它之前，computed 懒求值，OK。

修复后行号：声明 1875；使用点 1879（overlaidDefaultUnitName，computed 懒求值）/ 2096（editPriceForm 立即求值，原 TDZ 触发点）/ 3918（openEditPriceDialog 函数体内运行时求值）——全部在声明之后。

`useUserUnits()`（[composables/useUserUnits.ts](../frontend/src/composables/useUserUnits.ts)）是纯 composable，只依赖 Pinia 的 `useUserStore()`，无任何组件内变量依赖，提前调用安全。

## 验证
- `npm run build` 通过（45.67s，IngredientDetail chunk 正常产出 88.19 kB）。
- grep 确认声明点（1875）在全部使用点之前，无新增 TDZ。

## 影响
纯前端单文件约 3 行改动（+1 注释 +1 解构 +1 空行 -1 重复声明），无表结构变更，无 SQL/alembic。
