# 商品加权价格机制 - 体验与口径修补 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修补已上线的「商品加权价格机制」的四点体验/口径问题：权重编辑区 UI 重叠、普通用户看到无用的全局权重框、权重用数字框不好用、原料详情页的「价格趋势线 / 各商家价格」未按商品权重加权。

**Architecture:** 前端为主（权重编辑区重构 + chartData 局部加权 + 各商家列表汇总行），后端补一处批量权重端点 + 改一处 latest-price-by-merchant 的同商家多商品聚合。复用现成 `ingredient_price_service._resolve_weight`，不重写加权算法。**权重只影响「平均值」语义，极值/计数/原始记录不动。** 无表结构变更。

**Tech Stack:** 后端 FastAPI + SQLAlchemy + pytest；前端 Vue 3 + Vuetify 3 + Pinia。

**背景设计稿：** `docs/superpowers/specs/2026-07-06-product-weighted-price-design.md`

---

## 总原则（贯穿所有任务）

1. **权重只插手「平均值」语义**：加权 avg / 加权代表价 / 加权综合价。`min` / `max` / `count` / 单条原始记录 / sparkline 迷你折线，**一律不动**。
2. **只改原料详情页的价格趋势**；商品详情页是单商品、无商品间权重维度，不动。
3. **两处权重编辑控件同款**（`ProductDetail.vue` 基本信息 + `IngredientDetail.vue` 商品行对话框），改就一起改，保持一致。
4. 项目惯例：不自行 git 提交（等用户指令）；后端改动 `py_compile` + 相关 pytest；前端改动 `npm run build` 必须通过。

---

## Task 1: 后端 — 新增「原料下商品批量生效权重」端点

**目的：** 前端 `IngredientDetail` 的价格趋势加权 avg 需要「原料下每个商品的生效权重」（覆盖>全局>50）。逐商品拉 `my-weight` 太慢（N 次请求），加一个批量端点。

**Files:**
- Modify: `backend/app/api/nutrition.py`（在 `get_ingredient_latest_price_by_merchant` 附近新增端点）
- Test: `backend/tests/test_ingredient_product_weights.py`（新建）

**Step 1: 写失败测试**

新建 `backend/tests/test_ingredient_product_weights.py`：

```python
"""原料下商品批量生效权重端点测试。"""
from tests.test_proposals_framework import register_all  # 复用 P0 的注册夹具


def test_product_weights_override_beats_global(client, db_session):
    register_all()
    # 建原料 + 2 商品（全局权重不同）+ 当前用户对其中之一设覆盖
    # 调 GET /api/v1/nutrition/ingredients/{id}/product-weights
    # 断言：覆盖商品的 effective_weight = 覆盖值、source='override'；
    #       未覆盖商品的 effective_weight = 全局值、source='global'
    ...


def test_product_weights_empty_ingredient(client, db_session):
    register_all()
    # 无商品的原料 → 返回 {"items": []}
    ...
```

> 注：测试具体建表辅助参考 `backend/tests/test_shared_data.py` 既有原料/商品构造写法。

**Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_ingredient_product_weights.py -v`
Expected: FAIL（端点 404）

**Step 3: 实现端点**

在 `backend/app/api/nutrition.py` `get_ingredient_latest_price_by_merchant` 函数之后新增：

```python
@router.get("/ingredients/{ingredient_id}/product-weights")
async def get_ingredient_product_weights(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """原料下各有效商品的生效价格权重（覆盖 > 全局 > 50）。

    供前端加权均价计算用（价格趋势加权 avg）。返回每个商品的 global/override/effective/source。
    """
    from app.models.user_product_weight_override import UserProductWeightOverride

    products = db.query(Product).filter(
        Product.ingredient_id == ingredient_id,
        Product.is_active == True,  # noqa: E712
    ).all()

    uid = current_user.id if current_user else None
    overrides = {}
    if uid is not None and products:
        pid_list = [p.id for p in products]
        rows = db.query(UserProductWeightOverride).filter(
            UserProductWeightOverride.user_id == uid,
            UserProductWeightOverride.product_id.in_(pid_list),
            UserProductWeightOverride.is_active == True,  # noqa: E712
        ).all()
        overrides = {r.product_id: r.weight for r in rows}

    items = []
    for p in products:
        gw = int(p.price_weight) if p.price_weight is not None else 50
        ov = overrides.get(p.id)
        if ov is not None:
            eff, src = int(ov), "override"
        else:
            eff, src = gw, "global"
        items.append({
            "product_id": p.id,
            "name": p.name,
            "global_weight": gw,
            "override_weight": ov,
            "effective_weight": eff,
            "source": src,
        })
    return {"items": items}
```

**Step 4: 跑测试确认通过**

Run: `cd backend && python -m pytest tests/test_ingredient_product_weights.py -v`
Expected: PASS

**Step 5: 语法校验**

Run: `cd backend && python -m py_compile app/api/nutrition.py`
Expected: 无输出（成功）

---

## Task 2: 后端 — latest-price-by-merchant 同商家多商品按权加权

**目的：** 原料级「各商家价格」里，同一商家挂多个商品时，现在代表价只取「最新一条记录」（偏到某个商品）。改为该商家下各商品代表价按商品权重加权（属于「代表价=平均值」语义，符合总原则）。

**Files:**
- Modify: `backend/app/api/nutrition.py:1062-1150`（`get_ingredient_latest_price_by_merchant` 内的 `_lookup_merchant_prices`）
- Test: `backend/tests/test_ingredient_merchant_weighted.py`（新建）

**Step 1: 写失败测试**

新建 `backend/tests/test_ingredient_merchant_weighted.py`：

```python
"""原料级各商家价格：同商家多商品按权重加权测试。"""
from tests.test_proposals_framework import register_all


def test_same_merchant_multi_product_weighted(client, db_session):
    register_all()
    # 原料 I 下两商品 P1(权重 30)、P2(权重 70)，同一商家 M 各有一条记录
    # P1 单价折算到斤 = 10，P2 单价折算到斤 = 20
    # 期望 M 代表价 = (10*30 + 20*70) / (30+70) = 17.0
    # 调 GET /api/v1/nutrition/ingredients/{I}/latest-price-by-merchant
    # 断言 prices 中 M 的 price ≈ 17.0
    ...


def test_weight_zero_product_excluded_from_merchant(client, db_session):
    register_all()
    # P1 权重 0、P2 权重 50，同商家；期望 M 代表价 = P2 单价（P1 被排除）
    ...
```

**Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_ingredient_merchant_weighted.py -v`
Expected: FAIL（现实现取最新一条，得 10 或 20 而非 17）

**Step 3: 改造 `_lookup_merchant_prices`**

在 `backend/app/api/nutrition.py` 的 `_lookup_merchant_prices` 内，把「按商家只留最新一条」改为「按 (商家, 商品) 留每商品最新一条 → 同商家内按商品权重加权」。核心改动（保留原有单位折算 `ing_target='斤'` 与 `total_cost` 逻辑，只换聚合层）：

```python
# 顶部 import 区补：
from app.services.ingredient_price_service import _resolve_weight

def _lookup_merchant_prices(ing: Ingredient) -> list[dict]:
    """对单个食材查找各商家代表价。同商家多商品时按商品权重加权。"""
    products = db.query(Product).filter(
        Product.ingredient_id == ing.id,
        Product.is_active == True,  # noqa: E712
    ).all()
    product_map = {p.id: p for p in products}
    product_ids = list(product_map.keys())
    if not product_ids:
        return []

    records = db.query(ProductRecord).options(
        joinedload(ProductRecord.original_unit),
        joinedload(ProductRecord.merchant)
    ).join(Merchant, ProductRecord.merchant_id == Merchant.id).filter(
        ProductRecord.product_id.in_(product_ids),
        ProductRecord.merchant_id.isnot(None),
        Merchant.is_open == True,  # noqa: E712
    ).order_by(ProductRecord.recorded_at.desc()).all()

    # 按 (merchant, product) 各留最新一条
    mp_latest: dict = {}
    for record in records:
        key = (record.merchant_id, record.product_id)
        if key not in mp_latest:
            mp_latest[key] = record

    # 按商家分组：mid -> {pid: record}
    by_merchant: dict = defaultdict(dict)
    for (mid, pid), record in mp_latest.items():
        by_merchant[mid][pid] = record

    ing_target = "斤"
    uid = current_user.id if current_user else None
    results = []
    for mid, prod_records in by_merchant.items():
        # 每商品算折算单价 + 权重
        weighted: list = []  # [(unit_price, weight)]
        sample_record = None
        for pid, record in prod_records.items():
            if record.price is None or record.original_quantity is None or record.original_quantity <= 0 or not record.original_unit:
                continue
            total_price = float(record.price)
            original_quantity = float(record.original_quantity)
            original_unit_abbr = record.original_unit.abbreviation
            unit_price = None
            if ing_target and original_unit_abbr != ing_target:
                convert_result = unit_service.convert(
                    original_quantity, original_unit_abbr, ing_target,
                    entity_type="ingredient", entity_id=ing.id,
                )
                if convert_result is not None:
                    converted_quantity, _ = convert_result
                    if converted_quantity and float(converted_quantity) > 0:
                        unit_price = total_price / float(converted_quantity)
            if unit_price is None:
                unit_price = total_price / original_quantity

            w = _resolve_weight(db, user_id=uid, product=product_map.get(pid))
            if w <= 0:
                continue
            weighted.append((unit_price, w))
            if sample_record is None:
                sample_record = record

        if not weighted or sample_record is None:
            continue

        num = sum(up * w for up, w in weighted)
        den = sum(w for up, w in weighted)
        merchant_price = round(num / den, 2) if den > 0 else None
        if merchant_price is None:
            continue

        # total_cost 沿用原逻辑（以 sample_record 代表该商家行）
        total_cost = None
        if quantity is not None and quantity > 0 and quantity_unit:
            qty = quantity
            price_unit_abbr = ing_target
            if quantity_unit != price_unit_abbr:
                qty_convert = unit_service.convert(
                    quantity, quantity_unit, price_unit_abbr,
                    entity_type="ingredient", entity_id=ing.id,
                )
                if qty_convert is not None:
                    converted_val, _ = qty_convert
                    if converted_val and float(converted_val) > 0:
                        qty = float(converted_val)
                else:
                    qty = None
            if qty is not None:
                total_cost = round(merchant_price * qty, 2)

        results.append({
            "merchant_id": mid,
            "merchant_name": sample_record.merchant.name if sample_record.merchant else f"商家#{mid}",
            "price": merchant_price,
            "unit": ing_target,
            "total_cost": total_cost,
            "recorded_at": serialize_datetime(sample_record.recorded_at) if sample_record.recorded_at else None,
            "product_name": sample_record.product_name,
        })

    results.sort(key=lambda x: x["price"])
    if results:
        results[0]["is_lowest"] = True
        for r in results[1:]:
            r["is_lowest"] = False
    return results
```

> 注意：外层 `get_ingredient_latest_price_by_merchant` 原本在 `_lookup_merchant_prices` 返回后还有一段聚合子食材（CONTAINS 关系）的逻辑（nutrition.py:1100 附近 `child_costs_by_merchant` / HierarchyRelationType），**那段不动**，只换 `_lookup_merchant_prices` 函数体。`current_user` / `quantity` / `quantity_unit` / `unit_service` 在闭包作用域内可用（原函数本就是嵌套闭包）。

**Step 4: 跑测试确认通过**

Run: `cd backend && python -m pytest tests/test_ingredient_merchant_weighted.py -v`
Expected: PASS

**Step 5: 回归 + 语法校验**

Run: `cd backend && python -m pytest tests/ -k "merchant or price" -v && python -m py_compile app/api/nutrition.py`
Expected: 相关测试 PASS、无语法错误

---

## Task 3: 前端 — `ProductDetail.vue` 权重编辑区重构

**目的：** 解决别名 hint 与权重框重叠（问题 1）、普通用户不显示全局权重（问题 2）、权重改滑块（问题 3）。

**Files:**
- Modify: `frontend/src/views/products/ProductDetail.vue`
  - 模板 `192-234`（别名 + 全局 + 我的覆盖三件套）
  - `basicEditForm` 初始化 `1426-1440`、`2413-2423`（加 `myWeightEnabled`）
  - `saveBasicInfo` 提交 `2474-2486`（按 `myWeightEnabled` 决定 set/delete）

**Step 1: 改模板**（替换 192-234 整块）

```vue
<v-combobox
  v-model="basicEditForm.aliases"
  label="别名"
  variant="outlined"
  density="compact"
  multiple
  chips
  closable-chips
  hint="输入后回车添加多个别名"
/>

<!-- 价格权重区（与上方分隔，避免 hint 贴连） -->
<div class="mt-4">
  <!-- 全局权重：仅管理员可改；普通用户整块不渲染 -->
  <div v-if="userStore.user?.is_admin" class="mb-4">
    <div class="text-caption text-medium-emphasis mb-1">
      全局价格权重 <span class="text-disabled">（原料加权平均用；50=等权，0=排除该商品）</span>
    </div>
    <v-slider
      v-model="basicEditForm.priceWeight"
      :min="0"
      :max="100"
      :step="1"
      thumb-label
      color="primary"
    >
      <template #thumb-label="{ modelValue }">{{ modelValue }}</template>
      <template #append>
        <v-chip size="small" label>{{ basicEditForm.priceWeight }}</v-chip>
      </template>
    </v-slider>
  </div>

  <!-- 我的权重覆盖：开关 + 滑块（所有人可设） -->
  <div>
    <v-switch
      v-model="basicEditForm.myWeightEnabled"
      label="覆盖全局权重（仅影响我）"
      density="compact"
      color="primary"
      hide-details
    />
    <div class="text-caption text-medium-emphasis mb-1">
      全局默认：{{ basicEditForm.globalWeightReadOnly }}（不覆盖即用此值）
    </div>
    <v-slider
      v-if="basicEditForm.myWeightEnabled"
      v-model="basicEditForm.myWeight"
      :min="0"
      :max="100"
      :step="1"
      thumb-label
      color="tertiary"
    >
      <template #thumb-label="{ modelValue }">{{ modelValue }}</template>
      <template #append>
        <v-chip size="small" label color="tertiary">{{ basicEditForm.myWeight }}</v-chip>
      </template>
    </v-slider>
  </div>
</div>
```

**Step 2: 表单类型 + 初始化加 `myWeightEnabled`**

`basicEditForm` 类型（`1203` / `1230` 附近的 interface）补 `myWeightEnabled: boolean`。初始默认值（`1426-1440`）补 `myWeightEnabled: false`。

`editBasicInfo` 打开时（`2413-2423`）：

```ts
basicEditForm.value = {
  // ...原有字段...
  priceWeight: (product.value as any).price_weight ?? 50,
  myWeight: 50,                    // 默认值，下面按覆盖情况覆盖
  myWeightEnabled: false,          // 默认不覆盖
  globalWeightReadOnly: (product.value as any).price_weight ?? 50,
}
getProductMyWeight(product.value.id).then((res: any) => {
  basicEditForm.value.globalWeightReadOnly = res.global_weight
  basicEditForm.value.priceWeight = res.global_weight
  if (res.source === 'override') {
    basicEditForm.value.myWeightEnabled = true
    basicEditForm.value.myWeight = res.override_weight
  } else {
    basicEditForm.value.myWeightEnabled = false
    basicEditForm.value.myWeight = res.global_weight  // 滑块初值跟全局，勾选时从这开始
  }
}).catch(() => {})
```

**Step 3: 提交逻辑改**（`saveBasicInfo` 2481-2486）

```ts
// 我的权重覆盖：开关开 → set；关 → delete
if (basicEditForm.value.myWeightEnabled) {
  await setProductMyWeight(productId.value, basicEditForm.value.myWeight).catch(() => {})
} else {
  await deleteProductMyWeight(productId.value).catch(() => {})
}
```

**Step 4: 构建校验**

Run: `cd frontend && npm run build`
Expected: 成功，无 TS 报错

---

## Task 4: 前端 — `IngredientDetail.vue` 商品行权重控件同步重构

**目的：** 原料详情页「编辑商品」对话框里的权重控件与 Task 3 同款（`1648-1686`），同步改成滑块 + 开关，保持两处一致。

**Files:**
- Modify: `frontend/src/views/ingredients/IngredientDetail.vue`
  - 模板 `1648-1686`（productForm 三件套）
  - `productForm` 初始化 `2008-2012` 附近（加 `myWeightEnabled`）
  - `saveProduct` 提交（`2036-2048` 附近，按 `myWeightEnabled` 决定 set/delete）

**Step 1: 改模板**（替换 1648-1686 整块，结构与 Task 3 Step 1 完全一致，字段名换成 `productForm.xxx`，`userStore.user?.is_admin` 分支不变）

**Step 2: 表单初始化加 `myWeightEnabled`**（参照 Task 3 Step 2，`productForm` 打开时拉 `getProductMyWeight` 填充）

> 当前 `productForm` 打开逻辑在 `editProduct` / `openProductDialog` 附近（`1990-2012`），需补 `getProductMyWeight` 拉取与 `myWeightEnabled` 赋值，与 Task 3 同款。

**Step 3: 提交逻辑改**（`saveProduct` 内，`productForm.myWeightEnabled` 开 → `setProductMyWeight(p.id, productForm.myWeight)`，关 → `deleteProductMyWeight(p.id)`）

**Step 4: 构建校验**

Run: `cd frontend && npm run build`
Expected: 成功

---

## Task 5: 前端 — `IngredientDetail.vue` 价格趋势 avg 按商品权重加权

**目的：** 原料详情页价格趋势图的「平均线」从「各商品记录简单平均」改为「按日 × 按商品权重加权」，且只改 `avg`，`min`/`max`/`count` 原样（仍是当日记录的最低/最高/条数）。图表 tooltip 注明「加权平均」。

**Files:**
- Modify: `frontend/src/views/ingredients/IngredientDetail.vue`
  - 新增 `productWeights` ref + `loadProductWeights`（调 Task 1 端点）
  - `loadData` / 初始化处调一次 `loadProductWeights`
  - `chartData` computed（`2938-2980` 附近）改 avg 计算
- Modify: `frontend/src/components/charts/PriceTrendChart.vue:218`（tooltip 文案「平均」→「加权平均」；图例 `304` 「平均」→「加权平均」）

**Step 1: 新增权重加载**

在 `merchantPrices` ref 附近新增：

```ts
const productWeights = ref<Map<number, number>>(new Map())

const loadProductWeights = async () => {
  if (!ingredientId.value) return
  try {
    const res = await api.get(`/nutrition/ingredients/${ingredientId.value}/product-weights`)
    productWeights.value = new Map(
      (res.items || []).map((p: any) => [p.product_id, p.effective_weight as number])
    )
  } catch {
    productWeights.value = new Map()
  }
}
```

在 `loadData`（`3054` 附近，`loadProducts()` 那行旁）补 `loadProductWeights()`。在 `loadProducts` 完成后也补一次（商品增删后权重变）。

**Step 2: 改 `chartData` 的 avg**

把现有「按日收集 prices 数组 → avg = sum/length」改为「按日 × 按商品分组 → 每商品均价 × 权重 加权」。`min`/`max`/`count` 仍用当日全部记录：

```ts
const chartData = computed(() => {
  if (!chartPriceRecords.value || chartPriceRecords.value.length === 0) return []

  // 按日收集：allPrices（算 min/max/count）+ byProduct（算加权 avg）
  const dailyAll = new Map<string, number[]>()
  const dailyByProduct = new Map<string, Map<number, number[]>>()

  for (const record of chartPriceRecords.value) {
    if (!record.recorded_at) continue
    const date = new Date(record.recorded_at)
    if (isNaN(date.getTime())) continue
    const dateKey = date.toISOString().split('T')[0]

    const standardQty = parseFloat(String(record.standard_quantity))
    const price = parseFloat(String(record.price)) || 0
    const unitPriceJin = standardQty && standardQty > 0
      ? price * 500 / standardQty
      : price / (parseFloat(String(record.original_quantity)) || 1)
    const unitPrice = convertFromJin(unitPriceJin) ?? unitPriceJin

    if (!dailyAll.has(dateKey)) dailyAll.set(dateKey, [])
    dailyAll.get(dateKey)!.push(unitPrice)

    const pid = (record as any).product_id
    if (pid != null) {
      if (!dailyByProduct.has(dateKey)) dailyByProduct.set(dateKey, new Map())
      const pm = dailyByProduct.get(dateKey)!
      if (!pm.has(pid)) pm.set(pid, [])
      pm.get(pid)!.push(unitPrice)
    }
  }

  return Array.from(dailyAll.entries()).map(([date, prices]) => {
    const sorted = [...prices].sort((a, b) => a - b)
    // 加权 avg：每商品当日均价 × effective_weight
    const pm = dailyByProduct.get(date)
    let avg: number
    if (pm && pm.size > 0) {
      let num = 0, den = 0
      for (const [pid, ups] of pm) {
        const w = productWeights.value.get(pid) ?? 50
        if (w <= 0 || !ups.length) continue
        num += (ups.reduce((a, b) => a + b, 0) / ups.length) * w
        den += w
      }
      avg = den > 0 ? num / den : (prices.reduce((a, b) => a + b, 0) / prices.length)
    } else {
      avg = prices.reduce((a, b) => a + b, 0) / prices.length
    }
    return {
      date,
      min: sorted[0] || 0,
      max: sorted[sorted.length - 1] || 0,
      avg,
      count: prices.length,
    }
  }).sort((a, b) => a.date.localeCompare(b.date))
})
```

> 关键：`record.product_id` 字段需存在。`chartPriceRecords` 来自 `/products` 端点的 `ProductRecord`，模型含 `product_id`。若序列化未带，需先在 `loadChartPriceRecords` 确认响应含 `product_id`（grep `/products` 序列化或实测一条），缺则补序列化字段。

**Step 3: tooltip / 图例文案**

`PriceTrendChart.vue`：
- `218`：`平均: ¥...` → `加权平均: ¥...`
- `304`：`name: '平均'` → `name: '加权平均'`

**Step 4: 构建校验**

Run: `cd frontend && npm run build`
Expected: 成功

---

## Task 6: 前端 — `IngredientDetail.vue` 各商家列表底部加「加权综合价」

**目的：** 「各商家价格」列表底部加一行汇总，复用已加载的 `latestPrice`（已走统一加权服务），标注「商品加权综合价」。与上面「按商家看哪家便宜」是两个视角。

**Files:**
- Modify: `frontend/src/views/ingredients/IngredientDetail.vue:280-311`（各商家列表区块末尾）

**Step 1: 列表底部加汇总行**

在 `merchant-price-list` 的 `</div>` 之后、`</v-card-text>` 之前加：

```vue
<v-divider class="mt-2" />
<div class="d-flex justify-space-between align-center px-1 p-2">
  <span class="text-caption text-medium-emphasis">商品加权综合价</span>
  <span class="font-weight-bold text-tertiary">
    ¥{{ formatPrice(latestPrice) }}<span class="text-caption font-weight-regular">/{{ overlaidDefaultUnitName || '斤' }}</span>
  </span>
</div>
```

> 仅当 `latestPrice` 有值时显示（可包一层 `v-if="latestPrice"`）。`latestPrice` 已是加权价（来自 `/nutrition/ingredients/{id}/latest-price` 的 `average_price`），语义一致。

**Step 2: 构建校验**

Run: `cd frontend && npm run build`
Expected: 成功

---

## Task 7: 验证 + 记录要点

**Step 1: 后端整体校验**

Run: `cd backend && python -m pytest tests/test_ingredient_product_weights.py tests/test_ingredient_merchant_weighted.py -v && python -m py_compile app/api/nutrition.py`
Expected: 全 PASS、无语法错误

**Step 2: 前端整体校验**

Run: `cd frontend && npm run build`
Expected: 成功

**Step 3: 浏览器实测**（用户已开自动重载，不要自行启动服务）

请用户在浏览器核对：
- 商品详情页编辑基本信息：管理员见全局滑块 + 我的覆盖开关；普通用户只见我的覆盖开关 + 「全局默认 N」提示；别名框 hint 不再与权重区重叠。
- 原料详情页价格趋势：avg 线为加权值，tooltip 写「加权平均」；min/max/记录数不变。
- 原料详情页各商家价格：同商家多商品时代表价为加权；列表底部出现「商品加权综合价」。

**Step 4: 记录要点**

按 `CLAUDE.md` 项目索引，在 `cc/` 新增要点文档（前缀 `BUGFIX_` 或 `FEATURE_`），并在 `CLAUDE.md` 「最新修复记录」补一条。内容覆盖：四点修补、权重只影响平均值的原则、复用 `_resolve_weight`、新增 product-weights 端点、同商家多商品加权。

---

## 风险点

1. **`chartPriceRecords` 记录需带 `product_id`**：Task 5 Step 2 依赖。若 `/products` 序列化未返回该字段，需先补序列化（参考 `backend/app/api/products.py` 的 `_to_response`）。实现时先验证。
2. **latest-price-by-merchant 子食材聚合段**（nutrition.py `_lookup_merchant_prices` 调用方后续的 `child_costs_by_merchant` / HierarchyRelationType.CONTAINS 分支）**不能动**，只换 `_lookup_merchant_prices` 函数体本身。
3. **Decimal × float 类型**：后端加权计算 `num/den` 用 float（与现有 `_aggregate_weighted` 的 Decimal 混用时注意），同商家加权内单价已是 float，保持 float 即可。
4. **价格趋势「全部」大跨度性能**：前端按日 × 按商品聚合在客户端，记录量大时可能变慢。复用现有 `loadChartPriceRecords` 分批累积机制，不改加载策略。若实测卡顿再议。
5. **不动的边界**：商品详情页价格趋势（单商品）、各商家行 sparkline 迷你折线、min/max/count——本次明确不改。
