<template>
  <div class="mb-4">
    <div class="d-flex align-center mb-3">
      <v-icon start color="info">mdi-store-outline</v-icon>
      <span class="text-h6 font-weight-regular">按商家预估成本</span>
    </div>

    <div v-if="loading" class="d-flex ga-3">
      <v-skeleton-loader v-for="i in 3" :key="i" type="card" class="flex-1-1" max-width="240" />
    </div>
    <div v-else-if="!merchantList.length" class="text-center py-6 text-medium-emphasis">
      <v-icon size="40" color="medium-emphasis">mdi-store-off</v-icon>
      <div class="text-body-2 mt-2">暂无商家价格数据</div>
    </div>
    <div v-else class="merchant-cards">
      <v-card
        v-for="m in merchantList"
        :key="m.merchant_id"
        :class="{ 'merchant-card-recommended': m.is_recommended }"
        :color="m.is_recommended ? 'orange-lighten-5' : undefined"
        class="merchant-card"
        elevation="0"
        variant="outlined"
      >
        <v-card-text>
          <div class="d-flex align-center mb-1">
            <span class="text-body-1 font-weight-medium text-truncate">{{ m.merchant_name }}</span>
            <v-spacer />
            <v-chip v-if="m.is_recommended" size="x-small" color="orange" class="font-weight-bold">
              最实惠 ✓
            </v-chip>
          </div>
          <div class="text-caption text-medium-emphasis mb-2">
            覆盖 {{ m.covered_count }}/{{ m.total_ingredients }} 种食材
          </div>
          <div class="text-h5 font-weight-bold mb-1">
            ¥{{ (m.total_cost || 0).toFixed(2) }}
          </div>
          <div v-if="m.missing_ingredients?.length" class="text-caption text-warning">
            <v-icon size="12" color="warning">mdi-alert-circle-outline</v-icon>
            缺 {{ m.missing_ingredients.join('、') }}
          </div>
        </v-card-text>
      </v-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  merchantCosts?: { merchants?: any[] } | null
  loading?: boolean
}>()

const merchantList = computed(() => {
  return props.merchantCosts?.merchants || []
})
</script>

<style scoped>
.merchant-cards {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 4px;
}
.merchant-card {
  min-width: 180px;
  max-width: 240px;
  flex: 1;
}
.merchant-card-recommended {
  border-color: #ff9800 !important;
  border-width: 2px !important;
}
</style>
