// Administrative regions handler (lazy-load tree selector) - local mode
// Data stored in IndexedDB 'regions' store; seed from src/data/regions/*.json
import { getAll, getDb } from '../database'

interface RegionRow {
  id: number
  code: string
  name: string
  name_en?: string | null
  level: number
  parent_id?: number | null
  iso_country?: string | null
  path?: string | null
  is_active?: boolean
}

function isActive(r: any): boolean {
  return r.is_active !== false
}

function buildParentSet(rows: any[]): Set<number> {
  const set = new Set<number>()
  for (const r of rows) {
    if (isActive(r) && r.parent_id != null) set.add(Number(r.parent_id))
  }
  return set
}

// GET /regions - lazy-load children by parent_id or level (default level=0)
export async function listRegions(
  _params: Record<string, string>,
  query?: any,
): Promise<any[]> {
  const all: any[] = await getAll('regions')
  const active = all.filter(isActive)

  let subset: any[]
  if (query?.parent_id != null && query.parent_id !== '') {
    const pid = Number(query.parent_id)
    subset = active.filter((r) => Number(r.parent_id) === pid)
  } else if (query?.level != null && query.level !== '') {
    const lv = Number(query.level)
    subset = active.filter((r) => Number(r.level) === lv)
  } else {
    subset = active.filter((r) => Number(r.level) === 0)
  }

  subset.sort((a, b) => String(a.code || '').localeCompare(String(b.code || '')))

  const parentSet = buildParentSet(active)
  return subset.map((r) => ({
    id: r.id,
    code: r.code,
    name: r.name,
    name_en: r.name_en ?? null,
    level: r.level,
    iso_country: r.iso_country ?? null,
    path: r.path ?? null,
    has_children: parentSet.has(Number(r.id)),
  }))
}

// GET /regions/:id - detail with ancestor chain parsed from path field
export async function getRegion(params: Record<string, string>): Promise<any> {
  const id = Number(params.id)
  const all: any[] = await getAll('regions')
  const region = all.find((r) => Number(r.id) === id && isActive(r))
  if (!region) throw { status: 404, message: '\u533a\u5212\u4e0d\u5b58\u5728' }

  const ancestors: any[] = []
  const pathCodes = String(region.path || '').split('/').filter(Boolean)
  for (const code of pathCodes) {
    if (code === region.code) continue
    const anc = all.find((r) => r.code === code && isActive(r))
    if (anc) {
      ancestors.push({ id: anc.id, code: anc.code, name: anc.name, level: anc.level })
    }
  }

  const parentSet = buildParentSet(all.filter(isActive))
  return {
    id: region.id,
    code: region.code,
    name: region.name,
    name_en: region.name_en ?? null,
    level: region.level,
    iso_country: region.iso_country ?? null,
    path: region.path ?? null,
    has_children: parentSet.has(Number(region.id)),
    ancestors,
  }
}

// GET /admin/regions/seed-status
export async function seedStatus(): Promise<any> {
  const all: any[] = await getAll('regions')
  const active = all.filter(isActive)
  const counts: Record<string, number> = { '0': 0, '1': 0, '2': 0, '3': 0 }
  for (const r of active) {
    const lv = String(r.level)
    if (lv in counts) counts[lv]++
  }
  const cnProvinces = active.filter(
    (r) => Number(r.level) === 1 && r.iso_country === 'CN',
  ).length
  return {
    counts,
    needed: cnProvinces === 0,
    total: active.length,
  }
}

// POST /admin/regions/seed - upsert all region data from JSON files
// Uses dynamic import() instead of fetch() to bypass service worker interception
export async function seedRegions(): Promise<any> {
  const [countriesMod, chinaMod, namesMod] = await Promise.all([
    import('../../../data/regions/countries.json'),
    import('../../../data/regions/china_pca.json'),
    import('../../../data/regions/country_names_zh.json'),
  ])
  const countries = countriesMod.default
  const china = chinaMod.default
  const namesZh = namesMod.default

  // Read existing for upsert; determine starting id
  const existing: any[] = await getAll('regions')
  const codeMap = new Map<string, any>()
  let maxId = 0
  for (const r of existing) {
    if (r.code) codeMap.set(r.code, r)
    const n = Number(r.id)
    if (Number.isFinite(n) && n > maxId) maxId = n
  }
  let nextId = maxId + 1
  let created = 0
  let skipped = 0
  const records: any[] = []

  function upsert(
    code: string,
    name: string,
    level: number,
    parentId: number | null,
    isoCountry: string,
    path: string,
    nameEn?: string,
  ): number {
    const row = codeMap.get(code)
    if (row) {
      row.name = name
      row.level = level
      row.parent_id = parentId
      row.iso_country = isoCountry
      row.path = path
      if (nameEn !== undefined) row.name_en = nameEn
      row.is_active = true
      records.push(row)
      skipped++
      return row.id
    }
    const newRegion: RegionRow = {
      id: nextId++,
      code,
      name,
      name_en: nameEn ?? null,
      level,
      parent_id: parentId,
      iso_country: isoCountry,
      path,
      is_active: true,
    }
    codeMap.set(code, newRegion)
    records.push(newRegion)
    created++
    return newRegion.id
  }

  // Countries (level 0)
  for (const c of countries) {
    const alpha2 = c['alpha-2'] || ''
    const enName = c.name || ''
    if (!alpha2 || !enName) continue
    const zh = namesZh[alpha2] || enName
    upsert(alpha2, zh, 0, null, alpha2, alpha2, enName)
  }

  // Ensure China exists
  let cnId: number
  const cnRow = codeMap.get('CN')
  if (cnRow) {
    cnId = cnRow.id
  } else {
    cnId = upsert('CN', '\u4e2d\u56fd', 0, null, 'CN', 'CN', 'China')
  }

  // China provinces / cities / counties (level 1/2/3)
  for (const prov of china) {
    const pCode = prov.code
    const pName = prov.name
    const pId = upsert(pCode, pName, 1, cnId, 'CN', 'CN/' + pCode)
    for (const city of prov.children || []) {
      const cCode = city.code
      const cName = city.name
      const cId = upsert(cCode, cName, 2, pId, 'CN', 'CN/' + pCode + '/' + cCode)
      for (const county of city.children || []) {
        upsert(
          county.code,
          county.name,
          3,
          cId,
          'CN',
          'CN/' + pCode + '/' + cCode + '/' + county.code,
        )
      }
    }
  }

  // Bulk write in a single transaction
  const db = await getDb()
  const tx = db.transaction('regions', 'readwrite')
  // Fire all puts without awaiting each (IndexedDB processes them in order within the tx)
  for (const r of records) {
    tx.store.put(r)
  }
  await tx.done

  return { created, skipped, errors: 0 }
}
