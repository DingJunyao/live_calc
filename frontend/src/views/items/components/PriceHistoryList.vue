<template>
  <div class="price-history-list">
    <div class="section-header">
      <h2 class="section-title">价格历史</h2>
    </div>

    <div v-if="records.length === 0" class="no-data">
      <i class="mdi mdi-list-box-outline"></i>
      <p>暂无价格记录</p>
    </div>

    <div v-else class="table-container">
      <table class="price-table">
        <thead>
          <tr>
            <th v-if="type === 'ingredient'">商品</th>
            <th>日期</th>
            <th>商家</th>
            <th>单价</th>
            <th>数量</th>
            <th>单位</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="record in records" :key="record.id">
            <td v-if="type === 'ingredient'" class="product-name-cell">{{ record.product_name }}</td>
            <td>{{ formatDate(record.recorded_at) }}</td>
            <td>{{ record.merchant_name || '-' }}</td>
            <td class="price-cell">
              <div class="unit-price">¥{{ formatPrice(calculateUnitPrice(record)) }}/{{ record.original_unit }}</div>
              <div class="total-price">总计: ¥{{ formatPrice(record.price) }}</div>
            </td>
            <td>{{ record.original_quantity }}</td>
            <td>{{ record.original_unit }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页 -->
    <div v-if="pagination.total > pagination.pageSize" class="pagination">
      <button
        @click="$emit('page-change', pagination.page - 1)"
        class="page-btn"
        :disabled="pagination.page === 1"
      >
        <i class="mdi mdi-chevron-left"></i>
      </button>
      <span class="page-info">
        {{ pagination.page }} / {{ Math.ceil(pagination.total / pagination.pageSize) }}
      </span>
      <button
        @click="$emit('page-change', pagination.page + 1)"
        class="page-btn"
        :disabled="pagination.page >= Math.ceil(pagination.total / pagination.pageSize)"
      >
        <i class="mdi mdi-chevron-right"></i>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PriceRecord } from '../types'

defineProps<{
  records: PriceRecord[]
  type: 'product' | 'ingredient'
  pagination: {
    page: number
    pageSize: number
    total: number
  }
}>()

defineEmits<{
  'page-change': [page: number]
}>()

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatPrice(price: any): string {
  if (price === undefined || price === null) return '-'
  const numPrice = typeof price === 'string' ? parseFloat(price) : price
  if (isNaN(numPrice)) return '-'
  return numPrice.toFixed(2)
}

function calculateUnitPrice(record: PriceRecord): number {
  if (record.original_quantity && record.original_quantity > 0) {
    return record.price / record.original_quantity
  }
  return record.price
}
</script>

<style scoped>
.price-history-list {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 24px;
  padding: 20px;
}

.section-header {
  margin-bottom: 16px;
}

.section-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.table-container {
  overflow-x: auto;
}

.price-table {
  width: 100%;
  border-collapse: collapse;
}

.price-table th,
.price-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #f5f5f5;
}

.price-table th {
  background-color: #f9f9f9;
  font-weight: 600;
  color: #666;
  font-size: 13px;
}

.price-table td {
  font-size: 14px;
  color: #333;
}

.price-table tr:hover {
  background-color: #f9f9f9;
}

.price-cell {
  font-weight: 600;
  color: #42b883;
  vertical-align: top;
}

.unit-price {
  margin-bottom: 4px;
}

.total-price {
  font-size: 12px;
  color: #999;
  font-weight: normal;
}

.product-name-cell {
  font-weight: 500;
  color: #333;
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.no-data {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #999;
}

.no-data i {
  font-size: 40px;
  margin-bottom: 8px;
  color: #e5e5e5;
}

.no-data p {
  margin: 0;
  font-size: 14px;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 16px;
  gap: 12px;
}

.page-btn {
  width: 32px;
  height: 32px;
  border: 1px solid #e5e5e5;
  background-color: white;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  transition: all 0.3s;
}

.page-btn:hover:not(:disabled) {
  border-color: #42b883;
  color: #42b883;
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-info {
  font-size: 14px;
  color: #666;
  min-width: 60px;
  text-align: center;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .price-history-list {
    padding: 12px;
  }

  .price-table th,
  .price-table td {
    padding: 10px 8px;
    font-size: 13px;
  }

  .product-name-cell {
    max-width: 80px;
  }

  .price-table th:nth-child(3),
  .price-table td:nth-child(3) {
    display: none;
  }
}
</style>
