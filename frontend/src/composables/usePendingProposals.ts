import { ref } from 'vue'
import { api } from '@/api'
import { useUserStore } from '@/stores/user'

/**
 * 待审提议查询 composable。
 *
 * 列表页加载当前用户的所有 pending 提议（后端 /proposals 已按用户分流），
 * 按 `${entity_type}:${entity_id}` 建立索引，供列表项渲染"修改待审核"标记。
 *
 * create 类提议 entity_id 为 null（实体尚未存在），不参与列表标记。
 * 菜谱编辑提议 entity_type 为 "recipe_edit"，菜谱发布为 "recipe"，两者都需匹配。
 */
export function usePendingProposals() {
  // key: `${entityType}:${entityId}` → proposal 对象（仅 update/delete 类，entity_id 非 null）
  const pendingMap = ref<Map<string, any>>(new Map())
  // 原始 pending 提议列表（含 create 类，entity_id 可能为 null）
  const pendingList = ref<any[]>([])
  const loaded = ref(false)

  const buildKey = (entityType: string, entityId: number | string) => `${entityType}:${entityId}`

  const load = async () => {
    const userStore = useUserStore()
    // 管理员无需标记（管理员直写不产生 pending）；未登录跳过
    if (!userStore.user?.id || userStore.user?.is_admin) {
      pendingMap.value = new Map()
      pendingList.value = []
      loaded.value = true
      return
    }
    try {
      const resp = await api.get('/proposals', { params: { status: 'pending', limit: 200 } })
      const items: any[] = resp || []
      pendingList.value = items
      const map = new Map<string, any>()
      for (const p of items) {
        // 仅标记已存在实体的 update/delete 提议（entity_id 非 null）
        if (p.entity_id != null && p.action && p.action !== 'create') {
          const key = buildKey(p.entity_type, p.entity_id)
          // 同实体可能有多条，保留最新一条
          if (!map.has(key)) map.set(key, p)
        }
      }
      pendingMap.value = map
    } catch {
      pendingMap.value = new Map()
      pendingList.value = []
    } finally {
      loaded.value = true
    }
  }

  /**
   * 是否存在待审提议。entityTypes 支持传单个或多个（菜谱需查 recipe + recipe_edit）。
   */
  const has = (entityTypes: string | string[], entityId: number | string | undefined | null) => {
    if (entityId == null) return false
    const types = Array.isArray(entityTypes) ? entityTypes : [entityTypes]
    return types.some(t => pendingMap.value.has(buildKey(t, entityId)))
  }

  /**
   * 取待审提议对象（用于 tooltip 显示动作类型等）。
   */
  const get = (entityTypes: string | string[], entityId: number | string | undefined | null) => {
    if (entityId == null) return null
    const types = Array.isArray(entityTypes) ? entityTypes : [entityTypes]
    for (const t of types) {
      const p = pendingMap.value.get(buildKey(t, entityId))
      if (p) return p
    }
    return null
  }

  /**
   * 取待审 update 提议的有效 payload（已处理 recipe_edit 嵌套）。
   * 非 update（如 delete）或无提议时返回 null。供列表/详情做字段覆盖：
   *   const p = getPayload('ingredient', id); p?.name ?? item.name
   */
  const getPayload = (entityTypes: string | string[], entityId: number | string | undefined | null) => {
    const p = get(entityTypes, entityId)
    if (!p || p.action !== 'update') return null
    // recipe_edit 的 payload 结构为 {"update_data": {...}}
    const payload = p.payload || {}
    return payload.update_data || payload || null
  }

  /**
   * 按 payload 内的目标实体关联查询（用于 entity_unit_override / entity_density 等）。
   *
   * 这类实体的 create 提议 proposal.entity_id 为 null（新单位/密度尚未建立），
   * 但 payload 内含 entity_type + entity_id 指向所属实体（ingredient/product）。
   * 详情页据此判断"该商品/原料是否有待审的单位/密度提议"。
   */
  const hasByPayloadEntity = (
    proposalType: string,
    payloadEntityType: string,
    payloadEntityId: number | string | undefined | null,
  ) => {
    if (payloadEntityId == null) return false
    return pendingList.value.some(p =>
      p.entity_type === proposalType &&
      p.payload?.entity_type === payloadEntityType &&
      p.payload?.entity_id === payloadEntityId,
    )
  }

  const getByPayloadEntity = (
    proposalType: string,
    payloadEntityType: string,
    payloadEntityId: number | string | undefined | null,
  ) => {
    if (payloadEntityId == null) return null
    return pendingList.value.find(p =>
      p.entity_type === proposalType &&
      p.payload?.entity_type === payloadEntityType &&
      p.payload?.entity_id === payloadEntityId,
    ) || null
  }

  return { pendingMap, pendingList, loaded, load, has, get, getPayload, hasByPayloadEntity, getByPayloadEntity }
}
