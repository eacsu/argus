import {
  AmbientLight, BufferGeometry, Color, DirectionalLight, EdgesGeometry, Float32BufferAttribute,
  GridHelper, Group, LineBasicMaterial, LineSegments, Mesh, MeshStandardMaterial, OrthographicCamera,
  Scene, Vector3, WebGLRenderer,
} from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import type { Preview } from './preview'

export type View = 'iso' | 'top' | 'front' | 'side'

const VIEWS: Record<View, Vector3> = {
  iso: new Vector3(1.05, -1.45, 1.05),
  top: new Vector3(0, 0, 1),
  front: new Vector3(0, -1, 0),
  side: new Vector3(1, 0, 0),
}

export function createViewer(canvas: HTMLCanvasElement) {
  const renderer = new WebGLRenderer({ canvas, antialias: true })
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio))
  const css = getComputedStyle(document.documentElement)
  const color = (token: string) => new Color(css.getPropertyValue(token).trim())
  const scene = new Scene()
  scene.background = color('--bg-primary')
  const camera = new OrthographicCamera(-50, 50, 50, -50, 0.01, 2000)
  camera.up.set(0, 0, 1)
  camera.position.set(75, -85, 65)
  const orbit = new OrbitControls(camera, canvas)
  orbit.minZoom = 0.35
  orbit.maxZoom = 8
  orbit.listenToKeyEvents(canvas)
  const object = new Group()
  const material = new MeshStandardMaterial({
    color: color('--accent'), roughness: 0.65, metalness: 0.08,
  })
  const outlineMaterial = new LineBasicMaterial({
    color: color('--text-secondary'), transparent: true, opacity: 0.40,
  })
  const grid = new GridHelper(360, 72, color('--border-strong'), color('--surface-subtle'))
  grid.rotation.x = Math.PI / 2
  const key = new DirectionalLight(color('--surface'), 3.0)
  key.position.set(-30, -40, 90)
  const fill = new DirectionalLight(color('--bg-primary'), 0.8)
  fill.position.set(40, 35, 25)
  scene.add(object, grid, key, fill, new AmbientLight(color('--surface'), 1.2))
  const center = new Vector3()
  let span = 65
  let mesh: Mesh | undefined
  let lines: LineSegments | undefined
  let currentModel: Preview['model'] | undefined

  const draw = () => renderer.render(scene, camera)
  const resize = () => {
    const width = Math.max(1, canvas.clientWidth)
    const height = Math.max(1, canvas.clientHeight)
    const aspect = width / height
    const fitSize = Math.min(width / 0.8, height)
    const half = span * height / (2 * fitSize)
    camera.left = -half * aspect
    camera.right = half * aspect
    camera.top = half
    camera.bottom = -half
    camera.updateProjectionMatrix()
    renderer.setSize(width, height, false)
    draw()
  }
  const fit = () => {
    const direction = camera.position.clone().sub(orbit.target).normalize()
    orbit.target.copy(center)
    camera.position.copy(center).addScaledVector(direction, 150)
    camera.zoom = 1
    camera.updateProjectionMatrix()
    orbit.update()
    draw()
  }
  const setView = (view: View) => {
    camera.up.set(0, view === 'top' ? 1 : 0, view === 'top' ? 0 : 1)
    orbit.target.copy(center)
    camera.position.copy(center).addScaledVector(VIEWS[view].clone().normalize(), 150)
    orbit.update()
    draw()
  }

  function clearMesh() {
    if (mesh) {
      object.remove(mesh)
      mesh.geometry.dispose()
      mesh = undefined
    }
    if (lines) {
      object.remove(lines)
      lines.geometry.dispose()
      lines = undefined
    }
  }

  function setPreview(preview: Preview | undefined) {
    clearMesh()
    if (!preview) {
      draw()
      return
    }
    const geometry = new BufferGeometry()
    geometry.setAttribute('position', new Float32BufferAttribute(preview.mesh.positions, 3))
    geometry.setIndex(preview.mesh.indices)
    geometry.computeVertexNormals()
    mesh = new Mesh(geometry, material)
    lines = new LineSegments(new EdgesGeometry(geometry, 32), outlineMaterial)
    object.add(mesh, lines)
    const minimum = new Vector3(...preview.bounds.min)
    const maximum = new Vector3(...preview.bounds.max)
    center.addVectors(minimum, maximum).multiplyScalar(0.5)
    grid.position.set(center.x, center.y, minimum.z - 0.25)
    span = Math.max(10, maximum.distanceTo(minimum) * 1.32)
    resize()
    if (currentModel !== preview.model) {
      setView('iso')
      fit()
      currentModel = preview.model
    }
    draw()
  }

  const observer = new ResizeObserver(resize)
  observer.observe(canvas)
  orbit.addEventListener('change', draw)
  resize()

  return {
    setPreview,
    setView,
    fit,
    zoom(factor: number) {
      camera.zoom = Math.max(orbit.minZoom, Math.min(orbit.maxZoom, camera.zoom * factor))
      camera.updateProjectionMatrix()
      draw()
    },
    dispose() {
      observer.disconnect()
      orbit.removeEventListener('change', draw)
      orbit.dispose()
      clearMesh()
      material.dispose()
      outlineMaterial.dispose()
      grid.dispose()
      renderer.dispose()
    },
  }
}
