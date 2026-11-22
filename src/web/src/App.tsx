import { AlertCircle, Check, Clock, LoaderCircle } from 'lucide-react'
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { ExportControl } from './ExportControl'
import { GenerateButton, Inspector, type InspectorProps } from './Inspector'
import { defaults, generate, getModels, parseDraft, PreviewError, type Draft, type Model, type ModelId, type Preview } from './preview'
import { followModelLink, modelPath, useModelPath } from './routing'
import { Viewport } from './Viewport'

interface ModelState {
  draft: Draft
  status: 'building' | 'ready' | 'failed'
  preview?: Preview
  error?: PreviewError
}

const medium = window.matchMedia('(max-width: 1023px)')
function subscribe(listener: () => void) {
  medium.addEventListener('change', listener)
  return () => medium.removeEventListener('change', listener)
}

const number = new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 2 })

function App() {
  const [models, setModels] = useState<Model[]>([])
  const [catalogError, setCatalogError] = useState(false)
  const [catalogAttempt, retryCatalog] = useState(0)
  const [states, setStates] = useState<Partial<Record<ModelId, ModelState>>>({})
  const inFlight = useRef(new Set<ModelId>())
  const dialog = useRef<HTMLDialogElement>(null)
  const parametersButton = useRef<HTMLButtonElement>(null)
  const narrow = useSyncExternalStore(subscribe, () => medium.matches)
  const pathname = useModelPath()

  const renderModel = useCallback((model: Model, draft: Draft) => {
    if (inFlight.current.has(model.id)) return
    const { values, errors } = parseDraft(model, draft)
    if (Object.keys(errors).length) return
    inFlight.current.add(model.id)
    void generate(model.id, values).then((preview) => {
      if (preview.model !== model.id) throw new PreviewError('返回结果与零件不匹配，请重试。')
      setStates((current) => ({ ...current, [model.id]: { draft, status: 'ready', preview } }))
    }).catch((error: unknown) => {
      const failure = error instanceof PreviewError ? error : new PreviewError('无法连接到生成服务，请重试。')
      setStates((current) => ({
        ...current, [model.id]: { ...current[model.id], draft, status: 'failed', error: failure },
      }))
    }).finally(() => {
      inFlight.current.delete(model.id)
    })
  }, [])

  useEffect(() => {
    const request = new AbortController()
    getModels(request.signal).then((catalog) => {
      if (request.signal.aborted) return
      if (!catalog.length) throw new PreviewError('没有可预览的零件。')
      setModels(catalog)
    }).catch(() => { if (!request.signal.aborted) setCatalogError(true) })
    return () => request.abort()
  }, [catalogAttempt])

  const model = models.find((entry) => modelPath(entry.id) === pathname)
  const savedState = model && states[model.id]
  useEffect(() => {
    if (model && !savedState) renderModel(model, defaults(model))
  }, [model, savedState, renderModel])

  const modelName = model?.name
  useEffect(() => {
    dialog.current?.close()
    document.title = modelName ? `${modelName} · Argus 模型工作台` : 'Argus · 模型工作台'
  }, [modelName])

  const missingModel = Boolean(models.length && !model)
  const state: ModelState | undefined = model && (savedState ?? { draft: defaults(model), status: 'building' })
  const modelDraft = state?.draft
  const parsed = model && modelDraft ? parseDraft(model, modelDraft) : { values: {}, errors: {} }
  const errors = { ...state?.error?.fields, ...parsed.errors }
  const isBuilding = state?.status === 'building'
  const result = state?.preview
  const different = Boolean(result && model?.fields.some((field) => parsed.values[field.key] !== result.parameters[field.key]))
  const canGenerate = Boolean(state && !isBuilding && !Object.keys(parsed.errors).length &&
    (different || !result || state.error))
  const canReset = Boolean(model && modelDraft &&
    model.fields.some((field) => modelDraft[field.key] !== String(field.default)))
  const dimensions = result?.bounds.max.map((max, index) => number.format(max - result.bounds.min[index])).join(' × ')

  function updateDraft(update: (draft: Draft) => Draft) {
    if (!model) return
    setStates((current) => {
      const entry = current[model.id]
      if (!entry) return current
      return { ...current, [model.id]: { ...entry, error: undefined, draft: update(entry.draft) } }
    })
  }

  const inspector: Omit<InspectorProps, 'generate'> | undefined = model && modelDraft ? {
    model, draft: modelDraft, errors,
    building: isBuilding, canGenerate, canReset,
    change: (key, value) => updateDraft((draft) => ({ ...draft, [key]: value })),
    reset: () => updateDraft(() => defaults(model)),
  } : undefined
  function submitPreview() {
    if (!model || !modelDraft || !canGenerate || inFlight.current.has(model.id)) return
    setStates((current) => ({
      ...current, [model.id]: { ...current[model.id], draft: modelDraft, status: 'building', error: undefined },
    }))
    renderModel(model, modelDraft)
  }

  const failure = state?.error
  const statusState = isBuilding ? 'building' : failure ? 'failed' : different ? 'draft' : 'ready'
  const status = isBuilding ? '正在生成…' : different ? '有未生成的修改' : result ? '预览已更新' : ''
  const StatusIcon = isBuilding ? LoaderCircle : different ? Clock : Check
  const statusContent = (
    <>
      <div className="preview-status" data-state={statusState} role="status">
        {failure ? (
          <details className="preview-failure">
            <summary className="preview-state"><AlertCircle aria-hidden />生成失败</summary>
            <p className="preview-error">{failure.message}</p>
          </details>
        ) : status && (
          <span className="preview-state"><StatusIcon aria-hidden className={isBuilding ? 'spinner' : undefined} />{status}</span>
        )}
        {result && (different || isBuilding || failure) && <span className="previous-label">视口显示上次生成结果</span>}
      </div>
      {failure && <p className="visually-hidden" role="alert">{failure.message}</p>}
    </>
  )

  return (
    <div className="app-shell">
      <header className="topbar">
        <span className="brand-name">Argus</span>
        <span className="workspace-name">模型工作台</span>
      </header>

      {!model || !inspector ? (
        <main className="catalog-state">
          <p role="status">{missingModel ? '找不到此零件。' : catalogError ? '无法加载模型列表。' : '正在加载模型…'}</p>
          {missingModel && <a className="secondary-button" href={modelPath('base')} onClick={followModelLink}>返回底座</a>}
          {catalogError && <button className="secondary-button" onClick={() => {
            setCatalogError(false)
            retryCatalog((attempt) => attempt + 1)
          }}>重试</button>}
        </main>
      ) : (
        <div className="workspace">
          <nav className="parts" aria-label="零件">
            <h2>零件</h2>
            <div className="parts-list">
              {models.map((entry) => (
                <a key={entry.id} href={modelPath(entry.id)} aria-current={model.id === entry.id ? 'page' : undefined}
                  onClick={followModelLink}>{entry.name}</a>
              ))}
            </div>
          </nav>

          <main className="workbench">
            <div className="preview-heading">
              <div>
                <h1>{model.name}</h1>
                <p className="dimensions" data-testid="model-dimensions">{dimensions ? dimensions + ' mm' : '外形尺寸待生成'}</p>
              </div>
              <div className="preview-heading-actions">
                <ExportControl current={model.id} models={models} previewParameters={(id) => states[id]?.preview?.parameters} />
                {narrow && <button type="button" className="secondary-button" ref={parametersButton} aria-haspopup="dialog"
                  onClick={() => dialog.current?.showModal()}>参数</button>}
              </div>
            </div>

            <div className="model-workspace">
              <div className="preview-area">
                <Viewport key={model.id} name={model.name} preview={result} loading={isBuilding} status={statusContent} />
                {narrow && <div className="mobile-generate">
                  <GenerateButton building={isBuilding} disabled={!canGenerate} onClick={submitPreview} />
                </div>}
              </div>
              {narrow ? (
                <dialog className="parameters-dialog" ref={dialog} aria-labelledby="parameter-heading"
                  onClose={() => parametersButton.current?.focus()}>
                  <Inspector {...inspector} generate={submitPreview} close={() => dialog.current?.close()} />
                </dialog>
              ) : <aside className="parameter-rail"><Inspector {...inspector} generate={submitPreview} /></aside>}
            </div>
          </main>
        </div>
      )}
    </div>
  )
}

export default App
