<template>
  <div id="app">
    <RouterView />
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<style>
#app {
  min-height: 100vh;
  height: 100%;
  background: #f9faf9;
}
body {  margin: 0;}

/* 移动端防放大样式 - 艹，这个SB问题折磨了无数开发者 */
input, textarea, select {
  font-size: 16px !important; /* 关键：确保字体不小于16px防止iOS放大 */
  -webkit-text-size-adjust: 100% !important;
  transform: translateZ(0); /* 硬件加速优化 */
  -webkit-backface-visibility: hidden;
}
</style>
