<template>
  <!-- 顶部导航栏 - 移到 container 外面以便固定 -->
  <v-app-bar elevation="0" color="background" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
    <v-app-bar-title class="text-h6">
      <div class="d-flex align-center ga-2">
        <span class="text-truncate">{{ ingredient?.name || '原料详情' }}</span>
        <v-chip size="x-small" variant="tonal" color="primary">原料</v-chip>
      </div>
    </v-app-bar-title>
    <template #append>
      <v-btn icon="mdi-pencil" variant="text" @click="openEditDialog" />
      <v-btn icon="mdi-refresh" variant="text" :loading="loading" @click="loadData" />
    </template>
  </v-app-bar>

  <v-container fluid class="pa-0">
    <!-- 加载中 -->
    <div v-if="loading" class="text-center py-16">
      <v-progress-circular indeterminate color="primary" size="64" />
      <div class="text-body-1 mt-4">加载中...</div>
    </div>

    <!-- 错误提示 -->
    <v-alert v-else-if="error" type="error" class="ma-4">
      {{ error }}
      <template #append>
        <v-btn variant="text" @click="loadData">重试</v-btn>
      </template>
    </v-alert>

    <template v-else-if="ingredient">
      <!-- 基本信息卡片 -->
      <v-card elevation="0" class="ma-4">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="primary">mdi-information-outline</v-icon>
          基本信息
        </v-card-title>
        <v-divider />
        <v-card-text>
          <v-list density="compact">
            <v-list-item v-if="ingredient.default_unit_name">
              <template #prepend>
                <v-icon size="small" color="medium-emphasis">mdi-scale</v-icon>
              </template>
              <v-list-item-title>默认单位</v-list-item-title>
              <v-list-item-subtitle>{{ ingredient.default_unit_name }}</v-list-item-subtitle>
            </v-list-item>

            <v-list-item v-if="ingredient.aliases?.length">
              <template #prepend>
                <v-icon size="small" color="medium-emphasis">mdi-tag-outline</v-icon>
              </template>
              <v-list-item-title>别名</v-list-item-title>
              <v-list-item-subtitle>
                <v-chip
                  v-for="alias in ingredient.aliases"
                  :key="alias"
                  size="x-small"
                  class="mr-1"
                >
                  {{ alias }}
                </v-chip>
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item>
              <template #prepend>
                <v-icon size="small" color="medium-emphasis">mdi-calendar</v-icon>
              </template>
              <v-list-item-title>创建时间</v-list-item-title>
              <v-list-item-subtitle>{{ formatDateTime(ingredient.created_at) }}</v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-card-text>
      </v-card>

      <!-- 最新价格卡片 -->
      <v-card elevation="0" class="ma-4" v-if="latestPrice">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="tertiary">mdi-currency-cny</v-icon>
          最新价格
          <span class="text-caption text-medium-emphasis ml-2">（每{{ ingredient.default_unit_name || 'g' }}）</span>
        </v-card-title>
        <v-divider />
        <v-card-text class="text-center py-6">
          <div class="text-h3 font-weight-bold text-tertiary">
            ¥{{ formatPrice(latestPrice) }}
          </div>
        </v-card-text>
      </v-card>

      <!-- 价格趋势图表 -->
      <PriceTrendChart
        v-if="ingredient"
        title="价格趋势"
        icon="mdi-chart-line"
        icon-color="tertiary"
        :unit="chartUnit"
        empty-text="暂无价格历史数据"
        :data="chartData"
        :loading="loadingPrices"
        color="#ff9800"
        class="ma-4"
      />

      <!-- 关联商品卡片 -->
      <v-card elevation="0" class="ma-4">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="primary">mdi-package-variant</v-icon>
          关联商品
          <v-chip size="small" class="ml-2" v-if="products.length > 0">
            {{ products.length }}
          </v-chip>
        </v-card-title>
        <v-divider />

        <v-list v-if="products.length > 0" lines="one">
          <v-list-item
            v-for="product in products"
            :key="product.id"
            @click="goToProduct(product.id)"
          >
            <template #prepend>
              <v-avatar color="primary" size="36">
                <span class="text-white text-caption">{{ product.name?.charAt(0) }}</span>
              </v-avatar>
            </template>
            <v-list-item-title>{{ product.name }}</v-list-item-title>
            <v-list-item-subtitle v-if="product.brand">{{ product.brand }}</v-list-item-subtitle>
            <template #append>
              <v-icon>mdi-chevron-right</v-icon>
            </template>
          </v-list-item>
        </v-list>

        <v-card-text v-else class="text-center py-8">
          <v-icon size="48" color="medium-emphasis">mdi-package-variant-closed</v-icon>
          <div class="text-body-2 text-medium-emphasis mt-2">暂无关联商品</div>
        </v-card-text>
      </v-card>

      <!-- 价格记录列表 -->
      <v-card elevation="0" class="ma-4">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="primary">mdi-history</v-icon>
          价格记录
          <v-spacer />
          <v-btn
            v-if="priceRecords.length > 0"
            size="small"
            variant="text"
            color="primary"
            @click="showAddPriceDialog = true"
          >
            添加记录
          </v-btn>
        </v-card-title>
        <v-divider />

        <!-- 价格记录加载中 -->
        <div v-if="loadingPrices" class="text-center py-8">
          <v-progress-circular indeterminate color="primary" size="32" />
        </div>

        <!-- 价格记录列表 -->
        <v-list v-else-if="priceRecords.length > 0" lines="two">
          <v-list-item v-for="record in priceRecords" :key="record.id">
            <template #prepend>
              <v-avatar color="tertiary-container" size="40">
                <v-icon color="tertiary">mdi-receipt-text</v-icon>
              </v-avatar>
            </template>

            <v-list-item-title>
              {{ record.product_name }}
            </v-list-item-title>
            <v-list-item-subtitle>
              ¥{{ formatPrice(record.price) }} / {{ record.original_quantity }}{{ record.original_unit }}
              <template v-if="record.merchant_name"> · {{ record.merchant_name }}</template>
            </v-list-item-subtitle>

            <template #append>
              <div class="text-caption text-medium-emphasis">
                {{ formatDate(record.recorded_at) }}
              </div>
            </template>
          </v-list-item>
        </v-list>

        <!-- 空状态 -->
        <v-card-text v-else class="text-center py-8">
          <v-icon size="64" color="medium-emphasis">mdi-receipt-text-outline</v-icon>
          <div class="text-body-1 text-medium-emphasis mt-4">暂无价格记录</div>
        </v-card-text>

        <!-- 分页器 -->
        <div v-if="priceTotal > 0" class="d-flex flex-wrap justify-center align-center ga-2 py-4">
          <v-pagination
            v-model="pricePage"
            :length="priceTotalPages"
            :total-visible="3"
            rounded="circle"
            density="comfortable"
          />
          <span class="text-caption text-medium-emphasis">共 {{ priceTotal }} 条</span>
        </div>
      </v-card>

      <!-- 营养数据卡片 -->
      <v-card elevation="0" class="ma-4" v-if="nutritionData">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="success">mdi-food-apple-outline</v-icon>
          营养成分
          <span class="text-caption text-medium-emphasis ml-2">（每100g）</span>
          <v-spacer />
          <v-btn
            v-if="otherNutrientsCount > 0"
            size="small"
            variant="text"
            color="primary"
            class="text-caption"
            @click="showAllNutrients = !showAllNutrients"
          >
            {{ showAllNutrients ? '收起' : `展开 +${otherNutrientsCount} 项` }}
            <v-icon :icon="showAllNutrients ? 'mdi-chevron-up' : 'mdi-chevron-down'" end />
          </v-btn>
        </v-card-title>
        <v-divider />

        <v-card-text class="pa-0">
          <div class="nutrition-header d-flex py-2 border-bottom">
            <div class="text-caption text-medium-emphasis ps-4 flex-grow-1">营养素</div>
            <div class="text-caption text-medium-emphasis text-end pe-4" style="min-width: 80px">数量</div>
            <div class="text-caption text-medium-emphasis text-end pe-4" style="min-width: 60px">NRV%</div>
          </div>
          <div
            v-for="item in displayNutritionItems"
            :key="item.key"
            class="nutrition-row d-flex py-2"
            :class="{ 'border-bottom': item.key !== displayNutritionItems[displayNutritionItems.length - 1].key }"
          >
            <div class="text-body-2 ps-4 flex-grow-1">{{ item.label }}</div>
            <div class="text-body-2 text-end pe-4" style="min-width: 80px">
              {{ formatNutritionValue(getNutritionValue(item), getNutritionUnit(item) || item.unit) }}
            </div>
            <div class="text-body-2 text-end pe-4" style="min-width: 60px">
              {{ getNutritionNRV(item) }}%
            </div>
          </div>

          <div class="mt-4 text-caption text-medium-emphasis ps-4">
            NRV = 营养素参考值百分比
          </div>
        </v-card-text>
      </v-card>

      <!-- 层级关系卡片 -->
      <v-card elevation="0" class="ma-4">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="info">mdi-graph</v-icon>
          层级关系
          <v-spacer />
          <v-btn
            size="small"
            variant="text"
            color="primary"
            prepend-icon="mdi-plus"
            @click="openAddRelationDialog"
          >
            添加关系
          </v-btn>
        </v-card-title>
        <v-divider />

        <!-- 图表展示 -->
        <HierarchyGraph
          v-if="hasRelations"
          :ingredient-id="ingredientId"
          :ingredient-name="ingredient?.name || ''"
          :hierarchy-data="hierarchyData"
          height="400px"
          class="ma-4"
        />

        <!-- 图例说明 -->
        <v-card-text v-if="hasRelations" class="pt-0">
          <v-alert type="info" variant="tonal" density="compact">
            <template #title>
              <span class="text-caption">关系说明</span>
            </template>
            <div class="text-caption">
              <div class="d-flex align-center ga-2 mb-1">
                <v-chip size="x-small" color="info">●</v-chip>
                <span>实线 - 包含关系（父→子）</span>
              </div>
              <div class="d-flex align-center ga-2 mb-1">
                <v-chip size="x-small" color="warning">┄</v-chip>
                <span>虚线 - 回退关系（找不到数据时可回退）</span>
              </div>
              <div class="d-flex align-center ga-2">
                <v-chip size="x-small" color="success">┈</v-chip>
                <span>点线 - 可替代关系（相互替代）</span>
              </div>
            </div>
          </v-alert>
        </v-card-text>

        <!-- 空状态 -->
        <v-card-text v-if="!hasRelations" class="text-center py-8">
          <v-icon size="48" color="medium-emphasis">mdi-graph-outline</v-icon>
          <div class="text-body-2 text-medium-emphasis mt-2">暂无层级关系</div>
          <div class="text-caption text-medium-emphasis mt-1">
            可以设置原料之间的包含、回退或可替代关系
          </div>
        </v-card-text>
      </v-card>

      <!-- 层级关系列表（折叠面板） -->
      <v-card v-if="hasRelations" elevation="0" class="ma-4">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="primary">mdi-format-list-bulleted</v-icon>
          关系列表
        </v-card-title>
        <v-divider />

        <!-- 关系列表 -->
        <v-list density="compact">
          <!-- 子关系（当前原料是父，包含/回退到其他原料） -->
          <template v-if="hierarchyData?.child_relations?.length">
            <v-list-subheader>包含/可回退到</v-list-subheader>
            <v-list-item
              v-for="rel in hierarchyData.child_relations"
              :key="rel.id"
              class="relation-item-wrapper"
            >
              <div
                class="d-flex align-center flex-grow-1 py-2 relation-item-content"
                @click="goToIngredient(rel.child_id)"
              >
                <v-icon color="info" size="small" class="mr-3">mdi-arrow-down-right</v-icon>
                <div class="flex-grow-1">
                  <div class="text-body-2" v-html="getRelationListDisplayText(rel, 'child')"></div>
                  <div class="text-caption text-medium-emphasis mt-1">
                    <v-chip size="x-small" :color="getRelationTypeColor(rel.relation_type)">
                      {{ getRelationTypeLabel(rel.relation_type) }}
                    </v-chip>
                    <span class="ml-2">强度: {{ rel.strength }}%</span>
                  </div>
                </div>
                <v-btn
                  icon="mdi-pencil"
                  size="x-small"
                  variant="text"
                  color="primary"
                  class="mr-1"
                  @click.stop="openEditRelationDialog(rel)"
                />
                <v-btn
                  icon="mdi-delete"
                  size="x-small"
                  variant="text"
                  color="error"
                  @click.stop="confirmDeleteRelation(rel)"
                />
              </div>
            </v-list-item>
          </template>

          <!-- 父关系（当前原料是子，被其他原料包含/回退） -->
          <template v-if="hierarchyData?.parent_relations?.length">
            <v-list-subheader v-if="hierarchyData.child_relations?.length">所属关系</v-list-subheader>
            <v-list-subheader v-else>所属关系</v-list-subheader>
            <v-list-item
              v-for="rel in hierarchyData.parent_relations"
              :key="rel.id"
              class="relation-item-wrapper"
            >
              <div
                class="d-flex align-center flex-grow-1 py-2 relation-item-content"
                @click="goToIngredient(rel.parent_id)"
              >
                <v-icon color="success" size="small" class="mr-3">mdi-arrow-up-right</v-icon>
                <div class="flex-grow-1">
                  <div class="text-body-2" v-html="getRelationListDisplayText(rel, 'parent')"></div>
                  <div class="text-caption text-medium-emphasis mt-1">
                    <v-chip size="x-small" :color="getRelationTypeColor(rel.relation_type)">
                      {{ getRelationTypeLabel(rel.relation_type) }}
                    </v-chip>
                    <span class="ml-2">强度: {{ rel.strength }}%</span>
                  </div>
                </div>
                <v-btn
                  icon="mdi-pencil"
                  size="x-small"
                  variant="text"
                  color="primary"
                  class="mr-1"
                  @click.stop="openEditRelationDialog(rel)"
                />
                <v-btn
                  icon="mdi-delete"
                  size="x-small"
                  variant="text"
                  color="error"
                  @click.stop="confirmDeleteRelation(rel)"
                />
              </div>
            </v-list-item>
          </template>
        </v-list>
      </v-card>

      <!-- 关联菜谱卡片 -->
      <v-card elevation="0" class="ma-4">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="primary">mdi-chef-hat</v-icon>
          相关菜谱
          <v-chip size="small" class="ml-2" v-if="recipes.length > 0">
            {{ recipes.length }}
          </v-chip>
        </v-card-title>
        <v-divider />

        <v-list v-if="recipes.length > 0" lines="one">
          <v-list-item
            v-for="recipe in recipes"
            :key="recipe.id"
            @click="goToRecipe(recipe.id)"
          >
            <template #prepend>
              <v-avatar color="secondary" size="36">
                <v-icon color="white">mdi-food</v-icon>
              </v-avatar>
            </template>
            <v-list-item-title>{{ recipe.name }}</v-list-item-title>
            <v-list-item-subtitle v-if="recipe.category">{{ recipe.category }}</v-list-item-subtitle>
            <template #append>
              <v-icon>mdi-chevron-right</v-icon>
            </template>
          </v-list-item>
        </v-list>

        <v-card-text v-else class="text-center py-8">
          <v-icon size="48" color="medium-emphasis">mdi-book-open-variant</v-icon>
          <div class="text-body-2 text-medium-emphasis mt-2">暂无相关菜谱</div>
        </v-card-text>
      </v-card>

      <!-- 操作按钮 -->
      <div class="pa-4">
        <v-btn
          color="warning"
          variant="tonal"
          block
          prepend-icon="mdi-merge"
          class="mb-2"
          @click="showMergeDialog = true"
        >
          合并到其他原料
        </v-btn>
        <v-btn
          color="error"
          variant="tonal"
          block
          prepend-icon="mdi-delete"
          @click="confirmDelete"
        >
          删除原料
        </v-btn>
      </div>
    </template>

    <!-- 编辑对话框 -->
    <v-dialog v-model="showEditDialog" max-width="500">
      <v-card>
        <v-card-title>编辑原料</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="saveEdit">
            <v-text-field
              v-model="editForm.name"
              label="原料名称"
              variant="outlined"
              required
              class="mb-4"
            />
            <v-autocomplete
              v-model="editForm.default_unit_id"
              :items="units"
              item-title="name"
              item-value="id"
              label="默认单位"
              variant="outlined"
              clearable
              class="mb-4"
            />
            <v-combobox
              v-model="editForm.aliases"
              label="别名"
              variant="outlined"
              multiple
              chips
              closable-chips
              hint="按回车添加别名"
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showEditDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="saving" @click="saveEdit">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 添加价格记录对话框 -->
    <v-dialog v-model="showAddPriceDialog" max-width="500">
      <v-card>
        <v-card-title>添加价格记录</v-card-title>
        <v-card-text>
          <v-alert type="info" class="mb-4">
            请先选择一个关联商品，然后为其添加价格记录
          </v-alert>
          <v-autocomplete
            v-model="selectedPriceProduct"
            :items="products"
            item-title="name"
            item-value="id"
            label="选择商品"
            variant="outlined"
            required
            return-object
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showAddPriceDialog = false">取消</v-btn>
          <v-btn
            color="primary"
            :disabled="!priceForm.product_id"
            @click="goToAddPrice"
          >
            前往添加
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 合并对话框 -->
    <v-dialog v-model="showMergeDialog" max-width="500">
      <v-card>
        <v-card-title>合并原料</v-card-title>
        <v-card-text>
          <v-alert type="warning" class="mb-4">
            合并后，当前原料的菜谱引用、商品关联将迁移到目标原料，此操作不可恢复！
          </v-alert>
          <v-autocomplete
            v-model="selectedMergeTarget"
            v-model:search="mergeSearchQuery"
            :items="mergeTargets"
            item-title="name"
            item-value="id"
            label="选择目标原料"
            variant="outlined"
            :loading="loadingMergeTargets"
            hide-selected
            auto-select-first
            :custom-filter="() => true"
            return-object
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showMergeDialog = false">取消</v-btn>
          <v-btn
            color="warning"
            :loading="merging"
            :disabled="!mergeTargetId"
            @click="mergeIngredient"
          >
            确认合并
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 添加层级关系对话框 -->
    <v-dialog v-model="showAddRelationDialog" max-width="500">
      <v-card>
        <v-card-title>添加层级关系</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="addRelation">
            <v-autocomplete
              v-model="selectedTargetIngredient"
              v-model:search="ingredientSearchQuery"
              :items="availableIngredients"
              item-title="name"
              item-value="id"
              label="选择原料"
              variant="outlined"
              required
              :loading="loadingIngredients"
              class="mb-4"
              hint="输入名称搜索原料"
              persistent-hint
              hide-selected
              auto-select-first
              :custom-filter="() => true"
              return-object
            />

            <v-select
              v-model="relationForm.relation_type"
              :items="relationTypeOptions"
              item-title="label"
              item-value="value"
              label="关系类型"
              variant="outlined"
              required
              class="mb-4"
            >
              <template #item="{ item, props }">
                <v-list-item v-bind="props">
                  <template #prepend>
                    <v-icon :color="item.raw.color" size="small">{{ item.raw.icon }}</v-icon>
                  </template>
                </v-list-item>
              </template>
              <template #selection="{ item }">
                <v-chip size="small" :color="item.raw.color">
                  <v-icon start size="small">{{ item.raw.icon }}</v-icon>
                  {{ item.raw.label }}
                </v-chip>
              </template>
            </v-select>

            <v-slider
              v-model="relationForm.strength"
              label="关系强度"
              min="1"
              max="100"
              thumb-label
              :hints="true"
              class="mb-4"
            >
              <template #append>
                <v-chip size="small">{{ relationForm.strength }}%</v-chip>
              </template>
            </v-slider>

            <!-- 关系预览 -->
            <v-alert
              v-if="selectedTargetIngredient && relationForm.relation_type"
              type="info"
              variant="tonal"
              density="compact"
              class="mb-2"
            >
              <div class="text-body-2">
                {{ getRelationPreviewText(relationForm.relation_type, 'child') }}
              </div>
              <div class="text-caption mt-1 text-medium-emphasis">
                {{ getRelationDescriptionText(relationForm.relation_type, 'child') }}
              </div>
            </v-alert>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showAddRelationDialog = false">取消</v-btn>
          <v-btn
            color="primary"
            :loading="savingRelation"
            :disabled="!relationForm.target_ingredient_id"
            @click="addRelation"
          >
            添加
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 编辑层级关系对话框 -->
    <v-dialog v-model="showEditRelationDialog" max-width="500">
      <v-card>
        <v-card-title>编辑层级关系</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="saveEditRelation">
            <!-- 关系预览 -->
            <v-alert type="info" variant="tonal" density="compact" class="mb-4">
              <template #title>
                <div class="text-body-2">
                  <strong>{{ ingredient?.name }}</strong>
                  <span class="mx-2">{{ getRelationTypeLabel(editRelationForm.relation_type) }}</span>
                  <strong>{{ editRelationRelation?.child_name || editRelationRelation?.parent_name }}</strong>
                </div>
              </template>
              <div class="text-caption mt-1 text-medium-emphasis">
                {{ getEditRelationDirectionText() }}
              </div>
            </v-alert>

            <v-select
              v-model="editRelationForm.relation_type"
              :items="relationTypeOptions"
              item-title="label"
              item-value="value"
              label="关系类型"
              variant="outlined"
              required
              class="mb-4"
            >
              <template #item="{ item, props }">
                <v-list-item v-bind="props">
                  <template #prepend>
                    <v-icon :color="item.raw.color" size="small">{{ item.raw.icon }}</v-icon>
                  </template>
                </v-list-item>
              </template>
              <template #selection="{ item }">
                <v-chip size="small" :color="item.raw.color">
                  <v-icon start size="small">{{ item.raw.icon }}</v-icon>
                  {{ item.raw.label }}
                </v-chip>
              </template>
            </v-select>

            <v-slider
              v-model="editRelationForm.strength"
              label="关系强度"
              min="1"
              max="100"
              thumb-label
              :hints="true"
            >
              <template #append>
                <v-chip size="small">{{ editRelationForm.strength }}%</v-chip>
              </template>
            </v-slider>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showEditRelationDialog = false">取消</v-btn>
          <v-btn
            color="primary"
            :loading="savingRelation"
            @click="saveEditRelation"
          >
            保存
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 删除关系确认对话框 -->
    <v-dialog v-model="showDeleteRelationDialog" max-width="400">
      <v-card>
        <v-card-title class="text-error">确认删除关系</v-card-title>
        <v-card-text>
          确定要删除这个层级关系吗？
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showDeleteRelationDialog = false">取消</v-btn>
          <v-btn color="error" :loading="deletingRelation" @click="deleteRelation">删除</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 确认删除对话框 -->
    <v-dialog v-model="showDeleteDialog" max-width="400">
      <v-card>
        <v-card-title class="text-error">确认删除</v-card-title>
        <v-card-text>
          确定要删除原料「{{ ingredient?.name }}」吗？此操作不可恢复。
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showDeleteDialog = false">取消</v-btn>
          <v-btn color="error" :loading="deleting" @click="deleteIngredient">删除</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 提示消息 -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000">
      {{ snackbar.message }}
    </v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import PriceTrendChart from '@/components/charts/PriceTrendChart.vue'
import HierarchyGraph from '@/components/charts/HierarchyGraph.vue'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import { NUTRITION_LABEL_MAP, ENGLISH_TO_CHINESE_MAP } from '@/utils/nutritionLabels'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()

interface Ingredient {
  id: number
  name: string
  aliases?: string[]
  default_unit_id?: number
  default_unit_name?: string
  created_at: string
  updated_at?: string
}

interface Product {
  id: number
  name: string
  brand?: string
  ingredient_id?: number
}

interface PriceRecord {
  id: number
  product_id: number
  product_name: string
  price: number | string
  original_quantity: number | string
  original_unit: string
  merchant_name?: string
  recorded_at: string
}

interface Recipe {
  id: number
  name: string
  category?: string
}

interface Unit {
  id: number
  name: string
  abbreviation?: string
}

interface HierarchyRelation {
  id: number
  parent_id: number
  parent_name: string
  child_id: number
  child_name: string
  relation_type: string
  strength: number
  created_at: string
}

interface HierarchyData {
  parent_relations: HierarchyRelation[]
  child_relations: HierarchyRelation[]
}

const route = useRoute()
const router = useRouter()

const ingredientId = computed(() => Number(route.params.id))

const ingredient = ref<Ingredient | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

// 最新价格
const latestPrice = ref<number | null>(null)

// 关联商品
const products = ref<Product[]>([])

// 价格记录相关
const priceRecords = ref<PriceRecord[]>([])
const loadingPrices = ref(false)
const pricePage = ref(1)
const pricePageSize = ref(10)
const priceTotal = ref(0)
const priceTotalPages = computed(() => Math.ceil(priceTotal.value / pricePageSize.value))

// 营养数据
const nutritionData = ref<any>(null)

// 关联菜谱
const recipes = ref<Recipe[]>([])

// 单位列表
const units = ref<Unit[]>([])

// 层级关系数据
const hierarchyData = ref<HierarchyData | null>(null)
const loadingHierarchy = ref(false)

// 可选择的原料列表
const availableIngredients = ref<Ingredient[]>([])
const loadingIngredients = ref(false)
const ingredientSearchQuery = ref('')
const mergeSearchQuery = ref('')

// 搜索原料的防抖函数
let ingredientSearchTimeout: ReturnType<typeof setTimeout> | null = null
let mergeSearchTimeout: ReturnType<typeof setTimeout> | null = null

// 对话框状态
const showEditDialog = ref(false)
const showAddRelationDialog = ref(false)
const showEditRelationDialog = ref(false)
const showDeleteRelationDialog = ref(false)
const showAddPriceDialog = ref(false)
const showMergeDialog = ref(false)
const showDeleteDialog = ref(false)
const saving = ref(false)
const savingRelation = ref(false)
const deletingRelation = ref(false)
const merging = ref(false)
const deleting = ref(false)

// 表单数据
const editForm = ref({
  name: '',
  default_unit_id: null as number | null,
  aliases: [] as string[]
})

const priceForm = ref({
  product_id: null as number | null
})

// 选中的商品对象（用于显示名称）
const selectedPriceProduct = ref<Product | null>(null)

// 关系表单数据
const relationForm = ref({
  target_ingredient_id: null as number | null,
  relation_type: 'contains',
  strength: 50
})

// 选中的原料对象（用于显示名称）
const selectedTargetIngredient = ref<Ingredient | null>(null)

// 编辑关系数据
const editRelationRelation = ref<HierarchyRelation | null>(null)
const editRelationForm = ref({
  relation_type: 'contains',
  strength: 50
})

// 待删除的关系
const relationToDelete = ref<HierarchyRelation | null>(null)

// 关系类型选项
const relationTypeOptions = [
  {
    value: 'contains',
    label: '包含',
    description: '当前原料包含目标原料（父→子）',
    icon: 'mdi-arrow-down',
    color: 'info'
  },
  {
    value: 'fallback',
    label: '回退',
    description: '当前原料可回退到目标原料',
    icon: 'mdi-arrow-left',
    color: 'warning'
  },
  {
    value: 'substitutable',
    label: '可替代',
    description: '两个原料可以相互替代',
    icon: 'mdi-swap-horizontal',
    color: 'success'
  }
]

// 合并相关
const mergeTargetId = ref<number | null>(null)
const mergeTargets = ref<Ingredient[]>([])
const loadingMergeTargets = ref(false)

// 选中的合并目标对象（用于显示名称）
const selectedMergeTarget = ref<Ingredient | null>(null)

// 提示消息
const snackbar = ref({
  show: false,
  message: '',
  color: 'success'
})

// 营养素配置（默认显示的营养素）
const coreNutritionItems = [
  { key: '能量', label: '能量', unit: 'kcal' },
  { key: '蛋白质', label: '蛋白质', unit: 'g' },
  { key: '脂肪', label: '脂肪', unit: 'g' },
  { key: '碳水化合物', label: '碳水化合物', unit: 'g' },
  { key: '钠', label: '钠', unit: 'mg' }
]

// 营养素排序顺序（展开时这些营养素排在前面）
const nutrientSortOrder = [
  '能量', '蛋白质', '脂肪', '碳水化合物', '钠',
  '膳食纤维', '钙', '铁', '钾',
  '维生素A', '维生素B1', '维生素B2', '维生素B12', '维生素C',
  '维生素D', '维生素E', '维生素K'
]

// 展开状态
const showAllNutrients = ref(false)


// 营养素排序辅助函数
const sortNutrients = (items: any[]) => {
  return items.sort((a, b) => {
    const indexA = nutrientSortOrder.indexOf(a.key)
    const indexB = nutrientSortOrder.indexOf(b.key)

    // 如果都在排序列表中，按排序顺序
    if (indexA !== -1 && indexB !== -1) {
      return indexA - indexB
    }
    // 如果只有A在排序列表中，A排在前面
    if (indexA !== -1) {
      return -1
    }
    // 如果只有B在排序列表中，B排在前面
    if (indexB !== -1) {
      return 1
    }
    // 都不在排序列表中，按原顺序
    return 0
  })
}

// 根据展开状态返回要显示的营养素列表
const displayNutritionItems = computed(() => {
  if (!nutritionData.value?.nutrition) return []

  const coreNutrients = nutritionData.value.nutrition.core_nutrients || {}
  const allNutrients = nutritionData.value.nutrition.all_nutrients || {}

  // 常用营养素（从 core_nutrients 获取，因为键名是中文）
  const coreItems = coreNutritionItems
    .filter(item => coreNutrients[item.key])
    .map(item => ({
      key: item.key,
      label: item.label,
      unit: (coreNutrients[item.key] as any).unit || item.unit,
      isCore: true
    }))

  if (!showAllNutrients.value) {
    return coreItems
  }

  // 获取核心营养素的键集合（用于过滤）
  const coreKeys = new Set(coreNutritionItems.map(ci => ci.key))

  // 其他营养素（从 all_nutrients 获取，键已经是中文了）
  const availableKeys = Object.keys(allNutrients).filter(key => {
    const data = allNutrients[key]
    return data && typeof data === 'object' && 'value' in data
  })

  const otherItems = availableKeys
    .filter(key => {
      // 后端已经将键转为中文，直接检查是否是核心营养素
      return !coreKeys.has(key)
    })
    .map(key => {
      return {
        key: key,
        label: NUTRITION_LABEL_MAP[key] || key,
        unit: (allNutrients[key] as any).unit || '',
        isCore: false
      }
    })

  // 排序
  const sortedItems = sortNutrients([...coreItems, ...otherItems])

  return sortedItems
})

// 其他营养素数量（用于按钮文案）
const otherNutrientsCount = computed(() => {
  if (!nutritionData.value?.nutrition?.all_nutrients) return 0

  const allNutrients = nutritionData.value.nutrition.all_nutrients

  // 获取核心营养素的键集合
  const coreKeys = new Set(coreNutritionItems.map(ci => ci.key))

  const availableKeys = Object.keys(allNutrients).filter(key => {
    const data = allNutrients[key]
    return data && typeof data === 'object' && 'value' in data
  })

  return availableKeys.filter(key => {
    // 后端已经将键转为中文，直接检查是否是核心营养素
    return !coreKeys.has(key)
  }).length
})

// 从后端返回的嵌套结构中提取营养值
const getNutritionValue = (item: any) => {
  if (!nutritionData.value?.nutrition) return null

  // 如果是核心营养素，从 core_nutrients 获取（中文键）
  if (item.isCore) {
    const nutrient = nutritionData.value.nutrition.core_nutrients?.[item.key]
    return nutrient?.value
  }

  // 否则从 all_nutrients 获取（使用中文键，后端已转换）
  const nutrient = nutritionData.value.nutrition.all_nutrients?.[item.key]
  return nutrient?.value
}

const getNutritionUnit = (item: any) => {
  if (!nutritionData.value?.nutrition) return null

  // 如果是核心营养素，从 core_nutrients 获取（中文键）
  if (item.isCore) {
    const nutrient = nutritionData.value.nutrition.core_nutrients?.[item.key]
    return nutrient?.unit
  }

  // 否则从 all_nutrients 获取（使用中文键，后端已转换）
  const nutrient = nutritionData.value.nutrition.all_nutrients?.[item.key]
  return nutrient?.unit
}

const getNutritionNRV = (item: any) => {
  if (!nutritionData.value?.nutrition) return '-'

  let nutrient: any

  // 如果是核心营养素，从 core_nutrients 获取（中文键）
  if (item.isCore) {
    nutrient = nutritionData.value.nutrition.core_nutrients?.[item.key]
  } else {
    // 否则从 all_nutrients 获取（使用中文键，后端已转换）
    nutrient = nutritionData.value.nutrition.all_nutrients?.[item.key]
  }

  if (!nutrient) return '-'

  // 如果 standard 是"无标准"或类似的，表示没有推荐摄入量，显示 "-"
  if (nutrient.standard === '无标准' || nutrient.standard === '无标准值') {
    return '-'
  }

  // 如果 nrp_pct 是 undefined 或 null，显示 "-"
  if (nutrient.nrp_pct === undefined || nutrient.nrp_pct === null) {
    return '-'
  }

  // 显示实际百分比
  return nutrient.nrp_pct.toFixed(1)
}

// 计算是否有层级关系
const hasRelations = computed(() => {
  return (
    (hierarchyData.value?.child_relations?.length || 0) > 0 ||
    (hierarchyData.value?.parent_relations?.length || 0) > 0
  )
})

// 聚合价格数据用于图表（按日期分组）
const chartData = computed(() => {
  if (!priceRecords.value || priceRecords.value.length === 0) return []

  const dailyMap = new Map<string, number[]>()

  for (const record of priceRecords.value) {
    if (!record.recorded_at) continue
    const date = new Date(record.recorded_at)
    if (isNaN(date.getTime())) continue
    const dateKey = date.toISOString().split('T')[0]

    // 计算单价
    const quantity = parseFloat(String(record.original_quantity)) || 1
    const price = parseFloat(String(record.price)) || 0
    const unitPrice = price / quantity

    if (!dailyMap.has(dateKey)) {
      dailyMap.set(dateKey, [])
    }
    dailyMap.get(dateKey)!.push(unitPrice)
  }

  // 计算每日统计值
  return Array.from(dailyMap.entries())
    .map(([date, prices]) => {
      const sorted = prices.sort((a, b) => a - b)
      return {
        date,
        min: sorted[0] || 0,
        max: sorted[sorted.length - 1] || 0,
        avg: prices.reduce((a, b) => a + b, 0) / prices.length,
        count: prices.length
      }
    })
    .sort((a, b) => a.date.localeCompare(b.date))
})

// 获取实际使用的单位
const chartUnit = computed(() => {
  if (priceRecords.value && priceRecords.value.length > 0 && priceRecords.value[0].original_unit) {
    return priceRecords.value[0].original_unit
  }
  return ingredient.value?.default_unit_name || ''
})

// 加载数据
const loadData = async () => {
  loading.value = true
  error.value = null

  try {
    // 加载原料详情
    const response = await api.get(`/nutrition/ingredients/${ingredientId.value}`)
    ingredient.value = response

    // 并行加载其他数据
    await Promise.all([
      loadLatestPrice(),
      loadProducts(),
      loadPriceRecords(),
      loadNutritionData(),
      loadRecipes(),
      loadHierarchy()
    ])
  } catch (e: any) {
    console.error('加载原料失败', e)
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

// 加载最新价格
const loadLatestPrice = async () => {
  try {
    const response = await api.get(`/nutrition/ingredients/${ingredientId.value}/latest-price`)
    latestPrice.value = response.average_price
  } catch (e) {
    latestPrice.value = null
  }
}

// 加载关联商品
const loadProducts = async () => {
  try {
    const response = await api.get('/products/entity', {
      params: {
        ingredient_id: ingredientId.value,
        limit: 50
      }
    })
    products.value = response.items || []
  } catch (e) {
    products.value = []
  }
}

// 加载价格记录
const loadPriceRecords = async () => {
  loadingPrices.value = true
  try {
    const skip = (pricePage.value - 1) * pricePageSize.value
    const response = await api.get('/products', {
      params: {
        ingredient_id: ingredientId.value,
        skip,
        limit: pricePageSize.value,
        target_unit: ingredient.value?.default_unit_name
      }
    })
    priceRecords.value = response.items || []
    priceTotal.value = response.total || 0
  } catch (e) {
    console.error('加载价格记录失败', e)
    priceRecords.value = []
  } finally {
    loadingPrices.value = false
  }
}

// 加载营养数据
const loadNutritionData = async () => {
  try {
    const response = await api.get(`/nutrition/ingredients/${ingredientId.value}/nutrition`)
    nutritionData.value = response
  } catch (e) {
    console.error('加载营养失败', e)
    nutritionData.value = null
  }
}

// 加载关联菜谱
const loadRecipes = async () => {
  try {
    const response = await api.get(`/nutrition/ingredients/${ingredientId.value}/recipes`, {
      params: { limit: 50 }
    })
    recipes.value = response.items || []
  } catch (e) {
    recipes.value = []
  }
}

// 加载层级关系
const loadHierarchy = async () => {
  loadingHierarchy.value = true
  try {
    const response = await api.get(`/ingredients/${ingredientId.value}/hierarchy`)
    hierarchyData.value = response
  } catch (e) {
    console.error('加载层级关系失败', e)
    hierarchyData.value = { parent_relations: [], child_relations: [] }
  } finally {
    loadingHierarchy.value = false
  }
}

// 搜索原料
const searchIngredients = async (search: string) => {
  if (!search || search.length < 1) {
    availableIngredients.value = []
    return
  }

  loadingIngredients.value = true
  try {
    const response = await api.get('/ingredients', {
      params: { q: search, limit: 50 }
    })
    // 过滤掉当前原料
    availableIngredients.value = (response.items || []).filter(
      (item: Ingredient) => item.id !== ingredientId.value
    )
    console.log('[DEBUG] 搜索原料:', search, '返回结果:', availableIngredients.value)
  } catch (e) {
    availableIngredients.value = []
  } finally {
    loadingIngredients.value = false
  }
}

// 打开添加关系对话框
const openAddRelationDialog = () => {
  relationForm.value = {
    target_ingredient_id: null,
    relation_type: 'contains',
    strength: 50
  }
  availableIngredients.value = []
  showAddRelationDialog.value = true
}

// 添加层级关系
const addRelation = async () => {
  if (!relationForm.value.target_ingredient_id) return

  savingRelation.value = true
  try {
    await api.post('/ingredients/hierarchy', {
      parent_id: ingredientId.value,
      child_id: relationForm.value.target_ingredient_id,
      relation_type: relationForm.value.relation_type,
      strength: relationForm.value.strength
    })
    showMessage('关系添加成功', 'success')
    showAddRelationDialog.value = false
    await loadHierarchy()
  } catch (e: any) {
    // 从 response.data.detail 获取详细的错误信息
    const errorMessage = e.response?.data?.detail || e.message || '添加关系失败'
    showMessage(errorMessage, 'error')
  } finally {
    savingRelation.value = false
  }
}

// 打开编辑关系对话框
const openEditRelationDialog = (relation: HierarchyRelation) => {
  editRelationRelation.value = relation
  editRelationForm.value = {
    relation_type: relation.relation_type,
    strength: relation.strength
  }
  showEditRelationDialog.value = true
}

// 保存编辑的关系
const saveEditRelation = async () => {
  if (!editRelationRelation.value) return

  savingRelation.value = true
  try {
    await api.put(`/ingredients/hierarchy/${editRelationRelation.value.id}`, {
      relation_type: editRelationForm.value.relation_type,
      strength: editRelationForm.value.strength
    })
    showMessage('关系更新成功', 'success')
    showEditRelationDialog.value = false
    await loadHierarchy()
  } catch (e: any) {
    // 从 response.data.detail 获取详细的错误信息
    const errorMessage = e.response?.data?.detail || e.message || '更新关系失败'
    showMessage(errorMessage, 'error')
  } finally {
    savingRelation.value = false
  }
}

// 确认删除关系
const confirmDeleteRelation = (relation: HierarchyRelation) => {
  relationToDelete.value = relation
  showDeleteRelationDialog.value = true
}

// 删除层级关系
const deleteRelation = async () => {
  if (!relationToDelete.value) return

  deletingRelation.value = true
  try {
    await api.delete(`/ingredients/hierarchy/${relationToDelete.value.id}`)
    showMessage('关系删除成功', 'success')
    showDeleteRelationDialog.value = false
    await loadHierarchy()
  } catch (e: any) {
    // 从 response.data.detail 获取详细的错误信息
    const errorMessage = e.response?.data?.detail || e.message || '删除关系失败'
    showMessage(errorMessage, 'error')
  } finally {
    deletingRelation.value = false
  }
}

// 获取关系类型标签
const getRelationTypeLabel = (type: string) => {
  const option = relationTypeOptions.find(o => o.value === type)
  return option?.label || type
}

// 获取关系类型颜色
const getRelationTypeColor = (type: string) => {
  const option = relationTypeOptions.find(o => o.value === type)
  return option?.color || 'grey'
}

// 获取关系指向文本
// relationType: 关系类型（contains, fallback, substitutable）
// direction: 'child' 表示当前是父级（显示子原料），'parent' 表示当前是子级（显示父原料）
// fullText: 是否显示完整的"当前原料"文字
const getRelationDirectionText = (
  relationType: string,
  direction: 'child' | 'parent',
  fullText: boolean = true
) => {
  const currentText = fullText ? '当前原料' : '当前'

  // child_relations: 当前原料 → 子原料
  if (direction === 'child') {
    switch (relationType) {
      case 'contains':
        return `属于${currentText}`
      case 'fallback':
        return `可回退到${currentText}`
      case 'substitutable':
        return `可替代${currentText}`
      default:
        return ''
    }
  }

  // parent_relations: 父原料 → 当前原料
  if (direction === 'parent') {
    switch (relationType) {
      case 'contains':
        return `${currentText}属于`
      case 'fallback':
        return `${currentText}可回退到`
      case 'substitutable':
        return `可替代${currentText}`
      default:
        return ''
    }
  }

  return ''
}

// 获取关系列表显示文本（用于关系列表）
const getRelationListDisplayText = (rel: any, direction: 'child' | 'parent') => {
  const currentName = ingredient.value?.name || '当前原料'
  const currentShort = '当前'

  // child_relations: 当前原料是 parent
  if (direction === 'child') {
    const otherName = rel.child_name
    switch (rel.relation_type) {
      case 'contains':
        return `<span class="text-medium-emphasis">${otherName}</span> <span class="text-caption text-primary font-weight-bold">属于${currentShort}</span>`
      case 'fallback':
        // 对于 fallback，parent 是具体原料，child 是抽象原料
        // 在当前原料(parent)的详情中，显示"抽象原料 可回退到 当前原料"
        return `<span class="text-medium-emphasis">${otherName}</span> <span class="text-caption text-primary font-weight-bold">可回退到${currentShort}</span>`
      case 'substitutable':
        return `<span class="text-medium-emphasis">${otherName}</span> <span class="text-caption text-primary font-weight-bold">可替代${currentShort}</span>`
      default:
        return otherName
    }
  }

  // parent_relations: 当前原料是 child
  if (direction === 'parent') {
    const otherName = rel.parent_name
    switch (rel.relation_type) {
      case 'contains':
        return `<span class="text-caption text-primary font-weight-bold">${currentShort}属于</span> <span class="text-medium-emphasis ml-1">${otherName}</span>`
      case 'fallback':
        // 对于 fallback，parent 是具体原料，child 是抽象原料
        // 在当前原料(child)的详情中，显示"当前原料 可回退到 具体原料"
        return `<span class="text-caption text-primary font-weight-bold">${currentShort}可回退到</span> <span class="text-medium-emphasis ml-1">${otherName}</span>`
      case 'substitutable':
        return `<span class="text-caption text-primary font-weight-bold">可替代${currentShort}</span> <span class="text-medium-emphasis ml-1">${otherName}</span>`
      default:
        return otherName
    }
  }

  return ''
}

// 获取编辑关系对话框的关系指向文本
const getEditRelationDirectionText = () => {
  const rel = editRelationRelation.value
  if (!rel) return ''

  const relationType = editRelationForm.value.relation_type
  const currentText = '当前原料'

  // 判断是 child_relation 还是 parent_relation
  // child_relation: 当前原料是父，关联原料是子
  if (rel.child_name && !rel.parent_name) {
    // 这是 child_relation，格式：子原料 属于 当前原料
    return `${rel.child_name} ${getRelationDirectionText(relationType, 'child', true)}`
  }
  // parent_relation: 当前原料是子，关联原料是父
  else if (rel.parent_name && !rel.child_name) {
    // 这是 parent_relation，格式：当前原料 属于 父原料
    return `${getRelationDirectionText(relationType, 'parent', true)} ${rel.parent_name}`
  }

  return ''
}

// 获取关系预览文本（用于添加关系对话框）
// 显示格式：当前原料 [关系动词] 目标原料
const getRelationPreviewText = (relationType: string, direction: 'child' | 'parent') => {
  const currentName = ingredient.value?.name || '当前原料'
  const targetName = selectedTargetIngredient.value?.name || '目标原料'

  // child_relations: 当前原料是父，目标原料是子
  if (direction === 'child') {
    switch (relationType) {
      case 'contains':
        return `${currentName} 包含 ${targetName}`
      case 'fallback':
        return `${currentName} 可回退到 ${targetName}`
      case 'substitutable':
        return `${currentName} 和 ${targetName} 可相互替代`
      default:
        return `${currentName} - ${targetName}`
    }
  }

  // parent_relations: 当前原料是子，目标原料是父
  if (direction === 'parent') {
    switch (relationType) {
      case 'contains':
        return `${currentName} 属于 ${targetName}`
      case 'fallback':
        return `${currentName} 可回退到 ${targetName}`
      case 'substitutable':
        return `${currentName} 和 ${targetName} 可相互替代`
      default:
        return `${currentName} - ${targetName}`
    }
  }

  return ''
}

// 获取关系描述文本（解释关系的含义）
const getRelationDescriptionText = (relationType: string, direction: 'child' | 'parent') => {
  const targetName = selectedTargetIngredient.value?.name || '目标原料'

  // child_relations: 当前原料是父，目标原料是子
  if (direction === 'child') {
    switch (relationType) {
      case 'contains':
        return `即 ${targetName} 是 ${ingredient.value?.name || '当前原料'} 的一部分`
      case 'fallback':
        return `即当无法获取 ${ingredient.value?.name || '当前原料'} 时，可使用 ${targetName} 代替`
      case 'substitutable':
        return `即两者可以在某些情况下互相替换使用`
      default:
        return ''
    }
  }

  // parent_relations: 当前原料是子，目标原料是父
  if (direction === 'parent') {
    switch (relationType) {
      case 'contains':
        return `即 ${ingredient.value?.name || '当前原料'} 是 ${targetName} 的一部分`
      case 'fallback':
        return `即当无法获取 ${ingredient.value?.name || '当前原料'} 时，可使用 ${targetName} 代替`
      case 'substitutable':
        return `即两者可以在某些情况下互相替换使用`
      default:
        return ''
    }
  }

  return ''
}

// 加载单位列表
const loadUnits = async () => {
  try {
    const response = await api.get('/units/', { params: { limit: 100 } })
    units.value = response.items || response || []
  } catch (e) {
    units.value = []
  }
}

// 打开编辑对话框
const openEditDialog = () => {
  if (!ingredient.value) return
  editForm.value = {
    name: ingredient.value.name || '',
    default_unit_id: ingredient.value.default_unit_id || null,
    aliases: ingredient.value.aliases || []
  }
  showEditDialog.value = true
}

// 保存编辑
const saveEdit = async () => {
  if (!editForm.value.name.trim()) return

  saving.value = true
  try {
    const response = await api.put(`/nutrition/ingredients/${ingredientId.value}`, editForm.value)
    ingredient.value = response
    showEditDialog.value = false
    showMessage('保存成功', 'success')
  } catch (e: any) {
    showMessage(e.message || '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

// 前往添加价格
const goToAddPrice = () => {
  if (priceForm.value.product_id) {
    router.push(`/data/products/${priceForm.value.product_id}`)
  }
}

// 搜索合并目标
const searchMergeTargets = async (search?: string) => {
  if (!search || search.length < 1) {
    mergeTargets.value = []
    return
  }

  loadingMergeTargets.value = true
  try {
    const response = await api.get('/ingredients', {
      params: { q: search, limit: 20 }
    })
    // 过滤掉当前原料
    mergeTargets.value = (response.items || []).filter(
      (item: Ingredient) => item.id !== ingredientId.value
    )
  } catch (e) {
    mergeTargets.value = []
  } finally {
    loadingMergeTargets.value = false
  }
}

// 合并原料
const mergeIngredient = async () => {
  if (!mergeTargetId.value) return

  merging.value = true
  try {
    const response = await api.post('/ingredients/merge', {
      source_id: ingredientId.value,
      target_id: mergeTargetId.value
    })
    showMessage(response.message || '合并成功', 'success')
    // 跳转到目标原料
    router.push(`/data/ingredients/${mergeTargetId.value}`)
  } catch (e: any) {
    showMessage(e.message || '合并失败', 'error')
  } finally {
    merging.value = false
  }
}

// 确认删除
const confirmDelete = () => {
  showDeleteDialog.value = true
}

// 删除原料
const deleteIngredient = async () => {
  deleting.value = true
  try {
    await api.delete(`/nutrition/ingredients/${ingredientId.value}`)
    showMessage('删除成功', 'success')
    router.push('/data/ingredients')
  } catch (e: any) {
    showMessage(e.message || '删除失败', 'error')
  } finally {
    deleting.value = false
  }
}

// 跳转到商品详情
const goToProduct = (id: number) => {
  router.push(`/data/products/${id}`)
}

// 跳转到菜谱详情
const goToRecipe = (id: number) => {
  router.push(`/recipes/${id}`)
}

// 跳转到原料详情
const goToIngredient = (id: number) => {
  router.push(`/data/ingredients/${id}`)
}

// 返回
const goBack = () => {
  router.push('/data/ingredients')
}

// 格式化函数
const formatPrice = (price: any) => {
  const num = parseFloat(price) || 0
  return num.toFixed(2)
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

const formatDateTime = (dateStr: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatNutritionValue = (value: any, unit: string) => {
  const num = parseFloat(value) || 0
  return `${num.toFixed(1)} ${unit}`
}

// 显示消息
const showMessage = (message: string, color: string = 'success') => {
  snackbar.value = { show: true, message, color }
}

// 监听分页变化
watch(pricePage, loadPriceRecords)

// 监听原料搜索输入，执行防抖搜索
watch(ingredientSearchQuery, (newSearch) => {
  if (ingredientSearchTimeout) clearTimeout(ingredientSearchTimeout)
  ingredientSearchTimeout = setTimeout(() => {
    searchIngredients(newSearch)
  }, 300)
})

// 监听合并原料搜索输入，执行防抖搜索
watch(mergeSearchQuery, (newSearch) => {
  if (mergeSearchTimeout) clearTimeout(mergeSearchTimeout)
  mergeSearchTimeout = setTimeout(() => {
    searchMergeTargets(newSearch)
  }, 300)
})

// 监听选中的目标原料对象，同步 id 到表单
watch(selectedTargetIngredient, (newIngredient) => {
  relationForm.value.target_ingredient_id = newIngredient?.id || null
}, { immediate: true })

// 监听选中的合并目标对象，同步 id
watch(selectedMergeTarget, (newTarget) => {
  mergeTargetId.value = newTarget?.id || null
}, { immediate: true })

// 监听选中的商品对象，同步 id 到表单
watch(selectedPriceProduct, (newProduct) => {
  priceForm.value.product_id = newProduct?.id || null
}, { immediate: true })

// 监听路由参数变化，当原料 ID 变化时重新加载数据
watch(() => route.params.id, () => {
  if (route.params.id) {
    loadData()
  }
})

// 初始化
onMounted(() => {
  loadData()
  loadUnits()
})
</script>

<style scoped>
/* 营养成分表格样式 */
.nutrition-header {
  background: rgb(var(--v-theme-surface-variant));
  font-weight: 500;
}

.nutrition-row:hover {
  background: rgba(var(--v-theme-primary), 0.04);
}

.relation-item-wrapper :deep(.v-list-item__content) {
  padding: 0;
}

.relation-item-content {
  cursor: pointer;
  transition: background-color 0.2s;
  border-radius: 4px;
  padding: 8px;
  margin: -8px;
}

.relation-item-content:hover {
  background: rgba(var(--v-theme-primary), 0.08);
}
</style>
