import { Maximize, Minus, Plus } from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import type { Preview } from './preview'
import { createViewer, type View } from './viewer'

const views: Array<{ id: View; label: string }> = [
  { id: 'iso', label: '等轴测' }, { id: 'top', label: '顶视' },
  { id: 'front', label: '前视' }, { id: 'side', label: '侧视' },
]

export function Viewport({ name, preview, loading, status }: {
  name: string
  preview?: Preview
  loading: boolean
  status: ReactNode
}) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const viewer = useRef<ReturnType<typeof createViewer> | null>(null)
  const [view, setView] = useState<View>('iso')
  const [unavailable, setUnavailable] = useState(false)
  const ready = Boolean(preview) && !unavailable

  useEffect(() => {
    let mounted = true
    if (!canvas.current) return
    try {
      viewer.current = createViewer(canvas.current)
    } catch {
      queueMicrotask(() => { if (mounted) setUnavailable(true) })
    }
    return () => {
      mounted = false
      viewer.current?.dispose()
      viewer.current = null
    }
  }, [])

  useEffect(() => {
    viewer.current?.setPreview(preview)
  }, [preview])

  return (
    <section className="viewer" aria-label={name + '三维预览'}>
      <div className="viewer-tools">
        <div className="view-presets" role="group" aria-label="视角">
          {views.map((option) => (
            <button type="button" key={option.id} disabled={!ready} aria-pressed={view === option.id}
              onClick={() => { setView(option.id); viewer.current?.setView(option.id) }}>
              {option.label}
            </button>
          ))}
        </div>
        <div className="view-actions" role="group" aria-label="视图缩放">
          <button type="button" disabled={!ready} aria-label="缩小" title="缩小" onClick={() => viewer.current?.zoom(0.8)}><Minus /></button>
          <button type="button" disabled={!ready} aria-label="放大" title="放大" onClick={() => viewer.current?.zoom(1.25)}><Plus /></button>
          <button type="button" disabled={!ready} aria-label="适配视野" title="适配视野" onClick={() => viewer.current?.fit()}><Maximize /></button>
        </div>
      </div>
      <div className="canvas-area" data-model={preview?.model}>
        <canvas ref={canvas} tabIndex={ready ? 0 : -1} aria-label={name + '模型'} />
        {!ready && <p className="canvas-message" role="status">
          {unavailable ? '当前浏览器无法启用三维预览。' : loading ? '正在生成预览…' : '当前没有可用的预览。'}
        </p>}
      </div>
      <div className="viewer-footer">
        {status}
        {ready && <div className="gesture-hint">
          <span className="pointer-hint">拖动旋转 · 右键拖动平移 · 滚轮缩放</span>
          <span className="touch-hint">单指旋转 · 双指平移或缩放</span>
        </div>}
      </div>
    </section>
  )
}
