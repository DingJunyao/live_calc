// Auth handler ? local mode user & auth endpoints.
// ???????????????? system_config?key: local_user_profile??
// ????????????????

import { getDb } from '../database'

const DEFAULT_USER = {
  id: 1,
  username: 'local',
  email: 'local@local.dev',
  phone: null,
  is_admin: true,
  is_active: true,
  email_verified: true,
  avatar: null,
  nickname: null,
  created_at: new Date().toISOString(),
  nutrition_goals: null,
  daily_budget: null,
  unit_preferences: {
    energy_unit: 'kcal',
    mass_unit: { id: 3, name: '?', abbreviation: '?' },
    volume_unit: null,
    price_unit: { id: 3, name: '?', abbreviation: '?' },
  },
  region_id: null,
}

const PROFILE_KEY = 'local_user_profile'

// ??????????????????????????? always ???
async function loadUserProfile(): Promise<any> {
  const db = await getDb()
  const row = await db.get('system_config', PROFILE_KEY)
  const saved = row?.value
  if (!saved) return { ...DEFAULT_USER }
  // ???????????unit_preferences ?????????
  return {
    ...DEFAULT_USER,
    ...saved,
    unit_preferences: { ...DEFAULT_USER.unit_preferences, ...(saved.unit_preferences || {}) },
  }
}

// ?? patch ???????????????
async function saveUserProfile(patch: Record<string, any>): Promise<any> {
  const current = await loadUserProfile()
  const updated = { ...current, ...patch }
  const db = await getDb()
  // ????? Vue Proxy??????????
  const plain = JSON.parse(JSON.stringify(updated))
  await db.put('system_config', { key: PROFILE_KEY, value: plain })
  return plain
}

export async function getConfig(): Promise<any> {
  return { require_invite_code: false }
}

export async function getMe(): Promise<any> {
  return await loadUserProfile()
}

export async function updateMe(_params: Record<string, string>, data?: any): Promise<any> {
  return await saveUserProfile(data || {})
}

export async function login(): Promise<any> {
  return { access_token: 'local-mode', refresh_token: 'local-mode', token_type: 'bearer' }
}

export async function register(): Promise<any> {
  return { access_token: 'local-mode', refresh_token: 'local-mode', token_type: 'bearer' }
}

export async function refresh(): Promise<any> {
  return { access_token: 'local-mode', refresh_token: 'local-mode', token_type: 'bearer' }
}

export async function postAvatar(): Promise<any> {
  // ????????? no-op?????????????
  return { url: null }
}

export async function updateAccount(_params: Record<string, string>, data?: any): Promise<any> {
  // ???????????????????region_id / nickname / username ?????
  const patch: Record<string, any> = { ...(data || {}) }
  delete patch.current_password
  delete patch.new_password
  return await saveUserProfile(patch)
}

export async function getPersonalStats(): Promise<any> {
  return { total_records: 0, total_products: 0, total_recipes: 0 }
}

export async function listUsers(_params: Record<string, string>, query?: any): Promise<any> {
  const page = parseInt(query?.page) || 1
  const pageSize = parseInt(query?.page_size) || 20
  return { items: [await loadUserProfile()], total: 1, page, page_size: pageSize }
}

export async function getUser(): Promise<any> {
  return await loadUserProfile()
}

export async function updateUser(_params: Record<string, string>, data?: any): Promise<any> {
  return await saveUserProfile(data || {})
}

export async function deleteUser(): Promise<any> {
  return { ok: true }
}
