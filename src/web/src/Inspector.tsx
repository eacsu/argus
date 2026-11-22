import { X } from 'lucide-react'
import type { Draft, Model } from './preview'

export interface InspectorProps {
  model: Model
  draft: Draft
  errors: Record<string, string>
  building: boolean
  canGenerate: boolean
  canReset: boolean
  change: (key: string, value: string) => void
  reset: () => void
  generate: () => void
}

export function GenerateButton({ disabled, building, submit = false, onClick }: {
  disabled: boolean
  building: boolean
  submit?: boolean
  onClick?: () => void
}) {
  return (
    <button className="primary-button" type={submit ? 'submit' : 'button'} disabled={disabled} onClick={onClick}>
      {building ? '正在生成…' : '重新生成'}
    </button>
  )
}

export function Inspector(props: InspectorProps & { close?: () => void }) {
  const groups = Array.from(new Set(props.model.fields.map((field) => field.group)))
  return (
    <form className="inspector" aria-labelledby="parameter-heading" noValidate
      onSubmit={(event) => { event.preventDefault(); if (props.canGenerate) props.generate() }}>
      <div className="inspector-heading">
        <h2 id="parameter-heading">参数</h2>
        {props.close && <button className="icon-button" type="button" onClick={props.close} aria-label="关闭参数"><X /></button>}
      </div>

      <div className="inspector-fields">
        {groups.map((group) => (
          <fieldset className="parameter-group" key={group} disabled={props.building}>
            <legend>{group}</legend>
            {props.model.fields.filter((field) => field.group === group).map((field) => {
              const id = 'parameter-' + field.key
              const error = props.errors[field.key]
              return (
                <div className="parameter" key={field.key}>
                  <div className="parameter-row">
                    <label htmlFor={id}>{field.label}</label>
                    <div className="number-field" data-invalid={Boolean(error)}>
                      <input id={id} type="number" inputMode="decimal" step="any"
                        min={field.minimum} max={field.maximum} value={props.draft[field.key]}
                        onChange={(event) => props.change(field.key, event.target.value)}
                        aria-invalid={Boolean(error)} aria-describedby={id + '-unit' + (error ? ' ' + id + '-error' : '')} />
                      <span id={id + '-unit'}>{field.unit}</span>
                    </div>
                  </div>
                  {error && <p className="field-error" id={id + '-error'}>{error}</p>}
                </div>
              )
            })}
          </fieldset>
        ))}
      </div>

      <div className="inspector-footer">
        <button className="text-button reset-button" type="button" onClick={props.reset} disabled={!props.canReset || props.building}>
          恢复默认
        </button>
        <GenerateButton submit building={props.building} disabled={!props.canGenerate} />
      </div>
    </form>
  )
}
