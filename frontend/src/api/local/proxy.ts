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
