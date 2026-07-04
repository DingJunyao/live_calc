# 粘贴导入别名匹配缝隙修复

## 现象

快速填写「粘贴导入」粘贴文本 `青茄 1.88`，解析正常但商品列标 ⚠️ 待处理，未自动匹配到商品「青茄子」——而「青茄子」的别名恰为「青茄」，本应命中。

## 根因

后端 autocomplete 与前端粘贴导入的 tryAutoMatch 对「name 匹配」语义不一致，子串命中结果卡在两个优先级的缝隙里。

**数据流（输入 `青茄`）：**

1. 后端 [products_entity.py:799](../backend/app/api/products_entity.py#L799) autocomplete 先判名字**子串**：`search_lower in product.name.lower()` → `"青茄" in "青茄子"` → True → 标 `match_type="name"`。别名分支是 `elif`（[:802](../backend/app/api/products_entity.py#L802)），名字命中后不再下沉判别名，故「青茄子」被标成 `name` 返回（不是 `alias`）。

2. 前端 [PasteImportDialog.vue](../frontend/src/components/prices/PasteImportDialog.vue) `tryAutoMatch`：
   - Priority 1：`it.match_type === 'name' && it.name === row.name` → name 且**完全相等**。`"青茄子" === "青茄"` → False，不命中。
   - Priority 2：`ingredient_name` → 后端没返（name 先截胡），不命中。
   - Priority 3：`it.match_type === 'alias'` → 后端给的是 `name`，找不到。
   - Priority 4：`ingredient_alias` → 关联原料 id=212「茄子」别名为空，不命中。
   - 全部落空 → 行保持 `unmatched`。

一句话：后端 name 用子串（搜索框体验需要，合理），前端粘贴导入的「精确匹配」用全等；子串命中时结果既不算 name（前端要全等），后端也没标 alias（被 name 截胡），落到中间。

## 取证

- DB：`products.id=403` name=`青茄子` aliases=`["青茄"]` ingredient_id=212 is_active=1；`ingredients.id=212` name=`茄子` aliases=`[]`。仅 403 一个商品中招。
- 模型 [product_entity.py:18](../backend/app/models/product_entity.py#L18)：`aliases = Column(JSON)`，SQLAlchemy 读出为 Python list，后端 `for alias in product.aliases` 与前端拿到的 aliases 数组均正常 → 别名机制本身没坏。
- 后端 autocomplete 返回体含 `"aliases": product.aliases or []`（[:827](../backend/app/api/products_entity.py#L827)），前端本就有数据可自判。

## 修复

前端一处，不动后端通用搜索语义（autocomplete 被商品搜索框、快速填写、内联搜索共用，改其语义波及面大）。

[PasteImportDialog.vue](../frontend/src/components/prices/PasteImportDialog.vue) `tryAutoMatch` Priority 3：

```js
// 修复前
const aliasMatch = list.find((it: any) => it.match_type === 'alias')

// 修复后
const aliasMatch = list.find((it: any) =>
  it.match_type === 'alias' ||
  (Array.isArray(it.aliases) && it.aliases.includes(row.name))
)
```

无论后端把这条标成 `name` 还是 `alias`，只要返回的 aliases 数组含输入词，前端都能捞回。别名用全等（`includes`）与主名全等语义对称，不误伤。

## 验证

- `npm run build` 通过（20.02s，无新增告警）。
- 静态走查三种输入：
  - `青茄子`（主名全等）→ P1 命中，不走 P3 ✓
  - `青茄`（别名）→ P3 `aliases.includes("青茄")` 命中 403 ✓
  - `茄`（短子串非别名）→ P1 不等、P3 `["青茄"].includes("茄")` 不中，仍 unmatched，与修复前一致 ✓
- 项目暂无前端测试框架，以构建 + 静态走查替代。

## 影响

纯前端，无表结构变更，无需 alembic/SQL。

## 续修：原料别名缝隙（「翅中」→「鸡翅中」）

同一根因的另一情境——别名在原料（ingredient）而非商品（product）身上时，Pri 4 也被 name 子串截胡。

### 现象

粘贴导入 `翅中` 未匹配到商品「鸡翅中」——原料 id=516「鸡翅中」的别名恰为 `["翅中"]`。

### 根因

同源（name 子串截胡），叠加一个信息丢失：后端 autocomplete 返回体只含 `aliases`（商品别名），不含 `ingredient_aliases`（原料别名）。

**数据流（输入 `翅中`）：**

1. 后端 `"翅中" in product.name "鸡翅中"` → True → `match_type="name"`。原料别名 `["翅中"]` 不再判定。
2. 前端 Pri 1：`"鸡翅中"==="翅中"` ✗。Pri 2：`ingredient_name`？后端给 `name` ✗。Pri 3（修后）：`aliases=null` ✗。Pri 4（修前）：`ingredient_alias`？后端给 `name` ✗。全落空。
3. **关键**：即使前端想像 Pri 3 那样自判原料别名，也拿不到——后端没返 `ingredient_aliases`。

### 修复

两处：

1. **后端** [products_entity.py:828](../backend/app/api/products_entity.py#L828) 加一行 `ingredient_aliases` 字段：
   ```python
   "ingredient_aliases": product.ingredient.aliases if product.ingredient else [],
   ```

2. **前端** Pri 4 自判，对齐 Pri 3 模式：
   ```js
   const ingAliasMatch = list.find((it: any) =>
     it.match_type === 'ingredient_alias' ||
     (Array.isArray(it.ingredient_aliases) && it.ingredient_aliases.includes(row.name))
   )
   ```

### 验证

- `py_compile` 通过；`npm run build` 通过（12.66s）。
- 静态走查：
  - `翅中` → Pri 4 `ingredient_aliases=["翅中"].includes("翅中")` ✓ 命中 product 516
  - `鸡翅中` → Pri 1 全等命中 ✓
  - `翅根` → 同理 Pri 4 命中 product 708（原料 706 别名 `["翅根"]`）✓
  - `翅` → 不命中 alias/ingredient_aliases，仍 unmatched ✓
- 无表结构变更。
