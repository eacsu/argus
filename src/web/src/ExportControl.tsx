import { AlertCircle, Download, X } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { exportFormats, ExportRequestError, requestExport, type ExportFormat } from './export'
import type { Model, ModelId, Preview } from './preview'
import './export.css'

interface ExportControlProps {
  current: ModelId
  models: Model[]
  previewParameters: (id: ModelId) => Preview['parameters'] | undefined
}

function toggleSelection<T>(values: T[], value: T, checked: boolean): T[] {
  return checked ? [...values, value] : values.filter((entry) => entry !== value)
}

export function ExportControl({ current, models, previewParameters }: ExportControlProps) {
  const dialog = useRef<HTMLDialogElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const pending = useRef<AbortController | null>(null)
  const [modelIds, setModelIds] = useState<ModelId[]>([])
  const [formats, setFormats] = useState<ExportFormat[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const fileCount = modelIds.length * formats.length

  useEffect(() => () => pending.current?.abort(), [])

  function open() {
    setModelIds([current])
    setFormats(['3mf'])
    setError('')
    dialog.current?.showModal()
  }

  function onClose() {
    pending.current?.abort()
    pending.current = null
    setBusy(false)
    trigger.current?.focus()
  }

  async function download(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!fileCount || pending.current) return
    const selectedModels = models.filter(({ id }) => modelIds.includes(id)).map(({ id }) => ({
      id, parameters: previewParameters(id),
    }))
    const selectedFormats = exportFormats.filter((format) => formats.includes(format))
    const request = new AbortController()
    pending.current = request
    setBusy(true)
    setError('')
    try {
      const { blob, filename } = await requestExport(selectedModels, selectedFormats, request.signal)
      if (request.signal.aborted || !dialog.current?.open) return
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.append(link)
      link.click()
      link.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
      dialog.current?.close()
    } catch (failure) {
      if (request.signal.aborted) return
      setError(failure instanceof ExportRequestError ? failure.message : '无法连接导出服务，请重试。')
    } finally {
      if (pending.current === request) {
        pending.current = null
        setBusy(false)
      }
    }
  }

  return (
    <>
      <button type="button" className="secondary-button" ref={trigger} onClick={open}
        aria-haspopup="dialog"><Download aria-hidden />导出</button>
      <dialog className="export-dialog" ref={dialog} aria-labelledby="export-title" onClose={onClose}>
        <form className="export-form" onSubmit={download}>
          <header className="export-header">
            <h2 id="export-title">导出文件</h2>
            <button type="button" className="icon-button" aria-label="关闭导出"
              onClick={() => dialog.current?.close()}><X aria-hidden /></button>
          </header>

          <fieldset className="export-group" disabled={busy}>
            <legend>配件</legend>
            {models.map(({ id, name }) => (
              <label key={id} className="export-model-option">
                <input type="checkbox" checked={modelIds.includes(id)} aria-labelledby={'export-name-' + id}
                  aria-describedby={'export-source-' + id}
                  onChange={(event) => setModelIds(toggleSelection(modelIds, id, event.target.checked))} />
                <span id={'export-name-' + id}>{name}</span>
                <span id={'export-source-' + id} className="export-source">
                  {previewParameters(id) ? '当前预览' : '默认参数'}
                </span>
              </label>
            ))}
          </fieldset>

          <fieldset className="export-group" disabled={busy}>
            <legend>文件格式</legend>
            <div className="export-formats">
              {exportFormats.map((format) => (
                <label key={format}>
                  <input type="checkbox" checked={formats.includes(format)}
                    onChange={(event) => setFormats(toggleSelection(formats, format, event.target.checked))} />
                  {format.toUpperCase()}
                </label>
              ))}
            </div>
          </fieldset>

          <footer className="export-footer" data-error={Boolean(error)}>
            {error && <p className="form-error" role="alert"><AlertCircle aria-hidden />{error}</p>}
            <div className="export-actions-row">
              <p className="export-count" role="status">
                {busy ? `正在导出 ${fileCount} 个文件…` : fileCount > 1 ? `${fileCount} 个文件 · ZIP` :
                  fileCount === 1 ? '1 个文件' : '请选择配件和格式'}
              </p>
              <div className="export-actions">
                <button className="text-button" type="button" onClick={() => dialog.current?.close()}>取消</button>
                <button className="primary-button" type="submit" disabled={!fileCount || busy}>
                  {busy ? '正在导出…' : error ? '重试下载' : '下载'}
                </button>
              </div>
            </div>
          </footer>
        </form>
      </dialog>
    </>
  )
}
