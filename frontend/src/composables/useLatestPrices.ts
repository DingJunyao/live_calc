import { ref, type Ref } from 'vue'
import { api } from '@/api/client'

interface LatestPriceInfo {
  average_price: number | null
  unit: string | null
  latest_date?: string | null
}

/**
 * 并行拉取列表中每一项的“当天平均单价”，并回填到响应式数组上。
 * 复用原料 / 商品详情页所用的最新价格接口，避免重复实现。
 *
 * 回填字段（按需）：latest_price / latest_price_unit / latest_price_date
 *
 * @param items  响应式列表（ref）
 * @param urlFor 给定一项，返回其最新价格接口 URL
 */
export function useLatestPrices<T extends { id: number }>(
  items: Ref<T[]>,
  urlFor: (item: T) => string
) {
  const loading = ref(false)

  const load = async () => {
    if (!items.value.length) return
    loading.value = true
    const results = await Promise.allSettled(
      items.value.map(item => api.get<LatestPriceInfo>(urlFor(item)))
    )
    items.value.forEach((item, i) => {
      const r = results[i]
      const anyItem = item as any
      if (r.status === 'fulfilled' && r.value && r.value.average_price != null) {
        anyItem.latest_price = r.value.average_price
        anyItem.latest_price_unit = r.value.unit
        anyItem.latest_price_date = r.value.latest_date ?? null
      } else {
        anyItem.latest_price = null
        anyItem.latest_price_unit = null
        anyItem.latest_price_date = null
      }
    })
    loading.value = false
  }

  return { loading, load }
}

/**
 * 单价智能格式化：整数不带小数，否则最多两位并去尾零（10.30 -> 10.3，10 -> 10）。
 */
export function formatUnitPrice(price: number | string | null | undefined): string {
  if (price == null) return ''
  const num = parseFloat(String(price)) || 0
  return Number(num.toFixed(2)).toString()
}
