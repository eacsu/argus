export type ModelId = 'base' | 'bracket' | 'bracket-print' | 'head' | 'head-print'

export interface ParameterField {
  key: string
  label: string
  group: string
  default: number
  minimum: number
  maximum: number
  unit: string
}

export interface Model {
  id: ModelId
  name: string
  fields: ParameterField[]
}

export interface Preview {
  model: ModelId
  parameters: Record<string, number>
  bounds: { min: [number, number, number]; max: [number, number, number] }
  mesh: { positions: number[]; indices: number[] }
}

export type Draft = Record<string, string>

export class PreviewError extends Error {
  fields: Record<string, string>

  constructor(message: string, fields: Record<string, string> = {}) {
    super(message)
    this.fields = fields
  }
}

export function defaults(model: Model): Draft {
  return Object.fromEntries(model.fields.map((field) => [field.key, String(field.default)]))
}

export function parseDraft(model: Model, draft: Draft) {
  const values: Record<string, number> = {}
  const errors: Record<string, string> = {}
  for (const field of model.fields) {
    const text = draft[field.key]?.trim()
    const value = Number(text)
    if (!text || !Number.isFinite(value) || value < field.minimum || value > field.maximum) {
      errors[field.key] = '请输入 ' + field.minimum + '–' + field.maximum + ' ' + field.unit + ' 范围内的数值。'
    } else {
      values[field.key] = value
    }
  }
  return { values, errors }
}

export async function getModels(signal: AbortSignal): Promise<Model[]> {
  const response = await fetch('/api/models', { signal })
  if (!response.ok) throw new PreviewError('无法加载零件。')
  return (await response.json()).models
}

export async function generate(model: ModelId, parameters: Record<string, number>): Promise<Preview> {
  const response = await fetch('/api/models/' + model + '/preview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ parameters }),
  })
  if (!response.ok) {
    const data = await response.json().catch(() => null)
    throw new PreviewError(data?.detail?.message || '无法生成模型，请重试。', data?.detail?.fields)
  }
  return response.json()
}
