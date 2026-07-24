<template>
  <v-app>
    <v-container class="d-flex align-center justify-center" style="min-height: 100vh">
      <v-card max-width="560" class="pa-4 w-100">
        <v-card-title class="text-center text-h5 font-weight-bold py-4">
          初始化 - 本地数据模式
        </v-card-title>
        <v-card-text class="text-center text-medium-emphasis">
          首次启动需要初始化本地数据。初始化向导将帮助您设置基础单位、分类等数据。
        </v-card-text>
        <v-card-actions class="justify-center pb-4">
          <v-btn color="primary" variant="tonal" @click="goHome" size="large">
            <v-icon start>mdi-check</v-icon>
            开始使用
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-container>
  </v-app>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function goHome() {
  router.push('/')
}
</script>
