/**
 * 粘贴文本价格解析器
 *
 * 支持格式（名称与价格之间用空格或 tab 分隔）：
 *   名称 价格            -> 芹菜 1.88            (默认 1 斤)
 *   名称 价格/单位       -> 芽菇 4/袋            (1 袋)
 *   名称 价格/缩写单位   -> 嫩豆腐 5.18/kg       (1 kg)
 *   名称 价格/数量+单位  -> 土豆粉 2.5/200g      (200 g)
 */

export interface ParsedPriceLine {
  raw: string                 // 原始行
  name: string                // 商品名
  price: number | null        // 价格
  quantity: number            // 数量
  unit: string                // 单位缩写
  ok: boolean                 // 是否解析成功
  error?: string              // 失败原因
}

// 中文单位别名 -> 系统 abbreviation（克=g、千克=kg、斤=斤）
const UNIT_ALIASES: Record<string, string> = {
  '克': 'g',
  '公斤': 'kg',
  '千克': 'kg',
}

// 名称(非贪婪) 价格 [/[数量]单位]
// 组1 名称 | 组2 价格 | 组3 数量(可空) | 组4 单位(可空)
const LINE_RE = /^(.+?)\s+(\d+(?:\.\d+)?)(?:\/(\d*\.?\d*)\s*([A-Za-z一-龥]+))?\s*$/

function normalizeUnit(raw: string): string {
  return UNIT_ALIASES[raw] ?? raw
}

export function parsePasteLine(line: string): ParsedPriceLine {
  const trimmed = line.trim()

  if (trimmed === '') {
    return { raw: line, name: '', price: null, quantity: 0, unit: '', ok: false, error: '空行' }
  }
  if (trimmed.startsWith('#')) {
    return { raw: line, name: '', price: null, quantity: 0, unit: '', ok: false, error: '注释行' }
  }

  const m = trimmed.match(LINE_RE)
  if (!m) {
    return { raw: line, name: '', price: null, quantity: 0, unit: '', ok: false, error: '格式无法识别' }
  }

  const name = m[1].trim()
  const price = parseFloat(m[2])
  const qtyStr = m[3] ?? ''     // 可能为空串
  const unitStr = m[4]          // 可能为 undefined

  const quantity = qtyStr !== '' ? parseFloat(qtyStr) : 1
  const unit = unitStr ? normalizeUnit(unitStr) : '斤'

  if (!name) {
    return { raw: line, name: '', price, quantity, unit, ok: false, error: '商品名为空' }
  }
  if (!Number.isFinite(price) || price <= 0) {
    return { raw: line, name, price, quantity, unit, ok: false, error: '价格无效' }
  }

  return { raw: line, name, price, quantity, unit, ok: true }
}

export function parsePasteText(text: string): ParsedPriceLine[] {
  return text.split(/\r?\n/).map(parsePasteLine)
}
