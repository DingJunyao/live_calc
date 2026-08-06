export interface ProviderOption {
  value: string
  label: string
}

export const AI_PROVIDER_ORDER = ['claude_code', 'codex', 'openai', 'anthropic']
export const MACHINE_PROVIDER_ORDER = ['baidu', 'aliyun', 'deepl']

export const PROVIDER_LABELS: Record<string, string> = {
  claude_code: 'Claude Code',
  codex: 'Codex',
  openai: 'OpenAI 兼容',
  anthropic: 'Anthropic 兼容',
  baidu: '百度翻译',
  aliyun: '阿里云机器翻译',
  deepl: 'DeepL',
}

export function enabledProviderOptions(
  config: any,
  regions: Array<'ai' | 'machine'>,
  localMode = false,
): ProviderOption[] {
  if (!config) return []
  const options: ProviderOption[] = []
  const seen = new Set<string>()
  const order = [...AI_PROVIDER_ORDER, ...MACHINE_PROVIDER_ORDER]
  for (const region of regions) {
    const providers = config?.[region]?.providers || {}
    for (const key of order) {
      const value = providers[key]
      if (!value || value.enabled !== true) continue
      if (localMode && (key === 'claude_code' || key === 'codex')) continue
      if (localMode && region === 'machine') continue
      if (seen.has(key)) continue
      seen.add(key)
      options.push({ value: key, label: PROVIDER_LABELS[key] || key })
    }
  }
  return options
}
