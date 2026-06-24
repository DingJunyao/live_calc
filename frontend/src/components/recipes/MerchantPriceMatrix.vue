<template>
  <div>
    <div class="d-flex align-center mb-3">
      <v-icon start color="info">mdi-table-compare</v-icon>
      <span class="text-h6 font-weight-regular">商家比价推荐</span>
    </div>

    <v-card elevation="0" variant="outlined">
      <v-card-text class="pa-0">
        <div v-if="loading" class="text-center py-8">
          <v-progress-circular indeterminate size="24" />
        </div>
        <div v-else-if="!merchantNames.length" class="text-center py-6 text-medium-emphasis">
          <v-icon size="40" color="medium-emphasis">mdi-table-off</v-icon>
          <div class="text-body-2 mt-2">暂无比价数据</div>
        </div>
        <div v-else class="price-table-wrapper">
          <table class="price-matrix">
            <thead>
              <tr>
                <th class="sticky-col" style="min-width:160px">食材 / 用量</th>
                <th v-for="m in merchantNames" :key="m" class="text-right">
                  <span class="text-truncate d-inline-block" style="max-width:80px">{{ m }}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in tableRows" :key="row.recipeIngredientId">
                <td class="sticky-col" style="min-width:160px">
                  <span class="font-weight-medium">{{ row.name }}</span>
                  <span class="qty-badge">{{ row.quantityDisplay }}</span>
                  <v-tooltip v-if="row.fallbackChain" location="top">
                    <template #activator="{ props }">
                      <v-icon v-bind="props" size="x-small" color="info" class="ml-1">mdi-information</v-icon>
                    </template>
                    <div class="text-caption">根据以下食材计算价格：</div>
                    <div class="text-body-2 font-weight-bold">{{ row.fallbackChain }}</div>
                  </v-tooltip>
                </td>
                <td
                  v-for="(cell, mName) in row.merchantPrices"
                  :key="mName"
                  class="text-right"
                  :class="{ 'price-lowest': cell.isLowest, 'price-missing': !cell.hasPrice }"
                >
                  {{ cell.hasPrice ? `¥${cell.displayValue}` : '—' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  recipeIngredients?: any[] | null
  merchantPrices?: any[] | null
  loading?: boolean
}>()

const merchantNames = computed(() => {
  if (!props.merchantPrices?.length) return []
  const names = new Set<string>()
  for (const item of props.merchantPrices) {
    for (const p of (item.prices || [])) {
      names.add(p.merchant_name || `商家${p.merchant_id}`)
    }
  }
  return Array.from(names)
})

interface CellData {
  hasPrice: boolean
  displayValue: string
  rawValue: number
  isLowest: boolean
}

interface TableRow {
  recipeIngredientId: number
  name: string
  quantityDisplay: string
  merchantPrices: Record<string, CellData>
}

const tableRows = computed<TableRow[]>(() => {
  const ingredients = props.recipeIngredients || []
  const priceItems = props.merchantPrices || []

  return ingredients
    .filter((ing: any) => ing.ingredient_id)
    .map((ing: any) => {
      const priceItem = priceItems.find(
        (p: any) => p.recipeIngredientId === ing.id
      )

      const merchantPrices: Record<string, CellData> = {}
      const merchantPriceList = priceItem?.prices || []
      for (const mName of merchantNames.value) {
        const match = merchantPriceList.find(
          (p: any) => (p.merchant_name || `商家${p.merchant_id}`) === mName
        )
        if (match) {
          // 优先显示 total_cost（预估总价），回退到 price（单价）
          const displayVal = match.total_cost != null ? match.total_cost : (match.price || 0)
          merchantPrices[mName] = {
            hasPrice: true,
            displayValue: displayVal.toFixed(2),
            rawValue: displayVal,
            isLowest: match.is_lowest || false,
          }
        } else {
          merchantPrices[mName] = {
            hasPrice: false,
            displayValue: '',
            rawValue: 0,
            isLowest: false,
          }
        }
      }

      let qtyDisplay = priceItem?.qtyDisplay || ''
      if (!qtyDisplay) {
        if (ing.quantity) {
          qtyDisplay = `${ing.quantity}${ing.unit || ''}`
        } else if (ing.quantity_range) {
          let qr = ing.quantity_range
          if (typeof qr === 'string') {
            try { qr = JSON.parse(qr) } catch { /* ignore */ }
          }
          if (qr && typeof qr === 'object' && qr.min != null && qr.max != null) {
            qtyDisplay = `${qr.min}-${qr.max}${ing.unit || ''}`
          }
        }
      }

      return {
        recipeIngredientId: ing.id,
        name: ing.name,
        quantityDisplay: qtyDisplay,
        merchantPrices,
        fallbackChain: priceItem?.fallbackChain || null,
      }
    })
})
</script>

<style scoped>
.price-table-wrapper {
  overflow-x: auto;
  overflow-y: clip;
}
.price-matrix {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.price-matrix th,
.price-matrix td {
  padding: 8px 12px;
  white-space: nowrap;
  border-bottom: 1px solid #e0e0e0;
}
.price-matrix th {
  background: #f5f5f5;
  font-weight: 500;
  position: sticky;
  top: 0;
  z-index: 2;
}
.sticky-col {
  position: sticky;
  left: 0;
  background: white;
  z-index: 1;
  min-width: 120px;
  /* 防止滚动时背景透出 */
  box-shadow: 2px 0 6px rgba(0,0,0,0.06);
}
.price-matrix th.sticky-col {
  background: #f5f5f5;
  z-index: 3;
  box-shadow: 2px 0 6px rgba(0,0,0,0.08);
}
.qty-badge {
  display: inline-block;
  color: #888;
  font-size: 12px;
  margin-left: 6px;
  white-space: nowrap;
}
.price-lowest {
  font-weight: 700;
  color: #e65100;
}
.price-missing {
  color: #ccc;
}
.text-right {
  text-align: right;
}
</style>
