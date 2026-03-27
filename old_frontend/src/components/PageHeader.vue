<template>
  <header class="page-header" :class="{ scrolled: isScrolled }">
    <div class="nav-buttons">
      <button v-if="showBack" @click="$router.go(-1)" class="btn-square nav-btn" title="返回">
        <i class="mdi mdi-arrow-left"></i>
      </button>
      <button v-if="showHome" @click="$router.push('/')" class="btn-square nav-btn" title="主页">
        <i class="mdi mdi-home"></i>
      </button>
    </div>
    <h1 class="page-title">{{ title }}</h1>
    <div class="header-right">
      <slot name="extra"></slot>
      <div class="user-menu" v-if="user">
        <div class="user-trigger" @click="toggleUserMenu" ref="userTrigger">
          <span class="user-name">{{ user.username }}</span>
          <i class="mdi mdi-chevron-down"></i>
        </div>
        <div v-if="showUserMenu" class="user-dropdown" ref="userDropdown">
          <div class="user-info">
            <div class="user-avatar">{{ user.username.charAt(0).toUpperCase() }}</div>
            <div class="user-details">
              <div class="user-username">{{ user.username }}</div>
              <div class="user-email">{{ user.email }}</div>
            </div>
          </div>
          <div class="dropdown-divider"></div>
          <button @click="handleLogout" class="dropdown-item logout-item">
            <i class="mdi mdi-logout"></i>
            <span>退出登录</span>
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { useRouter } from 'vue-router'

interface Props {
  title: string
  showBack?: boolean
  showHome?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showHome: true
})

const userStore = useUserStore()
const router = useRouter()

const user = userStore.user
const showUserMenu = ref(false)
const userTrigger = ref<HTMLElement | null>(null)
const userDropdown = ref<HTMLElement | null>(null)
const isScrolled = ref(false)

function toggleUserMenu() {
  showUserMenu.value = !showUserMenu.value
}

function handleLogout() {
  showUserMenu.value = false
  userStore.logout()
  router.push('/login')
}

function handleClickOutside(event: MouseEvent) {
  if (showUserMenu.value) {
    const target = event.target as Node
    if (
      userTrigger.value &&
      !userTrigger.value.contains(target) &&
      userDropdown.value &&
      !userDropdown.value.contains(target)
    ) {
      showUserMenu.value = false
    }
  }
}

// 检测滚动以添加阴影效果
function handleScroll() {
  isScrolled.value = window.scrollY > 10
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  window.addEventListener('scroll', handleScroll)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  window.removeEventListener('scroll', handleScroll)
})
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2rem;
  position: sticky;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background: white;
  padding: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  transition: box-shadow 0.3s ease, backdrop-filter 0.3s ease;
}

.page-header.scrolled {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.nav-buttons {
  display: flex;
  gap: 0.5rem;
  min-width: 5.5rem; /* 2.5rem + 0.5rem + 2.5rem */
}

.btn-square {
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
}

.btn-square:hover {
  background: #e0e0e0;
}

.page-title {
  font-size: 1.5rem;
  color: #333;
  margin-left: 1rem;
  flex: 1;
  text-align: left;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
  min-width: fit-content;
}

.user-menu {
  position: relative;
  min-width: 8rem;
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: #f5f5f5;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: background-color 0.2s;
  user-select: none;
}

.user-trigger:hover {
  background: #e0e0e0;
}

.user-name {
  font-size: 0.875rem;
  color: #333;
  font-weight: 500;
}

.user-dropdown {
  position: absolute;
  top: calc(100% + 0.5rem);
  right: 0;
  background: white;
  border-radius: 0.75rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  min-width: 16rem;
  z-index: 1000;
  overflow: hidden;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  background: #f9f9f9;
}

.user-avatar {
  width: 2.5rem;
  height: 2.5rem;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 50%;
  font-weight: bold;
  font-size: 1rem;
}

.user-details {
  flex: 1;
}

.user-username {
  font-size: 0.875rem;
  font-weight: 600;
  color: #333;
}

.user-email {
  font-size: 0.75rem;
  color: #666;
  margin-top: 0.125rem;
}

.dropdown-divider {
  height: 1px;
  background: #e0e0e0;
  margin: 0;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  padding: 0.75rem 1rem;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.875rem;
  color: #333;
  transition: background-color 0.2s;
}

.dropdown-item:hover {
  background: #f5f5f5;
}

.logout-item {
  color: #de350b;
}

.logout-item:hover {
  background: #fef2f2;
}

/* 移动端优化 */
@media (max-width: 768px) {
  .page-header {
    margin-bottom: 1.5rem;
    padding: 0.75rem;
  }

  .header-right {
    gap: 0.375rem;
    flex-shrink: 0;
  }

  .nav-buttons {
    min-width: auto;
  }

  .btn-square {
    width: 2rem;
    height: 2rem;
    font-size: 0.875rem;
  }

  .page-title {
    font-size: 1.125rem;
    margin-left: 1rem;
  }

  .user-menu {
    min-width: auto;
  }

  .user-trigger {
    padding: 0.375rem 0.75rem;
  }

  .user-name {
    font-size: 0.75rem;
    max-width: 3rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .user-dropdown {
    min-width: 14rem;
    right: -0.5rem;
  }

  .user-info {
    padding: 0.75rem;
  }

  .user-avatar {
    width: 2rem;
    height: 2rem;
    font-size: 0.875rem;
  }

  .user-username {
    font-size: 0.8125rem;
  }

  .user-email {
    font-size: 0.6875rem;
  }

  .dropdown-item {
    padding: 0.625rem 0.875rem;
    font-size: 0.8125rem;
  }
}

/* 超小屏幕优化 */
@media (max-width: 480px) {
  .btn-square {
    width: 1.75rem;
    height: 1.75rem;
    font-size: 0.8125rem;
  }

  .page-title {
    font-size: 1rem;
    margin-left: 1rem;
  }

  .user-name {
    display: none;
  }

  .user-trigger {
    padding: 0.5rem;
    min-height: 1.75rem;
    min-width: 1.75rem;
    justify-content: center;
  }

  .user-dropdown {
    right: -0.5rem;
    min-width: 12rem;
  }

  .user-info {
    padding: 0.625rem;
  }

  .user-avatar {
    width: 1.75rem;
    height: 1.75rem;
    font-size: 0.8125rem;
  }

  .user-username {
    font-size: 0.75rem;
  }

  .user-email {
    font-size: 0.625rem;
  }

  .dropdown-item {
    padding: 0.5rem 0.75rem;
    font-size: 0.75rem;
  }
}
</style>
