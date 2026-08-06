// Hierarchy handler — ingredient parent/child relationships.

import { getDb, getById, addOne, putOne, deleteOne, getByIndex } from '../database'

export async function getHierarchy(params: Record<string, string>, _query?: any): Promise<any> {
  const id = parseInt(params.id)
  if (!Number.isFinite(id)) return { parent_relations: [], child_relations: [] }

  const db = await getDb()
  const [asParent, asChild] = await Promise.all([
    db.getAllFromIndex('ingredient_hierarchy', 'by_parent', id),
    db.getAllFromIndex('ingredient_hierarchy', 'by_child', id),
  ])

  // 收集涉及的原料 id，批量查名，组装成前端期望的 parent/child_name
  const ids = new Set<number>()
  ;[...asParent, ...asChild].forEach((r: any) => {
    if (r.parent_id != null) ids.add(r.parent_id)
    if (r.child_id != null) ids.add(r.child_id)
  })
  const nameMap: Record<number, string> = {}
  for (const iid of ids) {
    const ing = await getById('ingredients', iid)
    nameMap[iid] = ing?.name || `#${iid}`
  }

  const build = (r: any) => ({
    id: r.id,
    parent_id: r.parent_id,
    parent_name: nameMap[r.parent_id] || `#${r.parent_id}`,
    child_id: r.child_id,
    child_name: nameMap[r.child_id] || `#${r.child_id}`,
    relation_type: r.relation_type || r.relationship_type || 'contains',
    strength: r.strength ?? r.confidence ?? 100,
    created_at: r.created_at,
  })

  return {
    // 当前原料是子（被包含/回退源）→ 父关系
    parent_relations: asChild.map(build),
    // 当前原料是父（包含/回退到子）→ 子关系
    child_relations: asParent.map(build),
  }
}

export async function addHierarchyRelation(params: Record<string, string>): Promise<any> {
  const parentId = parseInt(params.parent_id)
  const childId = parseInt(params.child_id)

  // Check for duplicate
  const existing = await getByIndex('ingredient_hierarchy', 'by_parent', parentId)
  const dup = existing.find((r: any) => r.child_id === childId)
  if (dup) {
    return dup
  }

  const id = await addOne('ingredient_hierarchy', {
    parent_id: parentId,
    child_id: childId,
    created_at: new Date().toISOString(),
  })
  return await getById('ingredient_hierarchy', id as number)
}

export async function updateHierarchyRelation(params: Record<string, string>, data?: any): Promise<any> {
  const parentId = parseInt(params.parent_id)
  const childId = parseInt(params.child_id)

  const existing = await getByIndex('ingredient_hierarchy', 'by_parent', parentId)
  const relation = existing.find((r: any) => r.child_id === childId)
  if (!relation) throw { status: 404, message: `Hierarchy relation not found for parent ${parentId}, child ${childId}` }

  await putOne('ingredient_hierarchy', { ...relation, ...data, updated_at: new Date().toISOString() })
  return await getById('ingredient_hierarchy', relation.id)
}

export async function deleteHierarchyRelation(params: Record<string, string>): Promise<any> {
  const parentId = parseInt(params.parent_id)
  const childId = parseInt(params.child_id)

  const existing = await getByIndex('ingredient_hierarchy', 'by_parent', parentId)
  const relation = existing.find((r: any) => r.child_id === childId)
  if (!relation) throw { status: 404, message: `Hierarchy relation not found for parent ${parentId}, child ${childId}` }

  await deleteOne('ingredient_hierarchy', relation.id)
  return { ok: true }
}

export async function createHierarchy(_params: Record<string, string>, data?: any): Promise<any> {
  const id = await addOne('ingredient_hierarchy', {
    ...data,
    created_at: new Date().toISOString(),
  })
  return await getById('ingredient_hierarchy', id as number)
}
