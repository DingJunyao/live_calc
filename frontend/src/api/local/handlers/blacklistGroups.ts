// Local handler for admin blacklist-group management endpoints.
// 对齐云端 /admin/blacklist-groups 契约（列表返回数组，其余返回分组对象）。
import { getAll, getById, addOne, putOne, getByIndex } from '../database'

interface BlGroupRow {
  id: number
  name: string
  display_order?: number
  is_active?: boolean
  created_at?: string
}

interface BlGroupIngRow {
  id: number
  group_id: number
  ingredient_id: number
  is_ai_matched?: boolean
  is_active?: boolean
  created_at?: string
}

async function buildGroupResponse(group: BlGroupRow): Promise<any> {
  const allIngs = await getByIndex<BlGroupIngRow>('blacklist_group_ingredients', 'by_group_id', group.id)
  const active = allIngs.filter((r) => r.is_active !== false)
  const ingredients = []
  for (const r of active) {
    const ing = await getById<{ id: number; name: string }>('ingredients', r.ingredient_id)
    ingredients.push({
      id: r.id,
      ingredient_id: r.ingredient_id,
      ingredient_name: ing?.name ?? null,
      is_ai_matched: r.is_ai_matched ?? false,
    })
  }
  return {
    id: group.id,
    name: group.name,
    display_order: group.display_order ?? 0,
    is_active: group.is_active !== false,
    ingredients,
    ingredient_count: ingredients.length,
    created_at: group.created_at ?? null,
  }
}

export async function listGroups(): Promise<any> {
  const all = await getAll<BlGroupRow>('blacklist_groups')
  const active = all
    .filter((g) => g.is_active !== false)
    .sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0) || a.id - b.id)
  return Promise.all(active.map(buildGroupResponse))
}

export async function createGroup(_params: Record<string, string>, data?: any): Promise<any> {
  const all = await getAll<BlGroupRow>('blacklist_groups')
  if (all.some((g) => g.name === data?.name)) {
    throw { status: 400, message: '分组名已存在' }
  }
  const now = new Date().toISOString()
  const id = await addOne('blacklist_groups', {
    name: data?.name,
    display_order: data?.display_order ?? 0,
    is_active: true,
    created_at: now,
  })
  const group = await getById<BlGroupRow>('blacklist_groups', id as number)
  return buildGroupResponse(group!)
}

export async function updateGroup(params: Record<string, string>, data?: any): Promise<any> {
  const id = parseInt(params.id)
  const group = await getById<BlGroupRow>('blacklist_groups', id)
  if (!group) throw { status: 404, message: '分组不存在' }
  await putOne('blacklist_groups', {
    ...group,
    name: data?.name ?? group.name,
    display_order: data?.display_order ?? group.display_order ?? 0,
    is_active: data?.is_active ?? group.is_active ?? true,
  })
  const updated = await getById<BlGroupRow>('blacklist_groups', id)
  return buildGroupResponse(updated!)
}

export async function deleteGroup(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  const group = await getById<BlGroupRow>('blacklist_groups', id)
  if (!group) throw { status: 404, message: '分组不存在' }
  // 软删除：与云端一致，仅置 is_active=false
  await putOne('blacklist_groups', { ...group, is_active: false })
  return { message: '已删除' }
}

export async function addIngredients(params: Record<string, string>, data?: any): Promise<any> {
  const groupId = parseInt(params.id)
  const group = await getById<BlGroupRow>('blacklist_groups', groupId)
  if (!group) throw { status: 404, message: '分组不存在' }
  const ingredientIds: number[] = data?.ingredient_ids || []
  const existing = await getByIndex<BlGroupIngRow>('blacklist_group_ingredients', 'by_group_id', groupId)
  const now = new Date().toISOString()
  for (const ingId of ingredientIds) {
    const dup = existing.find((r) => r.ingredient_id === ingId)
    if (dup) {
      if (dup.is_active === false) {
        await putOne('blacklist_group_ingredients', { ...dup, is_active: true })
      }
    } else {
      await addOne('blacklist_group_ingredients', {
        group_id: groupId,
        ingredient_id: ingId,
        is_ai_matched: false,
        is_active: true,
        created_at: now,
      })
    }
  }
  return buildGroupResponse(group)
}

export async function removeIngredient(params: Record<string, string>): Promise<any> {
  const groupId = parseInt(params.id)
  const ingredientId = parseInt(params.ingredientId)
  const rows = await getByIndex<BlGroupIngRow>('blacklist_group_ingredients', 'by_group_id', groupId)
  const row = rows.find((r) => r.ingredient_id === ingredientId && r.is_active !== false)
  if (!row) throw { status: 404, message: '该原料不在分组中' }
  await putOne('blacklist_group_ingredients', { ...row, is_active: false })
  return { message: '已移除' }
}

// 本地模式无 AI 服务与过敏原种子数据，以下端点降级返回
export async function aiMatch(): Promise<any> {
  return { agent_session_id: 0, message: '本地模式暂不支持 AI 匹配' }
}

export async function allergensStatus(): Promise<any> {
  return { needed: false, missing_groups: [], empty_groups: [] }
}

export async function seedAllergens(): Promise<any> {
  return { message: '本地模式无需导入过敏原分组' }
}
