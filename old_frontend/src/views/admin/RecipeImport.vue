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
            :disabled="importing"
          />
        </div>
        <button @click="importFromUrl" :disabled="importing" class="btn-primary">
          {{ importing ? '导入中...' : '从URL导入' }}
        </button>

        <!-- 进度显示 -->
        <div v-if="importProgress.show" class="progress-section">
          <h3>📊 导入进度</h3>
          <div class="progress-bar-container">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: importProgress.percentage + '%' }"></div>
            </div>
            <span class="progress-text">{{ importProgress.percentage.toFixed(1) }}%</span>
          </div>
          <div class="progress-details">
            <div class="detail-item">
              <span class="label">当前阶段:</span>
              <span class="value">{{ importProgress.stage }}</span>
            </div>
            <div class="detail-item">
              <span class="label">进度:</span>
              <span class="value">{{ importProgress.current }} / {{ importProgress.total }}</span>
            </div>
            <div class="detail-item" v-if="importProgress.message">
              <span class="label">状态:</span>
              <span class="value">{{ importProgress.message }}</span>
            </div>
          </div>
        </div>
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
            :disabled="importing"
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
          <p>成功导入: {{ importResult.ingredients?.imported || 0 }} 个原料</p>
          <p>成功导入: {{ importResult.recipes?.imported || 0 }} 个菜谱</p>
          <p v-if="importResult.ingredients?.skipped > 0">跳过原料: {{ importResult.ingredients?.skipped }} 个</p>
          <p v-if="importResult.recipes?.skipped > 0">跳过菜谱: {{ importResult.recipes?.skipped }} 个</p>
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

// 进度状态
const importProgress = ref({
  show: false,
  stage: '',
  current: 0,
  total: 0,
  percentage: 0,
  message: ''
});

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
  importProgress.value = {
    show: true,
    stage: '准备中',
    current: 0,
    total: 0,
    percentage: 0,
    message: ''
  };

  try {
    // 使用流式响应来获取进度（如果有后端支持）
    const response = await api.post('/recipes/import-from-url-enhanced', { url: repoUrl.value });
    importResult.value = response;
    importProgress.value = {
      show: false,
      stage: '完成',
      current: 1,
      total: 1,
      percentage: 100,
      message: '导入完成'
    };
    alert(`导入完成! 成功: ${response.recipes?.imported || 0}, 失败: ${response.recipes?.failed || 0}`);
  } catch (error) {
    console.error('导入失败:', error);
    importResult.value = { success: false, error: error.message || '导入失败' };
    importProgress.value = {
      show: false,
      stage: '失败',
      current: 0,
      total: 0,
      percentage: 0,
      message: '导入失败'
    };
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
  importProgress.value = {
    show: true,
    stage: '上传中',
    current: 0,
    total: 1,
    percentage: 0,
    message: '正在上传文件...'
  };

  try {
    const formData = new FormData();
    formData.append('file', selectedFile.value);

    // 使用进度跟踪（如果后端支持）
    const result = await api.upload('/recipes/import-from-upload-enhanced', formData, (event) => {
      if (event.type === 'uploadProgress') {
        const data = event.data as any;
        importProgress.value = {
          show: true,
          stage: data.stage || '处理中',
          current: data.current || 0,
          total: data.total || 1,
          percentage: data.percentage || 0,
          message: data.message || ''
        };
      }
    });

    importResult.value = result;
    importProgress.value = {
      show: false,
      stage: '完成',
      current: 1,
      total: 1,
      percentage: 100,
      message: '导入完成'
    };
    alert(`导入完成! 成功: ${result.recipes?.imported || 0}, 失败: ${result.recipes?.failed || 0}`);
  } catch (error) {
    console.error('导入失败:', error);
    importResult.value = { success: false, error: error.message || '导入失败' };
    importProgress.value = {
      show: false,
      stage: '失败',
      current: 0,
      total: 0,
      percentage: 0,
      message: '导入失败'
    };
    alert('导入失败: ' + (error.message || '未知错误'));
  } finally {
    importing.value = false;
  }
}

async function importInitialRecipes() {
  importing.value = true;
  importResult.value = null;
  importProgress.value = {
    show: true,
    stage: '准备中',
    current: 0,
    total: 0,
    percentage: 0,
    message: ''
  };

  try {
    const response = await api.post('/recipes/import-initial-enhanced', {});
    importResult.value = response;
    importProgress.value = {
      show: false,
      stage: '完成',
      current: 1,
      total: 1,
      percentage: 100,
      message: '导入完成'
    };
    alert(`导入完成! 成功: ${response.recipes?.imported || 0}, 失败: ${response.recipes?.failed || 0}`);
  } catch (error) {
    console.error('导入初始菜谱失败:', error);
    importResult.value = { success: false, error: error.message || '导入失败' };
    importProgress.value = {
      show: false,
      stage: '失败',
      current: 0,
      total: 0,
      percentage: 0,
      message: '导入失败'
    };
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
  max-width: 900px;
}

.card {
  background: white;
  border-radius: 0.5rem;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
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

.form-control:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

.help-text {
  color: #666;
  font-size: 0.875rem;
  margin-top: 0.25rem;
  display: block;
}

/* 进度条样式 */
.progress-section {
  margin-top: 1.5rem;
  padding: 1.5rem;
  background: #f9f9f9;
  border-radius: 0.5rem;
}

.progress-section h3 {
  margin-top: 0;
  color: #667eea;
  font-size: 1.125rem;
}

.progress-bar-container {
  margin: 1rem 0;
}

.progress-bar {
  width: 100%;
  height: 24px;
  background: #e0e0e0;
  border-radius: 0.25rem;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transition: width 0.3s ease;
  border-radius: 0.25rem;
}

.progress-text {
  margin-left: 0.75rem;
  font-weight: 600;
  color: #667eea;
}

.progress-details {
  margin-top: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem;
  background: white;
  border-radius: 0.25rem;
}

.detail-item .label {
  color: #666;
  font-size: 0.875rem;
}

.detail-item .value {
  color: #333;
  font-weight: 600;
  font-size: 0.875rem;
}

/* 按钮样式 */
.btn-primary {
  padding: 0.75rem 1.5rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 1rem;
  transition: background 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #5a6fd8;
}

.btn-primary:disabled {
  background: #ccc;
  cursor: not-allowed;
  opacity: 0.7;
}

.btn-secondary {
  padding: 0.75rem 1.5rem;
  background: #6c757d;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 1rem;
  transition: background 0.2s;
}

.btn-secondary:hover:not(:disabled) {
  background: #5a6268;
}

.btn-secondary:disabled {
  background: #ccc;
  cursor: not-allowed;
  opacity: 0.7;
}

/* 结果卡片样式 */
.result-card {
  margin-top: 1.5rem;
}

.alert {
  padding: 1rem;
  border-radius: 0.5rem;
  margin: 0;
}

.alert-success {
  background: #e6f4ea;
  border: 1px solid #a3d9b1;
  color: #137333;
}

.alert-success h3 {
  margin-top: 0;
  margin-bottom: 0.5rem;
  color: #137333;
}

.alert-error {
  background: #fce8e6;
  border: 1px solid #f5a6a0;
  color: #d93025;
}

.alert-error h3 {
  margin-top: 0;
  margin-bottom: 0.5rem;
  color: #d93025;
}

.result-card ul {
  list-style: none;
  padding-left: 0;
  margin-top: 0.75rem;
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
    gap: 1rem;
  }

  .card {
    padding: 1rem;
  }

  .progress-section {
    padding: 1rem;
  }

  .progress-bar {
    height: 20px;
  }

  .detail-item {
    padding: 0.375rem;
    font-size: 0.8125rem;
  }

  .btn-primary,
  .btn-secondary {
    padding: 0.625rem 1.25rem;
    font-size: 0.875rem;
  }
}

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

  .progress-section {
    padding: 0.75rem;
  }
}
</style>
