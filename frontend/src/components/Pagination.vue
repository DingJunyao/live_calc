<template>
  <div class="pagination" v-if="totalPages > 1">
    <button
      @click="goToPage(1)"
      :disabled="currentPage === 1"
      class="pagination-btn"
      title="第一页"
    >
      <i class="mdi mdi-page-first"></i>
    </button>
    <button
      @click="goToPage(currentPage - 1)"
      :disabled="currentPage === 1"
      class="pagination-btn"
      title="上一页"
    >
      <i class="mdi mdi-chevron-left"></i>
    </button>
    <div class="pagination-pages">
      <template v-for="(item, index) in visiblePages" :key="index">
        <button
          v-if="item > 0"
          @click="goToPage(item)"
          :class="{ 'pagination-page': true, 'pagination-page-active': item === currentPage }"
        >
          {{ item }}
        </button>
        <span v-else class="pagination-ellipsis">...</span>
      </template>
    </div>
    <button
      @click="goToPage(currentPage + 1)"
      :disabled="currentPage === totalPages"
      class="pagination-btn"
      title="下一页"
    >
      <i class="mdi mdi-chevron-right"></i>
    </button>
    <button
      @click="goToPage(totalPages)"
      :disabled="currentPage === totalPages"
      class="pagination-btn"
      title="最后一页"
    >
      <i class="mdi mdi-page-last"></i>
    </button>
    <div class="pagination-info">
      <select v-model="pageSize" @change="handlePageSizeChange" class="pagination-select">
        <option :value="10">10 条/页</option>
        <option :value="20">20 条/页</option>
        <option :value="50">50 条/页</option>
        <option :value="100">100 条/页</option>
      </select>
      <span class="pagination-text">
        共 {{ total }} 条，第 {{ currentPage }} / {{ totalPages }} 页
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

interface Props {
  currentPage: number
  pageSize: number
  total: number
}

interface Emits {
  (e: 'change-page', page: number): void
  (e: 'change-page-size', size: number): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const currentPage = computed(() => props.currentPage)
const pageSize = ref(props.pageSize)
const totalPages = computed(() => Math.ceil(props.total / pageSize.value))

const visiblePages = computed(() => {
  const pages: number[] = []
  const total = totalPages.value
  const current = currentPage.value

  if (total <= 7) {
    for (let i = 1; i <= total; i++) {
      pages.push(i)
    }
  } else {
    if (current <= 4) {
      for (let i = 1; i <= 5; i++) {
        pages.push(i)
      }
      pages.push(-1)
    } else if (current >= total - 3) {
      pages.push(-1)
      for (let i = total - 4; i <= total; i++) {
        pages.push(i)
      }
    } else {
      pages.push(1)
      pages.push(-1)
      for (let i = current - 1; i <= current + 1; i++) {
        pages.push(i)
      }
      pages.push(-1)
      for (let i = total - 2; i <= total; i++) {
        pages.push(i)
      }
    }
  }
  return pages
})

const showEllipsisStart = computed(() => {
  return totalPages.value > 7 && currentPage.value > 4
})

const showEllipsisEnd = computed(() => {
  return totalPages.value > 7 && currentPage.value < totalPages.value - 3
})

function goToPage(page: number) {
  // 忽略省略号标记 (-1)
  if (page === -1) return
  if (page < 1) page = 1
  if (page > totalPages.value) page = totalPages.value
  emit('change-page', page)
}

function handlePageSizeChange(event: Event) {
  const target = event.target as HTMLSelectElement
  emit('change-page-size', Number(target.value))
}

watch(() => props.pageSize, (newSize) => {
  pageSize.value = newSize
})
</script>

<style scoped>
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1rem 0;
  margin-top: 2rem;
  flex-wrap: wrap;
}

.pagination-btn {
  width: 2.5rem;
  height: 2.5rem;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #f5f5f5;
  color: #333;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 1rem;
  padding: 0;
  transition: all 0.2s;
}

.pagination-btn:hover:not(:disabled) {
  background: #e0e0e0;
}

.pagination-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pagination-pages {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.pagination-page {
  width: 2.25rem;
  height: 2.5rem;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #f5f5f5;
  color: #333;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.pagination-page:hover {
  background: #e0e0e0;
}

.pagination-page-active {
  background: #42b883;
  color: white;
  border-color: #42b883;
}

.pagination-page-active:hover {
  background: #36966d;
}

.pagination-ellipsis {
  padding: 0 0.5rem;
  color: #666;
  font-size: 0.875rem;
}

.pagination-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-left: auto;
}

.pagination-select {
  padding: 0.375rem 1.5rem;
  background: #f5f5f5;
  color: #333;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
}

.pagination-text {
  font-size: 0.875rem;
  color: #666;
}

/* 移动端优化 */
@media (max-width: 768px) {
  .pagination {
    gap: 0.25rem;
  }

  .pagination-btn {
    width: 2rem;
    height: 2rem;
    font-size: 0.875rem;
  }

  .pagination-page {
    width: 2rem;
    height: 2rem;
    font-size: 0.8125rem;
  }

  .pagination-info {
    flex-direction: column;
    gap: 0.5rem;
    margin-top: 0.5rem;
  }
}

/* 超小屏幕优化 */
@media (max-width: 480px) {
  .pagination {
    gap: 0.125rem;
  }

  .pagination-btn {
    width: 1.75rem;
    height: 1.75rem;
    font-size: 0.8125rem;
  }

  .pagination-page {
    width: 1.75rem;
    height: 1.75rem;
    font-size: 0.75rem;
  }

  .pagination-select {
    padding: 0.25rem 1rem;
    font-size: 0.75rem;
  }

  .pagination-text {
    font-size: 0.75rem;
  }
}
</style>
