import { useEffect, useSyncExternalStore, type MouseEvent } from 'react'
import type { ModelId } from './preview'

const routeChange = 'argus:routechange'
export const DEFAULT_MODEL: ModelId = 'base-split'

export function modelPath(id: ModelId) {
  return '/models/' + id
}

function subscribePath(listener: () => void) {
  window.addEventListener('popstate', listener)
  window.addEventListener(routeChange, listener)
  return () => {
    window.removeEventListener('popstate', listener)
    window.removeEventListener(routeChange, listener)
  }
}

export function useModelPath() {
  const pathname = useSyncExternalStore(subscribePath, () => window.location.pathname)
  useEffect(() => {
    if (pathname !== '/' || window.location.pathname !== '/') return
    const path = modelPath(DEFAULT_MODEL) + window.location.search + window.location.hash
    window.history.replaceState(window.history.state, '', path)
    window.dispatchEvent(new Event(routeChange))
  }, [pathname])
  return pathname === '/' ? modelPath(DEFAULT_MODEL) : pathname.replace(/\/$/, '')
}

export function followModelLink(event: MouseEvent<HTMLAnchorElement>) {
  if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
  event.preventDefault()
  const url = event.currentTarget.href
  if (url === window.location.href) return
  window.history.pushState(null, '', url)
  window.dispatchEvent(new Event(routeChange))
}
