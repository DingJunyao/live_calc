# 价格录入场景优化设计方案

**日期：** 2026-03-12
**设计师：** 幽浮喵 (nekomata-engineer)

---

## 背景

用户测试了"录入价格"场景，发现以下问题需要优化：

1. 商品的候选下拉项数有限，输入"米"无法显示"五常大米"等选项
2. 移动端对话框高度太高，数量和单位分成两行
3. 取消按钮与提交按钮垂直排列，容易误触
4. 提交后有时会跳回登录页（token 过期问题）
5. 录入时需要快速维护原料和商品的功能

---

## 问题分析与解决方案

### 问题1：商品候选下拉项数有限

**问题描述：**
输入"米"时，无法在候选列表中看到"五常大米"、"糙米"、"黑米"等商品。当前实现只显示前10条结果。

**解决方案（方案 B）：**
改用 `<select>` 元素配合搜索过滤：

- 使用原生 `<select>` 元素作为选择器主体（自带滚动功能，项数无限制）
- 在 select 旁边添加搜索过滤输入框
- 用户输入时，通过 JavaScript 过滤 option 只显示匹配的项
- 选择后搜索框自动填充对应的名称

**技术实现：**
```html
<div class="select-with-search">
  <input
    v-model="productSearchTerm"
    @input="filterProductOptions"
    placeholder="搜索商品..."
    class="search-input"
  />
  <select v-model="newProduct.product_id" required>
    <option value="0">请选择商品</option>
    <option
      v-for="product in filteredProducts"
      :key="product.id"
      :value="product.id"
    >
      {{ product.name }}<span v-if="product.brand"> ({{ product.brand }})</span>
    </option>
  </select>
</div>
```

---

### 问题2：移动端对话框优化

**问题2a：对话框高度太高**

- 移动端 `max-height` 从 `90vh` 调整为 `85vh`
- 确保 `overflow-y: auto` 可滚动
- 适当减小移动端 padding

**问题2b：数量和单位分成两行**

将数量和单位放在同一个 `.form-group` 内，使用 flex 布局：

```html
<div class="form-group">
  <label>数量与单位</label>
  <div class="quantity-unit-row">
    <input
      v-model.number="newProduct.quantity"
      type="number"
      min="0"
      step="any"
      required
      placeholder="数量"
    />
    <select v-model="newProduct.unit" required>
      <option v-for="unit in units" :key="unit.id" :value="unit.abbreviation">
        {{ unit.name }}
      </option>
    </select>
  </div>
</div>
```

```css
.quantity-unit-row {
  display: flex;
  gap: 0.5rem;
}
.quantity-unit-row input {
  flex: 1;
}
.quantity-unit-row select {
  flex: 0 0 auto;
  min-width: 80px;
}
```

---

### 问题3：取消按钮误触

**问题描述：**
取消按钮与提交按钮垂直排列，取消按钮在上方，容易在点击提交按钮时误触取消。

**解决方案：**
- 移除底部的取消按钮（只保留确认提交按钮）
- 在对话框右上角添加关闭按钮（× 图标）
- **移除点击遮罩层关闭功能**（防止误触，用户必须主动点击关闭按钮）
- 保留 ESC 键关闭功能（作为键盘操作的兜底方案）

```typescript
function closeModal() {
  showAddModal.value = false
  // 不再在遮罩层点击时自动关闭
}

// 遮罩层点击时不执行任何操作
function handleOverlayClick(event: MouseEvent) {
  // 阻止事件冒泡，不关闭对话框
  event.stopPropagation()
}
```

```html
<div class="modal-overlay" @click="handleOverlayClick">
  <div class="modal-content" @click.stop>
    <!-- 表单内容 -->
  </div>
</div>
```

```html
<div class="modal-content">
  <div class="modal-header">
    <h2>添加价格记录</h2>
    <button class="close-btn" @click="closeModal" title="关闭">
      &times;
    </button>
  </div>
  <!-- 表单内容 -->
</div>
```

```css
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}
.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #999;
  padding: 0.25rem 0.5rem;
}
.close-btn:hover {
  color: #333;
}
.form-actions {
  /* 只保留提交按钮 */
  justify-content: flex-end;
}
```

---

### 问题4：提交后跳回登录页

**问题描述：**
提交价格记录后，有时会跳回登录页，不清楚为什么 token 这么快过期。

**根本原因：**
当前代码收到 401 响应时，直接清理 token 并跳转到登录页，没有尝试使用 refresh_token 刷新。

**解决方案（方案 A）：**
实现完整的 token 刷新机制：

1. 在 `client.ts` 中添加 `refresh_token` 存储
2. 拦截 401 响应，尝试使用 refresh_token 刷新
3. 刷新成功后重试原请求
4. 刷新失败才跳转登录页

```typescript
// api/client.ts
class ApiClient {
  private refreshToken: string | null = localStorage.getItem('refresh_token')

  // 设置 token 时同时保存 refresh_token
  setToken(accessToken: string, refreshToken?: string): void {
    this.token = accessToken
    if (refreshToken) {
      this.refreshToken = refreshToken
      localStorage.setItem('refresh_token', refreshToken)
    }
  }

  // 清理 token 时同时清理 refresh_token
  clearToken(): void {
    this.token = null
    this.refreshToken = null
    localStorage.removeItem('token')
    localStorage.removeItem('refresh_token')
  }

  // 尝试刷新 token
  private async tryRefreshToken(): Promise<boolean> {
    if (!this.refreshToken) return false

    try {
      const response = await fetch(`${this.baseURL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: this.refreshToken })
      })

      if (response.ok) {
        const data = await response.json()
        this.token = data.access_token
        if (data.refresh_token) {
          this.refreshToken = data.refresh_token
          localStorage.setItem('refresh_token', data.refresh_token)
        }
        localStorage.setItem('token', data.access_token)
        return true
      }
    } catch (e) {
      console.error('Token refresh failed:', e)
    }
    return false
  }

  // 发送请求（包含 401 处理）
  async request(path: string, options: RequestInit = {}): Promise<any> {
    // ... 原有逻辑 ...

    const response = await fetch(`${this.baseURL}${path}`, reqOptions)

    if (!response.ok) {
      if (response.status === 401) {
        // 尝试刷新 token
        const refreshed = await this.tryRefreshToken()
        if (refreshed) {
          // 重新设置 Authorization 头并重试
          reqOptions.headers = {
            ...reqOptions.headers,
            'Authorization': `Bearer ${this.token}`
          }
          return fetch(`${this.baseURL}${path}`, reqOptions).then(res => {
            if (!res.ok) throw new Error('Request failed')
            return res.json()
          })
        }
        // 刷新失败，清理并跳转
        this.clearToken()
        window.location.href = '/login'
        return Promise.reject(new Error('登录已过期，请重新登录'))
      }
      // ... 其他错误处理
    }
    return response.json()
  }
}
```

---

### 问题5：快速维护原料和商品功能

**问题描述：**
录入价格时，如果数据库中没有对应的商品或原料，需要先退出当前流程去创建，非常麻烦。

**解决方案（方案 A）：**
在商品/商家的下拉列表末尾添加"创建新商品/商家"选项：

```html
<select v-model="newProduct.product_id" required>
  <option :value="0">请选择商品</option>
  <option
    v-for="product in filteredProducts"
    :key="product.id"
    :value="product.id"
  >
    {{ product.name }}<template v-if="product.brand"> ({{ product.brand }})</template>
  </option>
  <!-- 快速创建选项 -->
  <option
    v-if="showProductCreateOption"
    :value="-1"
    class="create-option"
  >
    + 创建新商品：{{ productSearchTerm }}
  </option>
</select>
```

```typescript
// 计算是否显示创建选项
const showProductCreateOption = computed(() => {
  // 有搜索词，且搜索词没有匹配到任何现有商品
  const search = productSearchTerm.value.trim().toLowerCase()
  if (!search) return false
  return !filteredProducts.value.some(
    p => p.name.toLowerCase() === search
  )
})

// 选择创建选项时
function onProductChange() {
  if (newProduct.value.product_id === -1) {
    // 打开快速创建商品对话框
    openQuickCreateProductDialog()
  }
}
```

快速创建对话框设计：
- 包含必填字段（商品名称）
- 可选字段（品牌、条码、关联原料）
- 创建成功后自动选中并关闭对话框
- 用户无需离开当前页面

---

## 涉及文件

### 前端文件
- `frontend/src/views/products/ProductList.vue` - 价格记录列表页（主修改）
- `frontend/src/api/client.ts` - API 客户端（添加 token 刷新）

### 新增组件（可选）
- `frontend/src/components/QuickCreateProductDialog.vue` - 快速创建商品对话框
- `frontend/src/components/QuickCreateMerchantDialog.vue` - 快速创建商家对话框

---

## 验收标准

1. ✅ 输入"米"可以搜索并选择到"五常大米"、"糙米"等所有含"米"的商品
2. ✅ 移动端对话框高度合理，数量和单位在同一行显示
3. ✅ 对话框右上角有关闭按钮，取消按钮已移除，点击遮罩层不会关闭
4. ✅ Token 过期时自动刷新，不会莫名跳转登录页
5. ✅ 搜索商品时如果没有匹配项，显示"创建新商品"选项
6. ✅ 快速创建商品后自动选中，无需手动选择

---

## 实施优先级

| 优先级 | 问题 | 预计工作量 |
|--------|------|------------|
| P0 | 问题4（token刷新）| 中等，需要修改核心逻辑 |
| P1 | 问题1（下拉搜索）| 较大，需要重构 UI |
| P2 | 问题5（快速创建）| 中等，需要新增对话框 |
| P3 | 问题2（移动端优化）| 小，样式调整 |
| P4 | 问题3（取消按钮）| 小，样式调整 |

---

*设计完成喵～ φ(≧ω≦*)♪*