// Auth handler — local mode user & auth endpoints.
// Returns a static local user for all identity-related endpoints.

const localUser = {
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
    mass_unit: { id: 3, name: '斤', abbreviation: '斤' },
    volume_unit: null,
    price_unit: { id: 3, name: '斤', abbreviation: '斤' },
  },
  region_id: null,
}

export async function getConfig(): Promise<any> {
  return { require_invite_code: false }
}

export async function getMe(): Promise<any> {
  return { ...localUser }
}

export async function updateMe(_params: Record<string, string>, data?: any): Promise<any> {
  return { ...localUser, ...(data || {}) }
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
  return { url: null }
}

export async function updateAccount(_params: Record<string, string>, data?: any): Promise<any> {
  return { ...localUser, ...(data || {}) }
}

export async function getPersonalStats(): Promise<any> {
  return { total_records: 0, total_products: 0, total_recipes: 0 }
}

export async function listUsers(_params: Record<string, string>, query?: any): Promise<any> {
  const page = parseInt(query?.page) || 1
  const pageSize = parseInt(query?.page_size) || 20
  return { items: [{ ...localUser }], total: 1, page, page_size: pageSize }
}

export async function getUser(): Promise<any> {
  return { ...localUser }
}

export async function updateUser(_params: Record<string, string>, data?: any): Promise<any> {
  return { ...localUser, ...(data || {}) }
}

export async function deleteUser(): Promise<any> {
  return { ok: true }
}
