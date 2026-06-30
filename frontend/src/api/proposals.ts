// api/proposals.ts
// 提议-审核台 REST 客户端，复用现有 axios 封装（@/api/client）。
// 拦截器自动注入 Authorization: Bearer <jwt>（从 localStorage.access_token）。
import api from './client'

/** 提议实体类型（与后端 entity_type 对齐，非穷举）。 */
export type EntityType =
  | 'ingredient'
  | 'nutrition'
  | 'unit'
  | 'merchant'
  | 'product'
  | 'recipe'
  | string

/** 提议状态。 */
export type ProposalStatus =
  | 'pending' // 待审
  | 'applied' // 已批准并生效
  | 'rejected' // 已驳回
  | 'reverted' // 已回滚
  | string

/** 提议响应（与后端 ProposalResponse 对齐）。 */
export interface Proposal {
  id: number
  entity_type: EntityType
  entity_id: number | null
  entity_label: string | null   // 目标实体可读标签（后端 entity_label）
  action: string
  payload: Record<string, any>
  snapshot: Record<string, any> | null
  status: ProposalStatus
  review_policy: string
  risk_level: string
  proposer_id: number
  reviewer_id: number | null
  review_note: string | null
  revertable_until: string | null
  applied_at: string | null
  reviewed_at: string | null
  reverted_at: string | null
  preview?: Record<string, any> | null
}

/** 影响预览请求体。 */
export interface PreviewRequest {
  entity_type: EntityType
  entity_id?: number | null
  action: string
  payload: Record<string, any>
}

/** 审核请求体。 */
export interface ReviewRequest {
  approved: boolean
  note?: string
}

/** 列出提议（管理员看全部；普通用户仅自己）。 */
export function listProposals(
  status?: ProposalStatus,
  limit = 50,
): Promise<Proposal[]> {
  return api.get('/proposals', {
    params: { ...(status ? { status } : {}), limit },
  })
}

/** 获取提议详情。 */
export function getProposal(id: number): Promise<Proposal> {
  return api.get(`/proposals/${id}`)
}

/** 预览提议影响（如合并会影响多少引用）。 */
export function previewProposal(
  body: PreviewRequest,
): Promise<Record<string, any>> {
  return api.post('/proposals/preview', body)
}

/** 审核提议（仅管理员）。 */
export function reviewProposal(
  id: number,
  body: ReviewRequest,
): Promise<Proposal> {
  return api.post(`/proposals/${id}/review`, body)
}

/** 回滚已生效提议（仅管理员，须在 revertable_until 窗口内）。 */
export function revertProposal(id: number): Promise<Proposal> {
  return api.post(`/proposals/${id}/revert`)
}

/** 反垃圾：一键回退某用户全部已生效提议（仅管理员）。 */
export function revertByUser(
  userId: number,
): Promise<{ reverted_count: number }> {
  return api.post('/proposals/revert-by-user', { user_id: userId })
}

/** 审核策略档位。 */
export type ReviewPolicy = 'auto_approve' | 'auto_review' | 'manual' | string

/** 单条策略项（与后端 PolicyItem 对齐）。 */
export interface PolicyItem {
  entity_type: string
  action: string
  policy: ReviewPolicy
  risk_level: string
  is_default: boolean
}

/** 策略更新请求体。 */
export interface PolicyUpdate {
  entity_type: string
  action: string
  policy: ReviewPolicy
}

/** 列出全部 entity_type+action 的当前策略 + 风险（仅管理员）。 */
export function listPolicies(): Promise<PolicyItem[]> {
  return api.get('/proposals/policies')
}

/** 设置某 entity_type+action 的策略（仅管理员）。 */
export function updatePolicy(body: PolicyUpdate): Promise<PolicyItem> {
  return api.put('/proposals/policies', body)
}
