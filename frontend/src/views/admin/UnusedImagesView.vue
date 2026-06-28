<template>
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-app-bar-title class="text-h6">未使用图片清理</v-app-bar-title>
    <template #append>
      <v-btn
        v-if="selected.length > 0"
        color="error"
        variant="tonal"
        size="small"
        class="mr-2"
        :loading="deleting"
        :disabled="deleting"
        @click="confirmDelete"
      >
        <v-icon start size="small">mdi-delete</v-icon>
        删除选中（{{ selected.length }}）
      </v-btn>
      <v-btn
        color="primary"
        variant="tonal"
        size="small"
        :loading="loading"
        @click="loadImages"
      >
        <v-icon start size="small">mdi-refresh</v-icon>
        刷新
      </v-btn>
    </template>
  </v-app-bar>

  <v-container class="pa-4" style="margin-top: 48px">
    <v-alert
      v-if="errorMsg"
      type="error"
      closable
      class="mb-4"
      @click:close="errorMsg = ''"
    >{{ errorMsg }}</v-alert>

    <v-alert
      v-if="successMsg"
      type="success"
      closable
      class="mb-4"
      @click:close="successMsg = ''"
    >{{ successMsg }}</v-alert>

    <v-card elevation="0">
      <v-card-text>
        <div class="d-flex align-center mb-4">
          <v-icon color="medium-emphasis" class="mr-2">mdi-information-outline</v-icon>
          <span class="text-body-2 text-medium-emphasis">
            扫描结果：{{ images.length }} 张未使用的图片
          </span>
        </div>

        <v-row v-if="images.length > 0">
          <v-col
            v-for="img in images"
            :key="img.filename"
            cols="6"
            sm="4"
            md="3"
            lg="2"
          >
            <v-card
              elevation="1"
              :color="selected.includes(img.filename) ? 'primary' : undefined"
              @click="toggleSelect(img.filename)"
              style="cursor: pointer"
            >
              <v-img
                :src="img.url"
                height="100"
                cover
                class="bg-grey-lighten-3"
              >
                <template #placeholder>
                  <div class="d-flex align-center justify-center fill-height">
                    <v-icon color="grey">mdi-image-off</v-icon>
                  </div>
                </template>
              </v-img>
              <v-card-text class="pa-1 text-caption text-center text-truncate">
                {{ img.filename }}
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <v-card-text v-else-if="!loading" class="text-center py-8">
          <v-icon size="64" color="success">mdi-check-circle-outline</v-icon>
          <div class="text-body-1 mt-2">没有未使用的图片</div>
        </v-card-text>

        <v-skeleton-loader
          v-if="loading"
          type="card"
          class="mx-auto"
          max-width="300"
        />
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useDisplay } from 'vuetify'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import { api } from '@/api/client'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const { smAndDown } = useDisplay()

const images = ref<any[]>([])
const selected = ref<string[]>([])
const loading = ref(false)
const deleting = ref(false)
const errorMsg = ref('')
const successMsg = ref('')

const loadImages = async () => {
  loading.value = true
  errorMsg.value = ''
  selected.value = []
  try {
    const resp = await api.get('/admin/images/unused')
    images.value = resp.images || []
  } catch (e: any) {
    errorMsg.value = e.response?.data?.detail || e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const toggleSelect = (filename: string) => {
  const idx = selected.value.indexOf(filename)
  if (idx >= 0) {
    selected.value.splice(idx, 1)
  } else {
    selected.value.push(filename)
  }
}

const confirmDelete = async () => {
  if (!selected.value.length) return
  deleting.value = true
  errorMsg.value = ''
  successMsg.value = ''
  try {
    const resp = await api.post('/admin/images/unused/delete', {
      paths: selected.value,
    })
    successMsg.value = `已删除 ${resp.deleted?.length || 0} 张图片`
    if (resp.errors?.length) {
      errorMsg.value = `删除失败：${resp.errors.join('；')}`
    }
    await loadImages()
  } catch (e: any) {
    errorMsg.value = e.response?.data?.detail || e.message || '删除失败'
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  loadImages()
})
</script>
