<template>
  <!-- 顶部导航栏 - 移到 container 外面以便固定 -->
  <v-app-bar elevation="0" color="background" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
    <v-app-bar-title class="text-h6">
      <div class="d-flex align-center ga-2">
        <span class="text-truncate">{{ product?.name || '商品详情' }}</span>
        <v-chip size="x-small" variant="tonal" color="primary">商品</v-chip>
      </div>
    </v-app-bar-title>
    <template #append>
      <v-btn icon="mdi-tag-plus" variant="text" @click="openQuickPriceDialog" />
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

    <template v-else-if="product">
      <div class="product-layout">
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
            <v-list-item v-if="product.brand">
              <template #prepend>
                <v-icon size="small" color="medium-emphasis">mdi-tag-outline</v-icon>
              </template>
              <v-list-item-title>品牌</v-list-item-title>
              <v-list-item-subtitle>{{ product.brand }}</v-list-item-subtitle>
            </v-list-item>

            <v-list-item v-if="product.barcode">
              <template #prepend>
                <v-icon size="small" color="medium-emphasis">mdi-barcode</v-icon>
              </template>
              <v-list-item-title>条码</v-list-item-title>
              <v-list-item-subtitle class="font-family-monospace">{{ product.barcode }}</v-list-item-subtitle>
            </v-list-item>

            <v-list-item v-if="product.ingredient_name" @click="goToIngredient" class="cursor-pointer">
              <template #prepend>
                <v-icon size="small" color="medium-emphasis">mdi-leaf</v-icon>
              </template>
              <v-list-item-title>关联原料</v-list-item-title>
              <v-list-item-subtitle class="d-flex align-center">
                <span class="text-primary text-decoration-underline">{{ product.ingredient_name }}</span>
                <v-icon size="small" color="primary" class="ml-1">mdi-arrow-right</v-icon>
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item v-if="product.aliases?.length">
              <template #prepend>
                <v-icon size="small" color="medium-emphasis">mdi-file-document-multiple-outline</v-icon>
              </template>
              <v-list-item-title>别名</v-list-item-title>
              <v-list-item-subtitle>
                <v-chip
                  v-for="alias in product.aliases"
                  :key="alias"
                  size="x-small"
                  class="mr-1"
                >
                  {{ alias }}
                </v-chip>
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item v-if="product.tags?.length">
              <template #prepend>
                <v-icon size="small" color="medium-emphasis">mdi-tag-multiple-outline</v-icon>
              </template>
              <v-list-item-title>标签</v-list-item-title>
              <v-list-item-subtitle>
                <v-chip
                  v-for="tag in product.tags"
                  :key="tag"
                  size="x-small"
                  class="mr-1"
                >
                  {{ tag }}
                </v-chip>
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item>
              <template #prepend>
                <v-icon size="small" color="medium-emphasis">mdi-calendar</v-icon>
              </template>
              <v-list-item-title>创建时间</v-list-item-title>
              <v-list-item-subtitle>{{ formatToLocalDateTimeShort(product.created_at) }}</v-list-item-subtitle>
            </v-list-item>
          </v-list>

          <!-- 编辑模式 -->
          <v-form v-else @submit.prevent="saveBasicInfo">
            <v-text-field
              v-model="basicEditForm.name"
              label="商品名称"
              variant="outlined"
              density="compact"
              required
              class="mb-3"
            />
            <v-autocomplete
              v-model="selectedIngredient"
              v-model:search="ingredientSearch"
              :items="ingredients"
              item-title="name"
              item-value="id"
              label="关联原料 *"
              variant="outlined"
              density="compact"
              required
              :loading="loadingIngredients"
              :no-data-text="ingredientSearch ? '未找到匹配的原料' : '请输入搜索关键词'"
              placeholder="输入关键词搜索原料"
              clearable
              return-object
              auto-select-first
              hide-selected
              :custom-filter="() => true"
              class="mb-3"
            >
              <template #item="{ props, item }">
                <v-list-item v-bind="props">
                  <v-list-item-subtitle v-if="item.raw.aliases && item.raw.aliases.length > 0">
                    别名: {{ item.raw.aliases.join(', ') }}
                  </v-list-item-subtitle>
                </v-list-item>
              </template>
            </v-autocomplete>
            <v-text-field
              v-model="basicEditForm.brand"
              label="品牌"
              variant="outlined"
              density="compact"
              class="mb-3"
            />
            <v-text-field
              v-model="basicEditForm.barcode"
              label="条码"
              variant="outlined"
              density="compact"
              class="mb-3"
            />
            <v-combobox
              v-model="basicEditForm.tags"
              label="标签"
              variant="outlined"
              density="compact"
              multiple
              chips
              closable-chips
            />
            <v-combobox
              v-model="basicEditForm.aliases"
              label="别名"
              variant="outlined"
              density="compact"
              multiple
              chips
              closable-chips
              hint="输入后回车添加多个别名"
              persistent-hint
            />
          </v-form>
        </v-card-text>
      </v-card>

      <!-- 最新价格卡片 -->
      <v-card elevation="0" class="grid-item item-latest-price" v-if="product.latest_price">
        <v-card-title class="d-flex align-center pb-2">
          <v-icon start color="tertiary">mdi-currency-cny</v-icon>
          最新价格
        </v-card-title>
        <v-divider />
        <v-card-text class="text-center py-6">
          <div class="text-h3 font-weight-bold text-tertiary">
            ¥{{ formatPrice(product.latest_price) }}<span v-if="product.latest_price_unit" class="text-h6 font-weight-regular">/{{ product.latest_price_unit }}</span>
          </div>
          <div class="text-caption text-medium-emphasis mt-2">
            {{ formatToLocalDate(product.latest_price_date) }}
          </div>
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
          </v-card-text>
        </template>
      </v-card>

      <!-- Group 2: 单位与密度 | 价格趋势（行不对齐，独立高度） -->
      <div class="group-mid-wrapper">
        <div class="group-mid-left">
          <!-- 单位与密度管理卡片 -->
          <v-card elevation="0" class="grid-item item-units">
            <v-card-title class="d-flex align-center pb-2">
              <v-icon start color="secondary">mdi-ruler</v-icon>
              单位与密度
            </v-card-title>
            <v-divider />

            <!-- 自定义单位列表 -->
            <v-card-text class="pb-0">
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

              <v-list v-else-if="entityUnits.length > 0" density="compact" class="pa-0">
                <v-list-item
                  v-for="unit in entityUnits"
                  :key="unit.id"
                  class="px-0"
                >
                  <template #prepend>
                    <v-chip size="small" variant="tonal" color="primary" class="mr-3">
                      {{ unit.unit_name }}
                    </v-chip>
                  </template>
                  <v-list-item-title class="text-body-2">
                    <span v-if="unit.conversion_factor">1{{ unit.unit_name }} = {{ unit.conversion_factor }}个</span>
                    <span v-if="unit.weight_per_unit" class="ml-2">
                      <v-icon size="x-small">mdi-weight</v-icon>
                      {{ unit.weight_per_unit }}g/个
                    </span>
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
                      icon="mdi-pencil"
                      size="x-small"
                      variant="text"
                      color="primary"
                      @click.stop="openUnitDialog(unit)"
                    />
                    <v-btn
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
              <div class="d-flex align-center mb-2">
                <span class="text-body-2 font-weight-medium">密度信息</span>
                <v-spacer />
                <v-btn
                  v-if="!entityDensity"
                  size="small"
                  variant="text"
                  color="primary"
                  prepend-icon="mdi-plus"
                  @click="openDensityDialog()"
                >
                  设置密度
                </v-btn>
                <template v-else>
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
                    @click="deleteDensity(entityDensity.id)"
                  />
                </template>
              </div>

              <div v-if="entityDensity" class="d-flex align-center py-2">
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
                <span v-if="entityDensity.temperature" class="text-caption text-medium-emphasis ml-2">
                  ({{ entityDensity.temperature }}°C)
                </span>
                <span v-if="entityDensity.source" class="text-caption text-medium-emphasis ml-2">
                  来源: {{ entityDensity.source }}
                </span>
              </div>
              <div v-else class="text-center py-4">
                <v-icon size="32" color="medium-emphasis">mdi-water-off</v-icon>
                <div class="text-caption text-medium-emphasis mt-1">暂未设置密度</div>
              </div>
            </v-card-text>
          </v-card>
        </div>
        <div class="group-mid-right">
          <!-- 价格趋势图表 -->
          <PriceTrendChart
            v-if="product"
            title="价格趋势"
            icon="mdi-chart-line"
            icon-color="tertiary"
            :unit="chartUnit"
            empty-text="暂无价格历史数据"
            :data="chartData"
            :loading="loadingPrices"
            color="#ff9800"
            class="grid-item item-price-trend"
          />
        </div>
      </div>

      <!-- 价格记录列表 -->
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
            @click="openAddPriceDialog"
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
              ¥{{ formatPrice(record.price) }} / {{ record.original_quantity }}{{ record.original_unit }}
            </v-list-item-title>
            <v-list-item-subtitle>
              <template v-if="record.merchant_name">
                {{ record.merchant_name }} ·
              </template>
              {{ formatToLocalDateTimeShort(record.recorded_at) }}
            </v-list-item-subtitle>

            <template #append>
              <v-btn
                icon="mdi-delete"
                size="small"
                variant="text"
                color="error"
                @click="deletePriceRecord(record.id)"
              />
            </template>
          </v-list-item>
        </v-list>

        <!-- 空状态 -->
        <v-card-text v-else class="text-center py-8">
          <v-icon size="64" color="medium-emphasis">mdi-receipt-text-outline</v-icon>
          <div class="text-body-1 text-medium-emphasis mt-4">暂无价格记录</div>
          <v-btn
            color="primary"
            variant="tonal"
            class="mt-4"
            prepend-icon="mdi-plus"
            @click="openAddPriceDialog"
          >
            添加价格记录
          </v-btn>
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

      <!-- 营养数据卡片（有数据） -->
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
          </template>
          <template v-else>
            <v-btn size="small" variant="text" @click="cancelEditNutrition">取消</v-btn>
            <v-btn size="small" color="primary" variant="text" :loading="savingNutrition" @click="saveNutritionEdit">保存</v-btn>
          </template>
        </v-card-title>
        <v-divider />

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

      <!-- 营养数据卡片（无数据） -->
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

      <!-- 操作按钮 -->
      <div class="pa-4 d-flex flex-column ga-2">
        <v-btn
          color="primary"
          variant="tonal"
          block
          prepend-icon="mdi-call-split"
          :loading="splitting"
          @click="handleSplitToIngredient"
        >
          拆分为原料
        </v-btn>
        <v-btn
          color="warning"
          variant="tonal"
          block
          prepend-icon="mdi-merge"
          :disabled="siblingProducts.length === 0"
          @click="showMergeDialog = true"
        >
          合并到关联商品
        </v-btn>
        <v-btn
          color="error"
          variant="tonal"
          block
          prepend-icon="mdi-delete"
          @click="confirmDelete"
        >
          删除商品
        </v-btn>
      </div>
    </template>


    <!-- 添加价格记录对话框 -->
    <v-dialog v-model="showAddPriceDialog" max-width="500">
      <v-card>
        <v-card-title>添加价格记录</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="savePriceRecord">
            <v-text-field
              v-model.number="priceForm.price"
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
                  v-model.number="priceForm.quantity"
                  label="数量"
                  variant="outlined"
                  type="number"
                  required
                />
              </v-col>
              <v-col cols="6">
                <v-select
                  v-model="priceForm.unit"
                  :items="unitOptions"
                  label="单位"
                  variant="outlined"
                  required
                  :hint="currentIngredientDefaultUnit ? `原料默认单位: ${currentIngredientDefaultUnit}` : ''"
                  :persistent-hint="!!currentIngredientDefaultUnit"
                />
              </v-col>
            </v-row>
            <v-autocomplete
              v-model="priceForm.merchant_id"
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
          <v-btn @click="showAddPriceDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="savingPrice" @click="savePriceRecord">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 确认删除对话框 -->
    <v-dialog v-model="showDeleteDialog" max-width="400">
      <v-card>
        <v-card-title class="text-error">确认删除</v-card-title>
        <v-card-text>
          确定要删除商品「{{ product?.name }}」吗？此操作不可恢复。
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showDeleteDialog = false">取消</v-btn>
          <v-btn color="error" :loading="deleting" @click="deleteProduct">删除</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 拆分为原料 - 重命名对话框 -->
    <v-dialog v-model="showSplitRenameDialog" max-width="400" persistent>
      <v-card>
        <v-card-title>指定新原料名称</v-card-title>
        <v-card-text>
          <p class="text-body-2 mb-3">{{ splitRenameMessage }}</p>
          <v-text-field
            v-model="splitNewName"
            label="新原料名称"
            variant="outlined"
            :rules="[v => !!v?.trim() || '请输入原料名称']"
            @keyup.enter="confirmSplitWithNewName"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showSplitRenameDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="splitting" @click="confirmSplitWithNewName">确认</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 合并到关联商品 - 对话框 -->
    <v-dialog v-model="showMergeDialog" max-width="500" @update:model-value="onMergeDialogToggle">
      <v-card>
        <v-card-title class="text-warning">
          <v-icon start color="warning">mdi-merge</v-icon>
          合并到关联商品
        </v-card-title>
        <v-card-text>
          <p class="text-body-2 mb-3">
            选择要把 <strong>{{ product?.name }}</strong> 合并到哪个商品：
          </p>

          <!-- 加载中 -->
          <div v-if="loadingSiblings" class="text-center py-4">
            <v-progress-circular indeterminate size="24" />
            <span class="ml-2 text-body-2">加载关联商品...</span>
          </div>

          <!-- 无关联商品 -->
          <div v-else-if="siblingProducts.length === 0" class="text-center py-4 text-body-2 text-medium-emphasis">
            当前原料下没有其他商品可以合并
          </div>

          <!-- 商品列表 -->
          <v-radio-group v-else v-model="selectedMergeTarget" class="mt-0">
            <v-radio
              v-for="sibling in siblingProducts"
              :key="sibling.id"
              :value="sibling"
              class="mb-1"
            >
              <template #label>
                <div class="d-flex align-center ga-2 py-1">
                  <v-icon size="small">mdi-package-variant-closed</v-icon>
                  <span>{{ sibling.name }}</span>
                  <span v-if="sibling.brand" class="text-caption text-medium-emphasis">({{ sibling.brand }})</span>
                  <span v-if="sibling.latest_price" class="text-caption text-medium-emphasis">
                    — ¥{{ Number(sibling.latest_price).toFixed(2) }}{{ sibling.latest_price_unit ? '/' + sibling.latest_price_unit : '' }}
                  </span>
                </div>
              </template>
            </v-radio>
          </v-radio-group>

          <v-divider class="my-2" />

          <ul class="text-body-2 text-medium-emphasis mb-0">
            <li>价格记录将迁移到目标商品</li>
            <li>营养信息将丢弃</li>
            <li>当前商品将被删除</li>
          </ul>
          <p class="text-body-2 mt-2 text-error">此操作不可撤销。</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showMergeDialog = false">取消</v-btn>
          <v-btn
            color="warning"
            :disabled="!selectedMergeTarget"
            :loading="merging"
            @click="doMerge"
          >
            确认合并
          </v-btn>
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
      :product-id="product?.id ?? null"
      :product-name="product?.name ?? ''"
      @saved="onQuickPriceSaved"
    />
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import { getErrorMessage } from '@/utils/errorHandler'
import PriceTrendChart from '@/components/charts/PriceTrendChart.vue'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import { usePageTitle } from '@/composables/usePageTitle'
import QuickPriceRecordDialog from '@/components/prices/QuickPriceRecordDialog.vue'
import { NUTRITION_LABEL_MAP, ENGLISH_TO_CHINESE_MAP } from '@/utils/nutritionLabels'
import SparklineBackground from '@/components/charts/SparklineBackground.vue'
import { formatToLocalDate, formatToLocalDateTimeShort } from '@/utils/timezone'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const { setDetailTitle } = usePageTitle()

interface Product {
  id: number
  name: string
  brand?: string
  barcode?: string
  image_url?: string
  ingredient_id?: number
  ingredient_name?: string
  tags?: string[]
  aliases?: string[]
  latest_price?: number | string
  latest_price_unit?: string
  latest_price_date?: string
  created_at: string
  updated_at?: string
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

interface Merchant {
  id: number
  name: string
}

interface Ingredient {
  id: number
  name: string
  aliases?: string[]
  default_unit?: string
}

const route = useRoute()
const router = useRouter()

const productId = computed(() => Number(route.params.id))

const product = ref<Product | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

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

// 价格记录相关
const priceRecords = ref<PriceRecord[]>([])
const loadingPrices = ref(false)
const pricePage = ref(1)
const pricePageSize = ref(10)
const priceTotal = ref(0)
const priceTotalPages = computed(() => Math.ceil(priceTotal.value / pricePageSize.value))

// 营养数据
const nutritionData = ref<any>(null)
const loadingNutrition = ref(false)

// 商家列表
const merchants = ref<Merchant[]>([])

// 原料列表
const ingredients = ref<Ingredient[]>([])
const loadingIngredients = ref(false)
const ingredientSearch = ref('')
const selectedIngredient = ref<Ingredient | null>(null)

// 对话框状态
const showAddPriceDialog = ref(false)
const showDeleteDialog = ref(false)
const saving = ref(false)
const savingPrice = ref(false)
const deleting = ref(false)

// 拆分为原料
const splitting = ref(false)
const showSplitRenameDialog = ref(false)
const splitNewName = ref('')
const splitRenameMessage = ref('')

// 合并到关联商品
interface SiblingProduct {
  id: number
  name: string
  brand?: string
  latest_price?: number | string
  latest_price_unit?: string
}
const siblingProducts = ref<SiblingProduct[]>([])
const loadingSiblings = ref(false)
const showMergeDialog = ref(false)
const selectedMergeTarget = ref<SiblingProduct | null>(null)
const merging = ref(false)

// 基本信息内联编辑
const editingBasicInfo = ref(false)
const basicEditForm = ref({
  name: '',
  brand: '',
  barcode: '',
  ingredient_id: null as number | null,
  tags: [] as string[],
  aliases: [] as string[],
})

// 营养成分内联编辑
const editingNutrition = ref(false)
const savingNutrition = ref(false)

// 营养素定义：key 匹配后端 all_nutrients 的英文键名
const NUTRIENT_DEFINITIONS = [
  { key: 'energy', label: '能量', units: ['kcal', 'kJ'], defaultUnit: 'kcal' },
  { key: 'protein', label: '蛋白质', units: ['g', 'mg'], defaultUnit: 'g' },
  { key: 'fat', label: '脂肪', units: ['g', 'mg'], defaultUnit: 'g' },
  { key: 'carbohydrate', label: '碳水化合物', units: ['g', 'mg'], defaultUnit: 'g' },
  { key: 'fiber', label: '膳食纤维', units: ['g'], defaultUnit: 'g' },
  { key: 'calcium', label: '钙', units: ['mg', 'μg', 'g'], defaultUnit: 'mg' },
  { key: 'iron', label: '铁', units: ['mg', 'μg'], defaultUnit: 'mg' },
  { key: 'sodium', label: '钠', units: ['mg', 'g'], defaultUnit: 'mg' },
  { key: 'potassium', label: '钾', units: ['mg', 'g'], defaultUnit: 'mg' },
  { key: 'vitamin_a_rae', label: '维生素A', units: ['μg', 'IU', 'mg'], defaultUnit: 'μg' },
  { key: 'vitamin_c', label: '维生素C', units: ['mg', 'g'], defaultUnit: 'mg' },
  { key: 'vitamin_b1', label: '维生素B1', units: ['mg', 'μg'], defaultUnit: 'mg' },
  { key: 'vitamin_b2', label: '维生素B2', units: ['mg', 'μg'], defaultUnit: 'mg' },
  { key: 'vitamin_b12', label: '维生素B12', units: ['μg', 'mg'], defaultUnit: 'μg' },
  { key: 'vitamin_d', label: '维生素D', units: ['μg', 'IU'], defaultUnit: 'μg' },
  { key: 'vitamin_e', label: '维生素E', units: ['mg', 'IU'], defaultUnit: 'mg' },
  { key: 'vitamin_k', label: '维生素K', units: ['μg', 'mg'], defaultUnit: 'μg' },
  { key: 'magnesium', label: '镁', units: ['mg', 'g'], defaultUnit: 'mg' },
  { key: 'zinc', label: '锌', units: ['mg', 'μg'], defaultUnit: 'mg' },
  { key: 'selenium', label: '硒', units: ['μg', 'mg'], defaultUnit: 'μg' },
  { key: 'cholesterol', label: '胆固醇', units: ['mg', 'g'], defaultUnit: 'mg' },
  { key: 'saturated_fat', label: '饱和脂肪', units: ['g', 'mg'], defaultUnit: 'g' },
  { key: 'folate', label: '叶酸', units: ['μg', 'mg'], defaultUnit: 'μg' },
  { key: 'phosphorus', label: '磷', units: ['mg', 'g'], defaultUnit: 'mg' },
  { key: 'copper', label: '铜', units: ['mg', 'μg'], defaultUnit: 'mg' },
  { key: 'manganese', label: '锰', units: ['mg', 'μg'], defaultUnit: 'mg' },
  { key: 'vitamin_b6', label: '维生素B6', units: ['mg', 'μg'], defaultUnit: 'mg' },
  { key: 'pantothenic_acid', label: '维生素B5', units: ['mg'], defaultUnit: 'mg' },
  { key: 'monounsaturated_fat', label: '单不饱和脂肪', units: ['g', 'mg'], defaultUnit: 'g' },
  { key: 'polyunsaturated_fat', label: '多不饱和脂肪', units: ['g', 'mg'], defaultUnit: 'g' },
]

// 营养素同义键映射：将别名 key 映射到标准 key，避免编辑时重复
const NUTRIENT_PARENT_MAP: Record<string, string> = {
  // energy 已是标准键名，无需同义映射
}

// IU ↔ 质量换算系数
const IU_TO_MASS: Record<string, { factor: number, unit: string }> = {
  'vitamin_a_rae': { factor: 0.3, unit: 'μg' },
  'vitamin_d': { factor: 0.025, unit: 'μg' },
  'vitamin_e': { factor: 0.67, unit: 'mg' },
}

const MASS_TO_GRAMS: Record<string, number> = {
  'g': 1,
  'mg': 0.001,
  'μg': 0.000001,
}

const ENERGY_FACTORS: Record<string, number> = {
  'kcal': 1,
  'kJ': 4.184,
}

// 查找营养素定义
const findNutrientDef = (key: string) => {
  const def = NUTRIENT_DEFINITIONS.find(n => n.key === key)
  if (def) return def
  return buildDynamicDef(key)
}

const buildDynamicDef = (key: string) => {
  const zhName = ENGLISH_TO_CHINESE_MAP[key]
  if (zhName) {
    const label = zhName
    const isEnergy = key.startsWith('energy_') || key === 'energy'
    const isIUvitamin = /^vitamin_(a|d|e)/.test(key)
    const units = isEnergy ? ['kcal', 'kJ'] : isIUvitamin ? ['μg', 'mg', 'IU'] : ['g', 'mg', 'μg']
    const defaultUnit = isEnergy ? 'kcal' : isIUvitamin ? 'μg' : 'g'
    return { key, label, units, defaultUnit }
  }
  const allNutrients = nutritionData.value?.nutrition?.all_nutrients
  if (!allNutrients) return undefined
  const data: any = allNutrients[key]
  if (!data || typeof data !== 'object') return undefined
  const rawUnit = (data.unit || 'g').toLowerCase()
  const label = key
  const isMassUnit = (u: string) => ['g', 'gram', 'grams', 'mg', 'milligram', 'milligrams', 'μg', 'mcg', 'ug', 'microgram', 'micrograms'].includes(u)
  const isEnergyUnit = (u: string) => ['kcal', 'kj', 'calorie', 'calories', 'kilocalorie', 'kilocalories', '千卡', '千焦'].includes(u)
  const units = isEnergyUnit(rawUnit) ? ['kcal', 'kJ'] : isMassUnit(rawUnit) ? ['g', 'mg', 'μg'] : [rawUnit]
  return { key, label, units, defaultUnit: rawUnit }
}

const getAllNutrientDefs = () => {
  const defs = [...NUTRIENT_DEFINITIONS]
  const existingKeys = new Set(NUTRIENT_DEFINITIONS.map(d => d.key))
  for (const key of Object.keys(ENGLISH_TO_CHINESE_MAP)) {
    if (existingKeys.has(key)) continue
    const parentKey = NUTRIENT_PARENT_MAP[key]
    if (parentKey && existingKeys.has(parentKey)) continue
    const def = buildDynamicDef(key)
    if (def) { defs.push(def); existingKeys.add(key) }
  }
  const allNutrients = nutritionData.value?.nutrition?.all_nutrients
  if (allNutrients) {
    for (const key of Object.keys(allNutrients)) {
      if (existingKeys.has(key)) continue
      const data = allNutrients[key]
      const canonicalKey = data?.original_key || data?.key
      if (canonicalKey && canonicalKey !== key && existingKeys.has(canonicalKey)) continue
      const def = buildDynamicDef(key)
      if (def) { defs.push(def); existingKeys.add(key) }
    }
  }
  return defs
}

// 单位换算
const convertUnit = (value: number, fromUnit: string, toUnit: string, nutrientKey: string): number => {
  if (fromUnit === toUnit || value === 0) return value
  if (ENERGY_FACTORS[fromUnit] && ENERGY_FACTORS[toUnit]) {
    const inKcal = value * ENERGY_FACTORS[fromUnit]
    return inKcal / ENERGY_FACTORS[toUnit]
  }
  if (MASS_TO_GRAMS[fromUnit] && MASS_TO_GRAMS[toUnit]) {
    const inGrams = value * MASS_TO_GRAMS[fromUnit]
    return inGrams / MASS_TO_GRAMS[toUnit]
  }
  const iuInfo = IU_TO_MASS[nutrientKey]
  if (iuInfo) {
    if (fromUnit === 'IU' && MASS_TO_GRAMS[toUnit]) {
      const massInBase = value * iuInfo.factor
      const inGrams = massInBase * (MASS_TO_GRAMS[iuInfo.unit] || 1)
      return inGrams / (MASS_TO_GRAMS[toUnit] || 1)
    }
    if (toUnit === 'IU' && MASS_TO_GRAMS[fromUnit]) {
      const inGrams = value * (MASS_TO_GRAMS[fromUnit] || 1)
      const inBaseUnit = inGrams / (MASS_TO_GRAMS[iuInfo.unit] || 1)
      return inBaseUnit / iuInfo.factor
    }
  }
  return value
}

// 营养编辑条目
interface NutritionEditItem {
  key: string
  name: string
  value: number | null
  unit: string
  units: string[]
}
const nutritionEditItems = ref<NutritionEditItem[]>([])

const getNutrientOptionsForRow = (currentKey: string) => {
  const usedKeys = new Set(
    nutritionEditItems.value
      .filter(i => i.key !== currentKey)
      .map(i => i.key)
  )
  return getAllNutrientDefs().filter(n => !usedKeys.has(n.key))
}

const priceForm = ref({
  price: 0,
  quantity: 1,
  unit: '斤',
  merchant_id: null as number | null
})

// 打开添加价格记录对话框时，自动填充默认单位
const openAddPriceDialog = () => {
  // 如果原料有默认单位，使用默认单位；否则使用 'g'
  priceForm.value = {
    price: 0,
    quantity: 1,
    unit: currentIngredientDefaultUnit.value || '斤',
    merchant_id: null
  }
  showAddPriceDialog.value = true
}

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
  if (!entityDensity.value || typeof entityDensity.value.density !== 'number') return ''
  const val = entityDensity.value.density
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
    const response = await api.get(`/entities/product/${productId.value}/units`)
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
    const response = await api.get(`/entities/product/${productId.value}/density`)
    entityDensity.value = (Array.isArray(response) && response.length > 0) ? response[0] : null
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
    const response = await api.get(`/entities/product/${productId.value}/units/unmapped-units`)
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
      await api.put(`/entities/product/${productId.value}/units/${unitForm.value.id}`, payload)
    } else {
      await api.post(`/entities/product/${productId.value}/units`, payload)
    }
    showMessage('保存成功', 'success')
    showUnitDialog.value = false
    await loadEntityUnits()
    await loadUnmappedUnits()
  } catch (e: any) {
    showMessage(e.response?.data?.detail || e.message || '保存失败', 'error')
  } finally {
    savingUnit.value = false
  }
}

// 删除单位
const deleteEntityUnit = async (unitId: number) => {
  if (!confirm('确定删除此自定义单位？')) return
  try {
    await api.delete(`/entities/product/${productId.value}/units/${unitId}`)
    showMessage('删除成功', 'success')
    await loadEntityUnits()
    await loadUnmappedUnits()
  } catch (e: any) {
    showMessage(e.response?.data?.detail || e.message || '删除失败', 'error')
  }
}

// 打开密度对话框
const openDensityDialog = (density?: EntityDensity) => {
  if (density) {
    densityForm.value = {
      id: density.id,
      // 按当前输入单位显示（后端存储为 kg/m³）
      density: densityInputUnit.value === 'g/cm3' ? density.density / 1000 : density.density,
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
    await api.post(`/entities/product/${productId.value}/density`, {
      density: density,
      temperature: densityForm.value.temperature,
      source: densityForm.value.source
    })
    showMessage('保存成功', 'success')
    showDensityDialog.value = false
    await loadDensity()
  } catch (e: any) {
    showMessage(e.response?.data?.detail || e.message || '保存失败', 'error')
  } finally {
    savingDensity.value = false
  }
}

// 删除密度
const deleteDensity = async (densityId: number) => {
  if (!confirm('确定删除此密度数据？')) return
  try {
    await api.delete(`/entities/product/${productId.value}/density/${densityId}`)
    showMessage('删除成功', 'success')
    entityDensity.value = null
  } catch (e: any) {
    showMessage(e.response?.data?.detail || e.message || '删除失败', 'error')
  }
}

// 快速记录价格
const showQuickPriceDialog = ref(false)

const openQuickPriceDialog = () => {
  showQuickPriceDialog.value = true
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

// 聚合价格数据用于图表（按日期分组，计算最小、最大、平均价格）
const chartData = computed(() => {
  if (!priceRecords.value || priceRecords.value.length === 0) return []

  // 按日期分组
  const dailyMap = new Map<string, number[]>()

  for (const record of priceRecords.value) {
    if (!record.recorded_at) continue

    const date = new Date(record.recorded_at)
    if (isNaN(date.getTime())) continue

    const dateKey = date.toISOString().split('T')[0]

    // 计算单价，使用 standard_quantity（克）统一单位
    // 归一化到 ¥/斤（1斤=500g），确保不同单位的记录可比较
    const standardQty = parseFloat(String(record.standard_quantity))
    const price = parseFloat(String(record.price)) || 0
    const unitPrice = standardQty && standardQty > 0
      ? price * 500 / standardQty
      : price / (parseFloat(String(record.original_quantity)) || 1)

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

// 图表使用归一化后的统一单位（斤），确保跨单位数据可比较
const chartUnit = computed(() => '斤')

// 获取当前商品关联的原料的默认单位
const currentIngredientDefaultUnit = computed(() => {
  // 从 nutritionData 或 product 中获取原料的默认单位
  if (nutritionData.value?.ingredient?.default_unit) {
    return nutritionData.value.ingredient.default_unit
  }
  return null
})

// 单位选项
const unitOptions = [
  'g', 'kg', '斤', '两', 'ml', 'L', '个', '包', '袋', '盒', '瓶', '罐'
]

// 加载按商家分组的最新价格
const loadMerchantPrices = async () => {
  loadingMerchantPrices.value = true
  try {
    const response = await api.get(`/products/entity/${productId.value}/latest-price-by-merchant`)
    merchantPrices.value = response.prices || []
    merchantPriceUnit.value = response.unit || null
  } catch (e) {
    merchantPrices.value = []
    merchantPriceUnit.value = null
  } finally {
    loadingMerchantPrices.value = false
  }
}

// 加载同一原料下的关联商品
const loadSiblingProducts = async () => {
  if (!product.value?.ingredient_id) {
    siblingProducts.value = []
    return
  }

  loadingSiblings.value = true
  try {
    const response = await api.get('/products/entity', {
      params: {
        ingredient_ids: String(product.value.ingredient_id),
        limit: 50
      }
    })
    // 过滤掉当前商品
    const items = (response.items || []) as SiblingProduct[]
    siblingProducts.value = items.filter((item: SiblingProduct) => item.id !== productId.value)

    // 加载每个关联商品的最新价格
    for (const sibling of siblingProducts.value) {
      try {
        const detail = await api.get(`/products/entity/${sibling.id}`)
        sibling.latest_price = detail.latest_price
        sibling.latest_price_unit = detail.latest_price_unit
      } catch {
        // 忽略单个商品的加载失败
      }
    }
  } catch (e) {
    siblingProducts.value = []
  } finally {
    loadingSiblings.value = false
  }
}

// 合并对话框打开时重置选择
const onMergeDialogToggle = (open: boolean) => {
  if (open) {
    selectedMergeTarget.value = null
  }
}

// 执行合并
const doMerge = async () => {
  if (!selectedMergeTarget.value) return

  merging.value = true
  try {
    const result = await api.post(`/products/entity/${productId.value}/merge-into/${selectedMergeTarget.value.id}`)
    showMergeDialog.value = false
    const targetName = selectedMergeTarget.value.name
    selectedMergeTarget.value = null
    snackbar.value = { show: true, message: `已合并到「${targetName}」`, color: 'success' }
    // 跳转到目标商品详情页并重新加载数据
    await router.push(`/data/products/${result.target_id}`)
    loadData()
  } catch (e: any) {
    const msg = getErrorMessage(e, '合并失败')
    snackbar.value = { show: true, message: msg, color: 'error' }
  } finally {
    merging.value = false
  }
}

// 加载数据
const loadData = async () => {
  loading.value = true
  error.value = null

  try {
    // 只加载商品基本信息（名称、品牌、条码、标签、最新价格等）
    const response = await api.get(`/products/entity/${productId.value}`)
    product.value = response
    setDetailTitle(response.name, '商品', '商品详情')
    // 基本数据到位，立即渲染页面
    loading.value = false

    // 后台分别加载其他数据，互不影响
    loadMerchantPrices()
    loadPriceRecords()
    loadNutritionData()
    loadEntityUnits()
    loadDensity()
    loadUnmappedUnits()
    loadSiblingProducts()
  } catch (e: any) {
    console.error('加载商品失败', e)
    error.value = getErrorMessage(e, '加载失败')
    loading.value = false
  }
}

// 加载价格记录
const loadPriceRecords = async () => {
  loadingPrices.value = true
  try {
    const skip = (pricePage.value - 1) * pricePageSize.value
    const response = await api.get('/products', {
      params: {
        product_id: productId.value,
        skip,
        limit: pricePageSize.value
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
  if (!product.value?.ingredient_id) {
    nutritionData.value = null
    return
  }

  loadingNutrition.value = true
  try {
    const response = await api.get(`/nutrition/products/${productId.value}/nutrition`)
    nutritionData.value = response
  } catch (e) {
    nutritionData.value = null
  } finally {
    loadingNutrition.value = false
  }
}

// 加载商家列表
const loadMerchants = async () => {
  try {
    const response = await api.get('/merchants', { params: { limit: 100 } })
    merchants.value = response.items || []
  } catch (e) {
    merchants.value = []
  }
}

// 加载原料列表
const loadIngredients = async (searchText?: string) => {
  loadingIngredients.value = true
  try {
    const params: Record<string, any> = { limit: 100 }
    if (searchText) {
      params.q = searchText
    }
    const response = await api.get('/ingredients', { params })
    ingredients.value = response.items || []
  } catch (e: any) {
    console.error('加载原料列表失败', e)
  } finally {
    loadingIngredients.value = false
  }
}

// 监听原料搜索输入，防抖处理
let ingredientSearchTimeout: ReturnType<typeof setTimeout> | null = null
watch(ingredientSearch, (newVal) => {
  if (ingredientSearchTimeout) clearTimeout(ingredientSearchTimeout)
  ingredientSearchTimeout = setTimeout(() => {
    loadIngredients(newVal)
  }, 300)
})

// 监听选中的原料对象，同步 ingredient_id 到表单
watch(selectedIngredient, (newIngredient) => {
  basicEditForm.value.ingredient_id = newIngredient?.id || null
}, { immediate: true })

// === 基本信息内联编辑 ===
const startEditBasicInfo = () => {
  if (!product.value) return
  basicEditForm.value = {
    name: product.value.name || '',
    brand: product.value.brand || '',
    barcode: product.value.barcode || '',
    ingredient_id: product.value.ingredient_id || null,
    tags: [...(product.value.tags || [])],
    aliases: [...(product.value.aliases || [])],
  }
  // 加载原料列表
  if (product.value.ingredient_id) {
    loadIngredients().then(() => {
      const currentIngredient = ingredients.value.find(i => i.id === product.value.ingredient_id)
      if (currentIngredient) {
        selectedIngredient.value = currentIngredient
        ingredientSearch.value = currentIngredient.name
      } else {
        // 如果当前原料不在前 100 条结果中，单独获取并加入列表
        api.get(`/ingredients/${product.value!.ingredient_id}`).then((ingredient: Ingredient) => {
          if (ingredient) {
            ingredients.value.unshift(ingredient)
            selectedIngredient.value = ingredient
            ingredientSearch.value = ingredient.name
          }
        }).catch(err => {
          console.error('获取当前关联原料失败', err)
        })
      }
    })
  } else {
    loadIngredients()
  }
  editingBasicInfo.value = true
}

const cancelEditBasicInfo = () => {
  editingBasicInfo.value = false
  selectedIngredient.value = null
  ingredientSearch.value = ''
}

const saveBasicInfo = async () => {
  if (!basicEditForm.value.name.trim()) {
    showMessage('商品名称不能为空', 'error')
    return
  }
  if (!basicEditForm.value.ingredient_id) {
    showMessage('请选择关联的原料', 'error')
    return
  }

  saving.value = true
  try {
    const response = await api.put(`/products/entity/${productId.value}`, {
      name: basicEditForm.value.name,
      brand: basicEditForm.value.brand || null,
      barcode: basicEditForm.value.barcode || null,
      ingredient_id: basicEditForm.value.ingredient_id,
      tags: basicEditForm.value.tags,
      aliases: basicEditForm.value.aliases,
    })
    product.value = response
    // 重新加载营养数据（原料变更可能影响营养数据）
    await loadNutritionData()
    editingBasicInfo.value = false
    selectedIngredient.value = null
    ingredientSearch.value = ''
    showMessage('基本信息已保存', 'success')
  } catch (e: any) {
    showMessage(e.response?.data?.detail || e.message || '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

// === 营养成分内联编辑 ===
const startEditNutrition = () => {
  const items: NutritionEditItem[] = []
  // 只加载商品自身的自定义营养数据（mixin 模式：不显示从原料继承的）
  const customNutrients = nutritionData.value?.custom_nutrition_data?.all_nutrients || {}
  const addedKeys = new Set<string>()

  for (const [key, data] of Object.entries(customNutrients)) {
    if (!data || typeof data !== 'object' || !('value' in data)) continue

    let engKey = (data as any)?.original_key || (data as any)?.key || key
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

  // 按核心顺序排序
  const orderMap = new Map(NUTRIENT_DEFINITIONS.map((n, i) => [n.key, i]))
  items.sort((a, b) => {
    const oa = orderMap.get(a.key) ?? 999
    const ob = orderMap.get(b.key) ?? 999
    return oa - ob
  })

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

const onNutrientKeyChange = (index: number, newKey: string) => {
  if (!newKey) return
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
  if (!def.units.includes(oldUnit)) {
    item.unit = def.defaultUnit
  }
}

const onUnitChange = (index: number, newUnit: string) => {
  const item = nutritionEditItems.value[index]
  const oldUnit = item.unit
  if (oldUnit === newUnit) return
  if (item.value != null && item.value !== 0) {
    item.value = convertUnit(item.value, oldUnit, newUnit, item.key)
  }
  item.unit = newUnit
}

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
      // 商品允许删除全部覆盖数据，回退到继承原料的营养成分
      await api.put(`/products/entity/${productId.value}/nutrition`, null)
    } else {
      await api.post(`/nutrition/products/${productId.value}/nutrition`, {
        base_quantity: 100,
        base_unit: 'g',
        nutrients,
        source: 'custom',
      })
    }

    editingNutrition.value = false
    await loadNutritionData()
    showMessage('营养数据已保存', 'success')
  } catch (e: any) {
    showMessage(e.response?.data?.detail || e.message || '保存失败', 'error')
  } finally {
    savingNutrition.value = false
  }
}

// 保存价格记录
const savePriceRecord = async () => {
  if (!priceForm.value.price || !priceForm.value.quantity) return

  savingPrice.value = true
  try {
    await api.post('/products', {
      product_id: productId.value,
      product_name: product.value?.name,
      price: priceForm.value.price,
      original_quantity: priceForm.value.quantity,
      original_unit: priceForm.value.unit,
      merchant_id: priceForm.value.merchant_id
    })
    showAddPriceDialog.value = false
    // 重置表单
    priceForm.value = { price: 0, quantity: 1, unit: '斤', merchant_id: null }
    // 重新加载数据
    await loadData()
    showMessage('添加成功', 'success')
  } catch (e: any) {
    showMessage(e.response?.data?.detail || e.message || '添加失败', 'error')
  } finally {
    savingPrice.value = false
  }
}

// 删除价格记录
const deletePriceRecord = async (id: number) => {
  if (!confirm('确定删除此价格记录？')) return

  try {
    await api.delete(`/products/${id}`)
    await loadPriceRecords()
    showMessage('删除成功', 'success')
  } catch (e: any) {
    showMessage(e.response?.data?.detail || e.message || '删除失败', 'error')
  }
}

// 确认删除商品
const confirmDelete = () => {
  showDeleteDialog.value = true
}

// 拆分为原料
const handleSplitToIngredient = async () => {
  splitting.value = true
  try {
    const response = await api.post(`/products/entity/${productId.value}/split-to-ingredient`)
    showMessage(response.message || '拆分成功', 'success')
    router.push(`/data/ingredients/${response.ingredient_id}`)
  } catch (e: any) {
    const detail = e.response?.data?.detail || ''
    // 同名冲突（409）时，打开重命名对话框
    if (e.response?.status === 409) {
      splitRenameMessage.value = detail
      splitNewName.value = product.value?.name ? `${product.value.name}(新)` : ''
      showSplitRenameDialog.value = true
    } else {
      showMessage(getErrorMessage(e, '拆分失败'), 'error')
    }
  } finally {
    splitting.value = false
  }
}

// 用新名称确认拆分
const confirmSplitWithNewName = async () => {
  if (!splitNewName.value?.trim()) return
  splitting.value = true
  try {
    const response = await api.post(
      `/products/entity/${productId.value}/split-to-ingredient`,
      { new_name: splitNewName.value.trim() }
    )
    showSplitRenameDialog.value = false
    showMessage(response.message || '拆分成功', 'success')
    router.push(`/data/ingredients/${response.ingredient_id}`)
  } catch (e: any) {
    showMessage(getErrorMessage(e, '拆分失败'), 'error')
  } finally {
    splitting.value = false
  }
}

// 删除商品
const deleteProduct = async () => {
  deleting.value = true
  try {
    await api.delete(`/products/entity/${productId.value}`)
    showMessage('删除成功', 'success')
    router.push('/data/products')
  } catch (e: any) {
    showMessage(e.response?.data?.detail || e.message || '删除失败', 'error')
  } finally {
    deleting.value = false
  }
}

// 跳转到原料详情
const goToIngredient = () => {
  if (product.value?.ingredient_id) {
    router.push(`/data/ingredients/${product.value.ingredient_id}`)
  }
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

// 初始化
onMounted(() => {
  loadData()
  loadMerchants()
})
</script>

<style scoped>
.cursor-pointer {
  cursor: pointer;
}

.font-family-monospace {
  font-family: monospace;
}

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
  min-width: 0;
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

/* 移动端：flex 纵向堆叠 + CSS order 保持原顺序 */
.product-layout {
  display: flex;
  flex-direction: column;
}

.product-layout > .grid-item,
.group-mid-left > .grid-item,
.group-mid-right > .grid-item {
  margin: 16px;
}

/* 移动端：Group 2 容器透明化，子元素直接参与父 flex 流 */
.group-mid-wrapper {
  display: contents;
}
.group-mid-left, .group-mid-right {
  display: contents;
}

/* 移动端顺序（保持原模板顺序） */
.item-basic-info { order: 1; }
.item-latest-price { order: 2; }
.item-price-trend { order: 3; }
.item-price-records { order: 4; }
.item-nutrition { order: 5; }
.item-units { order: 6; }

/* 桌面端：CSS Grid + Flexbox 混合布局 */
@media (min-width: 960px) {
  .product-layout {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    padding: 16px;
  }

  .product-layout > .grid-item {
    margin: 0 !important;
  }

  /* Group 1: 基本信息 | 最新价格（行对齐） */
  .item-basic-info { grid-column: 1; grid-row: 1; }
  .item-latest-price { grid-column: 2; grid-row: 1; }

  /* Group 2: 单位与密度 | 价格趋势（行不对齐，独立高度） */
  .group-mid-wrapper {
    display: flex;
    grid-column: 1 / -1;
    grid-row: 2;
    gap: 16px;
    align-items: flex-start;
  }
  .group-mid-left, .group-mid-right {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-width: 0;
    gap: 16px;
  }
  .group-mid-left > .grid-item,
  .group-mid-right > .grid-item {
    margin: 0 !important;
  }

  /* Group 3: 营养成分 | 价格记录（行对齐） */
  .item-nutrition { grid-column: 1; grid-row: 3; }
  .item-price-records { grid-column: 2; grid-row: 3; }
}
</style>
