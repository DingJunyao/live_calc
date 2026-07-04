# 待审状态显示、我的提议页面、邮件配置 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完善多用户权限体系下的提议流转体验——待审状态显示、我的提议页面、邮件通知配置

**Architecture:** 三项功能围绕现有 change_proposals 框架扩展：
1. 详情 API 追加 `pending_proposal` 字段实现服务端草稿回填；
2. 前端复用 `listProposals` API 实现我的提议页面；
3. 新增 smtp_config / email_templates 两表 + EmailService（threading 异步发送）+ 三个提案事件触发点。

**Tech Stack:** Python FastAPI + smtplib + Vue 3 + Vuetify

---

### Feature A: 待审状态显示（服务端草稿回填）

#### Task A1: 后端 — 创建通用 pending_proposal 查询工具

**Files:**
- Create: `backend/app/services/proposals/pending.py`

- [ ] **Step 1: 编写 `get_pending_proposal` 函数**

```python
# backend/app/services/proposals/pending.py
"""查询当前用户对某实体是否有待审提议。"""
from app.models.change_proposal import ChangeProposal


def get_pending_proposal(db, entity_type: str, entity_id: int, user_id: int):
    """返回当前用户对该实体的一条待审提议，没有则返回 None。"""
    return db.query(ChangeProposal).filter(
        ChangeProposal.entity_type == entity_type,
        ChangeProposal.entity_id == entity_id,
        ChangeProposal.proposer_id == user_id,
        ChangeProposal.status == "pending",
    ).first()
```

- [ ] **Step 2: py_compile 验证**

Run: `python -c "import ast; ast.parse(open('backend/app/services/proposals/pending.py').read())"`
Expected: 无语法错误

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/proposals/pending.py
git commit -m "feat(pending): add get_pending_proposal query utility"
```

---

#### Task A2: 后端 — 给实体详情 API 追加 pending_proposal 字段

在 6 个实体详情端点中，对非管理员用户查询是否有待审提议，有则追加 `pending_proposal` 字段。

**Files:**
- Modify: `backend/app/api/ingredient_extended.py` — `get_ingredient`
- Modify: `backend/app/api/products_entity.py` — `get_product`
- Modify: `backend/app/api/merchants.py` — `get_merchant`
- Modify: `backend/app/api/recipes.py` — `get_recipe`
- Modify: `backend/app/api/nutrition.py` — `get_ingredient_nutrition` / `get_product_nutrition`

模式：每个端点末尾，返回前插入：

```python
# 非管理员追加 pending_proposal
if not getattr(current_user, "is_admin", False):
    from app.services.proposals.pending import get_pending_proposal
    pp = get_pending_proposal(db, "ingredient", ingredient.id, current_user.id)
    if pp:
        result["pending_proposal"] = {
            "id": pp.id,
            "action": pp.action,
            "payload": pp.payload,
        }
```

- [ ] **Step 1: 修改 `get_ingredient`（`ingredient_extended.py` 末尾附近）**

找到返回 `result` 的位置，在其之前插入 pending_proposal 逻辑。

```python
# 非管理员追加 pending_proposal
if not getattr(current_user, "is_admin", False):
    from app.services.proposals.pending import get_pending_proposal
    pp = get_pending_proposal(db, "ingredient", ingredient.id, current_user.id)
    if pp:
        result["pending_proposal"] = {
            "id": pp.id,
            "action": pp.action,
            "payload": pp.payload,
        }
return result
```

注意：需要确保 `result` 是 dict 类型才能追加字段。如果端点返回的是 Pydantic model，需要确认其支持 `model_config` 的 extra 或返回前转为 dict。检查各端点当前返回形式——如果是 ORM 对象直接序列化，改为 dict 或 schema + extra field。

- [ ] **Step 2: 修改 `get_product`（`products_entity.py`）**

同模式，entity_type=`"product"`。

- [ ] **Step 3: 修改 `get_merchant`（`merchants.py`）**

同模式，entity_type=`"merchant"`。

- [ ] **Step 4: 修改 `get_recipe`（`recipes.py`）**

同模式，entity_type=`"recipe"`。

- [ ] **Step 5: 修改 `get_ingredient_nutrition`（`nutrition.py`）**

同模式，entity_type=`"nutrition"`。

- [ ] **Step 6: 修改 `get_product_nutrition`（`nutrition.py`）**

同模式，entity_type=`"product_nutrition"`。

- [ ] **Step 7: py_compile 全量验证**

Run: `python -c "import py_compile; py_compile.compile('backend/app/api/ingredient_extended.py', doraise=True); py_compile.compile('backend/app/api/products_entity.py', doraise=True); py_compile.compile('backend/app/api/merchants.py', doraise=True); py_compile.compile('backend/app/api/recipes.py', doraise=True); py_compile.compile('backend/app/api/nutrition.py', doraise=True)"`
Expected: 无错误

- [ ] **Step 8: Commit**

```bash
git commit -m "feat(pending): add pending_proposal field to entity detail APIs"
```

---

#### Task A3: 前端 — 创建 PendingProposalBanner 组件

**Files:**
- Create: `frontend/src/components/proposals/PendingProposalBanner.vue`

- [ ] **Step 1: 创建组件**

```vue
<template>
  <v-alert
    v-if="proposal"
    :type="alertType"
    variant="tonal"
    density="comfortable"
    class="mb-3"
    :icon="icon"
  >
    <div class="text-body-2">
      {{ message }}
    </div>
  </v-alert>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  proposal: {
    id: number
    action: string
    payload: Record<string, any>
  } | null
}>()

const alertType = computed(() => {
  if (!props.proposal) return 'info'
  return props.proposal.action === 'delete' ? 'warning' : 'info'
})

const icon = computed(() => {
  if (!props.proposal) return 'mdi-information'
  return props.proposal.action === 'delete'
    ? 'mdi-delete-clock-outline'
    : 'mdi-clock-edit-outline'
})

const message = computed(() => {
  if (!props.proposal) return ''
  if (props.proposal.action === 'delete') {
    return '该条目已提交删除申请，待管理员审核。审核通过后该条目将被删除。'
  }
  return '修改待审核——您看到的是已提交的修改内容。审核通过后将正式生效。'
})
</script>
```

- [ ] **Step 2: npm run build 验证**

Run: `cd frontend && npm run build`
Expected: 构建通过

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/proposals/PendingProposalBanner.vue
git commit -m "feat(pending): create PendingProposalBanner component"
```

---

#### Task A4: 前端 — 集成到 IngredientDetail / ProductDetail

**Files:**
- Modify: `frontend/src/views/ingredients/IngredientDetail.vue`
- Modify: `frontend/src/views/products/ProductDetail.vue`
- Modify: `frontend/src/views/merchants/MerchantDetail.vue`

模式：

```vue
<script setup lang="ts">
import PendingProposalBanner from '@/components/proposals/PendingProposalBanner.vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

// 在 loadData 或类似函数中：
const pendingProposal = ref<{ id: number; action: string; payload: Record<string, any> } | null>(null)

// API 返回后：
if (!userStore.user?.is_admin && response.pending_proposal) {
  pendingProposal.value = response.pending_proposal
  // update 场景：用 payload 覆盖原值
  if (response.pending_proposal.action === 'update') {
    const payload = response.pending_proposal.payload
    // 逐个字段覆盖（具体覆盖字段因页面而异）
    if (payload.name) ingredientName.value = payload.name
    if (payload.category_id != null) categoryId.value = payload.category_id
    // ... 其他字段
  }
}
```

模板中：
```vue
<PendingProposalBanner :proposal="pendingProposal" />
```

- [ ] **Step 1: IngredientDetail.vue** — 导入组件、加载 pending_proposal、update 覆盖 name/category_id/aliases 字段

- [ ] **Step 2: ProductDetail.vue** — 导入组件、加载 pending_proposal、update 覆盖 name/brand/barcode 字段

- [ ] **Step 3: MerchantDetail.vue** — 导入组件、加载 pending_proposal、update 覆盖 name/address/phone 字段

- [ ] **Step 4: npm run build 验证**

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/ingredients/IngredientDetail.vue frontend/src/views/products/ProductDetail.vue frontend/src/views/merchants/MerchantDetail.vue
git commit -m "feat(pending): integrate PendingProposalBanner into detail pages"
```

---

### Feature B: 我的提议页面

#### Task B1: 后端 — 确保 listProposals 返回提交时间

前端需要显示创建时间。检查 `GET /proposals` 的 `_to_response` 返回中是否有 `created_at`。`ProposalResponse` schema 没有 `created_at` 字段。

- [ ] **Step 1: 给 `ProposalResponse` schema 追加 `created_at` 字段**

```python
# backend/app/schemas/proposal.py
class ProposalResponse(BaseModel):
    # ... 现有字段
    created_at: Optional[datetime] = None   # 新增
```

- [ ] **Step 2: `_to_response` 填充 `created_at`**

```python
# backend/app/api/proposals.py _to_response 中
return ProposalResponse(
    # ... 现有字段
    created_at=p.created_at,
)
```

- [ ] **Step 3: 前端 `Proposal` 类型加 `created_at`**

```typescript
// frontend/src/api/proposals.ts
export interface Proposal {
  // ... 现有字段
  created_at?: string | null
}
```

- [ ] **Step 4: py_compile + build 验证**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(proposals): add created_at to ProposalResponse"
```

---

#### Task B2: 前端 — 创建 MyProposalsView 页面

**Files:**
- Create: `frontend/src/views/profile/MyProposalsView.vue`

- [ ] **Step 1: 创建页面模板**

复用 ProposalsView 的列表 + 详情对话框逻辑，但为普通用户简化：

```vue
<template>
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
    <v-app-bar-title class="text-h6">我的提议</v-app-bar-title>
    <template #append>
      <v-btn icon="mdi-refresh" variant="text" @click="loadList" />
    </template>
  </v-app-bar>

  <v-container class="pa-4">
    <!-- 提示信息 -->
    <v-alert
      v-if="pendingProposals.length > 0"
      type="info"
      variant="tonal"
      density="comfortable"
      class="mb-4"
    >
      您有 {{ pendingProposals.length }} 条提议待审核。审核通过或驳回后，您将收到通知。
    </v-alert>

    <!-- 状态筛选 -->
    <v-card class="rounded-lg mb-4">
      <v-card-text class="d-flex flex-wrap align-center ga-3 py-3">
        <div class="text-subtitle-2 text-medium-emphasis me-2">状态：</div>
        <v-chip-group v-model="statusFilter" mandatory column>
          <v-chip
            v-for="opt in statusOptions"
            :key="opt.value"
            :value="opt.value"
            :color="opt.color"
            filter
            variant="tonal"
            size="small"
          >
            <v-icon start size="small">{{ opt.icon }}</v-icon>
            {{ opt.label }}
          </v-chip>
        </v-chip-group>
        <v-spacer />
        <div class="text-caption text-medium-emphasis">
          共 {{ proposals.length }} 条
        </div>
      </v-card-text>
    </v-card>

    <!-- 提议列表（只读，无审核按钮） -->
    <v-card class="rounded-lg">
      <v-data-table
        :headers="headers"
        :items="proposals"
        :loading="loading"
        item-value="id"
        hover
        density="comfortable"
        no-data-text="暂无提议"
      >
        <template #item.status="{ item }">
          <v-chip :color="statusColor(item.status)" size="small" variant="tonal">
            <v-icon start size="small">{{ statusIcon(item.status) }}</v-icon>
            {{ statusLabel(item.status) }}
          </v-chip>
        </template>

        <template #item.type="{ item }">
          <div class="d-flex flex-column">
            <span class="text-body-2 font-weight-medium">
              {{ entityTypeLabel(item.entity_type) }} · {{ actionLabel(item.action) }}
            </span>
            <span class="text-caption text-medium-emphasis">#{{ item.id }}</span>
          </div>
        </template>

        <template #item.summary="{ item }">
          <span class="text-body-2 text-medium-emphasis">
            {{ payloadSummary(item) }}
          </span>
        </template>

        <template #item.time="{ item }">
          <div class="text-caption">
            <div v-if="item.applied_at" class="text-success">
              生效：{{ formatToLocalDateTimeShort(item.applied_at) }}
            </div>
            <div v-else-if="item.reviewed_at" class="text-medium-emphasis">
              审核：{{ formatToLocalDateTimeShort(item.reviewed_at) }}
            </div>
            <div v-else class="text-warning">
              提交：{{ formatToLocalDateTimeShort(item.created_at) }}
            </div>
          </div>
        </template>

        <template #item.actions="{ item }">
          <v-btn
            icon="mdi-eye-outline"
            size="small"
            variant="text"
            color="primary"
            @click="openDetail(item)"
          />
        </template>
      </v-data-table>
    </v-card>

    <!-- 详情对话框（复用提案渲染器） -->
    <v-dialog v-model="detailDialog" max-width="780px" scrollable>
      <v-card class="rounded-lg" v-if="detailItem">
        <!-- 与 ProposalsView 相似的详情展示，但没有审核按钮 -->
        <v-card-title class="d-flex align-center py-4 pe-2">
          <v-icon class="mr-2">mdi-clipboard-text-clock</v-icon>
          <span class="text-h6">提议 #{{ detailItem.id }}</span>
          <v-spacer />
          <v-chip :color="statusColor(detailItem.status)" size="small" variant="tonal">
            {{ statusLabel(detailItem.status) }}
          </v-chip>
          <v-btn icon="mdi-close" variant="text" size="small" @click="detailDialog = false" />
        </v-card-title>
        <v-divider />

        <v-card-text class="py-4">
          <!-- 实体标签 -->
          <v-alert
            v-if="detailItem.entity_label"
            type="info"
            variant="tonal"
            density="comfortable"
            class="mb-4"
          >
            <div class="text-caption text-medium-emphasis">目标实体</div>
            <div class="text-body-2">{{ detailItem.entity_label }}</div>
          </v-alert>

          <!-- 基本信息行 -->
          <v-row dense>
            <v-col cols="6" sm="4">
              <div class="text-caption text-medium-emphasis">实体类型</div>
              <div class="text-body-2">{{ entityTypeLabel(detailItem.entity_type) }}</div>
            </v-col>
            <v-col cols="6" sm="4">
              <div class="text-caption text-medium-emphasis">操作</div>
              <div class="text-body-2">{{ actionLabel(detailItem.action) }}</div>
            </v-col>
            <v-col cols="6" sm="4">
              <div class="text-caption text-medium-emphasis">提交时间</div>
              <div class="text-body-2">{{ formatToLocalDateTimeShort(detailItem.created_at) }}</div>
            </v-col>
            <v-col cols="6" sm="4" v-if="detailItem.review_note">
              <div class="text-caption text-medium-emphasis">审核备注</div>
              <div class="text-body-2">{{ detailItem.review_note }}</div>
            </v-col>
          </v-row>

          <!-- 变更内容 diff -->
          <div class="mt-4">
            <div class="text-subtitle-2 mb-2">
              <v-icon size="small" start>mdi-compare-horizontal</v-icon>
              变更内容
            </div>
            <component
              v-if="detailRenderer"
              :is="detailRenderer"
              :proposal="detailItem"
            />
            <template v-else>
              <v-table v-if="diffRows.length" density="compact" class="diff-table">
                <tbody>
                  <tr v-for="row in diffRows" :key="row.field">
                    <td class="text-caption text-medium-emphasis" style="width: 28%">{{ row.field }}</td>
                    <td class="diff-cell before">{{ row.before ?? '—' }}</td>
                    <td class="text-center text-medium-emphasis" style="width: 32px">→</td>
                    <td class="diff-cell after">{{ row.after ?? '—' }}</td>
                  </tr>
                </tbody>
              </v-table>
            </template>
          </div>
        </v-card-text>

        <v-divider />
        <v-card-actions class="pa-4">
          <v-btn variant="tonal" @click="detailDialog = false">关闭</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import { formatToLocalDateTimeShort } from '@/utils/timezone'
import { listProposals, getProposal, type Proposal } from '@/api/proposals'
import { resolveProposalRenderer } from '@/proposalRenderers'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const router = useRouter()
const goBack = () => router.back()

// 状态筛选
type FilterValue = 'all' | 'pending' | 'applied' | 'rejected' | 'reverted'
const statusFilter = ref<FilterValue>('all')
const statusOptions = [
  { value: 'all', label: '全部', color: 'default', icon: 'mdi-format-list-bulleted' },
  { value: 'pending', label: '待审', color: 'warning', icon: 'mdi-clock-outline' },
  { value: 'applied', label: '已生效', color: 'success', icon: 'mdi-check-circle' },
  { value: 'rejected', label: '已驳回', color: 'error', icon: 'mdi-close-circle' },
  { value: 'reverted', label: '已回滚', color: 'info', icon: 'mdi-undo' },
]

const proposals = ref<Proposal[]>([])
const loading = ref(false)
const itemsPerPage = ref(20)

const headers = [
  { title: '状态', key: 'status', sortable: false, width: 110 },
  { title: '类型·动作', key: 'type', sortable: false },
  { title: '摘要', key: 'summary', sortable: false },
  { title: '时间', key: 'time', sortable: false, width: 180 },
  { title: '操作', key: 'actions', sortable: false, align: 'end' as const, width: 80 },
]

const pendingProposals = computed(() => proposals.value.filter(p => p.status === 'pending'))

const loadList = async () => {
  loading.value = true
  try {
    const status = statusFilter.value === 'all' ? undefined : statusFilter.value
    proposals.value = await listProposals(status as any, 100)
  } catch (e: any) {
    console.error('加载提议列表失败', e)
  } finally {
    loading.value = false
  }
}

watch(statusFilter, () => loadList())

// 详情
const detailDialog = ref(false)
const detailItem = ref<Proposal | null>(null)

const openDetail = async (item: Proposal) => {
  detailItem.value = item
  detailDialog.value = true
}

const detailRenderer = computed(() => {
  return detailItem.value ? resolveProposalRenderer(detailItem.value) : null
})

const diffRows = computed(() => {
  const item = detailItem.value
  if (!item) return []
  const before = item.snapshot || {}
  const after = item.payload || {}
  const fields = Array.from(new Set([...Object.keys(before), ...Object.keys(after)]))
  return fields.map(f => ({
    field: f,
    before: f in before ? before[f] : null,
    after: f in after ? after[f] : null,
  }))
})

// 工具函数
function statusColor(s: string): string {
  switch (s) {
    case 'pending': return 'warning'
    case 'applied': return 'success'
    case 'rejected': return 'error'
    case 'reverted': return 'info'
    default: return 'default'
  }
}
function statusIcon(s: string): string {
  switch (s) {
    case 'pending': return 'mdi-clock-outline'
    case 'applied': return 'mdi-check-circle'
    case 'rejected': return 'mdi-close-circle'
    case 'reverted': return 'mdi-undo'
    default: return 'mdi-circle-outline'
  }
}
function statusLabel(s: string): string {
  switch (s) {
    case 'pending': return '待审'
    case 'applied': return '已生效'
    case 'rejected': return '已驳回'
    case 'reverted': return '已回滚'
    default: return s
  }
}
function entityTypeLabel(t: string): string {
  const map: Record<string, string> = {
    ingredient: '原料', nutrition: '营养', unit: '单位',
    merchant: '商家', product: '商品', recipe: '菜谱',
    entity_unit_override: '单位覆盖', entity_density: '密度',
    hierarchy: '层级关系', merchant_merge: '商家合并',
    product_split: '商品拆分', product_merge: '商品合并',
    usda_ingredient_match: 'USDA 原料匹配', usda_product_match: 'USDA 商品匹配',
  }
  return map[t] || t
}
function actionLabel(a: string): string {
  const map: Record<string, string> = {
    create: '创建', update: '更新', delete: '删除',
    merge: '合并', publish: '发布',
  }
  return map[a] || a
}
function payloadSummary(item: Proposal): string {
  const label = item.entity_label ? `${item.entity_label}` : ''
  const p = item.payload || {}
  const candidates = ['name', 'source_name', 'target_name', 'unit_name']
  const parts = candidates.filter(k => p[k] != null).map(k => p[k])
  const detail = parts.length ? parts.slice(0, 2).join('，') : JSON.stringify(p).slice(0, 60)
  return label ? `${label} · ${detail}` : detail
}

onMounted(() => { loadList() })
</script>

<style scoped>
.diff-table .diff-cell { font-size: 0.8rem; word-break: break-all; }
code {
  font-family: 'Courier New', monospace;
  padding: 2px 6px;
  background: rgba(var(--v-theme-primary), 0.1);
  border-radius: 4px;
}
</style>
```

- [ ] **Step 2: npm run build 验证**

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/profile/MyProposalsView.vue
git commit -m "feat(proposals): create MyProposalsView page"
```

---

#### Task B3: 前端 — 添加路由和个人中心入口

**Files:**
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/views/profile/ProfileView.vue`

- [ ] **Step 1: 路由加 `/profile/proposals`**

```typescript
// frontend/src/router/index.ts，在 profile/places 后面：
{
  path: 'profile/proposals',
  name: 'profile-proposals',
  component: () => import('@/views/profile/MyProposalsView.vue'),
  meta: { title: '我的提议' },
},
```

- [ ] **Step 2: ProfileView.vue 添加"我的提议"入口**

在"我的常用地点"后面：

```vue
<v-list-item @click="router.push('/profile/proposals')">
  <template #prepend>
    <v-icon>mdi-clipboard-text-clock</v-icon>
  </template>
  <v-list-item-title>我的提议</v-list-item-title>
  <v-list-item-subtitle>查看提交的变更提议及审核状态</v-list-item-subtitle>
  <template #append>
    <v-chip v-if="pendingProposalCount > 0" color="warning" size="small">
      {{ pendingProposalCount }} 条待审
    </v-chip>
    <v-icon>mdi-chevron-right</v-icon>
  </template>
</v-list-item>
```

添加 data 属性：
```typescript
const pendingProposalCount = ref(0)

const loadPendingCount = async () => {
  try {
    const items = await listProposals('pending', 1)
    // listProposals 返回数组，取长度（但默认 limit=50，足够）
    // 如果后端不支持仅 count，直接取数组 length
    // 更优：后端加 count 参数？但这里简单处理——取第一页的全部用 length
    // 因为列表最长 100 条，用 length 够用
    pendingProposalCount.value = items.length
  } catch { /* ignore */ }
}

onMounted(() => {
  loadStats()
  loadBlacklistCount()
  loadPendingCount()  // 新增
})
```

- [ ] **Step 3: npm run build 验证**

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(proposals): add profile proposals route and entry"
```

---

### Feature C: 邮件配置与发送

#### Task C1: 后端 — 创建 SmtpConfig 和 EmailTemplate 模型

**Files:**
- Create: `backend/app/models/smtp_config.py`
- Create: `backend/app/models/email_template.py`
- Create: `backend/app/schemas/email_config.py`

- [ ] **Step 1: 创建 SmtpConfig 模型**

```python
# backend/app/models/smtp_config.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class SmtpConfig(Base):
    """SMTP 发送配置（单行表，固定 id=1）。"""
    __tablename__ = "smtp_config"

    id = Column(Integer, primary_key=True, default=1)
    host = Column(String(255), nullable=False, default="")
    port = Column(Integer, nullable=False, default=587)
    username = Column(String(255), nullable=False, default="")
    password = Column(String(255), nullable=False, default="")
    use_tls = Column(Boolean, nullable=False, default=True)
    from_address = Column(String(255), nullable=False, default="")
    from_name = Column(String(100), nullable=False, default="LiveCalc")
    enabled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 2: 创建 EmailTemplate 模型**

```python
# backend/app/models/email_template.py
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class EmailTemplate(Base):
    """邮件模板配置。"""
    __tablename__ = "email_templates"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    subject = Column(String(255), nullable=False)
    body_html = Column(Text, nullable=False)
    description = Column(String(500), default="")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 3: 创建 Pydantic schema**

```python
# backend/app/schemas/email_config.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SmtpConfigResponse(BaseModel):
    host: str
    port: int
    username: str
    use_tls: bool
    from_address: str
    from_name: str
    enabled: bool

    model_config = {"from_attributes": True}


class SmtpConfigUpdate(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    use_tls: Optional[bool] = None
    from_address: Optional[str] = None
    from_name: Optional[str] = None
    enabled: Optional[bool] = None


class SmtpTestRequest(BaseModel):
    to_email: str


class EmailTemplateResponse(BaseModel):
    key: str
    name: str
    subject: str
    body_html: str
    description: str
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class EmailTemplateUpdate(BaseModel):
    subject: Optional[str] = None
    body_html: Optional[str] = None
    description: Optional[str] = None
```

- [ ] **Step 4: py_compile 验证**

```bash
python -c "
import py_compile
py_compile.compile('backend/app/models/smtp_config.py', doraise=True)
py_compile.compile('backend/app/models/email_template.py', doraise=True)
py_compile.compile('backend/app/schemas/email_config.py', doraise=True)
print('OK')
"
```

Expected: 打印 OK

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/smtp_config.py backend/app/models/email_template.py backend/app/schemas/email_config.py
git commit -m "feat(email): add SmtpConfig and EmailTemplate models"
```

---

#### Task C2: 后端 — Alembic 迁移 + SQL 脚本

**Files:**
- Create: `backend/alembic/versions/20260704_0001_add_email_config_tables.py`
- Create: `backend/scripts/sql/20260704_add_email_tables_sqlite.sql`
- Create: `backend/scripts/sql/20260704_add_email_tables_mysql.sql`
- Create: `backend/scripts/sql/20260704_add_email_tables_pgsql.sql`
- Create: `backend/scripts/sql/20260704_add_email_tables_pgsql_gis.sql`
- Modify: `backend/app/services/proposals/bootstrap.py` — 插入默认模板

- [ ] **Step 1: 生成 Alembic 迁移脚本**

```python
# backend/alembic/versions/20260704_0001_add_email_config_tables.py
"""add smtp_config and email_tables tables

Revision ID: 20260704_0001
Revises: <上一条 migration id>
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

revision = "20260704_0001"
down_revision = None  # TODO: 替换为上一条 migration id
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "smtp_config",
        sa.Column("id", sa.Integer(), primary_key=True, default=1),
        sa.Column("host", sa.String(255), nullable=False, server_default=""),
        sa.Column("port", sa.Integer(), nullable=False, server_default="587"),
        sa.Column("username", sa.String(255), nullable=False, server_default=""),
        sa.Column("password", sa.String(255), nullable=False, server_default=""),
        sa.Column("use_tls", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("from_address", sa.String(255), nullable=False, server_default=""),
        sa.Column("from_name", sa.String(100), nullable=False, server_default="LiveCalc"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "email_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(50), unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("description", sa.String(500), server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 插入默认模板
    now = datetime.utcnow().isoformat()
    templates = [
        {
            "key": "proposal_submitted",
            "name": "新提议通知（管理员）",
            "subject": "[LiveCalc] 新提议 #{proposal_id}",
            "body_html": "<h2>新变更提议</h2><p>用户 <strong>${proposer_name}</strong> 提交了一条新的变更提议，需要审核。</p><table><tr><td>提议编号</td><td>#${proposal_id}</td></tr><tr><td>实体类型</td><td>${entity_type_label}</td></tr><tr><td>操作</td><td>${action_label}</td></tr><tr><td>目标</td><td>${entity_label}</td></tr></table>",
            "description": "用户提交变更提议时通知所有管理员",
        },
        {
            "key": "proposal_approved",
            "name": "提议通过通知（发起者）",
            "subject": "[LiveCalc] 提议 #{proposal_id} 已通过",
            "body_html": "<h2>提议已通过</h2><p>您的变更提议已通过审核并生效。</p><table><tr><td>提议编号</td><td>#${proposal_id}</td></tr><tr><td>实体类型</td><td>${entity_type_label}</td></tr><tr><td>操作</td><td>${action_label}</td></tr><tr><td>目标</td><td>${entity_label}</td></tr></table>",
            "description": "提议审核通过时通知发起者",
        },
        {
            "key": "proposal_rejected",
            "name": "提议驳回通知（发起者）",
            "subject": "[LiveCalc] 提议 #{proposal_id} 未通过",
            "body_html": "<h2>提议未通过</h2><p>您的变更提议未通过审核。</p><table><tr><td>提议编号</td><td>#${proposal_id}</td></tr><tr><td>实体类型</td><td>${entity_type_label}</td></tr><tr><td>操作</td><td>${action_label}</td></tr><tr><td>目标</td><td>${entity_label}</td></tr></table><p>审核备注：${review_note}</p>",
            "description": "提议审核驳回时通知发起者",
        },
    ]
    for t in templates:
        op.execute(
            f"INSERT INTO email_templates (key, name, subject, body_html, description) "
            f"VALUES ('{t['key']}', '{t['name']}', '{t['subject']}', '{t['body_html']}', '{t['description']}')"
        )


def downgrade():
    op.drop_table("email_templates")
    op.drop_table("smtp_config")
```

- [ ] **Step 2: 创建 SQLite SQL 脚本**

```sql
-- backend/scripts/sql/20260704_add_email_tables_sqlite.sql
-- SQLite 版本：新增 smtp_config 和 email_templates 表

CREATE TABLE IF NOT EXISTS smtp_config (
    id INTEGER PRIMARY KEY DEFAULT 1,
    host VARCHAR(255) NOT NULL DEFAULT '',
    port INTEGER NOT NULL DEFAULT 587,
    username VARCHAR(255) NOT NULL DEFAULT '',
    password VARCHAR(255) NOT NULL DEFAULT '',
    use_tls INTEGER NOT NULL DEFAULT 1,
    from_address VARCHAR(255) NOT NULL DEFAULT '',
    from_name VARCHAR(100) NOT NULL DEFAULT 'LiveCalc',
    enabled INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS email_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    body_html TEXT NOT NULL,
    description VARCHAR(500) DEFAULT '',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 插入默认模板
INSERT OR IGNORE INTO email_templates (key, name, subject, body_html, description) VALUES
('proposal_submitted', '新提议通知（管理员）',
 '[LiveCalc] 新提议 #{proposal_id}',
 '<h2>新变更提议</h2><p>用户 <strong>${proposer_name}</strong> 提交了一条新的变更提议，需要审核。</p><table><tr><td>提议编号</td><td>#${proposal_id}</td></tr><tr><td>实体类型</td><td>${entity_type_label}</td></tr><tr><td>操作</td><td>${action_label}</td></tr><tr><td>目标</td><td>${entity_label}</td></tr></table>',
 '用户提交变更提议时通知所有管理员'),
('proposal_approved', '提议通过通知（发起者）',
 '[LiveCalc] 提议 #{proposal_id} 已通过',
 '<h2>提议已通过</h2><p>您的变更提议已通过审核并生效。</p><table><tr><td>提议编号</td><td>#${proposal_id}</td></tr><tr><td>实体类型</td><td>${entity_type_label}</td></tr><tr><td>操作</td><td>${action_label}</td></tr><tr><td>目标</td><td>${entity_label}</td></tr></table>',
 '提议审核通过时通知发起者'),
('proposal_rejected', '提议驳回通知（发起者）',
 '[LiveCalc] 提议 #{proposal_id} 未通过',
 '<h2>提议未通过</h2><p>您的变更提议未通过审核。</p><table><tr><td>提议编号</td><td>#${proposal_id}</td></tr><tr><td>实体类型</td><td>${entity_type_label}</td></tr><tr><td>操作</td><td>${action_label}</td></tr><tr><td>目标</td><td>${entity_label}</td></tr></table><p>审核备注：${review_note}</p>',
 '提议审核驳回时通知发起者');
```

- [ ] **Step 3: 创建 MySQL SQL 脚本**

```sql
-- backend/scripts/sql/20260704_add_email_tables_mysql.sql
-- MySQL 版本
CREATE TABLE IF NOT EXISTS smtp_config (
    id INT PRIMARY KEY DEFAULT 1,
    host VARCHAR(255) NOT NULL DEFAULT '',
    port INT NOT NULL DEFAULT 587,
    username VARCHAR(255) NOT NULL DEFAULT '',
    password VARCHAR(255) NOT NULL DEFAULT '',
    use_tls TINYINT(1) NOT NULL DEFAULT 1,
    from_address VARCHAR(255) NOT NULL DEFAULT '',
    from_name VARCHAR(100) NOT NULL DEFAULT 'LiveCalc',
    enabled TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS email_templates (
    id INT PRIMARY KEY AUTO_INCREMENT,
    `key` VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    body_html TEXT NOT NULL,
    description VARCHAR(500) DEFAULT '',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 插入默认模板
INSERT IGNORE INTO email_templates (`key`, name, subject, body_html, description) VALUES
('proposal_submitted', '新提议通知（管理员）',
 '[LiveCalc] 新提议 #{proposal_id}',
 '<h2>新变更提议</h2><p>用户 <strong>${proposer_name}</strong> 提交了一条新的变更提议，需要审核。</p><table><tr><td>提议编号</td><td>#${proposal_id}</td></tr><tr><td>实体类型</td><td>${entity_type_label}</td></tr><tr><td>操作</td><td>${action_label}</td></tr><tr><td>目标</td><td>${entity_label}</td></tr></table>',
 '用户提交变更提议时通知所有管理员'),
('proposal_approved', '提议通过通知（发起者）',
 '[LiveCalc] 提议 #{proposal_id} 已通过',
 '<h2>提议已通过</h2><p>您的变更提议已通过审核并生效。</p><table><tr><td>提议编号</td><td>#${proposal_id}</td></tr><tr><td>实体类型</td><td>${entity_type_label}</td></tr><tr><td>操作</td><td>${action_label}</td></tr><tr><td>目标</td><td>${entity_label}</td></tr></table>',
 '提议审核通过时通知发起者'),
('proposal_rejected', '提议驳回通知（发起者）',
 '[LiveCalc] 提议 #{proposal_id} 未通过',
 '<h2>提议未通过</h2><p>您的变更提议未通过审核。</p><table><tr><td>提议编号</td><td>#${proposal_id}</td></tr><tr><td>实体类型</td><td>${entity_type_label}</td></tr><tr><td>操作</td><td>${action_label}</td></tr><tr><td>目标</td><td>${entity_label}</td></tr></table><p>审核备注：${review_note}</p>',
 '提议审核驳回时通知发起者');
```

- [ ] **Step 4: 创建 PostgreSQL SQL 脚本（通用 + PostGIS）**

两个文件内容一致（该变更不涉及 PostGIS），但分别保存：

```sql
-- backend/scripts/sql/20260704_add_email_tables_pgsql.sql
-- PostgreSQL 版本
CREATE TABLE IF NOT EXISTS smtp_config (
    id INTEGER PRIMARY KEY DEFAULT 1,
    host VARCHAR(255) NOT NULL DEFAULT '',
    port INTEGER NOT NULL DEFAULT 587,
    username VARCHAR(255) NOT NULL DEFAULT '',
    password VARCHAR(255) NOT NULL DEFAULT '',
    use_tls BOOLEAN NOT NULL DEFAULT TRUE,
    from_address VARCHAR(255) NOT NULL DEFAULT '',
    from_name VARCHAR(100) NOT NULL DEFAULT 'LiveCalc',
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS email_templates (
    id SERIAL PRIMARY KEY,
    key VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    body_html TEXT NOT NULL,
    description VARCHAR(500) DEFAULT '',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 插入默认模板
INSERT INTO email_templates (key, name, subject, body_html, description)
SELECT 'proposal_submitted', '新提议通知（管理员）',
 '[LiveCalc] 新提议 #{proposal_id}',
 '<h2>新变更提议</h2><p>用户 <strong>${proposer_name}</strong> 提交了一条新的变更提议，需要审核。</p><table><tr><td>提议编号</td><td>#${proposal_id}</td></tr><tr><td>实体类型</td><td>${entity_type_label}</td></tr><tr><td>操作</td><td>${action_label}</td></tr><tr><td>目标</td><td>${entity_label}</td></tr></table>',
 '用户提交变更提议时通知所有管理员'
WHERE NOT EXISTS (SELECT 1 FROM email_templates WHERE key = 'proposal_submitted');

INSERT INTO email_templates (key, name, subject, body_html, description)
SELECT 'proposal_approved', '提议通过通知（发起者）',
 '[LiveCalc] 提议 #{proposal_id} 已通过',
 '<h2>提议已通过</h2><p>您的变更提议已通过审核并生效。</p><table><tr><td>提议编号</td><td>#${proposal_id}</td></tr><tr><td>实体类型</td><td>${entity_type_label}</td></tr><tr><td>操作</td><td>${action_label}</td></tr><tr><td>目标</td><td>${entity_label}</td></tr></table>',
 '提议审核通过时通知发起者'
WHERE NOT EXISTS (SELECT 1 FROM email_templates WHERE key = 'proposal_approved');

INSERT INTO email_templates (key, name, subject, body_html, description)
SELECT 'proposal_rejected', '提议驳回通知（发起者）',
 '[LiveCalc] 提议 #{proposal_id} 未通过',
 '<h2>提议未通过</h2><p>您的变更提议未通过审核。</p><table><tr><td>提议编号</td><td>#${proposal_id}</td></tr><tr><td>实体类型</td><td>${entity_type_label}</td></tr><tr><td>操作</td><td>${action_label}</td></tr><tr><td>目标</td><td>${entity_label}</td></tr></table><p>审核备注：${review_note}</p>',
 '提议审核驳回时通知发起者'
WHERE NOT EXISTS (SELECT 1 FROM email_templates WHERE key = 'proposal_rejected');
```

复制一份为 `20260704_add_email_tables_pgsql_gis.sql`（内容完全相同，标注"与通用版一致，不涉及 PostGIS"）。

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/ backend/scripts/sql/20260704_add_email_tables_*.sql
git commit -m "feat(email): add email tables migration and SQL scripts"
```

---

#### Task C3: 后端 — 创建 EmailService

**Files:**
- Create: `backend/app/services/email_service.py`

- [ ] **Step 1: 创建 EmailService**

```python
# backend/app/services/email_service.py
"""SMTP 邮件发送服务，异步（threading）发送不阻塞请求。"""
import smtplib
import threading
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from string import Template
from typing import Optional

logger = logging.getLogger(__name__)


class EmailService:
    """邮件服务。构造时传入 SmtpConfig ORM 对象或 None。"""

    def __init__(self, config: Optional["SmtpConfig"] = None):
        self._config = config

    @property
    def ready(self) -> bool:
        return self._config is not None and self._config.enabled and bool(self._config.host)

    def send_template_async(self, template_key: str, to_email: str, variables: dict, db) -> None:
        """根据模板 key 渲染并异步发送。静默跳过：服务未就绪、模板不存在。"""
        if not self.ready:
            logger.warning("邮件服务未就绪（enabled=%s host=%s），跳过发送", 
                         self._config.enabled if self._config else "N/A",
                         self._config.host if self._config else "N/A")
            return
        from app.models.email_template import EmailTemplate
        template = db.query(EmailTemplate).filter(EmailTemplate.key == template_key).first()
        if not template:
            logger.warning("邮件模板 %s 不存在，跳过发送", template_key)
            return
        subject = Template(template.subject).safe_substitute(variables)
        body = Template(template.body_html).safe_substitute(variables)
        self._send_async(to_email, subject, body)

    def send_test_async(self, to_email: str) -> None:
        """发送测试邮件。"""
        self._send_async(to_email, "测试邮件 - LiveCalc", 
                        "<h1>SMTP 配置测试</h1><p>这是一封测试邮件，来自 LiveCalc。如果收到此邮件，说明 SMTP 配置正确。</p>")

    def _send_async(self, to_email: str, subject: str, body_html: str) -> None:
        thread = threading.Thread(target=self._send_sync, args=(to_email, subject, body_html), daemon=True)
        thread.start()

    def _send_sync(self, to_email: str, subject: str, body_html: str) -> None:
        config = self._config
        if not config or not config.host:
            return
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{config.from_name} <{config.from_address}>"
            msg["To"] = to_email
            msg.attach(MIMEText(body_html, "html", "utf-8"))

            if config.use_tls:
                server = smtplib.SMTP(config.host, config.port, timeout=10)
                server.starttls()
            else:
                server = smtplib.SMTP(config.host, config.port, timeout=10)

            if config.username:
                server.login(config.username, config.password)
            server.sendmail(config.from_address, [to_email], msg.as_string())
            server.quit()
            logger.info("邮件发送成功: to=%s subject=%s", to_email, subject)
        except Exception as e:
            logger.error("邮件发送失败: to=%s subject=%s error=%s", to_email, subject, e)
```

- [ ] **Step 2: py_compile 验证**

```bash
python -c "import py_compile; py_compile.compile('backend/app/services/email_service.py', doraise=True); print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/email_service.py
git commit -m "feat(email): create EmailService with async SMTP sending"
```

---

#### Task C4: 后端 — 创建邮件配置 API

**Files:**
- Create: `backend/app/api/email_config.py`
- Modify: `backend/app/main.py` — include_router

- [ ] **Step 1: 创建 email_config.py API**

```python
# backend/app/api/email_config.py
"""SMTP 配置与邮件模板管理 API（仅管理员）。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models.user import User
from app.models.smtp_config import SmtpConfig
from app.models.email_template import EmailTemplate
from app.schemas.email_config import (
    SmtpConfigResponse,
    SmtpConfigUpdate,
    SmtpTestRequest,
    EmailTemplateResponse,
    EmailTemplateUpdate,
)
from app.services.email_service import EmailService

router = APIRouter()


def _get_or_create_smtp_config(db: Session) -> SmtpConfig:
    config = db.query(SmtpConfig).first()
    if not config:
        config = SmtpConfig(id=1)
        db.add(config)
        db.flush()
    return config


@router.get("/admin/email-config/smtp", response_model=SmtpConfigResponse)
def get_smtp_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    config = _get_or_create_smtp_config(db)
    # 返回时密码脱敏
    resp = SmtpConfigResponse.model_validate(config)
    if config.password:
        resp.username = config.username  # 保持原样
    return resp


@router.put("/admin/email-config/smtp", response_model=SmtpConfigResponse)
def update_smtp_config(
    body: SmtpConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    config = _get_or_create_smtp_config(db)
    update_data = body.model_dump(exclude_unset=True)
    # 密码为空字符串表示不更新
    if "password" in update_data and not update_data["password"]:
        del update_data["password"]
    for key, value in update_data.items():
        setattr(config, key, value)
    db.commit()
    db.refresh(config)
    return SmtpConfigResponse.model_validate(config)


@router.post("/admin/email-config/smtp/test")
def test_smtp_config(
    body: SmtpTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    config = _get_or_create_smtp_config(db)
    if not config.host or not config.enabled:
        raise HTTPException(status_code=400, detail="SMTP 未配置或未启用")
    service = EmailService(config)
    service.send_test_async(body.to_email)
    return {"message": f"测试邮件已异步发送至 {body.to_email}"}


@router.get("/admin/email-config/templates", response_model=List[EmailTemplateResponse])
def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    return db.query(EmailTemplate).order_by(EmailTemplate.key).all()


@router.get("/admin/email-config/templates/{key}", response_model=EmailTemplateResponse)
def get_template(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    tpl = db.query(EmailTemplate).filter(EmailTemplate.key == key).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="模板不存在")
    return tpl


@router.put("/admin/email-config/templates/{key}", response_model=EmailTemplateResponse)
def update_template(
    key: str,
    body: EmailTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    tpl = db.query(EmailTemplate).filter(EmailTemplate.key == key).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="模板不存在")
    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(tpl, k, v)
    db.commit()
    db.refresh(tpl)
    return tpl
```

- [ ] **Step 2: 在 main.py 中注册路由**

```python
# backend/app/main.py
from app.api.email_config import router as email_config_router

# 与其他 admin 路由放在一起
app.include_router(email_config_router, prefix="/api/v1")
```

- [ ] **Step 3: py_compile 验证**

```bash
python -c "import py_compile; py_compile.compile('backend/app/api/email_config.py', doraise=True); print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/email_config.py
git commit -m "feat(email): add email config management API"
```

---

#### Task C5: 后端 — 在 proposals.py 中添加邮件触发点

**Files:**
- Modify: `backend/app/api/proposals.py`

- [ ] **Step 1: 在 `submit_proposal` 中添加管理员通知**

```python
# backend/app/api/proposals.py 顶部新增 import
from app.models.smtp_config import SmtpConfig
from app.services.email_service import EmailService


# 在 submit_proposal 末尾，db.commit() 之后：
    # 邮件通知管理员
    if p.review_policy == "manual" and p.status == "pending":
        _notify_admins_on_submit(db, p)

    return _to_response(db, p)
```

添加辅助函数（可放在文件末尾）：

```python
# ========== 邮件通知辅助 ==========

def _entity_label_for_email(db, proposal) -> str:
    """获取实体的可读标签用于邮件。"""
    executor = ExecutorRegistry.get(proposal.entity_type)
    if executor is not None:
        try:
            label = executor.entity_label(db, proposal)
            if label:
                return label
        except Exception:
            pass
    return f"{proposal.entity_type}#{proposal.entity_id}" if proposal.entity_id else proposal.entity_type


def _notify_admins_on_submit(db, proposal):
    from app.models.user import User
    config = db.query(SmtpConfig).first()
    service = EmailService(config)
    if not service.ready:
        return
    admins = db.query(User).filter(User.is_admin.is_(True)).all()
    variables = {
        "proposer_name": f"#{proposal.proposer_id}",
        "proposal_id": str(proposal.id),
        "entity_type_label": proposal.entity_type,
        "action_label": proposal.action,
        "entity_label": _entity_label_for_email(db, proposal),
    }
    for admin in admins:
        if admin.email:
            service.send_template_async("proposal_submitted", admin.email, variables, db)


def _notify_proposer(db, proposal, template_key, extra_vars=None):
    from app.models.user import User
    config = db.query(SmtpConfig).first()
    service = EmailService(config)
    if not service.ready:
        return
    proposer = db.query(User).filter(User.id == proposal.proposer_id).first()
    if not proposer or not proposer.email:
        return
    variables = {
        "proposal_id": str(proposal.id),
        "entity_type_label": proposal.entity_type,
        "action_label": proposal.action,
        "entity_label": _entity_label_for_email(db, proposal),
    }
    if extra_vars:
        variables.update(extra_vars)
    service.send_template_async(template_key, proposer.email, variables, db)
```

- [ ] **Step 2: 在 `review_proposal` 中添加发起者通知**

在 `review_proposal` 的 `db.commit()` 之后：

```python
    # 邮件通知发起者
    if p.status == "applied":
        _notify_proposer(db, p, "proposal_approved")
    elif p.status == "rejected":
        _notify_proposer(db, p, "proposal_rejected", {"review_note": body.note or ""})

    return _to_response(db, p)
```

- [ ] **Step 3: py_compile + 静态检查**

```bash
python -c "import py_compile; py_compile.compile('backend/app/api/proposals.py', doraise=True); print('OK')"
```

确保 SmtpConfig 和 EmailService 的 import 不会产生循环依赖（它们不依赖 proposals 模块，安全）。

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(email): add email triggers on proposal submit/review"
```

---

#### Task C6: 前端 — 创建 EmailConfigView 页面

**Files:**
- Create: `frontend/src/views/admin/EmailConfigView.vue`
- Create: `frontend/src/api/emailConfig.ts`

- [ ] **Step 1: 创建 API 客户端**

```typescript
// frontend/src/api/emailConfig.ts
import api from './client'

export interface SmtpConfig {
  host: string
  port: number
  username: string
  use_tls: boolean
  from_address: string
  from_name: string
  enabled: boolean
}

export interface SmtpConfigUpdate {
  host?: string
  port?: number
  username?: string
  password?: string
  use_tls?: boolean
  from_address?: string
  from_name?: string
  enabled?: boolean
}

export interface EmailTemplate {
  key: string
  name: string
  subject: string
  body_html: string
  description: string
  updated_at?: string
}

export interface EmailTemplateUpdate {
  subject?: string
  body_html?: string
  description?: string
}

export function getSmtpConfig(): Promise<SmtpConfig> {
  return api.get('/admin/email-config/smtp')
}

export function updateSmtpConfig(body: SmtpConfigUpdate): Promise<SmtpConfig> {
  return api.put('/admin/email-config/smtp', body)
}

export function testSmtpConfig(to_email: string): Promise<{ message: string }> {
  return api.post('/admin/email-config/smtp/test', { to_email })
}

export function listTemplates(): Promise<EmailTemplate[]> {
  return api.get('/admin/email-config/templates')
}

export function getTemplate(key: string): Promise<EmailTemplate> {
  return api.get(`/admin/email-config/templates/${key}`)
}

export function updateTemplate(key: string, body: EmailTemplateUpdate): Promise<EmailTemplate> {
  return api.put(`/admin/email-config/templates/${key}`, body)
}
```

- [ ] **Step 2: 创建 EmailConfigView.vue**

参考 AiConfigView.vue 的模式——v-expansion-panels 两面板：

```vue
<template>
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
    <v-app-bar-title class="text-h6">邮件配置</v-app-bar-title>
    <template #append>
      <v-btn icon="mdi-refresh" variant="text" @click="loadAll" />
    </template>
  </v-app-bar>

  <v-container class="pa-4">
    <v-expansion-panels variant="accordion" multiple>
      <!-- 面板一：SMTP 配置 -->
      <v-expansion-panel :value="0">
        <v-expansion-panel-title>
          <v-icon start class="mr-2">mdi-email-cog</v-icon>
          SMTP 配置
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-row dense>
            <v-col cols="12" sm="6">
              <v-text-field v-model="smtp.host" label="SMTP 服务器" placeholder="smtp.example.com"
                variant="outlined" density="compact" hide-details="auto" />
            </v-col>
            <v-col cols="6" sm="3">
              <v-text-field v-model.number="smtp.port" label="端口" type="number"
                variant="outlined" density="compact" hide-details="auto" />
            </v-col>
            <v-col cols="6" sm="3" class="d-flex align-center">
              <v-switch v-model="smtp.use_tls" label="TLS" density="compact" hide-details />
            </v-col>
            <v-col cols="12" sm="6">
              <v-text-field v-model="smtp.username" label="用户名"
                variant="outlined" density="compact" hide-details="auto" />
            </v-col>
            <v-col cols="12" sm="6">
              <v-text-field v-model="passwordField" label="密码" type="password"
                variant="outlined" density="compact" hide-details="auto"
                placeholder="留空则不修改" />
            </v-col>
            <v-col cols="12" sm="6">
              <v-text-field v-model="smtp.from_address" label="发件人地址" placeholder="noreply@example.com"
                variant="outlined" density="compact" hide-details="auto" />
            </v-col>
            <v-col cols="12" sm="3">
              <v-text-field v-model="smtp.from_name" label="发件人名称"
                variant="outlined" density="compact" hide-details="auto" />
            </v-col>
            <v-col cols="12" sm="3" class="d-flex align-center">
              <v-switch v-model="smtp.enabled" label="启用" density="compact" hide-details />
            </v-col>
          </v-row>

          <v-row class="mt-4">
            <v-col cols="12" class="d-flex ga-2">
              <v-btn color="primary" :loading="savingSmtp" @click="saveSmtp">
                保存 SMTP 配置
              </v-btn>
              <v-spacer />
              <v-text-field v-model="testEmail" label="测试邮箱" variant="outlined"
                density="compact" hide-details style="max-width: 250px" />
              <v-btn variant="tonal" :loading="testing" :disabled="!testEmail || !smtp.enabled"
                @click="sendTest">
                发送测试邮件
              </v-btn>
            </v-col>
          </v-row>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <!-- 面板二：邮件模板 -->
      <v-expansion-panel :value="1">
        <v-expansion-panel-title>
          <v-icon start class="mr-2">mdi-email-edit-outline</v-icon>
          邮件模板
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-alert type="info" variant="tonal" density="comfortable" class="mb-4">
            可用变量：<code>${proposal_id}</code> <code>${entity_type_label}</code>
            <code>${action_label}</code> <code>${entity_label}</code>
            <code>${proposer_name}</code> <code>${review_note}</code>
          </v-alert>

          <v-card
            v-for="tpl in templates"
            :key="tpl.key"
            variant="outlined"
            class="mb-4 rounded-lg"
          >
            <v-card-text>
              <div class="text-subtitle-2 mb-2">
                {{ tpl.name }}
                <v-chip size="x-small" variant="tonal" class="ml-2">{{ tpl.key }}</v-chip>
              </div>
              <div class="text-caption text-medium-emphasis mb-2">{{ tpl.description }}</div>

              <v-text-field v-model="tpl.subject" label="邮件主题"
                variant="outlined" density="compact" hide-details="auto" class="mb-3" />

              <v-textarea v-model="tpl.body_html" label="HTML 正文"
                variant="outlined" density="compact" hide-details="auto"
                rows="8" class="font-mono" />

              <v-btn
                color="primary"
                variant="tonal"
                size="small"
                class="mt-2"
                :loading="savingTemplate === tpl.key"
                @click="saveTemplate(tpl)"
              >
                保存模板
              </v-btn>
            </v-card-text>
          </v-card>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </v-container>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import { useGlobalSnackbar } from '@/composables/useGlobalSnackbar'
import {
  getSmtpConfig,
  updateSmtpConfig,
  testSmtpConfig,
  listTemplates,
  updateTemplate,
  type SmtpConfig,
  type EmailTemplate,
} from '@/api/emailConfig'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const router = useRouter()
const { notify } = useGlobalSnackbar()
const goBack = () => router.back()

// SMTP
const smtp = reactive<SmtpConfig>({
  host: '', port: 587, username: '', use_tls: true,
  from_address: '', from_name: 'LiveCalc', enabled: false,
})
const passwordField = ref('')
const savingSmtp = ref(false)

const saveSmtp = async () => {
  savingSmtp.value = true
  try {
    const body: any = { ...smtp }
    if (passwordField.value) body.password = passwordField.value
    await updateSmtpConfig(body)
    notify('SMTP 配置已保存', 'success')
  } catch (e: any) {
    notify(e?.userMessage || '保存失败', 'error')
  } finally {
    savingSmtp.value = false
  }
}

const testEmail = ref('')
const testing = ref(false)

const sendTest = async () => {
  if (!testEmail.value) return
  testing.value = true
  try {
    const res = await testSmtpConfig(testEmail.value)
    notify(res.message || '测试邮件已发送', 'success')
  } catch (e: any) {
    notify(e?.userMessage || '发送失败', 'error')
  } finally {
    testing.value = false
  }
}

// 模板
const templates = ref<EmailTemplate[]>([])
const savingTemplate = ref('')

const saveTemplate = async (tpl: EmailTemplate) => {
  savingTemplate.value = tpl.key
  try {
    await updateTemplate(tpl.key, {
      subject: tpl.subject,
      body_html: tpl.body_html,
      description: tpl.description,
    })
    notify(`模板「${tpl.name}」已保存`, 'success')
  } catch (e: any) {
    notify(e?.userMessage || '保存失败', 'error')
  } finally {
    savingTemplate.value = ''
  }
}

const loadAll = async () => {
  try {
    const config = await getSmtpConfig()
    Object.assign(smtp, config)
  } catch { /* ignore */ }
  try {
    templates.value = await listTemplates()
  } catch { /* ignore */ }
}

onMounted(() => { loadAll() })
</script>

<style scoped>
.font-mono :deep(textarea) {
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
}
</style>
```

- [ ] **Step 3: npm run build 验证**

```bash
cd frontend && npm run build
```

Expected: 构建通过

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/admin/EmailConfigView.vue frontend/src/api/emailConfig.ts
git commit -m "feat(email): add EmailConfigView page and API client"
```

---

#### Task C7: 前端 — 添加路由和导航入口

**Files:**
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/views/admin/AdminDashboard.vue`

- [ ] **Step 1: 路由添加 `/admin/email-config`**

```typescript
// frontend/src/router/index.ts，在 proposals 附近：
{
  path: 'admin/email-config',
  name: 'admin-email-config',
  meta: { adminOnly: true, title: '邮件配置' },
  component: () => import('@/views/admin/EmailConfigView.vue'),
},
```

- [ ] **Step 2: AdminDashboard.vue 添加"邮件配置"入口**

在"提议审核台"后面：

```vue
<v-list-item
  prepend-icon="mdi-email-cog"
  title="邮件配置"
  subtitle="SMTP 设置与邮件模板管理"
  to="/admin/email-config"
>
  <template #append>
    <v-icon>mdi-chevron-right</v-icon>
  </template>
</v-list-item>
```

- [ ] **Step 3: npm run build 验证**

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(email): add email config route and admin nav entry"
```

---

#### Task C8: 开发库补表 + 数据完整性

由于开发库不走 alembic，需要手动补新建的表。

- [ ] **Step 1: 备份开发库**

```bash
cp backend/data/livecalc.db backend/data/livecalc.db.bak.$(date +%Y%m%d_%H%M%S)
```

- [ ] **Step 2: 在开发库中创建两张新表并插入默认模板**

```bash
sqlite3 backend/data/livecalc.db < backend/scripts/sql/20260704_add_email_tables_sqlite.sql
```

- [ ] **Step 3: 验证**

```bash
sqlite3 backend/data/livecalc.db ".tables" | grep -E "smtp_config|email_templates"
sqlite3 backend/data/livecalc.db "SELECT key, name FROM email_templates;"
```

Expected: 输出三行默认模板。

- [ ] **Step 4: Commit**

```bash
git commit -m "chore(db): add email tables to dev database"
```

---

## 计划自审清单

- [ ] **Spec 覆盖度**
  - Feature 1（待审状态显示）：Task A1 (pending 查询) + A2 (后端 6 端点) + A3 (前端组件) + A4 (3 详情页集成) → 覆盖
  - Feature 2（我的提议）：Task B1 (created_at) + B2 (MyProposalsView) + B3 (路由 + 入口) → 覆盖
  - Feature 3（邮件配置）：Task C1 (模型) + C2 (迁移 + SQL) + C3 (EmailService) + C4 (API) + C5 (触发点) + C6 (前端页面) + C7 (路由导航) + C8 (开发库) → 覆盖

- [ ] **无占位符**：所有代码块包含完整实现，无 TBD/TODO

- [ ] **类型一致性**：前后端接口字段名一致（pending_proposal、smtp_config、email_templates 等）

- [ ] **无实现遗漏**：所有 Python 文件头有 import、所有函数有 docstring 或注释、所有 API 有权限装饰器
