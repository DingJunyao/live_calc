// 本地存储 URL 路由引擎。
// 将 API 路径（/api/v1/...）映射到 IndexedDB 处理函数模块。
// ROUTES 表由各业务域模块在应用初始化时填充。

// ============================================================
// Handler 模块接口
// ============================================================

export interface HandlerModule {
  get?: (params: Record<string, string>, query?: any) => Promise<any>
  post?: (params: Record<string, string>, data?: any) => Promise<any>
  put?: (params: Record<string, string>, data?: any) => Promise<any>
  delete?: (params: Record<string, string>) => Promise<any>
}

// ============================================================
// 路由定义
// ============================================================

interface Route {
  pattern: RegExp
  paramNames: string[]
  module: HandlerModule
}

/** 路由表 — 初始为空，由各业务域模块通过 addRoutes / addRoute 注册。 */
export const ROUTES: Route[] = []

/**
 * 注册一组路由。
 * @param basePath  路径前缀，如 '/ingredients'
 * @param module    处理该路径下各 HTTP 方法的 HandlerModule
 */
export function addRoutes(basePath: string, module: HandlerModule): void {
  ROUTES.push({
    pattern: new RegExp(`^${escapeRegex(basePath)}$`),
    paramNames: [],
    module,
  })
}

/**
 * 注册带路径参数的单条路由。
 * 路径中的 :param 段会被转换为命名捕获组。
 * 如 '/ingredients/:id' → 匹配 /ingredients/123 并将 { id: '123' } 传给 handler。
 */
export function addRoute(pattern: string, module: HandlerModule): void {
  const paramNames: string[] = []
  const regexStr = pattern.replace(/:([a-zA-Z_][a-zA-Z0-9_]*)/g, (_match, name) => {
    paramNames.push(name)
    return '([^/]+)'
  })
  ROUTES.push({
    pattern: new RegExp(`^${regexStr}$`),
    paramNames,
    module,
  })
}

/** 对路由 basePath 中的特殊字符做转义，使其安全嵌入正则。 */
function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

// ============================================================
// 路由解析与派发
// ============================================================

export interface RouteResult {
  handler: Function
  pathParams: Record<string, string>
}

/**
 * 将 HTTP 方法 + URL 解析为对应的 handler。
 * 自动去除 /api/v1 前缀。
 * 匹配失败时抛出 { status, message } 与 Axios 错误格式兼容。
 */
export function parseRoute(method: string, url: string): RouteResult {
  const path = url.replace(/^\/api\/v1/, '') || '/'

  for (const route of ROUTES) {
    const match = path.match(route.pattern)
    if (match) {
      const pathParams: Record<string, string> = {}
      route.paramNames.forEach((name, i) => {
        pathParams[name] = match[i + 1]
      })
      const handler = (route.module as any)[method.toLowerCase()]
      if (typeof handler !== 'function') {
        throw { status: 405, message: `Method ${method} not allowed for ${url}` }
      }
      return { handler, pathParams }
    }
  }

  throw { status: 404, message: `Route not found: ${method} ${url}` }
}

// ============================================================
// 导出入口函数
// ============================================================

export async function localGet(url: string, query?: any): Promise<any> {
  const { handler, pathParams } = parseRoute('get', url)
  return handler(pathParams, query)
}

export async function localPost(url: string, data?: any): Promise<any> {
  const { handler, pathParams } = parseRoute('post', url)
  return handler(pathParams, data)
}

export async function localPut(url: string, data?: any): Promise<any> {
  const { handler, pathParams } = parseRoute('put', url)
  return handler(pathParams, data)
}

export async function localDelete(url: string): Promise<any> {
  const { handler, pathParams } = parseRoute('delete', url)
  return handler(pathParams)
}

// ============================================================
// 路由注册 — 各业务域处理函数
// ============================================================

import * as auth from './handlers/auth'
import * as units from './handlers/units'
import * as products from './handlers/products'
import * as ingredients from './handlers/ingredients'
import * as merchants from './handlers/merchants'
import * as nutrition from './handlers/nutrition'
import * as hierarchy from './handlers/hierarchy'
import * as blacklist from './handlers/blacklist'
import * as admin from './handlers/admin'
import * as recipes from './handlers/recipes'
import * as meals from './handlers/meals'
import * as sparklines from './handlers/sparklines'
import * as usda from './handlers/usda'
import * as agents from './handlers/agents'

// ---- Auth ----
addRoute('/auth/config', { get: auth.getConfig })
addRoute('/auth/me', { get: auth.getMe, put: auth.updateMe })
addRoute('/auth/login', { post: auth.login })
addRoute('/auth/register', { post: auth.register })
addRoute('/auth/refresh', { post: auth.refresh })
addRoute('/auth/me/avatar', { post: auth.postAvatar })
addRoute('/auth/me/account', { put: auth.updateAccount })
addRoute('/auth/personal-stats', { get: auth.getPersonalStats })
addRoute('/auth/users', { get: auth.listUsers })
addRoute('/auth/users/:id', { get: auth.getUser, put: auth.updateUser, delete: auth.deleteUser })

// ---- USDA ----
addRoute('/usda/search', { get: usda.searchUsda })
addRoute('/usda/:fdcId', { get: usda.getUsdaFood })
addRoute('/usda/preview-nutrition', { get: usda.previewNutrition })
addRoute('/usda/match/ingredient/:ingredientId', { post: usda.matchIngredient })
addRoute('/usda/match/product/:productId', { post: usda.matchProduct })
addRoute('/admin/usda/download', { post: usda.downloadUsda })

// ---- Units ----
addRoute('/units', { get: units.listUnits, post: units.createUnit })
addRoute('/units/convert', { post: units.convertUnits })
addRoute('/units/:id', { get: units.getUnit, put: units.updateUnit, delete: units.deleteUnit })
addRoute('/units/:id/conversions', { get: units.listUnitConversions })

// ---- Products (exact sub-paths before param paths) ----
addRoute('/products/entity', { get: products.listEntity, post: products.createEntity })
addRoute('/products/entity/:id', { get: products.getEntity, put: products.updateEntity, delete: products.deleteEntity })
addRoute('/products/entity/:id/barcodes', { get: products.listBarcodes, post: products.addBarcode })
addRoute('/products/entity/:id/latest-price', { get: products.getLatestPrice })
addRoute('/products/autocomplete', { get: products.autocomplete })
addRoute('/products', { get: products.listRecords, post: products.createRecord })
addRoute('/products/:id', { put: products.updateRecord, delete: products.deleteRecord })
addRoute('/products/:id/my-weight', { get: products.getWeight, put: products.setWeight, delete: products.deleteWeight })

// ---- Ingredients (exact sub-paths before param paths) ----
addRoute('/ingredients/categories', { get: ingredients.listCategories })
addRoute('/ingredients/merge', { post: ingredients.mergeIngredients })
addRoute('/ingredients/batch-create-products', { post: ingredients.batchCreateProducts })
addRoute('/ingredients/search-by-name/:name', { get: ingredients.searchByName })
addRoute('/ingredients/hierarchy', { post: hierarchy.createHierarchy })
addRoute('/ingredients/hierarchy/:id', { get: hierarchy.getHierarchy })
addRoute('/ingredients/:id', { get: ingredients.getIngredient, put: ingredients.updateIngredient, delete: ingredients.deleteIngredient })
addRoute('/ingredients', { get: ingredients.listIngredients, post: ingredients.createIngredient })
addRoute('/ingredients/:parent_id/hierarchy/:child_id', {
  post: hierarchy.addHierarchyRelation,
  put: hierarchy.updateHierarchyRelation,
  delete: hierarchy.deleteHierarchyRelation,
})

// ---- Merchants ----
addRoute('/merchants/map-config', { get: merchants.getMapConfig })
addRoute('/merchants/favorites', { get: merchants.listFavorites })
addRoute('/merchants/coordinates', { get: merchants.getCoordinates })
addRoute('/merchants/places', { get: merchants.listUserPlaces })
addRoute('/merchants/:id', { get: merchants.getMerchant, put: merchants.updateMerchant, delete: merchants.deleteMerchant })
addRoute('/merchants/:id/favorite', { post: merchants.addFavorite, delete: merchants.removeFavorite })
addRoute('/merchants/:id/prices', { get: merchants.getMerchantPrices })
addRoute('/merchants/:id/product-prices', { get: merchants.getMerchantProductPrices })
addRoute('/merchants', { get: merchants.listMerchants, post: merchants.createMerchant })

// ---- Nutrition ----
addRoute('/nutrition/ingredients', { get: nutrition.listNutritionIngredients })
addRoute('/nutrition/ingredients/:id', { get: nutrition.getNutritionIngredient })
addRoute('/nutrition/ingredients/:id/nutrition', { get: nutrition.getIngredientNutrition, post: nutrition.updateIngredientNutrition })
addRoute('/nutrition/ingredients/:id/nutrition/base', { get: nutrition.getIngredientNutritionBase })
addRoute('/nutrition/ingredients/:id/latest-price', { get: nutrition.getLatestPrice })
addRoute('/nutrition/ingredients/:id/latest-price-by-merchant', { get: nutrition.getLatestPriceByMerchant })
addRoute('/nutrition/ingredients/:id/product-weights', { get: nutrition.getProductWeights })
addRoute('/nutrition/products/:id/nutrition', { get: nutrition.getProductNutrition, post: nutrition.updateProductNutrition })
addRoute('/nutrition/search', { get: nutrition.searchNutrition })

// ---- Blacklist ----
addRoute('/blacklist/ingredient-ids', { get: blacklist.getEffectiveIngredientIds })
addRoute('/blacklist/groups', { get: blacklist.listBlacklistGroups, post: blacklist.subscribeToGroups })
addRoute('/blacklist/groups/:id', { delete: blacklist.unsubscribeFromGroup })
addRoute('/blacklist/:ingredient_id', { delete: blacklist.removeFromBlacklist })
addRoute('/blacklist', { get: blacklist.listBlacklist, post: blacklist.addToBlacklist })

// ---- Admin ----
addRoute('/admin/map-config', { get: admin.getMapConfig, put: admin.updateMapConfig })
addRoute('/admin/config', { get: admin.getConfig })
addRoute('/admin/stats', { get: admin.getStats })
addRoute('/admin/storage-config', { get: admin.getStorageConfig, put: admin.updateStorageConfig })
addRoute('/admin/email-templates', { get: admin.listEmailTemplates })
addRoute('/admin/email-templates/:key', { put: admin.updateEmailTemplate })
addRoute('/admin/map-api-keys', { get: admin.getMapApiKeys, put: admin.updateMapApiKeys })
addRoute('/admin/images/scan', { post: admin.scanImages })
addRoute('/admin/images/unused', { get: admin.getUnusedImages })
addRoute('/admin/email-config/smtp', { get: admin.getSmtpConfig, put: admin.updateSmtpConfig })
addRoute('/admin/email-config/templates', { get: admin.listTemplates })
addRoute('/admin/email-config/templates/:key', { get: admin.getEmailTemplate, put: admin.updateEmailTemplate })
addRoute('/admin/translation-config', { get: admin.getTranslationConfig, put: admin.updateTranslationConfig })
addRoute('/admin/translation-config/test', { post: admin.testTranslationConnection })

// ---- Recipes (exact sub-paths before param paths) ----
addRoute('/recipes/batch-cost', { post: recipes.batchCost })
addRoute('/recipes', { get: recipes.listRecipes, post: recipes.createRecipe })
addRoute('/recipes/:id', { get: recipes.getRecipe, put: recipes.updateRecipe, delete: recipes.deleteRecipe })
addRoute('/recipes/:id/cost', { get: recipes.getRecipeCost })
addRoute('/recipes/:id/nutrition', { get: recipes.getRecipeNutrition })
addRoute('/recipes/:id/cost-history', { get: recipes.getCostHistory })
addRoute('/recipes/:id/cost-history-range', { get: recipes.getCostHistoryRange })
addRoute('/recipes/:id/merchant-costs', { get: recipes.getMerchantCosts })
addRoute('/recipes/:id/publish', { post: recipes.publishRecipe })
addRoute('/recipes/:id/images', { post: recipes.uploadImage })
addRoute('/recipes/:id/images/:filename', { delete: recipes.deleteImage })

// ---- Meals ----
addRoute('/meals/recommendations/generate', { post: meals.generate })
addRoute('/meals/recommendations/refresh', { post: meals.refresh })
addRoute('/meals/recommendations', { get: meals.getRecommendations })

// ---- Sparklines ----
addRoute('/sparklines/products', { get: sparklines.getProductSparklines })
addRoute('/sparklines/ingredients', { get: sparklines.getIngredientSparklines })

// ---- Agent ----
addRoute('/agent/task-types', { get: agents.getTaskTypes })
addRoute('/agent/sessions/:id/messages', { post: agents.postMessage })
addRoute('/agent/sessions/:id/cancel', { post: agents.cancelSession })
addRoute('/agent/sessions/:id', { get: agents.getSession })
addRoute('/agent/sessions', { get: agents.listSessions, post: agents.createSession })
