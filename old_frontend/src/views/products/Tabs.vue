<!-- 为新产品/原料页面添加导航 -->
<nav class="nav-tabs">
  <router-link to="/products" class="nav-tab">价格记录</router-link>
  <router-link to="/ingredients" class="nav-tab">原料管理</router-link>
</nav>

<div class="tab-content">
  <router-view />
</div>