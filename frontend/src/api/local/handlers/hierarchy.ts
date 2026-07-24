// Hierarchy handler — ingredient parent/child relationships.

import { getDb, getAll, getById, addOne, putOne, deleteOne, getByIndex } from '../database'

export async function getHierarchy(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  const db = await getDb()
  const [asParent, asChild] = await Promise.all([
    db.getAllFromIndex('ingredient_hierarchy', 'by_parent', id),
    db.getAllFromIndex('ingredient_hierarchy', 'by_child', id),
  ])
  return {
    parents: asChild.map((r: any) => r.parent_id),
    children: asParent.map((r: any) => r.child_id),
    relations: {
      as_parent: asParent,
      as_child: asChild,
    },
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
