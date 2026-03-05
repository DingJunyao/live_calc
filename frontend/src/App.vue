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
</style>
