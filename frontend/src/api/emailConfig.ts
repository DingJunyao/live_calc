import api from './client'

export interface SmtpConfig {
  host: string
  port: number
  username: string
  use_tls: boolean
  use_ssl: boolean
  from_address: string
  from_name: string
  enabled: boolean
}

export interface SmtpConfigUpdate {
  host?: string
  port?: number
  username?: string
  password?: string
  use_tls?: boolean
  use_ssl?: boolean
  from_address?: string
  from_name?: string
  enabled?: boolean
}

export interface EmailTemplate {
  key: string
  name: string
  subject: string
  body_html: string
  description: string
  updated_at?: string
}

export interface EmailTemplateUpdate {
  subject?: string
  body_html?: string
  description?: string
}

export function getSmtpConfig(): Promise<SmtpConfig> {
  return api.get('/admin/email-config/smtp')
}

export function updateSmtpConfig(body: SmtpConfigUpdate): Promise<SmtpConfig> {
  return api.put('/admin/email-config/smtp', body)
}

export function testSmtpConfig(to_email: string): Promise<{ message: string }> {
  return api.post('/admin/email-config/smtp/test', { to_email })
}

export function listTemplates(): Promise<EmailTemplate[]> {
  return api.get('/admin/email-config/templates')
}

export function getTemplate(key: string): Promise<EmailTemplate> {
  return api.get(`/admin/email-config/templates/${key}`)
}

export function updateTemplate(key: string, body: EmailTemplateUpdate): Promise<EmailTemplate> {
  return api.put(`/admin/email-config/templates/${key}`, body)
}
