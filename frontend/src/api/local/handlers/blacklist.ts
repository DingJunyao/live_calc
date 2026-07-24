// Blacklist handler — ingredient blacklist and group subscriptions.

import { getAll, getById, addOne, deleteOne, getByIndex, getDb } from '../database'

export async function listBlacklist(_params: Record<string, string>, query?: any): Promise<any> {
  const all = await getAll('blacklist_group_ingredients')
  return { items: all, total: all.length }
}

export async function addToBlacklist(_params: Record<string, string>, data?: any): Promise<any> {
  const existing = await getByIndex('blacklist_group_ingredients', 'by_ingredient_id', data.ingredient_id)
  const dup = existing.find((r: any) => r.group_id === (data.group_id || data.groupId))
  if (dup) return dup

  const id = await addOne('blacklist_group_ingredients', {
    ...data,
    created_at: new Date().toISOString(),
  })
  return await getById('blacklist_group_ingredients', id as number)
}

export async function removeFromBlacklist(params: Record<string, string>): Promise<any> {
  const ingredientId = parseInt(params.ingredient_id)
  const existing = await getByIndex('blacklist_group_ingredients', 'by_ingredient_id', ingredientId)
  for (const item of existing) {
    await deleteOne('blacklist_group_ingredients', item.id)
  }
  return { ok: true }
}

export async function listBlacklistGroups(_params: Record<string, string>): Promise<any> {
  const all = await getAll('blacklist_groups')
  return { items: all, total: all.length }
}

export async function subscribeToGroups(_params: Record<string, string>, data?: any): Promise<any> {
  const groupIds: number[] = data?.group_ids || data?.groupIds || []
  for (const gid of groupIds) {
    await addOne('blacklist_subscriptions', {
      group_id: gid,
      created_at: new Date().toISOString(),
    })
  }
  return { ok: true }
}

export async function unsubscribeFromGroup(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  const existing = await getByIndex('blacklist_subscriptions', 'by_group_id', id)
  for (const sub of existing) {
    await deleteOne('blacklist_subscriptions', sub.id)
  }
  return { ok: true }
}

export async function getEffectiveIngredientIds(_params: Record<string, string>): Promise<any> {
  // Get all blacklisted ingredient IDs by combining:
  // 1. Direct blacklist entries
  // 2. Group subscriptions' ingredients
  const [subscriptions, entries] = await Promise.all([
    getAll('blacklist_subscriptions'),
    getAll('blacklist_group_ingredients'),
  ])

  const subscribedGroupIds = new Set(subscriptions.map((s: any) => s.group_id))
  const ingredientIds = new Set<number>()

  for (const entry of entries) {
    if (subscribedGroupIds.has(entry.group_id)) {
      ingredientIds.add(entry.ingredient_id)
    }
  }

  return { ingredient_ids: Array.from(ingredientIds) }
}
