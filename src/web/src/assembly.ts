import type { ExportId } from './export'
import type { Bounds, Preview } from './preview'

export type BaseView = 'closed' | 'upper' | 'lower'

export const BASE_VIEWS: { value: BaseView; name: string }[] = [
  { value: 'closed', name: '闭合底座' },
  { value: 'upper', name: '上盖' },
  { value: 'lower', name: '下座' },
]

export const BASE_EXPORTS: { id: ExportId; name: string }[] = [
  { id: 'base-lower', name: '下座' },
  { id: 'base-upper', name: '上盖' },
]

export function basePreview(preview: Preview, view: BaseView): Preview {
  if (!preview.parts) return preview
  const parts = preview.parts.filter(({ id }) => {
    if (view === 'closed') return id.startsWith('gimbal_base_') || id === 'servo_horn_long' || id === 'mg90s_servo_horn' || id.startsWith('m3_')
    return id === (view === 'upper' ? 'gimbal_base_upper' : 'gimbal_base_lower')
  })
  if (!parts.length) return preview

  const bounds: Bounds = {
    min: [...parts[0].bounds.min],
    max: [...parts[0].bounds.max],
  }
  for (const part of parts.slice(1)) {
    for (let axis = 0; axis < 3; axis++) {
      bounds.min[axis] = Math.min(bounds.min[axis], part.bounds.min[axis])
      bounds.max[axis] = Math.max(bounds.max[axis], part.bounds.max[axis])
    }
  }
  return { ...preview, parts, bounds }
}
