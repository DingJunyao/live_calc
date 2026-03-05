<template>
  <div class="recipe-import">
    <PageHeader title="菜谱导入管理" :show-back="true" />

    <div class="import-sections">
      <!-- 在线导入部分 -->
      <div class="card">
        <h2>在线导入菜谱</h2>
        <div class="form-group">
          <label>菜谱仓库地址:</label>
          <input
            v-model="repoUrl"
            type="url"
            placeholder="https://github.com/Anduin2017/HowToCook"
            class="form-control"
          />
        </div>
        <button @click="importFromUrl" :disabled="importing" class="btn-primary">
          {{ importing ? '导入中...' : '从URL导入' }}
        </button>
      </div>

      <!-- 上传导入部分 -->
      <div class="card">
        <h2>上传文件导入</h2>
        <div class="form-group">
          <label>选择ZIP文件:</label>
          <input
            type="file"
            @change="handleFileUpload"
            accept=".zip,.json,.tar.gz"
            class="form-control"
          />
          <small class="help-text">支持 .zip, .json, .tar.gz 格式文件</small>
        </div>
        <button
          @click="importFromFile"
          :disabled="!selectedFile || importing"
          class="btn-primary"
        >
          {{ importing ? '导入中...' : '上传并导入' }}
        </button>
      </div>

      <!-- 初始导入部分 -->
      <div class="card">
        <h2>导入初始菜谱</h2>
        <p>如果系统中还没有导入过任何菜谱，可以使用此功能导入初始菜谱集合。</p>
        <button @click="importInitialRecipes" :disabled="importing" class="btn-secondary">
          {{ importing ? '导入中...' : '导入初始菜谱' }}
        </button>
      </div>

      <!-- 导入结果展示 -->
      <div v-if="importResult" class="card result-card">
        <h2>导入结果</h2>
        <div v-if="importResult.success" class="alert alert-success">
          <h3>✅ 导入成功!</h3>
          <p>成功导入: {{ importResult.imported_count || 0 }} 个菜谱</p>
          <p>失败数量: {{ importResult.failed_count || 0 }} 个</p>
          <div v-if="importResult.errors && importResult.errors.length > 0">
            <h4>错误信息:</h4>
            <ul>
              <li v-for="(error, index) in importResult.errors" :key="index">{{ error }}</li>
            </ul>
          </div>
        </div>
        <div v-else class="alert alert-error">
          <h3>❌ 导入失败!</h3>
          <p>{{ importResult.error || '未知错误' }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { api } from '@/api/client';
import PageHeader from '@/components/PageHeader.vue';

const repoUrl = ref('https://github.com/Anduin2017/HowToCook');
const selectedFile = ref<File | null>(null);
const importing = ref(false);
const importResult = ref<any>(null);

function handleFileUpload(event: Event) {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    selectedFile.value = target.files[0];
  }
}

async function importFromUrl() {
  if (!repoUrl.value.trim()) {
    alert('请输入菜谱仓库地址');
    return;
  }

  importing.value = true;
  importResult.value = null;

  try {
    const response = await api.post('/recipes/import-from-url', { url: repoUrl.value });
    importResult.value = response;
    alert(`导入完成! 成功: ${response.imported_count || 0}, 失败: ${response.failed_count || 0}`);
  } catch (error) {
    console.error('导入失败:', error);
    importResult.value = { success: false, error: error.message || '导入失败' };
    alert('导入失败: ' + (error.message || '未知错误'));
  } finally {
    importing.value = false;
  }
}

async function importFromFile() {
  if (!selectedFile.value) {
    alert('请选择要上传的文件');
    return;
  }

  importing.value = true;
  importResult.value = null;

  try {
    const formData = new FormData();
    formData.append('file', selectedFile.value);

    const result = await api.upload('/recipes/import-from-upload', formData);
    importResult.value = result;
    alert(`导入完成! 成功: ${result.imported_count || 0}, 失败: ${result.failed_count || 0}`);
  } catch (error) {
    console.error('导入失败:', error);
    importResult.value = { success: false, error: error.message || '导入失败' };
    alert('导入失败: ' + (error.message || '未知错误'));
  } finally {
    importing.value = false;
  }
}

async function importInitialRecipes() {
  importing.value = true;
  importResult.value = null;

  try {
    const response = await api.post('/recipes/import-initial', {});
    importResult.value = response;
    alert(`导入完成! 成功: ${response.imported_count || 0}, 失败: ${response.failed_count || 0}`);
  } catch (error) {
    console.error('导入初始菜谱失败:', error);
    importResult.value = { success: false, error: error.message || '导入失败' };
    alert('导入初始菜谱失败: ' + (error.message || '未知错误'));
  } finally {
    importing.value = false;
  }
}
</script>

<style scoped>
.recipe-import {
  padding: 2rem;
}

.import-sections {
  display: grid;
  gap: 2rem;
  max-width: 800px;
}

.card {
  background: white;
  border-radius: 0.5rem;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.card h2 {
  margin-top: 0;
  color: #333;
  border-bottom: 1px solid #eee;
  padding-bottom: 0.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #555;
  font-weight: 500;
}

.form-control {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  font-size: 1rem;
  box-sizing: border-box;
}

.help-text {
  color: #666;
  font-size: 0.875rem;
  margin-top: 0.25rem;
  display: block;
}

.btn-primary {
  padding: 0.75rem 1.5rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 1rem;
}

.btn-primary:hover:not(:disabled) {
  background: #5a6fd8;
}

.btn-primary:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 0.75rem 1.5rem;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 1rem;
}

.btn-secondary:hover:not(:disabled) {
  background: #5a6268;
}

.btn-secondary:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.alert {
  padding: 1rem;
  border-radius: 0.5rem;
  margin: 1rem 0;
}

.alert-success {
  background: #e6f4ea;
  border: 1px solid #a3d9b1;
  color: #137333;
}

.alert-error {
  background: #fce8e6;
  border: 1px solid #f5a6a0;
  color: #d93025;
}

.result-card ul {
  list-style: none;
  padding-left: 0;
}

.result-card li {
  background: #f8f9fa;
  padding: 0.5rem;
  margin: 0.25rem 0;
  border-radius: 0.25rem;
  border-left: 3px solid #ccc;
}

/* 移动端优化 */
@media (max-width: 768px) {
  .recipe-import {
    padding: 0.75rem;
  }

  .import-sections {
    gap: 1.5rem;
  }

  .card {
    padding: 1rem;
  }

  .card h2 {
    font-size: 1.125rem;
  }

  .form-group {
    margin-bottom: 0.75rem;
  }

  .form-group label {
    font-size: 0.8125rem;
  }

  .form-control {
    font-size: 0.875rem;
    padding: 0.625rem;
  }

  .help-text {
    font-size: 0.75rem;
  }

  .btn-primary,
  .btn-secondary {
    padding: 0.625rem 1.25rem;
    font-size: 0.8125rem;
  }

  .alert {
    padding: 0.75rem;
    font-size: 0.8125rem;
  }

  .result-card li {
    font-size: 0.8125rem;
  }
}

/* 超小屏幕优化 */
@media (max-width: 480px) {
  .recipe-import {
    padding: 0.5rem;
  }

  .card {
    padding: 0.75rem;
  }

  .card h2 {
    font-size: 1rem;
  }

  .btn-primary,
  .btn-secondary {
    width: 100%;
  }

  .alert {
    font-size: 0.75rem;
  }

  .result-card li {
    font-size: 0.75rem;
  }
}
</style>