<template>
  <!-- 顶部导航栏 - 移到 container 外面以便固定 -->
  <v-app-bar elevation="0" color="background" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
    <v-app-bar-title class="text-h6">
      <div class="d-flex align-center ga-2">
        <span class="text-truncate">{{ overlaidIngredientName || '原料详情' }}</span>
        <v-chip size="x-small" variant="tonal" color="primary">原料</v-chip>
      </div>
    </v-app-bar-title>
    <template #append>
      <!-- 桌面端：按钮平铺 -->
      <template v-if="isDesktop">
        <v-btn icon="mdi-tag-plus" variant="text" @click="openQuickPriceDialog" />
        <v-btn icon="mdi-refresh" variant="text" :loading="loading" @click="loadData" />
      </template>
      <!-- 移动端：三点溢出菜单 -->
      <v-menu v-else :close-on-content-click="true" location="bottom end">
        <template #activator="{ props: menuProps }">
          <v-btn icon="mdi-dots-vertical" variant="text" v-bind="menuProps" :loading="loading" />
        </template>
        <v-list density="compact" nav>
          <v-list-item prepend-icon="mdi-tag-plus" title="记录价格" @click="openQuickPriceDialog" />
          <v-list-item prepend-icon="mdi-refresh" title="刷新" @click="loadData" />
        </v-list>
      </v-menu>
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
      <div class="px-4 pt-4 pb-0">
        <PendingProposalBanner :proposal="pendingProposal" />
      </div>
      <div class="ingredient-layout">
      <!-- 基本信息 -->
      <v-card elevation="0" class="grid-item item-basic-info">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="primary">mdi-information-outline</v-icon>
          基本信息
          <v-spacer />
          <v-btn
            v-if="!editingBasicInfo"
            icon="mdi-pencil"
            size="small"
            variant="text"
            color="primary"
            @click="startEditBasicInfo"
          />
          <template v-else>
            <v-btn size="small" variant="text" @click="cancelEditBasicInfo">取消</v-btn>
            <v-btn size="small" color="primary" variant="text" :loading="saving" @click="saveBasicInfo">保存</v-btn>
          </template>
        </v-card-title>
        <v-divider />
        <v-card-text>
          <!-- 展示模式 -->
          <v-list v-if="!editingBasicInfo" density="compact">
            <v-list-item v-if="ingredient.category">
              <template #prepend>
                <v-icon size="small" color="medium-emphasis">mdi-folder-outline</v-icon>
              </template>
              <v-list-item-title>分类</v-list-item-title>
              <v-list-item-subtitle>{{ overlaidCategory }}</v-list-item-subtitle>
            </v-list-item>

            <v-list-item v-if="overlaidAliases?.length" class="aliases-list-item">
              <template #prepend>
                <v-icon size="small" color="medium-emphasis">mdi-tag-outline</v-icon>
              </template>
              <v-list-item-title>别名</v-list-item-title>
              <v-list-item-subtitle class="aliases-subtitle">
                <v-chip
                  v-for="alias in overlaidAliases!"
                  :key="alias"
                  size="small"
                  class="mr-1 mb-1"
                  label
                >
                  {{ alias }}
                </v-chip>
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item v-if="ingredient.making_recipe_name">
              <template #prepend>
                <v-icon size="small" color="success">mdi-pot-steam-outline</v-icon>
              </template>
              <v-list-item-title>制作来源</v-list-item-title>
              <v-list-item-subtitle>由「{{ ingredient.making_recipe_name }}」制作</v-list-item-subtitle>
            </v-list-item>

            <v-list-item v-if="overlaidServingWeight">
              <template #prepend>
                <v-icon size="small" color="medium-emphasis">mdi-scale-balance</v-icon>
              </template>
              <v-list-item-title>成品基准量</v-list-item-title>
              <v-list-item-subtitle>{{ overlaidServingWeight }}{{ overlaidServingWeightUnitName || 'g' }}/份</v-list-item-subtitle>
            </v-list-item>

            <v-list-item>
              <template #prepend>
                <v-icon size="small" color="medium-emphasis">mdi-calendar</v-icon>
              </template>
              <v-list-item-title>创建时间</v-list-item-title>
              <v-list-item-subtitle>{{ formatToLocalDateTimeShort(ingredient.created_at) }}</v-list-item-subtitle>
            </v-list-item>
          </v-list>

          <!-- 编辑模式 -->
          <v-form v-else @submit.prevent="saveBasicInfo">
            <v-text-field
              v-model="basicEditForm.name"
              label="原料名称"
              variant="outlined"
              density="compact"
              required
              class="mb-3"
            />
            <v-autocomplete
              v-model="basicEditForm.category_id"
              :items="categories"
              item-title="display_name"
              item-value="id"
              label="分类"
              variant="outlined"
              density="compact"
              clearable
              class="mb-3"
            />
            <v-combobox
              v-model="basicEditForm.aliases"
              label="别名"
              variant="outlined"
              density="compact"
              multiple
              chips
              closable-chips
              hint="按回车添加别名"
              persistent-hint
              class="mb-3"
            />
            <div class="text-subtitle-2 mb-1">自制来源（半成品）</div>
            <div class="text-caption text-medium-emphasis mb-2">若此原料由某菜谱制作（如米饭由蒸米饭制作），选择制作菜谱并填写成品基准量，其成本将由该菜谱推导。</div>
            <v-autocomplete
              v-model="basicEditForm.making_recipe_id"
              :items="recipeOptions"
              item-title="name"
              item-value="id"
              label="制作菜谱"
              variant="outlined"
              density="compact"
              clearable
              :loading="recipeSearching"
              @update:search="onRecipeSearch"
              class="mb-3"
            />
            <v-row>
              <v-col cols="6">
                <v-text-field
                  v-model.number="basicEditForm.serving_weight"
                  label="成品基准量"
                  type="number"
                  variant="outlined"
                  density="compact"
                  hide-details
                  hint="每份多重（如1碗饭200g）"
                  persistent-hint
                />
              </v-col>
              <v-col cols="6">
                <v-autocomplete
                  v-model="basicEditForm.serving_weight_unit_id"
                  :items="units"
                  item-title="name"
                  item-value="id"
                  label="基准量单位"
                  variant="outlined"
                  density="compact"
                  clearable
                  hide-details
                />
              </v-col>
            </v-row>
          </v-form>
        </v-card-text>
      </v-card>

      <!-- 最新价格（加载中） -->
      <v-card elevation="0" class="grid-item item-latest-price" v-if="loadingLatestPrice && !latestPrice">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="tertiary">mdi-currency-cny</v-icon>
          最新价格
        </v-card-title>
        <v-divider />
        <v-card-text class="text-center py-6">
          <v-progress-circular indeterminate size="28" />
          <div class="text-body-2 text-medium-emphasis mt-2">加载中...</div>
        </v-card-text>
      </v-card>

      <!-- 最新价格 -->
      <v-card elevation="0" class="grid-item item-latest-price" v-else-if="latestPrice">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="tertiary">mdi-currency-cny</v-icon>
          最新价格
        </v-card-title>
        <v-divider />
        <v-card-text class="py-6">
          <div class="d-flex align-center ga-4 flex-wrap">
            <div class="text-h3 font-weight-bold text-tertiary">
              ¥{{ formatPrice(latestPrice) }}<span class="text-h6 font-weight-regular">/{{ massUnitName }}</span>
            </div>
            <template v-if="latestChartTrend">
              <v-divider vertical class="d-none d-sm-flex" />
              <div class="text-center">
                <div class="text-caption text-medium-emphasis">区间</div>
                <div class="text-subtitle-1 font-weight-bold">
                  ¥{{ latestChartTrend.min.toFixed(2) }} - ¥{{ latestChartTrend.max.toFixed(2) }}/{{ chartUnit }}
                </div>
              </div>
              <div v-if="latestChartTrend.count" class="text-center">
                <div class="text-caption text-medium-emphasis">记录</div>
                <div class="text-subtitle-1 font-weight-bold">{{ latestChartTrend.count }}</div>
              </div>
            </template>
          </div>
          <div v-if="latestPriceDate" class="text-caption text-medium-emphasis mt-2">
            {{ formatToLocalDate(latestPriceDate) }}
          </div>
          <!-- 加权来源明细（透明追溯） -->
          <v-expansion-panels v-if="latestPriceParticipants.length" variant="accordion" class="mt-2">
            <v-expansion-panel>
              <v-expansion-panel-title class="text-caption">
                加权明细（{{ latestPriceParticipants.length }} 个商品参与）
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <div v-for="p in latestPriceParticipants" :key="p.product_id" class="text-caption d-flex justify-space-between">
                  <span>{{ p.name }} <v-chip size="x-small" :color="p.weight === 0 ? 'grey' : 'default'">权重 {{ p.weight }}</v-chip></span>
                  <span class="text-medium-emphasis">¥{{ Number(p.unit_price).toFixed(4) }}（{{ p.weight_source === 'override' ? '我的' : '全局' }}）</span>
                </div>
                <div v-for="e in latestPriceExcluded" :key="'ex_' + e.product_id" class="text-caption text-medium-emphasis">
                  已排除：{{ e.name }}（{{ e.reason === 'weight_zero' ? '权重为0' : '当日无记录' }}）
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-card-text>

        <!-- 各商家最新价格 -->
        <!-- 加载中 -->
        <template v-if="loadingMerchantPrices">
          <v-divider />
          <v-card-text class="text-center py-4">
            <v-progress-circular indeterminate size="18" class="mr-2" />
            <span class="text-caption text-medium-emphasis">加载商家价格...</span>
          </v-card-text>
        </template>
        <template v-else-if="merchantPrices.length > 0">
          <v-divider />
          <v-card-text class="pa-3">
            <div class="text-caption text-medium-emphasis mb-2">各商家价格</div>
            <div class="merchant-price-list">
              <div
                v-for="mp in merchantPrices"
                :key="mp.merchant_id"
                class="merchant-price-item"
                :class="{ 'merchant-price-lowest': mp.is_lowest }"
                style="position: relative"
              >
                <SparklineBackground
                  v-if="mp.sparkline_data"
                  :data="mp.sparkline_data"
                  color="tertiary"
                />
                <div class="merchant-price-name text-truncate" style="position: relative; z-index: 1">{{ mp.merchant_name }}</div>
                <div class="merchant-price-value" style="position: relative; z-index: 1">
                  <span class="font-weight-bold" :class="mp.is_lowest ? 'text-success' : ''">
                    ¥{{ mp.price.toFixed(2) }}
                  </span>
                </div>
                <div v-if="mp.recorded_at" class="merchant-price-date" style="position: relative; z-index: 1">
                  {{ formatToLocalDate(mp.recorded_at) }}
                </div>
                <div v-if="mp.is_lowest" class="merchant-price-badge">
                  <v-chip size="x-small" color="success" variant="flat" label>最低</v-chip>
                </div>
              </div>
            </div>
            <v-divider class="mt-1" />
            <div v-if="latestPrice" class="d-flex justify-space-between align-center px-1 pt-2">
              <span class="text-caption text-medium-emphasis">商品加权综合价</span>
              <span class="font-weight-bold text-tertiary">
                ¥{{ formatPrice(latestPrice) }}<span class="text-caption font-weight-regular">/{{ massUnitName }}</span>
              </span>
            </div>
          </v-card-text>
        </template>
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
        :loading="loadingChartPrices"
        color="#ff9800"
        avg-label="加权平均"
        class="grid-item item-price-trend"
        @filter-change="onPriceTrendFilterChange"
      />

      <!-- 关联商品 -->
      <v-card elevation="0" class="grid-item item-products">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="primary">mdi-package-variant</v-icon>
          关联商品
          <v-chip size="small" class="ml-2" v-if="products.length > 0">
            {{ products.length }}
          </v-chip>
          <v-spacer />
          <v-btn size="small" variant="text" color="primary" @click="openAddProductDialog">
            <v-icon start>mdi-plus</v-icon>
            添加
          </v-btn>
        </v-card-title>
        <v-divider />

        <v-list v-if="products.length > 0">
          <v-list-item
            v-for="product in products"
            :key="product.id"
            @click="goToProduct(product.id)"
            class="product-list-item"
          >
            <template #prepend>
              <v-avatar color="primary" size="36">
                <span class="text-white text-caption">{{ product.name?.charAt(0) }}</span>
              </v-avatar>
            </template>

            <div class="d-flex align-center w-100 ga-2 py-1">
              <!-- 左侧：名称 + 品牌 -->
              <div class="flex-grow-1" style="min-width: 0">
                <div class="text-body-2 text-truncate">{{ product.name }}</div>
                <div v-if="product.brand" class="text-caption text-medium-emphasis text-truncate">{{ product.brand }}</div>
              </div>

              <!-- 右侧：加载中/价格 + 迷你图 + 操作按钮 -->
              <div class="d-flex align-center ga-1 flex-shrink-0">
                <!-- 价格区域 -->
                <div v-if="productPrices[product.id]" class="text-right" style="min-width: 68px">
                  <div v-if="productPrices[product.id].loading" class="text-center">
                    <v-progress-circular indeterminate size="14" width="2" />
                  </div>
                  <template v-else-if="productPrices[product.id].latestPrice !== null">
                    <div class="text-body-2 font-weight-bold text-tertiary text-no-wrap" style="line-height: 1.2">
                      ¥{{ Number(productPrices[product.id].latestPrice).toFixed(2) }}
                      <span v-if="productPrices[product.id].latestPriceUnit" class="text-caption font-weight-regular">{{ productPrices[product.id].latestPriceUnit }}</span>
                    </div>
                    <div v-if="productPrices[product.id].latestPriceDate" class="text-caption text-medium-emphasis" style="font-size: 0.6rem; line-height: 1">
                      {{ formatToLocalDate(productPrices[product.id].latestPriceDate) }}
                    </div>
                  </template>
                </div>

                <!-- 迷你图 -->
                <div
                  v-if="productPrices[product.id]?.sparklineData?.length >= 2"
                  style="width: 44px; height: 26px; position: relative"
                >
                  <SparklineBackground
                    :data="productPrices[product.id].sparklineData"
                    color="tertiary"
                    :height="26"
                  />
                </div>

                <v-btn
                  icon="mdi-pencil"
                  size="x-small"
                  variant="text"
                  density="compact"
                  @click.stop="openEditProductDialog(product)"
                />
                <v-btn
                  icon="mdi-delete"
                  size="x-small"
                  variant="text"
                  density="compact"
                  color="error"
                  :disabled="products.length <= 1"
                  @click.stop="openDeleteProductDialog(product)"
                />
                <v-icon size="small">mdi-chevron-right</v-icon>
              </div>
            </div>
          </v-list-item>
        </v-list>

        <v-card-text v-else class="text-center py-8">
          <v-icon size="48" color="medium-emphasis">mdi-package-variant-closed</v-icon>
          <div class="text-body-2 text-medium-emphasis mt-2">暂无关联商品</div>
        </v-card-text>
      </v-card>

      <!-- 价格记录 -->
      <v-card elevation="0" class="grid-item item-price-records">
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
              <div>¥{{ formatPrice(record.price) }} / {{ record.original_quantity }}{{ record.original_unit }}
              <template v-if="record.merchant_name"> · {{ record.merchant_name }}</template></div>
              <div class="text-caption text-medium-emphasis mt-1">
                {{ formatToLocalDate(record.recorded_at) }}
              </div>
            </v-list-item-subtitle>

            <template #append>
              <div class="d-flex ga-1">
                <v-btn
                  v-if="record.is_owner || userStore.user?.is_admin"
                  icon="mdi-pencil"
                  size="small"
                  variant="text"
                  color="primary"
                  @click="openEditPriceDialog(record)"
                />
                <v-btn
                  v-if="record.is_owner || userStore.user?.is_admin"
                  icon="mdi-delete"
                  size="small"
                  variant="text"
                  color="error"
                  @click="deletePriceRecord(record.id)"
                />
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

      <!-- 相关菜谱 -->
      <v-card elevation="0" class="grid-item item-recipes">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="primary">mdi-chef-hat</v-icon>
          相关菜谱
          <v-chip size="small" class="ml-2" v-if="recipeTotal > 0">
            {{ recipeTotal }}
          </v-chip>
        </v-card-title>
        <v-divider />

        <v-list v-if="recipes.length > 0" lines="two">
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
            <v-list-item-title>{{ recipe.name }}<v-chip v-if="!recipe.is_public" size="x-small" color="warning" variant="tonal" class="ml-2">未发布</v-chip></v-list-item-title>
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

        <!-- 分页器 -->
        <div v-if="recipeTotal > 0" class="d-flex flex-wrap justify-center align-center ga-2 py-4">
          <v-pagination
            v-model="recipePage"
            :length="recipeTotalPages"
            :total-visible="3"
            rounded="circle"
            density="comfortable"
          />
          <span class="text-caption text-medium-emphasis">共 {{ recipeTotal }} 条</span>
        </div>
      </v-card>

      <!-- Group 3: 营养成分 | 层级关系 + 关系列表 + 单位与密度（独立列高） -->
      <div class="group-3-wrapper">
        <div class="group-3-left">
      <!-- 营养成分 -->
      <v-card elevation="0" class="grid-item item-nutrition" v-if="nutritionData">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="success">mdi-food-apple-outline</v-icon>
          营养成分
          <span class="text-caption text-medium-emphasis ml-2">（每100g）</span>
          <v-spacer />
          <template v-if="!editingNutrition">
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
            <v-btn
              icon="mdi-pencil"
              size="small"
              variant="text"
              color="primary"
              @click="startEditNutrition"
            />
            <v-btn size="small" variant="text" color="primary" prepend-icon="mdi-database-search"
              @click="usdaDialog = true">匹配 USDA</v-btn>
          </template>
          <template v-else>
            <v-btn size="small" variant="text" @click="cancelEditNutrition">取消</v-btn>
            <v-btn size="small" color="primary" variant="text" :loading="savingNutrition" @click="saveNutritionEdit">保存</v-btn>
          </template>
        </v-card-title>
        <v-divider />
        <PendingProposalBanner :proposal="nutritionPendingProposal" class="mx-4 mt-3 mb-0" />

        <!-- 展示模式 -->
        <v-card-text v-if="!editingNutrition" class="pa-0">
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

        <!-- 编辑模式 -->
        <v-card-text v-else class="pa-0">
          <div class="nutrition-edit-table py-2 px-2 header-row border-bottom">
            <div class="text-caption text-medium-emphasis ps-2">营养素</div>
            <div class="text-caption text-medium-emphasis text-end">数量</div>
            <div class="text-caption text-medium-emphasis text-end">单位</div>
            <div></div>
          </div>
          <div
            v-for="(entry, index) in nutritionEditItems"
            :key="index"
            class="nutrition-edit-table align-center py-1 px-2"
            :class="{ 'border-bottom': index !== nutritionEditItems.length - 1 }"
          >
            <div class="ps-1 pe-1">
              <v-autocomplete
                :model-value="entry.key"
                :items="getNutrientOptionsForRow(entry.key)"
                item-title="label"
                item-value="key"
                variant="outlined"
                density="compact"
                hide-details
                placeholder="选择营养素"
                class="nutrition-edit-input"
                @update:model-value="(v: string) => onNutrientKeyChange(index, v)"
              >
                <template #item="{ props, item }">
                  <v-list-item v-bind="props" :subtitle="item.raw.defaultUnit" />
                </template>
              </v-autocomplete>
            </div>
            <div class="px-1">
              <v-text-field
                v-model.number="entry.value"
                variant="outlined"
                density="compact"
                hide-details
                type="number"
                placeholder="0"
                class="nutrition-edit-input text-end"
              />
            </div>
            <div class="px-1">
              <v-select
                v-model="entry.unit"
                :items="entry.units"
                variant="outlined"
                density="compact"
                hide-details
                class="nutrition-edit-input"
                @update:model-value="(v: string) => onUnitChange(index, v)"
              />
            </div>
            <div class="text-center">
              <v-btn
                icon="mdi-delete"
                size="x-small"
                variant="text"
                color="error"
                density="compact"
                @click="removeNutrientEditItem(index)"
              />
            </div>
          </div>
          <!-- 空状态指引 -->
          <div v-if="nutritionEditItems.length === 0" class="text-center py-4">
            <span class="text-caption text-medium-emphasis">暂无营养素，点击下方按钮添加</span>
          </div>
          <div class="pa-3">
            <v-btn
              size="small"
              variant="tonal"
              color="primary"
              prepend-icon="mdi-plus"
              @click="addEmptyNutrientRow"
            >
              添加营养素
            </v-btn>
          </div>
        </v-card-text>
      </v-card>

      <!-- 营养编辑：无数据时的卡片（允许进入编辑模式添加） -->
      <v-card v-else elevation="0" class="grid-item item-nutrition">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="success">mdi-food-apple-outline</v-icon>
          营养成分
          <span class="text-caption text-medium-emphasis ml-2">（每100g）</span>
          <v-spacer />
          <v-btn
            v-if="!loadingNutrition"
            icon="mdi-pencil"
            size="small"
            variant="text"
            color="primary"
            @click="startEditNutrition"
          />
          <v-btn v-if="!loadingNutrition" size="small" variant="text" color="primary" prepend-icon="mdi-database-search"
            @click="usdaDialog = true">匹配 USDA</v-btn>
        </v-card-title>
        <v-divider />
        <!-- 懒加载中状态 -->
        <v-card-text v-if="loadingNutrition && !editingNutrition" class="text-center py-6">
          <v-progress-circular indeterminate size="28" />
          <div class="text-body-2 text-medium-emphasis mt-2">加载中...</div>
        </v-card-text>
        <v-card-text v-else-if="!editingNutrition" class="text-center py-8">
          <v-icon size="48" color="medium-emphasis">mdi-food-apple-outline</v-icon>
          <div class="text-body-2 text-medium-emphasis mt-2">暂无营养数据</div>
          <div class="text-caption text-medium-emphasis mt-1">点击编辑按钮添加</div>
        </v-card-text>
        <v-card-text v-else class="pa-0">
          <div class="nutrition-edit-table py-2 px-2 header-row border-bottom">
            <div class="text-caption text-medium-emphasis ps-2">营养素</div>
            <div class="text-caption text-medium-emphasis text-end">数量</div>
            <div class="text-caption text-medium-emphasis text-end">单位</div>
            <div></div>
          </div>
          <div
            v-for="(entry, index) in nutritionEditItems"
            :key="index"
            class="nutrition-edit-table align-center py-1 px-2"
            :class="{ 'border-bottom': index !== nutritionEditItems.length - 1 }"
          >
            <div class="ps-1 pe-1">
              <v-autocomplete
                :model-value="entry.key"
                :items="getNutrientOptionsForRow(entry.key)"
                item-title="label"
                item-value="key"
                variant="outlined"
                density="compact"
                hide-details
                placeholder="选择营养素"
                class="nutrition-edit-input"
                @update:model-value="(v: string) => onNutrientKeyChange(index, v)"
              >
                <template #item="{ props, item }">
                  <v-list-item v-bind="props" :subtitle="item.raw.defaultUnit" />
                </template>
              </v-autocomplete>
            </div>
            <div class="px-1">
              <v-text-field
                v-model.number="entry.value"
                variant="outlined"
                density="compact"
                hide-details
                type="number"
                placeholder="0"
                class="nutrition-edit-input text-end"
              />
            </div>
            <div class="px-1">
              <v-select
                v-model="entry.unit"
                :items="entry.units"
                variant="outlined"
                density="compact"
                hide-details
                class="nutrition-edit-input"
                @update:model-value="(v: string) => onUnitChange(index, v)"
              />
            </div>
            <div class="text-center">
              <v-btn icon="mdi-delete" size="x-small" variant="text" color="error" density="compact" @click="removeNutrientEditItem(index)" />
            </div>
          </div>
          <div v-if="nutritionEditItems.length === 0" class="text-center py-4">
            <span class="text-caption text-medium-emphasis">暂无营养素，点击下方按钮添加</span>
          </div>
          <div class="pa-3">
            <v-btn size="small" variant="tonal" color="primary" prepend-icon="mdi-plus" @click="addEmptyNutrientRow">
              添加营养素
            </v-btn>
            <div class="d-flex justify-end mt-3">
              <v-btn size="small" variant="text" @click="cancelEditNutrition">取消</v-btn>
              <v-btn size="small" color="primary" variant="text" :loading="savingNutrition" @click="saveNutritionEdit">保存</v-btn>
            </div>
          </div>
        </v-card-text>
      </v-card>
        </div>
        <div class="group-3-right">

      <!-- 层级关系 -->
      <v-card elevation="0" class="grid-item item-hierarchy">
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

        <!-- 加载中 -->
        <v-card-text v-if="loadingHierarchy" class="text-center py-6">
          <v-progress-circular indeterminate size="28" />
          <div class="text-body-2 text-medium-emphasis mt-2">加载中...</div>
        </v-card-text>

        <!-- 空状态 -->
        <v-card-text v-else-if="!hasRelations" class="text-center py-8">
          <v-icon size="48" color="medium-emphasis">mdi-graph-outline</v-icon>
          <div class="text-body-2 text-medium-emphasis mt-2">暂无层级关系</div>
          <div class="text-caption text-medium-emphasis mt-1">
            可以设置原料之间的包含、回退或可替代关系
          </div>
        </v-card-text>
      </v-card>

      <!-- 关系列表 -->
      <v-card v-if="hasRelations" elevation="0" class="grid-item item-relation-list">
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
                    <span class="ml-2">强度: {{ Math.round(rel.strength) }}%</span>
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
                    <span class="ml-2">强度: {{ Math.round(rel.strength) }}%</span>
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

      <!-- 单位与密度 -->
      <v-card elevation="0" class="grid-item item-units">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="secondary">mdi-ruler</v-icon>
          单位与密度
        </v-card-title>
        <v-divider />

        <!-- 自定义单位列表 -->
        <v-card-text class="pb-0">
          <PendingProposalBanner v-if="pendingUnitProposal" :proposal="pendingUnitProposal" class="mb-2" />
          <div class="d-flex align-center mb-2">
            <span class="text-body-2 font-weight-medium">自定义单位</span>
            <v-spacer />
            <v-btn
              size="small"
              variant="text"
              color="primary"
              prepend-icon="mdi-plus"
              @click="openUnitDialog()"
            >
              添加单位
            </v-btn>
          </div>

          <!-- 待配置单位（来自菜谱的 count 类型单位，尚未映射） -->
          <div v-if="unmappedUnits.length > 0" class="mb-3">
            <div class="text-caption text-medium-emphasis mb-1">
              待配置单位（来自菜谱，点击快速添加，默认 100 g）
            </div>
            <v-chip
              v-for="item in unmappedUnits"
              :key="item.unit_id"
              size="small"
              variant="outlined"
              color="warning"
              class="mr-1 mb-1"
              style="cursor: pointer"
              @click="quickAddUnmappedUnit(item)"
            >
              {{ item.unit_name }}
              <span class="text-caption ml-1">({{ item.usage_count }}次)</span>
            </v-chip>
          </div>

          <div v-if="loadingUnits" class="text-center py-4">
            <v-progress-circular indeterminate color="primary" size="24" />
          </div>

          <v-list v-else-if="mergedEntityUnits.length > 0" density="compact" class="pa-0">
            <v-list-item
              v-for="unit in mergedEntityUnits"
              :key="unit.id"
              class="px-0"
            >
              <template #prepend>
                <v-chip size="small" :variant="(unit as any)._pending ? 'outlined' : 'tonal'" :color="(unit as any)._pending ? 'info' : 'primary'" class="mr-3">
                  {{ unit.unit_name }}
                </v-chip>
              </template>
              <v-list-item-title class="text-body-2">
                <span v-if="unit.conversion_factor">1{{ unit.unit_name }} = {{ unit.conversion_factor }}个</span>
                <span v-if="unit.weight_per_unit" class="ml-2">
                  <v-icon size="x-small">mdi-weight</v-icon>
                  {{ unit.weight_per_unit }}g/个
                </span>
                <v-chip v-if="(unit as any)._pending" size="x-small" color="info" variant="tonal" class="ml-1">待审</v-chip>
              </v-list-item-title>
              <v-list-item-subtitle class="text-caption">
                <template v-if="unit.is_default">
                  <span class="text-primary">默认单位</span>
                  <span class="mx-1">·</span>
                </template>
                <span class="text-medium-emphasis">{{ unit.source === 'import' ? '自动' : '手动' }}</span>
              </v-list-item-subtitle>
              <template #append>
                <v-btn
                  v-if="!(unit as any)._pending"
                  icon="mdi-pencil"
                  size="x-small"
                  variant="text"
                  color="primary"
                  @click.stop="openUnitDialog(unit)"
                />
                <v-btn
                  v-if="!(unit as any)._pending"
                  icon="mdi-delete"
                  size="x-small"
                  variant="text"
                  color="error"
                  @click.stop="deleteEntityUnit(unit.id)"
                />
              </template>
            </v-list-item>
          </v-list>

          <div v-else class="text-center py-4">
            <v-icon size="32" color="medium-emphasis">mdi-ruler</v-icon>
            <div class="text-caption text-medium-emphasis mt-1">暂无自定义单位</div>
          </div>
        </v-card-text>

        <v-divider class="mx-4" />

        <!-- 密度管理 -->
        <v-card-text>
          <PendingProposalBanner v-if="pendingDensityProposal" :proposal="pendingDensityProposal" class="mb-2" />
          <div class="d-flex align-center mb-2">
            <span class="text-body-2 font-weight-medium">密度信息</span>
            <v-spacer />
            <v-btn
              v-if="!displayDensity"
              size="small"
              variant="text"
              color="primary"
              prepend-icon="mdi-plus"
              @click="openDensityDialog()"
            >
              设置密度
            </v-btn>
            <template v-else-if="!(displayDensity as any)._pending">
              <v-btn
                icon="mdi-pencil"
                size="x-small"
                variant="text"
                color="primary"
                class="mr-1"
                @click="openDensityDialog(entityDensity)"
              />
              <v-btn
                icon="mdi-delete"
                size="x-small"
                variant="text"
                color="error"
                @click="deleteDensity(entityDensity!.id)"
              />
            </template>
          </div>

          <div v-if="displayDensity" class="d-flex align-center py-2">
            <v-icon size="small" color="medium-emphasis" class="mr-2">mdi-water</v-icon>
            <span class="text-body-2">
              {{ displayDensityValue }}
            </span>
            <v-chip
              size="x-small"
              variant="tonal"
              color="primary"
              class="ml-1 cursor-pointer"
              @click="toggleDisplayDensityUnit"
              :title="'点击切换为 ' + (densityDisplayUnit === 'g/cm3' ? 'kg/m³' : 'g/cm³')"
            >
              {{ densityDisplayUnit === 'g/cm3' ? 'g/cm³' : 'kg/m³' }}
              <v-icon end size="x-small">mdi-swap-horizontal</v-icon>
            </v-chip>
            <v-chip v-if="(displayDensity as any)._pending" size="x-small" color="info" variant="tonal" class="ml-1">待审</v-chip>
            <span v-if="displayDensity.temperature" class="text-caption text-medium-emphasis ml-2">
              ({{ displayDensity.temperature }}°C)
            </span>
            <span v-if="displayDensity.source" class="text-caption text-medium-emphasis ml-2">
              来源: {{ displayDensity.source }}
            </span>
          </div>
          <div v-else class="text-center py-4">
            <v-icon size="32" color="medium-emphasis">mdi-water-off</v-icon>
            <div class="text-caption text-medium-emphasis mt-1">暂未设置密度</div>
          </div>
        </v-card-text>
      </v-card>
        </div>
      </div>
      </div>

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

      <!-- 添加/编辑单位对话框 -->
      <v-dialog v-model="showUnitDialog" max-width="450">
        <v-card>
          <v-card-title>{{ unitForm.id ? '编辑单位' : '添加单位' }}</v-card-title>
          <v-card-text>
            <v-form @submit.prevent="saveEntityUnit">
              <v-text-field
                v-model="unitForm.unit_name"
                label="单位名称"
                variant="outlined"
                placeholder="如：盒(12个)、根、袋"
                required
                class="mb-3"
              />
              <v-text-field
                v-model.number="unitForm.conversion_factor"
                label="换算系数"
                variant="outlined"
                type="number"
                hint="1单位 = 几个基础单位"
                persistent-hint
                class="mb-3"
              />
              <v-text-field
                v-model.number="unitForm.weight_per_unit"
                label="单个重量 (g)"
                variant="outlined"
                type="number"
                hint="每个单位对应的重量（克）"
                persistent-hint
                class="mb-3"
              />
              <v-checkbox
                v-model="unitForm.is_default"
                label="设为默认单位"
                density="compact"
                hide-details
              />
            </v-form>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn @click="showUnitDialog = false">取消</v-btn>
            <v-btn color="primary" :loading="savingUnit" @click="saveEntityUnit">保存</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <!-- 添加/编辑密度对话框 -->
      <v-dialog v-model="showDensityDialog" max-width="450">
        <v-card>
          <v-card-title>{{ densityForm.id ? '编辑密度' : '设置密度' }}</v-card-title>
          <v-card-text>
            <v-form @submit.prevent="saveDensity">
              <div class="d-flex align-start ga-2 mb-3">
                <v-text-field
                  v-model.number="densityForm.density"
                  :label="'密度 (' + densityInputUnitLabel + ')'"
                  variant="outlined"
                  type="number"
                  required
                  class="flex-grow-1"
                />
                <v-btn-toggle
                  v-model="densityInputUnit"
                  mandatory
                  color="primary"
                  density="compact"
                  variant="outlined"
                  divided
                  class="mt-2"
                >
                  <v-btn value="g/cm3" size="small">g/cm³</v-btn>
                  <v-btn value="kg/m3" size="small">kg/m³</v-btn>
                </v-btn-toggle>
              </div>
              <v-text-field
                v-model.number="densityForm.temperature"
                label="参考温度 (°C)"
                variant="outlined"
                type="number"
                class="mb-3"
              />
              <v-text-field
                v-model="densityForm.source"
                label="来源"
                variant="outlined"
                placeholder="如：实测、USDA"
                class="mb-3"
              />
            </v-form>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn @click="showDensityDialog = false">取消</v-btn>
            <v-btn color="primary" :loading="savingDensity" @click="saveDensity">保存</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </template>

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

    <!-- 编辑价格记录对话框 -->
    <v-dialog v-model="showEditPriceDialog" max-width="500">
      <v-card>
        <v-card-title>编辑价格记录</v-card-title>
        <v-card-text>
          <div class="text-body-2 text-medium-emphasis mb-3">
            商品：{{ editingPriceRecord?.product_name }}
          </div>
          <v-form @submit.prevent="saveEditPriceRecord">
            <v-text-field
              v-model.number="editPriceForm.price"
              label="价格（元）"
              variant="outlined"
              type="number"
              step="0.01"
              required
              class="mb-4"
            />
            <v-row dense>
              <v-col cols="6">
                <v-text-field
                  v-model.number="editPriceForm.quantity"
                  label="数量"
                  variant="outlined"
                  type="number"
                  required
                />
              </v-col>
              <v-col cols="6">
                <v-select
                  v-model="editPriceForm.unit"
                  :items="unitOptions"
                  label="单位"
                  variant="outlined"
                  required
                />
              </v-col>
            </v-row>
            <v-autocomplete
              v-model="editPriceForm.merchant_id"
              :items="merchants"
              item-title="name"
              item-value="id"
              label="商家（可选）"
              variant="outlined"
              clearable
              class="mt-4"
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showEditPriceDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="savingPrice" @click="saveEditPriceRecord">保存</v-btn>
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

    <!-- 合并确认对话框 -->
    <v-dialog v-model="showMergeConfirmDialog" max-width="400">
      <v-card>
        <v-card-title class="text-warning">确认合并</v-card-title>
        <v-card-text>
          确定要将「{{ ingredient?.name }}」合并到「{{ selectedMergeTarget?.name }}」吗？
          <br /><br />
          <span class="text-error">此操作不可恢复！</span>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showMergeConfirmDialog = false">取消</v-btn>
          <v-btn color="warning" :loading="merging" @click="doMerge">确认合并</v-btn>
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
              :min="1"
              :max="100"
              :step="1"
              thumb-label
              :hints="true"
              class="mb-4"
            >
              <template #thumb-label="{ modelValue }">
                {{ Math.round(modelValue) }}%
              </template>
              <template #append>
                <v-chip size="small">{{ Math.round(relationForm.strength) }}%</v-chip>
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
              :min="1"
              :max="100"
              :step="1"
              thumb-label
              :hints="true"
            >
              <template #thumb-label="{ modelValue }">
                {{ Math.round(modelValue) }}%
              </template>
              <template #append>
                <v-chip size="small">{{ Math.round(editRelationForm.strength) }}%</v-chip>
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


    <!-- 添加/编辑商品对话框 -->
    <v-dialog v-model="showProductDialog" max-width="500">
      <v-card>
        <v-card-title>{{ isEditingProduct ? '编辑商品' : '添加商品' }}</v-card-title>
        <v-card-text>
          <v-form>
            <v-text-field
              v-model="productForm.name"
              label="商品名称"
              variant="outlined"
              required
              class="mb-4"
            />
            <v-text-field
              v-model="productForm.brand"
              label="品牌"
              variant="outlined"
              class="mb-4"
            />
            <v-text-field
              v-model="productForm.barcode"
              label="条码"
              variant="outlined"
              class="mb-4"
            />
            <v-combobox
              v-model="productForm.aliases"
              label="别名"
              variant="outlined"
              multiple
              chips
              closable-chips
              hint="输入后回车添加多个别名"
            />
            <!-- 价格权重区（与上方分隔，避免 hint 贴连） -->
            <div class="mt-4">
              <!-- 全局权重：仅管理员可改；普通用户整块不渲染 -->
              <div v-if="userStore.user?.is_admin" class="mb-4">
                <div class="text-caption text-medium-emphasis mb-1">
                  全局价格权重 <span class="text-disabled">（原料加权平均用；50=等权，0=排除该商品）</span>
                </div>
                <v-slider
                  v-model="productForm.priceWeight"
                  :min="0"
                  :max="100"
                  :step="1"
                  thumb-label
                  color="primary"
                >
                  <template #thumb-label="{ modelValue }">{{ modelValue }}</template>
                  <template #append>
                    <v-chip size="small" label>{{ productForm.priceWeight }}</v-chip>
                  </template>
                </v-slider>
              </div>
              <!-- 我的权重覆盖：开关 + 滑块（所有人可设） -->
              <div>
                <v-switch
                  v-model="productForm.myWeightEnabled"
                  label="覆盖全局权重（仅影响我）"
                  density="compact"
                  color="tertiary"
                  hide-details
                />
                <div class="text-caption text-medium-emphasis mb-1">
                  全局默认：{{ productForm.globalWeightReadOnly }}（不覆盖即用此值）
                </div>
                <v-slider
                  v-if="productForm.myWeightEnabled"
                  v-model="productForm.myWeight"
                  :min="0"
                  :max="100"
                  :step="1"
                  thumb-label
                  color="tertiary"
                >
                  <template #thumb-label="{ modelValue }">{{ modelValue }}</template>
                  <template #append>
                    <v-chip size="small" label color="tertiary">{{ productForm.myWeight }}</v-chip>
                  </template>
                </v-slider>
              </div>
            </div>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showProductDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="savingProduct" @click="saveProduct">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 删除商品确认对话框 -->
    <v-dialog v-model="showDeleteProductDialog" max-width="400">
      <v-card>
        <v-card-title class="text-error">确认删除商品</v-card-title>
        <v-card-text>
          确定要删除商品「{{ deletingProduct?.name }}」吗？此操作不可恢复。
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showDeleteProductDialog = false">取消</v-btn>
          <v-btn color="error" :loading="deletingProductLoading" @click="deleteProduct">删除</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 提示消息 -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000">
      {{ snackbar.message }}
    </v-snackbar>

    <!-- 快速记录价格对话框 -->
    <QuickPriceRecordDialog
      v-model="showQuickPriceDialog"
      :product-id="quickPriceProduct?.id ?? null"
      :product-name="quickPriceProduct?.name ?? ''"
      :products="quickPriceProducts"
      @saved="onQuickPriceSaved"
    />

    <!-- USDA 匹配对话框 -->
    <UsdaMatchDialog v-model="usdaDialog" entity-type="ingredient" :entity-id="ingredientId" @matched="onUsdaMatched" />
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, LONG_REQUEST_TIMEOUT } from '@/api/client'
import { getProductMyWeight, setProductMyWeight, deleteProductMyWeight } from '@/api/productWeight'
import { getErrorMessage } from '@/utils/errorHandler'
import PriceTrendChart from '@/components/charts/PriceTrendChart.vue'
import HierarchyGraph from '@/components/charts/HierarchyGraph.vue'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import { usePageTitle } from '@/composables/usePageTitle'
import QuickPriceRecordDialog from '@/components/prices/QuickPriceRecordDialog.vue'
import { NUTRITION_LABEL_MAP, ENGLISH_TO_CHINESE_MAP } from '@/utils/nutritionLabels'
import SparklineBackground from '@/components/charts/SparklineBackground.vue'
import UsdaMatchDialog from '@/components/usda/UsdaMatchDialog.vue'
import { formatToLocalDate, formatToLocalDateTimeShort } from '@/utils/timezone'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { useUserUnits } from '@/composables/useUserUnits'
import { buildNutrientDefinitions } from '@/composables/nutrientDefinitions'
import { useUserStore } from '@/stores/user'
import PendingProposalBanner from '@/components/proposals/PendingProposalBanner.vue'
import { usePendingProposals } from '@/composables/usePendingProposals'

const { ask } = useConfirmDialog()
const userStore = useUserStore()

const usdaDialog = ref(false)
function onUsdaMatched() {
  loadNutritionData()
}

const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const { setDetailTitle } = usePageTitle()

interface Ingredient {
  id: number
  name: string
  aliases?: string[]
  category_id?: number
  category?: string
  serving_weight?: number | null
  serving_weight_unit_id?: number | null
  serving_weight_unit_name?: string
  making_recipe_id?: number | null
  making_recipe_name?: string
  created_at: string
  updated_at?: string
}

interface Product {
  id: number
  name: string
  brand?: string
  barcode?: string
  aliases?: string[]
  ingredient_id?: number
}

interface ProductPriceInfo {
  loading: boolean
  latestPrice: number | null
  latestPriceUnit: string | null
  latestPriceDate: string | null
  sparklineData: number[]
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
  is_public?: boolean
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
const pendingProposal = ref<{ id: number; action: string; payload: Record<string, any> } | null>(null)
// 单位/密度的待审提议（create 类，按 payload 内目标实体关联）
const { load: loadPendingProposals, pendingList, getByPayloadEntity: getPendingByPayload } = usePendingProposals()
const pendingUnitProposal = computed(() => getPendingByPayload('entity_unit_override', 'ingredient', ingredientId.value))
const pendingDensityProposal = computed(() => getPendingByPayload('entity_density', 'ingredient', ingredientId.value))

// 待审 create 提议：自定义单位（实体尚未建立，合并到列表显示）
const pendingUnitItems = computed(() => {
  return pendingList.value
    .filter(p => p.entity_type === 'entity_unit_override' &&
                 p.action === 'create' &&
                 p.payload?.entity_type === 'ingredient' &&
                 p.payload?.entity_id === ingredientId.value)
    .map(p => {
      const pl = p.payload || {}
      return {
        id: -Number(p.id),
        entity_type: 'ingredient',
        entity_id: ingredientId.value,
        unit_name: pl.unit_name || '',
        base_unit_id: pl.base_unit_id ?? null,
        conversion_factor: pl.conversion_factor != null ? Number(pl.conversion_factor) : null,
        weight_per_unit: pl.weight_per_unit != null ? Number(pl.weight_per_unit) : null,
        weight_unit_id: pl.weight_unit_id ?? null,
        is_default: pl.is_default ?? false,
        source: pl.source ?? null,
        _pending: true,
      } as EntityUnitOverride & { _pending: boolean }
    })
})
const mergedEntityUnits = computed(() => [...entityUnits.value, ...pendingUnitItems.value])

// 待审 create 提议：密度（实体尚未建立，无 entityDensity 时显示草稿值）
const pendingDensityItem = computed(() => {
  const p = pendingList.value.find(x =>
    x.entity_type === 'entity_density' &&
    x.action === 'create' &&
    x.payload?.entity_type === 'ingredient' &&
    x.payload?.entity_id === ingredientId.value,
  )
  if (!p) return null
  const pl = p.payload || {}
  return {
    density: pl.density != null ? Number(pl.density) : null,
    temperature: pl.temperature ?? null,
    condition: pl.condition ?? null,
    source: pl.source ?? null,
    confidence: pl.confidence != null ? Number(pl.confidence) : 1,
    _pending: true,
  } as EntityDensity & { _pending: boolean }
})
const displayDensity = computed(() => entityDensity.value || pendingDensityItem.value)
const loading = ref(true)
const error = ref<string | null>(null)

// 展示值——如果有待审核的 update 提议，则用提议中的值覆盖原值
const overlaidIngredientName = computed(() => {
  if (pendingProposal.value?.action === 'update' && pendingProposal.value?.payload?.name) {
    return pendingProposal.value.payload.name
  }
  return ingredient.value?.name || ''
})

const overlaidCategory = computed(() => {
  if (pendingProposal.value?.action === 'update' && pendingProposal.value?.payload?.category_id !== undefined) {
    const cat = categories.value.find((c: { id: number; name: string; display_name: string }) => c.id === pendingProposal.value!.payload.category_id)
    return cat?.display_name || String(pendingProposal.value.payload.category_id)
  }
  return ingredient.value?.category
})

const overlaidAliases = computed(() => {
  if (pendingProposal.value?.action === 'update' && Array.isArray(pendingProposal.value?.payload?.aliases)) {
    return pendingProposal.value.payload.aliases
  }
  return ingredient.value?.aliases
})

// 用户级单位偏好（能量/质量/记价单位）——须在 editPriceForm 等引用前声明，否则触发 TDZ
const { energyUnit, priceUnitName, massUnitName, massUnit } = useUserUnits()

const overlaidServingWeight = computed(() => {
  if (pendingProposal.value?.action === 'update' && pendingProposal.value?.payload?.serving_weight !== undefined) {
    return pendingProposal.value.payload.serving_weight
  }
  return ingredient.value?.serving_weight
})

const overlaidServingWeightUnitName = computed(() => {
  if (pendingProposal.value?.action === 'update' && pendingProposal.value?.payload?.serving_weight_unit_id !== undefined) {
    const uid = pendingProposal.value.payload.serving_weight_unit_id
    if (uid) {
      const found = units.value.find((u: any) => u.id === uid)
      if (found) return found.name
    }
    return ''
  }
  return ingredient.value?.serving_weight_unit_name
})

// 最新价格
const latestPrice = ref<number | null>(null)
const latestPriceDate = ref<string | null>(null)
const loadingLatestPrice = ref(false)
const latestPriceParticipants = ref<any[]>([])
const latestPriceExcluded = ref<any[]>([])
// 原料下各商品生效权重（覆盖>全局>50），供价格趋势加权 avg 用
const productWeights = ref<Map<number, number>>(new Map())

// 按商家分组的最新价格
interface MerchantPrice {
  merchant_id: number
  merchant_name: string
  price: number
  unit: string
  recorded_at: string | null
  product_name: string
  is_lowest: boolean
}
const merchantPrices = ref<MerchantPrice[]>([])
const merchantPriceUnit = ref<string | null>(null)
const loadingMerchantPrices = ref(false)

// 关联商品
const products = ref<Product[]>([])

// 商品价格懒加载数据（按 product.id 索引）
const productPrices = ref<Record<number, ProductPriceInfo>>({})

// 商品管理对话框
const showProductDialog = ref(false)
const isEditingProduct = ref(false)
const editingProductId = ref<number | null>(null)
const savingProduct = ref(false)
const productForm = ref({
  name: '',
  brand: '',
  barcode: '',
  aliases: [] as string[],
  priceWeight: 50 as number,
  myWeight: 50 as number,
  myWeightEnabled: false as boolean,
  globalWeightReadOnly: 50 as number,
})
// 删除商品
const showDeleteProductDialog = ref(false)
const deletingProduct = ref<Product | null>(null)
const deletingProductLoading = ref(false)

// 打开添加商品对话框
const openAddProductDialog = () => {
  isEditingProduct.value = false
  editingProductId.value = null
  productForm.value = { name: '', brand: '', barcode: '', aliases: [], priceWeight: 50, myWeight: 50, myWeightEnabled: false, globalWeightReadOnly: 50 }
  showProductDialog.value = true
}

// 打开编辑商品对话框
const openEditProductDialog = (product: Product) => {
  isEditingProduct.value = true
  editingProductId.value = product.id
  productForm.value = {
    name: product.name || '',
    brand: product.brand || '',
    barcode: (product as any).barcode || '',
    aliases: [...((product as any).aliases || [])],
    priceWeight: (product as any).price_weight ?? 50,
    myWeight: (product as any).price_weight ?? 50,
    myWeightEnabled: false,
    globalWeightReadOnly: (product as any).price_weight ?? 50,
  }
  // 拉取当前用户生效权重（覆盖 > 全局）
  getProductMyWeight(product.id).then((res: any) => {
    productForm.value.globalWeightReadOnly = res.global_weight
    productForm.value.priceWeight = res.global_weight
    if (res.source === 'override') {
      productForm.value.myWeightEnabled = true
      productForm.value.myWeight = res.override_weight
    } else {
      productForm.value.myWeightEnabled = false
      productForm.value.myWeight = res.global_weight
    }
  }).catch(() => {})
  showProductDialog.value = true
}

// 保存商品（新增或编辑）
const saveProduct = async () => {
  if (!productForm.value.name.trim()) {
    showMessage('商品名称不能为空', 'error')
    return
  }
  savingProduct.value = true
  try {
    if (isEditingProduct.value && editingProductId.value) {
      // 编辑
      const _payload: any = {
        name: productForm.value.name,
        brand: productForm.value.brand || null,
        barcode: productForm.value.barcode || null,
        ingredient_id: ingredientId.value,
        aliases: productForm.value.aliases,
      }
      // 全局 price_weight 仅管理员可改
      if (userStore.user?.is_admin) {
        _payload.price_weight = productForm.value.priceWeight
      }
      const response = await api.put(`/products/entity/${editingProductId.value}`, _payload)
      // 我的权重覆盖：开关开 → set；关 → delete（用回全局）
      if (productForm.value.myWeightEnabled) {
        await setProductMyWeight(editingProductId.value, productForm.value.myWeight).catch(() => {})
      } else {
        await deleteProductMyWeight(editingProductId.value).catch(() => {})
      }
      if (userStore.user?.is_admin) {
        // 更新本地列表
        const idx = products.value.findIndex(p => p.id === editingProductId.value)
        if (idx !== -1) {
          products.value[idx] = { ...products.value[idx], ...response }
        }
        showMessage('商品已更新', 'success')
      } else {
        showMessage('已提交，待管理员审核', 'info')
      }
    } else {
      // 新增
      const response = await api.post('/products/entity', {
        name: productForm.value.name,
        brand: productForm.value.brand || null,
        barcode: productForm.value.barcode || null,
        ingredient_id: ingredientId.value,
        aliases: productForm.value.aliases,
      })
      products.value.push(response)
      showMessage('商品已添加', 'success')
    }
    showProductDialog.value = false
    // 权重/商品变更后刷新依赖加权的数据：最新价、各商家代表价、趋势权重
    // （我的覆盖对所有人立即生效；admin 全局立即生效；新增/删除商品改变加权分母）
    loadLatestPrice()
    loadMerchantPrices()
    loadProductWeights()
  } catch (e: any) {
    showMessage(e.response?.data?.detail || e.message || '保存失败', 'error')
  } finally {
    savingProduct.value = false
  }
}

// 打开删除商品对话框
const openDeleteProductDialog = (product: Product) => {
  if (products.value.length <= 1) {
    showMessage('该原料只有一个关联商品，无法删除', 'warning')
    return
  }
  deletingProduct.value = product
  showDeleteProductDialog.value = true
}

// 删除商品
const deleteProduct = async () => {
  if (!deletingProduct.value) return
  deletingProductLoading.value = true
  try {
    await api.delete(`/products/entity/${deletingProduct.value.id}`)
    if (userStore.user?.is_admin) {
      products.value = products.value.filter(p => p.id !== deletingProduct.value!.id)
      showMessage('商品已删除', 'success')
    } else {
      showMessage('删除提议已提交，待管理员审核', 'info')
    }
    showDeleteProductDialog.value = false
    deletingProduct.value = null
    // 删除商品改变加权分母，刷新依赖加权的数据
    loadLatestPrice()
    loadMerchantPrices()
    loadProductWeights()
  } catch (e: any) {
    showMessage(e.response?.data?.detail || e.message || '删除失败', 'error')
  } finally {
    deletingProductLoading.value = false
  }
}

// 价格记录相关
const priceRecords = ref<PriceRecord[]>([])
const loadingPrices = ref(false)
const pricePage = ref(1)
const pricePageSize = ref(10)
const priceTotal = ref(0)
const priceTotalPages = computed(() => Math.ceil(priceTotal.value / pricePageSize.value))

// 图表专用数据源（按时间区间累积加载，独立于下方分页列表的 priceRecords）
const chartPriceRecords = ref<PriceRecord[]>([])
// 已请求覆盖到的最早日期：undefined=未请求, null=已全量, Date=已覆盖到该日
const chartEarliestDate = ref<Date | null | undefined>(undefined)
const loadingChartPrices = ref(false)

// 营养数据
const nutritionData = ref<any>(null)
const nutritionPendingProposal = ref<{ id: number; action: string; payload: Record<string, any> } | null>(null)
const loadingNutrition = ref(false)

// 关联菜谱
const recipes = ref<Recipe[]>([])
const recipePage = ref(1)
const recipePageSize = ref(10)
const recipeTotal = ref(0)
const recipeTotalPages = computed(() => Math.ceil(recipeTotal.value / recipePageSize.value))

// 单位列表
const units = ref<Unit[]>([])
const categories = ref<{ id: number; name: string; display_name: string }[]>([])

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
const showAddRelationDialog = ref(false)
const showEditRelationDialog = ref(false)
const showDeleteRelationDialog = ref(false)
const showAddPriceDialog = ref(false)
const showEditPriceDialog = ref(false)
const editingPriceRecord = ref<PriceRecord | null>(null)
const savingPrice = ref(false)
const editPriceForm = ref({
  price: 0,
  quantity: 1,
  unit: priceUnitName.value,
  merchant_id: null as number | null
})
const showMergeDialog = ref(false)
const showMergeConfirmDialog = ref(false)
const showDeleteDialog = ref(false)
const saving = ref(false)
const savingRelation = ref(false)
const deletingRelation = ref(false)
const merging = ref(false)
const deleting = ref(false)

// 表单数据
// 基本信息编辑
const editingBasicInfo = ref(false)
const basicEditForm = ref({
  name: '',
  category_id: null as number | null,
  aliases: [] as string[],
  serving_weight: null as number | null,
  serving_weight_unit_id: null as number | null,
  making_recipe_id: null as number | null,
})

// 制作菜谱搜索（半成品自制来源）
const recipeOptions = ref<{ id: number; name: string }[]>([])
const recipeSearching = ref(false)
let recipeSearchTimer: any = null

const onRecipeSearch = (q: string) => {
  if (recipeSearchTimer) clearTimeout(recipeSearchTimer)
  if (!q || !q.trim()) return
  recipeSearchTimer = setTimeout(async () => {
    recipeSearching.value = true
    try {
      const res = await api.get('/recipes', { params: { search: q.trim(), page: 1, per_page: 20 } })
      const items = (res as any)?.items || (res as any)?.data || []
      recipeOptions.value = items.map((r: any) => ({ id: r.id, name: r.name }))
    } catch (e) {
      console.error('搜索菜谱失败', e)
    } finally {
      recipeSearching.value = false
    }
  }, 300)
}

// 营养编辑
const editingNutrition = ref(false)
const savingNutrition = ref(false)

// 营养素定义：key 匹配后端 all_nutrients 的英文键名（能量行跟随用户能量单位偏好）
// （useUserUnits 解构前置，供 editPriceForm / 价格显示等引用）
const NUTRIENT_DEFINITIONS = computed(() => buildNutrientDefinitions(energyUnit.value))

// 营养素同义键映射：将别名 key 映射到标准 key，避免编辑时重复
const NUTRIENT_PARENT_MAP: Record<string, string> = {
  // energy 已是标准键名，无需同义映射
}

// IU ↔ 质量换算系数（1 IU = ? 质量单位）
const IU_TO_MASS: Record<string, { factor: number, unit: string }> = {
  'vitamin_a_rae': { factor: 0.3, unit: 'μg' },   // 1 IU = 0.3 μg RAE
  'vitamin_d': { factor: 0.025, unit: 'μg' },      // 1 IU = 0.025 μg
  'vitamin_e': { factor: 0.67, unit: 'mg' },        // 1 IU = 0.67 mg d-α-tocopherol
}

// 质量单位换算表（统一到 g）
const MASS_TO_GRAMS: Record<string, number> = {
  'g': 1,
  'mg': 0.001,
  'μg': 0.000001,
}

// 能量单位换算表
const ENERGY_FACTORS: Record<string, number> = {
  'kcal': 1,
  'kJ': 4.184,
}

// 查找营养素定义
const findNutrientDef = (key: string) => {
  const def = NUTRIENT_DEFINITIONS.value.find(n => n.key === key)
  if (def) return def
  return buildDynamicDef(key)
}

// 从 ENGLISH_TO_CHINESE_MAP 或 USDA all_nutrients 数据中动态构建营养素定义
const buildDynamicDef = (key: string) => {
  // 优先从 ENGLISH_TO_CHINESE_MAP 查找（覆盖 USDA 全部营养素）
  // 注意：直接使用 zhName 作为 label，不使用 NUTRITION_LABEL_MAP 映射，
  // 因为那是显示层（如"能量"→"热量"）的规范，编辑表单应与 NUTRIENT_DEFINITIONS 一致
  const zhName = ENGLISH_TO_CHINESE_MAP[key]
  if (zhName) {
    const label = zhName
    const isEnergy = key.startsWith('energy_') || key === 'energy'
    const isIUvitamin = /^vitamin_(a|d|e)/.test(key)
    const units = isEnergy ? ['kcal', 'kJ'] : isIUvitamin ? ['μg', 'mg', 'IU'] : ['g', 'mg', 'μg']
    const defaultUnit = isEnergy ? 'kcal' : isIUvitamin ? 'μg' : 'g'
    return { key, label, units, defaultUnit }
  }
  // 兜底：从 all_nutrients 数据动态构建
  const allNutrients = nutritionData.value?.nutrition?.all_nutrients
  if (!allNutrients) return undefined
  const data: any = allNutrients[key]
  if (!data || typeof data !== 'object') return undefined
  const rawUnit = (data.unit || 'g').toLowerCase()
  const label = key
  // 标准化单位名：USDA 数据可能用 "milligrams"、"grams" 等全称
  const isMassUnit = (u: string) => ['g', 'gram', 'grams', 'mg', 'milligram', 'milligrams', 'μg', 'mcg', 'ug', 'microgram', 'micrograms'].includes(u)
  const isEnergyUnit = (u: string) => ['kcal', 'kj', 'calorie', 'calories', 'kilocalorie', 'kilocalories', '千卡', '千焦'].includes(u)
  const units = isEnergyUnit(rawUnit) ? ['kcal', 'kJ'] : isMassUnit(rawUnit) ? ['g', 'mg', 'μg'] : [rawUnit]
  return { key, label, units, defaultUnit: rawUnit }
}

// 完整营养素列表：静态定义 + ENGLISH_TO_CHINESE_MAP 全部 USDA 营养素 + 数据中额外营养素
const getAllNutrientDefs = () => {
  const defs = [...NUTRIENT_DEFINITIONS.value]
  const existingKeys = new Set(NUTRIENT_DEFINITIONS.value.map(d => d.key))
  // 从 ENGLISH_TO_CHINESE_MAP 添加
  for (const key of Object.keys(ENGLISH_TO_CHINESE_MAP)) {
    if (existingKeys.has(key)) continue
    // 跳过同义别名（NUTRIENT_PARENT_MAP 将别名映射到标准 key）
    const parentKey = NUTRIENT_PARENT_MAP[key]
    if (parentKey && existingKeys.has(parentKey)) continue
    const def = buildDynamicDef(key)
    if (def) { defs.push(def); existingKeys.add(key) }
  }
  // 从当前营养数据中补充未覆盖的 key（如稀有营养素）
  const allNutrients = nutritionData.value?.nutrition?.all_nutrients
  if (allNutrients) {
    for (const key of Object.keys(allNutrients)) {
      if (existingKeys.has(key)) continue
      // 跳过与已有定义同义的 key（如 all_nutrients 中的中文 key 对应已存在的英文 key）
      const data = allNutrients[key]
      const canonicalKey = data?.original_key || data?.key
      if (canonicalKey && canonicalKey !== key && existingKeys.has(canonicalKey)) continue
      const def = buildDynamicDef(key)
      if (def) { defs.push(def); existingKeys.add(key) }
    }
  }
  return defs
}

// 获取营养素的可用单位列表
const getUnitsForKey = (key: string): string[] => {
  const def = findNutrientDef(key)
  return def ? def.units : ['g', 'mg', 'μg']
}

// 单位换算：返回换算后的值
const convertUnit = (value: number, fromUnit: string, toUnit: string, nutrientKey: string): number => {
  if (fromUnit === toUnit || value === 0) return value

  // 能量换算
  if (ENERGY_FACTORS[fromUnit] && ENERGY_FACTORS[toUnit]) {
    const inKcal = value * ENERGY_FACTORS[fromUnit]
    return inKcal / ENERGY_FACTORS[toUnit]
  }

  // 质量单位换算
  if (MASS_TO_GRAMS[fromUnit] && MASS_TO_GRAMS[toUnit]) {
    const inGrams = value * MASS_TO_GRAMS[fromUnit]
    return inGrams / MASS_TO_GRAMS[toUnit]
  }

  // IU ↔ 质量
  const iuInfo = IU_TO_MASS[nutrientKey]
  if (iuInfo) {
    if (fromUnit === 'IU' && MASS_TO_GRAMS[toUnit]) {
      // IU → 质量: value * factor 得到 iuInfo.unit, 再转到目标单位
      const massInBase = value * iuInfo.factor  // 质量值，单位是 iuInfo.unit
      const inGrams = massInBase * (MASS_TO_GRAMS[iuInfo.unit] || 1)
      return inGrams / (MASS_TO_GRAMS[toUnit] || 1)
    }
    if (toUnit === 'IU' && MASS_TO_GRAMS[fromUnit]) {
      // 质量 → IU
      const inGrams = value * (MASS_TO_GRAMS[fromUnit] || 1)
      const inBaseUnit = inGrams / (MASS_TO_GRAMS[iuInfo.unit] || 1)
      return inBaseUnit / iuInfo.factor
    }
  }

  return value // 无法换算，原值返回
}

// 营养编辑条目
interface NutritionEditItem {
  key: string           // 英文 key（对应后端 all_nutrients）
  name: string          // 中文显示名
  value: number | null  // 数值
  unit: string          // 当前单位
  units: string[]       // 可选单位列表
}
const nutritionEditItems = ref<NutritionEditItem[]>([])

// 行内名称下拉可选列表（过滤已选的，保留当前行自身的 key）
const getNutrientOptionsForRow = (currentKey: string) => {
  const usedKeys = new Set(
    nutritionEditItems.value
      .filter(i => i.key !== currentKey)
      .map(i => i.key)
  )
  return getAllNutrientDefs().filter(n => !usedKeys.has(n.key))
}


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
    color: 'info',
    reverse: false
  },
  {
    value: 'contained_by',
    label: '被包含',
    description: '当前原料属于目标原料（子→父）',
    icon: 'mdi-arrow-up',
    color: 'info',
    reverse: true
  },
  {
    value: 'fallback',
    label: '回退',
    description: '当前原料可回退到目标原料',
    icon: 'mdi-arrow-left',
    color: 'warning',
    reverse: false
  },
  {
    value: 'fallback_by',
    label: '被回退',
    description: '目标原料可回退到当前原料',
    icon: 'mdi-arrow-right',
    color: 'warning',
    reverse: true
  },
  {
    value: 'substitutable',
    label: '可替代',
    description: '两个原料可以相互替代',
    icon: 'mdi-swap-horizontal',
    color: 'success',
    reverse: false
  }
]

// 合并相关
const mergeTargetId = ref<number | null>(null)
const mergeTargets = ref<Ingredient[]>([])
const loadingMergeTargets = ref(false)


// 选中的合并目标对象（用于显示名称）
const selectedMergeTarget = ref<Ingredient | null>(null)

// 自定义单位相关
import type { EntityUnitOverride, EntityDensity, UnmappedUnitItem } from '@/types'
const entityUnits = ref<EntityUnitOverride[]>([])
const unmappedUnits = ref<UnmappedUnitItem[]>([])
const entityDensity = ref<EntityDensity | null>(null)
const loadingUnits = ref(false)
const showUnitDialog = ref(false)
const showDensityDialog = ref(false)
const savingUnit = ref(false)
const savingDensity = ref(false)
const unitForm = ref<{
  id: number | null
  unit_name: string
  conversion_factor: number | null
  weight_per_unit: number | null
  is_default: boolean
}>({
  id: null,
  unit_name: '',
  conversion_factor: null,
  weight_per_unit: null,
  is_default: false
})
const densityForm = ref<{
  id: number | null
  density: number | null
  temperature: number | null
  source: string | null
}>({
  id: null,
  density: null,
  temperature: null,
  source: null
})
const densityInputUnit = ref<string>('g/cm3') // 输入单位，默认 g/cm³
const densityDisplayUnit = ref<string>('g/cm3') // 显示单位，默认 g/cm³

const densityInputUnitLabel = computed(() => densityInputUnit.value === 'g/cm3' ? 'g/cm³' : 'kg/m³')

// 显示密度值（根据选中的显示单位换算）
const displayDensityValue = computed(() => {
  if (!displayDensity.value || displayDensity.value.density === null || displayDensity.value.density === undefined) return ''
  const val = Number(displayDensity.value.density)
  if (isNaN(val)) return ''
  if (densityDisplayUnit.value === 'g/cm3') {
    return (val / 1000).toLocaleString('zh-CN', { maximumFractionDigits: 4 })
  }
  return val.toLocaleString('zh-CN', { maximumFractionDigits: 1 })
})

// 切换显示单位
const toggleDisplayDensityUnit = () => {
  densityDisplayUnit.value = densityDisplayUnit.value === 'g/cm3' ? 'kg/m3' : 'g/cm3'
}

// 输入单位切换时自动转换当前值
watch(densityInputUnit, (newUnit, oldUnit) => {
  if (densityForm.value.density !== null && densityForm.value.density !== undefined && oldUnit && newUnit !== oldUnit) {
    if (oldUnit === 'g/cm3' && newUnit === 'kg/m3') {
      densityForm.value.density = densityForm.value.density * 1000
    } else if (oldUnit === 'kg/m3' && newUnit === 'g/cm3') {
      densityForm.value.density = densityForm.value.density / 1000
    }
  }
})

// 加载自定义单位
const loadEntityUnits = async () => {
  loadingUnits.value = true
  try {
    const response = await api.get(`/entities/ingredient/${ingredientId.value}/units`)
    entityUnits.value = response.items || response || []
  } catch (e) {
    console.error('加载自定义单位失败', e)
    entityUnits.value = []
  } finally {
    loadingUnits.value = false
  }
}

// 加载密度（API 返回列表，取第一项）
const loadDensity = async () => {
  try {
    const response = await api.get(`/entities/ingredient/${ingredientId.value}/density`)
    if (Array.isArray(response) && response.length > 0) {
      const d = response[0]
      // 后端 density 是 Decimal，JSON 序列化为 string，转 number 供显示/换算
      if (d && d.density !== null && d.density !== undefined) {
        d.density = Number(d.density)
      }
      entityDensity.value = d
    } else {
      entityDensity.value = null
    }
  } catch (e) {
    entityDensity.value = null
  }
}

// 打开单位对话框（支持传入 EntityUnitOverride 或 unit_name 字符串）
const openUnitDialog = (unit?: EntityUnitOverride | string) => {
  if (typeof unit === 'string') {
    unitForm.value = {
      id: null,
      unit_name: unit,
      conversion_factor: null,
      weight_per_unit: 100,
      is_default: false
    }
  } else if (unit) {
    unitForm.value = {
      id: unit.id,
      unit_name: unit.unit_name,
      conversion_factor: unit.conversion_factor,
      weight_per_unit: unit.weight_per_unit,
      is_default: unit.is_default
    }
  } else {
    unitForm.value = {
      id: null,
      unit_name: '',
      conversion_factor: null,
      weight_per_unit: null,
      is_default: false
    }
  }
  showUnitDialog.value = true
}

// 加载未映射单位（来自菜谱的 count 类型单位，尚未配置 Override）
const loadUnmappedUnits = async () => {
  try {
    const response = await api.get(`/entities/ingredient/${ingredientId.value}/units/unmapped-units`)
    unmappedUnits.value = response || []
  } catch (e) {
    unmappedUnits.value = []
  }
}

// 快速添加未映射单位
const quickAddUnmappedUnit = (item: UnmappedUnitItem) => {
  openUnitDialog(item.unit_name)
}

// 保存单位
const saveEntityUnit = async () => {
  if (!unitForm.value.unit_name.trim()) {
    showMessage('请输入单位名称', 'error')
    return
  }
  savingUnit.value = true
  try {
    const payload = {
      unit_name: unitForm.value.unit_name,
      conversion_factor: unitForm.value.conversion_factor,
      weight_per_unit: unitForm.value.weight_per_unit,
      is_default: unitForm.value.is_default
    }
    if (unitForm.value.id) {
      await api.put(`/entities/ingredient/${ingredientId.value}/units/${unitForm.value.id}`, payload)
    } else {
      await api.post(`/entities/ingredient/${ingredientId.value}/units`, payload)
    }
    if (userStore.user?.is_admin) {
      showMessage('保存成功', 'success')
      showUnitDialog.value = false
      await loadEntityUnits()
      await loadUnmappedUnits()
    } else {
      showMessage('已提交，待管理员审核', 'info')
      showUnitDialog.value = false
    }
  } catch (e: any) {
    showMessage(e.response?.data?.detail || e.message || '保存失败', 'error')
  } finally {
    savingUnit.value = false
  }
}

// 删除单位
const deleteEntityUnit = async (unitId: number) => {
  if (!(await ask({ text: '确定删除此自定义单位？', color: 'error', confirmText: '删除' }))) return
  try {
    await api.delete(`/entities/ingredient/${ingredientId.value}/units/${unitId}`)
    if (userStore.user?.is_admin) {
      showMessage('删除成功', 'success')
      await loadEntityUnits()
      await loadUnmappedUnits()
    } else {
      showMessage('删除提议已提交，待管理员审核', 'info')
    }
  } catch (e: any) {
    showMessage(e.response?.data?.detail || e.message || '删除失败', 'error')
  }
}

// 打开密度对话框
const openDensityDialog = (density?: EntityDensity) => {
  if (density) {
    densityForm.value = {
      id: density.id,
      // 按当前输入单位显示（后端存储为 kg/m³）；Number() 兜底防 density 为 string
      density: densityInputUnit.value === 'g/cm3' ? Number(density.density) / 1000 : Number(density.density),
      temperature: density.temperature,
      source: density.source
    }
  } else {
    densityForm.value = {
      id: null,
      density: null,
      temperature: null,
      source: null
    }
  }
  showDensityDialog.value = true
}

// 保存密度
const saveDensity = async () => {
  if (!densityForm.value.density) {
    showMessage('请输入密度值', 'error')
    return
  }
  savingDensity.value = true
  try {
    // 转换为 kg/m³ 后存储
    let density = densityForm.value.density
    if (densityInputUnit.value === 'g/cm3') {
      density = density * 1000
    }
    await api.post(`/entities/ingredient/${ingredientId.value}/density`, {
      density: density,
      temperature: densityForm.value.temperature,
      source: densityForm.value.source
    })
    if (userStore.user?.is_admin) {
      showMessage('保存成功', 'success')
      showDensityDialog.value = false
      await loadDensity()
    } else {
      showMessage('已提交，待管理员审核', 'info')
      showDensityDialog.value = false
    }
  } catch (e: any) {
    showMessage(e.response?.data?.detail || e.message || '保存失败', 'error')
  } finally {
    savingDensity.value = false
  }
}

// 删除密度
const deleteDensity = async (densityId: number) => {
  if (!(await ask({ text: '确定删除此密度数据？', color: 'error', confirmText: '删除' }))) return
  try {
    await api.delete(`/entities/ingredient/${ingredientId.value}/density/${densityId}`)
    if (userStore.user?.is_admin) {
      showMessage('删除成功', 'success')
      entityDensity.value = null
    } else {
      showMessage('删除提议已提交，待管理员审核', 'info')
    }
  } catch (e: any) {
    showMessage(e.response?.data?.detail || e.message || '删除失败', 'error')
  }
}

// 快速记录价格
const showQuickPriceDialog = ref(false)
const quickPriceProduct = ref<{ id: number; name: string } | null>(null)
const quickPriceProducts = ref<{ id: number; name: string }[]>([])

const openQuickPriceDialog = async () => {
  if (!ingredient.value) return
  try {
    const response = await api.get('/products/entity', {
      params: { ingredient_id: ingredientId.value, limit: 50 }
    })
    const products: { id: number; name: string }[] = response.items || []
    if (products.length === 0) {
      snackbar.value = { show: true, message: '该原料暂无关联商品，请先添加商品', color: 'warning' }
      return
    }
    const matched = products.find(p => p.name === ingredient.value!.name) || products[0]
    quickPriceProduct.value = matched
    quickPriceProducts.value = products
    showQuickPriceDialog.value = true
  } catch (e: any) {
    snackbar.value = { show: true, message: '加载商品失败', color: 'error' }
  }
}

const onQuickPriceSaved = () => {
  loadData()
}

// 提示消息
const snackbar = ref({
  show: false,
  message: '',
  color: 'success'
})

// 营养素配置（默认显示的营养素）——能量单位跟随用户偏好
const coreNutritionItems = computed(() => [
  { key: '能量', label: '能量', unit: energyUnit.value },
  { key: '蛋白质', label: '蛋白质', unit: 'g' },
  { key: '脂肪', label: '脂肪', unit: 'g' },
  { key: '碳水化合物', label: '碳水化合物', unit: 'g' },
  { key: '钠', label: '钠', unit: 'mg' }
])

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
  const coreItems = coreNutritionItems.value
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
  const coreKeys = new Set(coreNutritionItems.value.map(ci => ci.key))

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
  const coreKeys = new Set(coreNutritionItems.value.map(ci => ci.key))

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

// 聚合价格数据用于图表（按日期分组，转换到原料的默认单位）
const chartData = computed(() => {
  if (!chartPriceRecords.value || chartPriceRecords.value.length === 0) return []

  // 图表按用户质量偏好单位归一化（与 chartUnit 对齐；unitFactors 表覆盖 mass/volume）
  // ⚠️ 用单位缩写（abbr）作 key 查 unitFactors，不能用 name——
  // 表里是 'kg':1000 而非 '千克':1000，用 name 会命中不到→toFactor=1→单价少算 1000 倍
  const defaultUnit = massUnit.value?.abbreviation ?? '斤'
  const dailyAll = new Map<string, number[]>()
  const dailyByProduct = new Map<string, Map<number, number[]>>()

  for (const record of chartPriceRecords.value) {
    if (!record.recorded_at) continue
    const date = new Date(record.recorded_at)
    if (isNaN(date.getTime())) continue
    const dateKey = date.toISOString().split('T')[0]

    // 计算原始单价
    const quantity = parseFloat(String(record.original_quantity)) || 1
    const price = parseFloat(String(record.price)) || 0
    const originalUnitPrice = price / quantity

    // 转换到原料的默认单位
    let convertedUnitPrice = originalUnitPrice
    const originalUnit = record.original_unit

    // 如果原始单位和默认单位不同，进行转换
    if (originalUnit && originalUnit !== defaultUnit) {
      // 常用单位转换系数（相对于g）
      const unitFactors: Record<string, number> = {
        'g': 1,
        'kg': 1000,
        '斤': 500,
        '两': 50,
        'mg': 0.001,
        'oz': 28.3495,
        'lb': 453.592,
        'mL': 1,
        'ml': 1,
        'L': 1000,
      }

      // 计数单位的默认回退：1个=100g
      // 如果有 entity_unit_overrides，优先使用实际重量
      let fromFactor = unitFactors[originalUnit]
      if (fromFactor === undefined) {
        // 检查是否有该原料/商品的自定义单位
        const entityUnit = entityUnits.value?.find(
          (eu: any) => eu.unit_name === originalUnit
        )
        if (entityUnit && entityUnit.weight_per_unit && entityUnit.weight_unit_id) {
          // weight_per_unit 是以 weight_unit 为单位，通常是 g
          const conversionCount = entityUnit.conversion_factor || 1
          fromFactor = (entityUnit.weight_per_unit * conversionCount) // 每1个原始单位 = ?g
        } else {
          // 默认：1个=100g
          fromFactor = 100
        }
      }

      const toFactor = unitFactors[defaultUnit] || 1

      // 单价转换公式：新单价 = 原单价 × (toFactor / fromFactor)
      convertedUnitPrice = originalUnitPrice * (toFactor / fromFactor)
    }

    if (!dailyAll.has(dateKey)) {
      dailyAll.set(dateKey, [])
    }
    dailyAll.get(dateKey)!.push(convertedUnitPrice)

    // 按商品分组（仅用于加权 avg；权重只作用于平均值）
    const pid = (record as any).product_id
    if (pid != null) {
      if (!dailyByProduct.has(dateKey)) dailyByProduct.set(dateKey, new Map())
      const pm = dailyByProduct.get(dateKey)!
      if (!pm.has(pid)) pm.set(pid, [])
      pm.get(pid)!.push(convertedUnitPrice)
    }
  }

  // 计算每日统计值：min/max/count 用记录级（不动），avg 按商品权重加权
  return Array.from(dailyAll.entries())
    .map(([date, prices]) => {
      const sorted = [...prices].sort((a, b) => a - b)
      // 加权 avg：每商品当日均价 × 生效权重（覆盖>全局>50），权重 0 排除
      const pm = dailyByProduct.get(date)
      let avg: number
      if (pm && pm.size > 0) {
        let num = 0, den = 0
        for (const [pid, ups] of pm) {
          const w = productWeights.value.get(pid) ?? 50
          if (w <= 0 || !ups.length) continue
          num += (ups.reduce((a, b) => a + b, 0) / ups.length) * w
          den += w
        }
        avg = den > 0 ? num / den : (prices.reduce((a, b) => a + b, 0) / prices.length)
      } else {
        avg = prices.reduce((a, b) => a + b, 0) / prices.length
      }
      return {
        date,
        min: sorted[0] || 0,
        max: sorted[sorted.length - 1] || 0,
        avg,
        count: prices.length
      }
    })
    .sort((a, b) => a.date.localeCompare(b.date))
})

// 最新趋势数据点（用于最新价格卡片右侧展示）
const latestChartTrend = computed(() => {
  const data = chartData.value
  if (!data || data.length === 0) return null
  return data[data.length - 1]
})

// 图表使用用户偏好的质量单位（默认斤）
const chartUnit = computed(() => massUnitName.value)

// 加载数据
const loadData = async () => {
  loading.value = true
  error.value = null

  // 重置图表累积池（导航到其他原料时避免残留旧数据）
  chartPriceRecords.value = []
  chartEarliestDate.value = undefined

  try {
    // 只加载原料基本信息（名称、别名、默认单位等）
    const response = await api.get(`/nutrition/ingredients/${ingredientId.value}`)
    ingredient.value = response
    pendingProposal.value = response.pending_proposal || null
    // 加载当前用户所有 pending 提议（用于单位/密度区域按 payload 关联显示横幅）
    loadPendingProposals()
    setDetailTitle(response.name, '原料', '原料详情')
    // 基本数据到位，立即渲染页面
    loading.value = false

    // 后台分别加载其他数据，互不影响
    loadLatestPrice()
    loadMerchantPrices()
    loadProducts()
    loadProductWeights()
    loadPriceRecords()
    loadChartPriceRecords(daysAgo(30))  // 图表默认加载近 30 天（月）
    loadNutritionData()
    loadRecipes()
    loadHierarchy()
    loadEntityUnits()
    loadDensity()
    loadUnmappedUnits()
  } catch (e: any) {
    console.error('加载原料失败', e)
    error.value = getErrorMessage(e, '加载失败')
    loading.value = false
  }
}

// 加载最新价格
const loadLatestPrice = async () => {
  loadingLatestPrice.value = true
  try {
    const response = await api.get(`/nutrition/ingredients/${ingredientId.value}/latest-price`)
    latestPrice.value = response.average_price
    latestPriceDate.value = response.latest_date
    latestPriceParticipants.value = response.participants || []
    latestPriceExcluded.value = response.excluded || []
  } catch (e) {
    latestPrice.value = null
    latestPriceDate.value = null
    latestPriceParticipants.value = []
    latestPriceExcluded.value = []
  } finally {
    loadingLatestPrice.value = false
  }
}

// 加载原料下各商品生效权重（覆盖>全局>50），供价格趋势加权 avg
const loadProductWeights = async () => {
  if (!ingredientId.value) return
  try {
    const res = await api.get(`/nutrition/ingredients/${ingredientId.value}/product-weights`)
    productWeights.value = new Map(
      (res.items || []).map((p: any) => [p.product_id, p.effective_weight as number])
    )
  } catch {
    productWeights.value = new Map()
  }
}

// 加载按商家分组的最新价格
const loadMerchantPrices = async () => {
  loadingMerchantPrices.value = true
  try {
    const response = await api.get(`/nutrition/ingredients/${ingredientId.value}/latest-price-by-merchant`)
    merchantPrices.value = response.prices || []
    merchantPriceUnit.value = response.unit || null
  } catch (e) {
    merchantPrices.value = []
    merchantPriceUnit.value = null
  } finally {
    loadingMerchantPrices.value = false
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
    // 懒加载每个商品的最新价格和迷你图数据
    products.value.forEach(p => loadProductPrice(p))
  } catch (e) {
    products.value = []
  }
}

// 懒加载单个商品的最新价格和迷你图数据
const loadProductPrice = async (product: Product) => {
  const pid = product.id
  // 初始化 / 跳过已加载或加载中的
  const existing = productPrices.value[pid]
  if (existing) {
    if (existing.loading) return
    if (existing.latestPrice !== null) return
  }
  productPrices.value[pid] = {
    loading: true,
    latestPrice: null,
    latestPriceUnit: null,
    latestPriceDate: null,
    sparklineData: [],
  }
  try {
    // 获取最新价格
    const detail: any = await api.get(`/products/entity/${pid}`)
    const info = productPrices.value[pid]
    if (!info) return
    info.latestPrice = detail.latest_price ?? null
    info.latestPriceUnit = detail.latest_price_unit ?? null
    info.latestPriceDate = detail.latest_price_date ?? null

    // 获取近期价格记录用于迷你图
    const records: any = await api.get('/products', {
      params: { product_id: pid, limit: 20 },
    })
    const items: any[] = records.items || []
    // 按日期排序，算单价
    const pricePoints = items
      .filter((r: any) => r.price && Number(r.original_quantity) > 0)
      .sort((a: any, b: any) => (a.recorded_at || '').localeCompare(b.recorded_at || ''))
      .map((r: any) => {
        const qty = Number(r.original_quantity) || 1
        return Number(r.price) / qty
      })
    info.sparklineData = pricePoints
  } catch (e) {
    console.error(`加载商品 ${product.name} 价格数据失败`, e)
  } finally {
    if (productPrices.value[pid]) {
      productPrices.value[pid].loading = false
    }
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
        limit: pricePageSize.value
        // 不传递 target_unit，显示原始价格记录
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

// 今天往前 n 天的日期
const daysAgo = (n: number): Date => {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d
}

// 加载图表价格记录（按时间区间累积）
// startDate 为空表示「全部」；「全部」请求放宽超时到 30s，规避前端 10s 上限
const loadChartPriceRecords = async (startDate?: Date) => {
  // 判断是否需要发请求（已覆盖则跳过）
  let needFetch = false
  if (startDate) {
    if (chartEarliestDate.value === undefined) {
      needFetch = true
    } else if (chartEarliestDate.value === null) {
      needFetch = false  // 已全量，已覆盖
    } else {
      needFetch = startDate < chartEarliestDate.value
    }
  } else {
    needFetch = chartEarliestDate.value !== null
  }
  if (!needFetch) return

  loadingChartPrices.value = true
  try {
    const params: Record<string, any> = {
      ingredient_id: ingredientId.value,
      limit: 1000,
    }
    if (startDate) {
      params.start_date = startDate.toISOString().split('T')[0]
    }
    const response = await api.get('/products', {
      params,
      timeout: startDate ? undefined : LONG_REQUEST_TIMEOUT,  // 「全部」用长超时
    })
    const items = response.items || []
    // 按 id 去重合并
    const existing = new Set(chartPriceRecords.value.map(r => r.id))
    for (const r of items) {
      if (!existing.has(r.id)) {
        chartPriceRecords.value.push(r)
      }
    }
    // 更新已覆盖范围（取更早）
    if (startDate) {
      chartEarliestDate.value = (chartEarliestDate.value instanceof Date && chartEarliestDate.value < startDate)
        ? chartEarliestDate.value
        : startDate
    } else {
      chartEarliestDate.value = null
    }
  } catch (e) {
    console.error('加载图表价格记录失败', e)
  } finally {
    loadingChartPrices.value = false
  }
}

// 当前图表区间（用于编辑/删除后刷新）
const currentChartFilter = ref<'week' | 'month' | 'quarter' | 'year' | 'all'>('month')

// 图表区间切换：按时间区间发起请求
const onPriceTrendFilterChange = (filter: 'week' | 'month' | 'quarter' | 'year' | 'all') => {
  currentChartFilter.value = filter
  const startDateMap: Record<string, Date | undefined> = {
    week: daysAgo(7),
    month: daysAgo(30),
    quarter: daysAgo(90),
    year: daysAgo(365),
    all: undefined,
  }
  loadChartPriceRecords(startDateMap[filter])
}

// 重置图表缓存并重新加载当前区间（用于价格记录变更后刷新）
const refreshChart = () => {
  chartPriceRecords.value = []
  chartEarliestDate.value = undefined
  const startDateMap: Record<string, Date | undefined> = {
    week: daysAgo(7),
    month: daysAgo(30),
    quarter: daysAgo(90),
    year: daysAgo(365),
    all: undefined,
  }
  loadChartPriceRecords(startDateMap[currentChartFilter.value])
}

// 加载营养数据
const loadNutritionData = async () => {
  loadingNutrition.value = true
  try {
    const response = await api.get(`/nutrition/ingredients/${ingredientId.value}/nutrition`)
    nutritionData.value = response
    nutritionPendingProposal.value = response.pending_proposal || null
  } catch (e) {
    console.error('加载营养失败', e)
    nutritionData.value = null
    nutritionPendingProposal.value = null
  } finally {
    loadingNutrition.value = false
  }
}

// 加载关联菜谱
const loadRecipes = async () => {
  try {
    const skip = (recipePage.value - 1) * recipePageSize.value
    const response = await api.get(`/nutrition/ingredients/${ingredientId.value}/recipes`, {
      params: { skip, limit: recipePageSize.value }
    })
    recipes.value = response.items || []
    recipeTotal.value = response.total || 0
  } catch (e) {
    recipes.value = []
  }
}

// 加载层级关系
const loadHierarchy = async () => {
  loadingHierarchy.value = true
  try {
    const response = await api.get(`/ingredients/${ingredientId.value}/hierarchy`, {
      params: { depth: 2 }
    })
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

// 反向关系类型映射到实际数据库类型
const reverseTypeMapping: Record<string, string> = {
  contained_by: 'contains',
  fallback_by: 'fallback'
}

// 添加层级关系
const addRelation = async () => {
  if (!relationForm.value.target_ingredient_id) return

  savingRelation.value = true
  try {
    const selectedType = relationForm.value.relation_type
    const option = relationTypeOptions.find(o => o.value === selectedType)
    const isReverse = option?.reverse ?? false

    // 将虚拟反向类型映射回实际数据库类型
    const actualType = reverseTypeMapping[selectedType] || selectedType

    // 反向关系时交换 parent_id 和 child_id
    const parentId = isReverse ? relationForm.value.target_ingredient_id : ingredientId.value
    const childId = isReverse ? ingredientId.value : relationForm.value.target_ingredient_id

    await api.post('/ingredients/hierarchy', {
      parent_id: parentId,
      child_id: childId,
      relation_type: actualType,
      strength: relationForm.value.strength
    })
    if (userStore.user?.is_admin) {
      showMessage('关系添加成功', 'success')
      showAddRelationDialog.value = false
      await loadHierarchy()
    } else {
      showMessage('已提交，待管理员审核', 'info')
      showAddRelationDialog.value = false
    }
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
    strength: Math.round(relation.strength)
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
    if (userStore.user?.is_admin) {
      showMessage('关系更新成功', 'success')
      showEditRelationDialog.value = false
      await loadHierarchy()
    } else {
      showMessage('已提交，待管理员审核', 'info')
      showEditRelationDialog.value = false
    }
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
    if (userStore.user?.is_admin) {
      showMessage('关系删除成功', 'success')
      showDeleteRelationDialog.value = false
      await loadHierarchy()
    } else {
      showMessage('删除提议已提交，待管理员审核', 'info')
      showDeleteRelationDialog.value = false
    }
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
      case 'contained_by':
        return `${currentName} 属于 ${targetName}`
      case 'fallback':
        return `${currentName} 可回退到 ${targetName}`
      case 'fallback_by':
        return `${targetName} 可回退到 ${currentName}`
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
      case 'contained_by':
        return `${targetName} 包含 ${currentName}`
      case 'fallback':
        return `${currentName} 可回退到 ${targetName}`
      case 'fallback_by':
        return `${targetName} 可回退到 ${currentName}`
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
  const currentName = ingredient.value?.name || '当前原料'

  // child_relations: 当前原料是父，目标原料是子
  if (direction === 'child') {
    switch (relationType) {
      case 'contains':
        return `即 ${targetName} 是 ${currentName} 的一部分`
      case 'contained_by':
        return `即 ${currentName} 是 ${targetName} 的一部分`
      case 'fallback':
        return `即当无法获取 ${currentName} 时，可使用 ${targetName} 代替`
      case 'fallback_by':
        return `即当无法获取 ${targetName} 时，可使用 ${currentName} 代替`
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
        return `即 ${currentName} 是 ${targetName} 的一部分`
      case 'contained_by':
        return `即 ${targetName} 是 ${currentName} 的一部分`
      case 'fallback':
        return `即当无法获取 ${currentName} 时，可使用 ${targetName} 代替`
      case 'fallback_by':
        return `即当无法获取 ${targetName} 时，可使用 ${currentName} 代替`
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

const loadCategories = async () => {
  try {
    const response = await api.get('/ingredients/categories')
    categories.value = response || []
  } catch (e) {
    categories.value = []
  }
}

// === 基本信息内联编辑 ===
const startEditBasicInfo = () => {
  if (!ingredient.value) return
  basicEditForm.value = {
    name: ingredient.value.name || '',
    category_id: ingredient.value.category_id ?? null,
    aliases: [...(ingredient.value.aliases || [])],
    serving_weight: ingredient.value.serving_weight ?? null,
    serving_weight_unit_id: ingredient.value.serving_weight_unit_id ?? null,
    making_recipe_id: ingredient.value.making_recipe_id ?? null,
  }
  // 预填当前制作菜谱到选项
  if (ingredient.value.making_recipe_id) {
    recipeOptions.value = [{
      id: ingredient.value.making_recipe_id,
      name: ingredient.value.making_recipe_name || `菜谱#${ingredient.value.making_recipe_id}`,
    }]
  }
  editingBasicInfo.value = true
}

const cancelEditBasicInfo = () => {
  editingBasicInfo.value = false
}

const saveBasicInfo = async () => {
  if (!basicEditForm.value.name.trim()) {
    showMessage('原料名称不能为空', 'error')
    return
  }
  saving.value = true
  try {
    const payload = {
      name: basicEditForm.value.name,
      category_id: basicEditForm.value.category_id,
      aliases: basicEditForm.value.aliases,
      serving_weight: basicEditForm.value.serving_weight,
      serving_weight_unit_id: basicEditForm.value.serving_weight_unit_id,
    }
    await api.put(`/ingredients/${ingredientId.value}`, payload)
    // 处理制作菜谱关系变更（设置/清除某菜谱的 result_ingredient_id）
    const oldRecipeId = ingredient.value.making_recipe_id ?? null
    const newRecipeId = basicEditForm.value.making_recipe_id ?? null
    if (oldRecipeId !== newRecipeId) {
      // 清除旧制作菜谱的成品绑定
      if (oldRecipeId) {
        await api.put(`/recipes/${oldRecipeId}`, { result_ingredient_id: null })
      }
      // 设置新制作菜谱的成品绑定
      if (newRecipeId) {
        await api.put(`/recipes/${newRecipeId}`, { result_ingredient_id: ingredientId.value })
      }
    }
    if (userStore.user?.is_admin) {
      // 重新拉取原料详情（含新的 making_recipe_* / serving_weight 信息）
      const fresh = await api.get(`/ingredients/${ingredientId.value}`)
      ingredient.value = fresh
      // 刷新价格数据（默认单位可能影响价格显示）
      await loadLatestPrice()
      await loadPriceRecords()
      editingBasicInfo.value = false
      showMessage('基本信息已保存', 'success')
    } else {
      editingBasicInfo.value = false
      showMessage('已提交，待管理员审核', 'info')
      // 重新加载详情，刷新 pending_proposal 以显示草稿覆盖（横幅+字段覆盖）
      await loadData()
    }
  } catch (e: any) {
    showMessage(e.response?.data?.detail || e.message || '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

// === 营养成分内联编辑 ===
const startEditNutrition = () => {
  const items: NutritionEditItem[] = []
  const allNutrients = nutritionData.value?.nutrition?.all_nutrients || {}
  const addedKeys = new Set<string>()

  // 遍历 all_nutrients 中所有已有数据的营养素
  for (const [key, data] of Object.entries(allNutrients)) {
    if (!data || typeof data !== 'object' || !('value' in data)) continue

    // 提取英文键：优先用 original_key（计算器转换时保留），其次是 data.key，最后才是遍历键
    let engKey = (data as any)?.original_key || (data as any)?.key || key
    // 将同义别名映射到标准 key（NUTRIENT_PARENT_MAP），避免显示为重复
    engKey = NUTRIENT_PARENT_MAP[engKey] || engKey
    if (addedKeys.has(engKey)) continue

    const def = findNutrientDef(engKey)
    const zhName = ENGLISH_TO_CHINESE_MAP[engKey] || key
    const label = NUTRITION_LABEL_MAP[zhName] || zhName

    items.push({
      key: engKey,
      name: def ? def.label : label,
      value: data.value ?? null,
      unit: data.unit || (def ? def.defaultUnit : 'g'),
      units: def ? def.units : ['g', 'mg', 'μg'],
    })
    addedKeys.add(engKey)
  }

  // 按核心顺序排序：NUTRIENT_DEFINITIONS 中排前面的优先
  const orderMap = new Map(NUTRIENT_DEFINITIONS.value.map((n, i) => [n.key, i]))
  items.sort((a, b) => {
    const oa = orderMap.get(a.key) ?? 999
    const ob = orderMap.get(b.key) ?? 999
    return oa - ob
  })

  // 再按展示模式的排序规则微调（中文键排序，同 displayNutritionItems）
  const chKey = (key: string) => ENGLISH_TO_CHINESE_MAP[key] || key
  items.sort((a, b) => {
    const ca = chKey(a.key)
    const cb = chKey(b.key)
    const ia = nutrientSortOrder.indexOf(ca)
    const ib = nutrientSortOrder.indexOf(cb)
    if (ia !== -1 && ib !== -1) return ia - ib
    if (ia !== -1) return -1
    if (ib !== -1) return 1
    return 0
  })

  nutritionEditItems.value = items
  editingNutrition.value = true
}

const cancelEditNutrition = () => {
  editingNutrition.value = false
  nutritionEditItems.value = []
}

const removeNutrientEditItem = (index: number) => {
  nutritionEditItems.value.splice(index, 1)
}

// 行内营养素下拉改变
const onNutrientKeyChange = (index: number, newKey: string) => {
  if (!newKey) return
  // 检查是否与其他行重复（涵盖中英文 key 变体）
  const variants = [newKey]
  if (ENGLISH_TO_CHINESE_MAP[newKey]) variants.push(ENGLISH_TO_CHINESE_MAP[newKey])
  for (const [eng, zh] of Object.entries(ENGLISH_TO_CHINESE_MAP)) {
    if (zh === newKey && !variants.includes(eng)) variants.push(eng)
  }
  const exists = nutritionEditItems.value.some((item, i) =>
    i !== index && variants.includes(item.key)
  )
  if (exists) {
    showMessage('该营养素已存在', 'error')
    return
  }
  const def = findNutrientDef(newKey)
  if (!def) return
  const item = nutritionEditItems.value[index]
  const oldUnit = item.unit
  item.key = newKey
  item.name = def.label
  item.units = [...def.units]
  // 如果旧单位不在新可用单位列表中，切换到默认单位
  if (!def.units.includes(oldUnit)) {
    item.unit = def.defaultUnit
  }
}

// 行内单位下拉改变 — 自动换算数值
const onUnitChange = (index: number, newUnit: string) => {
  const item = nutritionEditItems.value[index]
  const oldUnit = item.unit
  if (oldUnit === newUnit) return
  if (item.value != null && item.value !== 0) {
    item.value = convertUnit(item.value, oldUnit, newUnit, item.key)
  }
  item.unit = newUnit
}

// 直接添加一个新行，用户通过行内 autocomplete 选择营养素
const addEmptyNutrientRow = () => {
  nutritionEditItems.value.push({
    key: '',
    name: '',
    value: null,
    unit: 'g',
    units: ['g', 'mg', 'μg', 'kcal', 'kJ', 'IU'],
  })
}

const saveNutritionEdit = async () => {
  savingNutrition.value = true
  try {
    const nutrients: { name: string; value: number; unit: string; key?: string }[] = []

    for (const entry of nutritionEditItems.value) {
      if (entry.value != null && entry.value > 0 && entry.name.trim()) {
        nutrients.push({
          name: entry.name,
          value: entry.value,
          unit: entry.unit || 'g',
          key: entry.key,
        })
      }
    }

    if (nutrients.length === 0) {
      showMessage('请至少填写一项营养素', 'error')
      savingNutrition.value = false
      return
    }

    const res = await api.post(`/nutrition/ingredients/${ingredientId.value}/nutrition`, {
      base_quantity: 100,
      base_unit: 'g',
      nutrients,
      source: 'custom',
    })

    // 共享数据分流：管理员直写 / 普通用户补空自动通过（applied，营养已变）/
    // 普通用户有数据→manual 待审（status=pending，营养未变）。
    // 按后端返回 message 区分提示，避免普通用户待审时误报「已保存」。
    editingNutrition.value = false
    const msg: string = (res && res.message) || ''
    if (msg.includes('待管理员审核')) {
      // 普通用户有数据→manual 待审：营养未落地，无需刷新
      showMessage('已提交，待管理员审核', 'info')
    } else {
      // 管理员直写 或 普通用户补空自动通过：营养已落地，刷新展示
      await loadNutritionData()
      showMessage('营养数据已保存', 'success')
    }
  } catch (e: any) {
    showMessage(e.response?.data?.detail || e.message || '保存失败', 'error')
  } finally {
    savingNutrition.value = false
  }
}

// 前往添加价格
const goToAddPrice = () => {
  if (priceForm.value.product_id) {
    router.push(`/data/products/${priceForm.value.product_id}`)
  }
}

// 价格记录单位选项
const unitOptions = ['g', 'kg', '斤', '两', 'ml', 'L', '个', '包', '袋', '盒', '瓶', '罐']

// 商家列表
interface Merchant {
  id: number
  name: string
}
const merchants = ref<Merchant[]>([])

const loadMerchants = async () => {
  try {
    const response = await api.get('/merchants', { params: { skip: 0, limit: 100 } })
    merchants.value = response.items || response || []
  } catch {
    merchants.value = []
  }
}

// 打开编辑价格记录对话框
const openEditPriceDialog = async (record: PriceRecord) => {
  editingPriceRecord.value = record
  // 查找该记录的 merchant_id
  let merchantId: number | null = null
  try {
    const resp = await api.get('/merchants', { params: { skip: 0, limit: 100 } })
    const allMerchants = resp.items || resp || []
    // 从记录中没有 merchant_id 字段，用 merchant_name 反查
    if (record.merchant_name) {
      const m = allMerchants.find((x: Merchant) => x.name === record.merchant_name)
      if (m) merchantId = m.id
    }
  } catch { /* ignore */ }

  editPriceForm.value = {
    price: Number(record.price),
    quantity: Number(record.original_quantity),
    unit: record.original_unit || priceUnitName.value,
    merchant_id: merchantId
  }
  // 确保商家列表已加载
  if (merchants.value.length === 0) {
    await loadMerchants()
  }
  showEditPriceDialog.value = true
}

// 保存编辑的价格记录
const saveEditPriceRecord = async () => {
  if (!editingPriceRecord.value) return
  if (!editPriceForm.value.price || !editPriceForm.value.quantity) return

  savingPrice.value = true
  try {
    await api.put(`/products/${editingPriceRecord.value.id}`, {
      price: editPriceForm.value.price,
      original_quantity: editPriceForm.value.quantity,
      original_unit: editPriceForm.value.unit,
      merchant_id: editPriceForm.value.merchant_id
    })
    showEditPriceDialog.value = false
    editingPriceRecord.value = null
    await loadPriceRecords()
    refreshChart()
    showMessage('更新成功', 'success')
  } catch (e: any) {
    showMessage(e.response?.data?.detail || e.message || '更新失败', 'error')
  } finally {
    savingPrice.value = false
  }
}

// 删除价格记录
const deletePriceRecord = async (id: number) => {
  if (!(await ask({ text: '确定删除此价格记录？', color: 'error', confirmText: '删除' }))) return

  try {
    await api.delete(`/products/${id}`)
    await loadPriceRecords()
    refreshChart()
    showMessage('删除成功', 'success')
  } catch (e: any) {
    showMessage(e.response?.data?.detail || e.message || '删除失败', 'error')
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

// 合并原料 - 打开确认对话框
const mergeIngredient = () => {
  if (!mergeTargetId.value) return
  showMergeConfirmDialog.value = true
}

// 执行合并操作
const doMerge = async () => {
  if (!mergeTargetId.value) return

  merging.value = true
  try {
    const response = await api.post('/ingredients/merge', {
      source_ingredient_ids: [ingredientId.value],
      target_ingredient_id: mergeTargetId.value
    })
    const msg: string = (response && response.message) || ''
    if (msg.includes('待管理员审核')) {
      showMessage('合并提议已提交，待管理员审核', 'info')
    } else {
      showMessage(msg || '合并成功', 'success')
    }
    // 关闭所有对话框
    showMergeDialog.value = false
    showMergeConfirmDialog.value = false
    // 管理员直写→跳转；普通用户待审→留在当前页
    if (!msg.includes('待管理员审核')) {
      router.push(`/data/ingredients/${mergeTargetId.value}`)
    }
  } catch (e: any) {
    showMessage(e.response?.data?.detail || e.message || '合并失败', 'error')
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
    if (userStore.user?.is_admin) {
      showMessage('删除成功', 'success')
      router.push('/data/ingredients')
    } else {
      showMessage('删除提议已提交，待管理员审核', 'info')
    }
  } catch (e: any) {
    showMessage(e.response?.data?.detail || e.message || '删除失败', 'error')
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
  router.back()
}

// 格式化函数
const formatPrice = (price: any) => {
  const num = parseFloat(price) || 0
  return num.toFixed(2)
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

// 监听菜谱分页变化
watch(recipePage, loadRecipes)

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
  loadCategories()
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

/* 营养编辑表格 — 四列精确网格 */
.nutrition-edit-table {
  display: grid;
  grid-template-columns: 1fr 144px 144px 36px;
  gap: 2px;
}
.nutrition-edit-table.header-row {
  background: rgb(var(--v-theme-surface-variant));
  font-weight: 500;
}
.nutrition-edit-table > div {
  min-width: 0; /* 防止溢出 */
}

/* 营养编辑表格紧凑输入框 */
.nutrition-edit-input :deep(.v-field) {
  font-size: 0.8125rem;
  min-height: 32px;
  padding: 0 8px;
}
.nutrition-edit-input :deep(.v-field__input) {
  min-height: 30px;
  padding-top: 2px;
  padding-bottom: 2px;
}
.nutrition-edit-input :deep(.v-field.v-field--outlined) {
  border-radius: 6px;
}

/* 数量输入框右对齐 */
.text-end.nutrition-edit-input :deep(input) {
  text-align: end;
}

/* 别名列表项样式 - 允许高度自适应 */
.aliases-list-item {
  align-items: flex-start !important;
}

.aliases-list-item :deep(.v-list-item__content) {
  overflow: visible !important;
}

/* 别名标签容器样式 */
.aliases-subtitle {
  white-space: normal !important;
  overflow: visible !important;
  text-overflow: clip !important;
  line-height: 1.5;
  display: block !important;
}

.aliases-subtitle .v-chip {
  display: inline-flex !important;
  height: auto !important;
  padding: 4px 10px !important;
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

/* === 商家价格横向列表 === */
.merchant-price-list {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 10px 2px 4px 2px;
  scrollbar-width: thin;
}

.merchant-price-item {
  flex: 0 0 auto;
  min-width: 100px;
  max-width: 140px;
  padding: 8px 12px;
  border-radius: 8px;
  background: rgba(var(--v-theme-on-surface), 0.04);
  text-align: center;
  position: relative;
  transition: background-color 0.2s;
}

.merchant-price-item:hover {
  background: rgba(var(--v-theme-on-surface), 0.08);
}

.merchant-price-lowest {
  background: rgba(var(--v-theme-success), 0.08);
  border: 1px solid rgba(var(--v-theme-success), 0.3);
}

.merchant-price-lowest:hover {
  background: rgba(var(--v-theme-success), 0.12);
}

.merchant-price-name {
  font-size: 0.75rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
  margin-bottom: 4px;
}

.merchant-price-value {
  font-size: 0.95rem;
}

.merchant-price-date {
  font-size: 0.65rem;
  color: rgba(var(--v-theme-on-surface), var(--v-disabled-opacity));
  margin-top: 2px;
}

.merchant-price-badge {
  position: absolute;
  top: -8px;
  right: -4px;
}

/* === 响应式布局 === */

/* 移动端：flex 纵向堆叠 + CSS order 重排序 */
.ingredient-layout {
  display: flex;
  flex-direction: column;
}

.ingredient-layout > .grid-item,
.group-3-left > .grid-item,
.group-3-right > .grid-item {
  margin: 16px;
}

/* 移动端：Group 3 容器透明化，子元素直接参与父 flex 流 */
.group-3-wrapper {
  display: contents;
}
.group-3-left, .group-3-right {
  display: contents;
}

/* 移动端顺序 */
.item-basic-info { order: 1; }
.item-latest-price { order: 2; }
.item-price-trend { order: 3; }
.item-products { order: 4; }
.item-price-records { order: 5; }
.item-recipes { order: 6; }
.item-nutrition { order: 7; }
.item-hierarchy { order: 8; }
.item-relation-list { order: 8; }
.item-units { order: 9; }

/* 桌面端：CSS Grid + Flexbox 混合布局 */
@media (min-width: 960px) {
  .ingredient-layout {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    padding: 16px;
  }

  .ingredient-layout > .grid-item {
    margin: 0 !important;
  }

  /* Group 1: 基本信息 | 最新价格 / 关联商品 | 价格趋势（行对齐） */
  .item-basic-info { grid-column: 1; grid-row: 1; }
  .item-latest-price { grid-column: 2; grid-row: 1; }
  .item-products { grid-column: 1; grid-row: 2; }
  .item-price-trend { grid-column: 2; grid-row: 2; }

  /* Group 2: 相关菜谱 | 价格记录（行对齐） */
  .item-recipes { grid-column: 1; grid-row: 3; }
  .item-price-records { grid-column: 2; grid-row: 3; }

  /* Group 3: 独立 flex 容器，左右列互不影响 */
  .group-3-wrapper {
    display: flex;
    grid-column: 1 / -1;
    grid-row: 4;
    gap: 16px;
    align-items: flex-start;
  }
  .group-3-left, .group-3-right {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-width: 0;
    gap: 16px;
  }
  .group-3-left > .grid-item,
  .group-3-right > .grid-item {
    margin: 0 !important;
  }
}
</style>
