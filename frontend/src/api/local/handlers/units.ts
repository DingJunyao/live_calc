// Units handler — CRUD for units and unit conversions.

import { getAll, getById, addOne, putOne, getByIndex } from '../database'

export async function listUnits(_params: Record<string, string>, query?: any): Promise<any> {
  const all = await getAll('units')
  const unitType = query?.unit_type
  const filtered = unitType ? all.filter((u: any) => u.unit_type === unitType) : all
  return { items: filtered, total: filtered.length }
}

export async function getUnit(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  const unit = await getById('units', id)
  if (!unit) throw { status: 404, message: `Unit ${id} not found` }
  return unit
}

export async function createUnit(_params: Record<string, string>, data?: any): Promise<any> {
  const id = await addOne('units', {
    ...data,
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  })
  return await getById('units', id as number)
}

export async function updateUnit(params: Record<string, string>, data?: any): Promise<any> {
  const id = parseInt(params.id)
  const existing = await getById('units', id)
  if (!existing) throw { status: 404, message: `Unit ${id} not found` }
  await putOne('units', { ...existing, ...data, id, updated_at: new Date().toISOString() })
  return await getById('units', id)
}

export async function deleteUnit(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  const existing = await getById('units', id)
  if (!existing) throw { status: 404, message: `Unit ${id} not found` }
  await putOne('units', { ...existing, id, is_active: false, updated_at: new Date().toISOString() })
  return { ok: true }
}

export async function convertUnits(_params: Record<string, string>, data?: any): Promise<any> {
  const { value, from_unit_id, to_unit_id } = data || {}
  if (from_unit_id === to_unit_id) {
    return { value, unit_id: to_unit_id }
  }
  // Look for direct conversion
  const fromConversions = await getByIndex('unit_conversions', 'by_from_unit', from_unit_id)
  const direct = fromConversions.find((c: any) => c.to_unit_id === to_unit_id)
  if (direct) {
    return { value: value * direct.factor, unit_id: to_unit_id }
  }
  // Reverse conversion
  const toConversions = await getByIndex('unit_conversions', 'by_from_unit', to_unit_id)
  const reverse = toConversions.find((c: any) => c.to_unit_id === from_unit_id)
  if (reverse) {
    return { value: value / reverse.factor, unit_id: to_unit_id }
  }
  throw { status: 400, message: `No conversion found between units ${from_unit_id} and ${to_unit_id}` }
}

export async function listUnitConversions(params: Record<string, string>): Promise<any> {
  const id = parseInt(params.id)
  const all = await getAll('unit_conversions')
  return all.filter((c: any) => c.from_unit_id === id || c.to_unit_id === id)
}
