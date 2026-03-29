<template>
  <v-bottom-navigation
    :elevation="3"
    color="primary"
    grow
    class="mobile-nav"
  >
    <v-btn value="prices" to="/">
      <v-icon>mdi-currency-cny</v-icon>
      <span>记录</span>
    </v-btn>

    <v-btn value="recipes" to="/recipes">
      <v-icon>mdi-book-open-variant</v-icon>
      <span>菜谱</span>
    </v-btn>

    <v-btn value="data" to="/data">
      <v-icon>mdi-database</v-icon>
      <span>数据</span>
    </v-btn>

    <v-btn value="profile" to="/profile">
      <v-icon>mdi-account</v-icon>
      <span>我的</span>
    </v-btn>
  </v-bottom-navigation>
</template>

<script setup lang="ts">
// 移动端底部导航 - 使用 CSS 媒体查询控制显示
</script>

<style>
/* 只在移动端显示 */
@media (max-width: 960px) {
  .mobile-nav {
    display: none !important;
  }
}
</style>
