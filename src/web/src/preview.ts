export type ModelId = 'base' | 'base-servo' | 'base-split' | 'gimbal-assembly' | 'sg90s' | 'servo-horn' | 'servo-horn-single' |
  'servo-horn-long' | 'bracket' | 'bracket-print' | 'head' | 'head-print'

export function stateModel(id: ModelId): ModelId {
  return id === 'gimbal-assembly' ? 'base-split' : id
}

export interface ParameterField {
  key: string
  label: string
  group: string
  default: number
  minimum: number
  maximum: number
  unit: string
  choices?: { value: number; label: string; defaults: Record<string, number> }[]
  active_when?: [string, number] | null
}

export interface Model {
  id: ModelId
  name: string
  fields: ParameterField[]
}

export interface MeshData { positions: number[]; indices: number[] }
export interface Bounds { min: [number, number, number]; max: [number, number, number] }
export interface PreviewPart { id: string; name: string; mesh: MeshData; bounds: Bounds }

export interface Preview {
  model: ModelId
  parameters: Record<string, number>
  bounds: Bounds
  mesh?: MeshData
  parts?: PreviewPart[]
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

export function changeDraft(model: Model, draft: Draft, key: string, value: string): Draft {
  const field = model.fields.find((field) => field.key === key)
  const choice = field?.choices?.find((choice) => String(choice.value) === value)
  const preset = Object.fromEntries(Object.entries(choice?.defaults ?? {}).map(([field, value]) => [field, String(value)]))
  return { ...draft, ...preset, [key]: value }
}

export function isFieldActive(field: ParameterField, draft: Draft): boolean {
  const condition = field.active_when
  return !condition || Number(draft[condition[0]]) === condition[1]
}

export function parseDraft(model: Model, draft: Draft) {
  const values: Record<string, number> = {}
  const errors: Record<string, string> = {}
  for (const field of model.fields) {
    if (!isFieldActive(field, draft)) {
      values[field.key] = field.default
      continue
    }
    const text = draft[field.key]?.trim()
    const value = Number(text)
    if (field.choices?.length && (!text || !field.choices.some((choice) => choice.value === value))) {
      errors[field.key] = '请选择列表中的型号。'
    } else if (!text || !Number.isFinite(value) || value < field.minimum || value > field.maximum) {
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
