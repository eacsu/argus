import type { ModelId, Preview } from './preview'

export const exportFormats = ['step', '3mf', 'stl'] as const
export type ExportFormat = typeof exportFormats[number]
export type ExportId = ModelId | 'base-lower' | 'base-upper'

export interface ExportModel {
  id: ExportId
  parameters?: Preview['parameters']
}

export class ExportRequestError extends Error {}

export async function requestExport(models: ExportModel[], formats: ExportFormat[], signal: AbortSignal) {
  const response = await fetch('/api/exports', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ models, formats }),
    signal,
  })
  if (!response.ok) {
    const data = await response.json().catch(() => null)
    throw new ExportRequestError(data?.detail?.message || '导出失败，请重试。')
  }
  const filename = response.headers.get('Content-Disposition')?.match(/filename="([^"]+)"/i)?.[1]
  if (!filename) throw new ExportRequestError('导出响应缺少文件名，请重试。')
  return { blob: await response.blob(), filename }
}
