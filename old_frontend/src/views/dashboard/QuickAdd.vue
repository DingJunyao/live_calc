<template>
  <div class="quick-add">
    <h2>快速添加</h2>
    <div class="add-buttons">
      <router-link to="/products/new" class="add-btn">
        <span class="btn-icon">📝</span>
        <span>添加价格</span>
      </router-link>
      <router-link to="/locations/new" class="add-btn">
        <span class="btn-icon">📍</span>
        <span>添加地点</span>
      </router-link>
      <router-link to="/recipes/new" class="add-btn">
        <span class="btn-icon">🍳</span>
        <span>创建菜谱</span>
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()

const handleAddProduct = () => {
  router.push('/products/new')
}

const handleAddLocation = () => {
  router.push('/locations/new')
}

const handleAddRecipe = () => {
  router.push('/recipes/new')
}
</script>

<style scoped>
.quick-add {
  padding: 2rem;
}

.quick-add h2 {
  font-size: 1.25rem;
  color: #333;
  margin-bottom: 1.5rem;
}

.add-buttons {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.add-btn {
  background: white;
  padding: 1.5rem 2rem;
  border-radius: 0.5rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  text-align: center;
  text-decoration: none;
  color: #333;
  transition: transform 0.2s, box-shadow 0.2s;
}

.add-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.add-btn .btn-icon {
  font-size: 1.5rem;
  display: block;
  margin-bottom: 0.5rem;
}
</style>
