import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import {
  ApiError,
  createGeneration,
  createProject,
  getGeneration,
  getModelVersion,
  getProject,
  listProjects,
  uploadImage,
  type Generation,
  type ModelVersion,
  type Project,
} from './api'
import { ModelViewer } from './ModelViewer'

const STAGE_LABEL: Record<Generation['state'], string> = {
  queued: '排隊中',
  submitting: '提交中',
  generating: '生成中',
  downloading: '下載中',
  validating: '驗證中',
  ready: '已完成',
  failed: '失敗',
}

function useSelectedProject(): [string | null, (id: string) => void] {
  const [projectId, setProjectId] = useState(() =>
    new URLSearchParams(window.location.search).get('project'),
  )
  useEffect(() => {
    const onPopState = () =>
      setProjectId(new URLSearchParams(window.location.search).get('project'))
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])
  const select = (id: string) => {
    const url = new URL(window.location.href)
    url.searchParams.set('project', id)
    window.history.pushState(null, '', url)
    setProjectId(id)
  }
  return [projectId, select]
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}

function Home({ onSelect }: { onSelect: (id: string) => void }) {
  const [name, setName] = useState('')
  const [projects, setProjects] = useState<Project[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    listProjects()
      .then((result) => setProjects(result.items))
      .catch(() => {})
  }, [])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) return
    setBusy(true)
    try {
      const project = await createProject(trimmed)
      onSelect(project.id)
    } catch (error) {
      setError(errorMessage(error, '建立專案失敗，請重試。'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section>
      <form onSubmit={handleSubmit}>
        <label htmlFor="project-name">專案名稱</label>
        <input
          id="project-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          maxLength={100}
          required
        />
        <button type="submit" disabled={busy}>
          建立專案
        </button>
      </form>
      {error && <p role="alert">{error}</p>}
      {projects.length > 0 && (
        <ul>
          {projects.map((project) => (
            <li key={project.id}>
              <button type="button" onClick={() => onSelect(project.id)}>
                {project.name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function Workspace({ projectId }: { projectId: string }) {
  const [projectName, setProjectName] = useState<string | null>(null)
  const [sourceAssetId, setSourceAssetId] = useState<string | null>(null)
  const [generation, setGeneration] = useState<Generation | null>(null)
  const [modelVersion, setModelVersion] = useState<ModelVersion | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  // One key per submit attempt: a lost response reuses it, a retry after failure gets a new one.
  const pendingKey = useRef<string | null>(null)

  useEffect(() => {
    let cancelled = false
    getProject(projectId).then(
      (detail) => {
        if (cancelled) return
        setProjectName(detail.name)
        setSourceAssetId(detail.source_asset_id)
        // Only track a generation for the image currently attached to the project.
        setGeneration(
          detail.generations.find((item) => item.source_asset_id === detail.source_asset_id) ??
            null,
        )
      },
      () => {},
    )
    return () => {
      cancelled = true
    }
  }, [projectId])

  const generationId = generation?.id ?? null
  const generationState = generation?.state ?? null
  const modelVersionId = generation?.model_version_id ?? null
  const generationDone = generationState === 'ready' || generationState === 'failed'

  useEffect(() => {
    if (!generationId || generationDone) return
    let active = true
    const timer = window.setInterval(() => {
      getGeneration(generationId).then(
        (updated) => {
          if (active) setGeneration(updated)
        },
        () => {},
      )
    }, 1000)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [generationId, generationDone])

  useEffect(() => {
    if (generationState !== 'ready' || !modelVersionId) return
    let cancelled = false
    getModelVersion(modelVersionId).then(
      (version) => {
        if (!cancelled) setModelVersion(version)
      },
      () => {},
    )
    return () => {
      cancelled = true
    }
  }, [generationState, modelVersionId])

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setBusy(true)
    try {
      const asset = await uploadImage(projectId, file)
      setError(null)
      setSourceAssetId(asset.id)
      setGeneration(null)
      setModelVersion(null)
      pendingKey.current = null
    } catch (error) {
      setError(errorMessage(error, '上傳失敗，請確認圖片格式與大小後重試。'))
    } finally {
      setBusy(false)
    }
  }

  async function handleGenerate() {
    if (!sourceAssetId) return
    setBusy(true)
    pendingKey.current ??= crypto.randomUUID()
    try {
      const created = await createGeneration(projectId, sourceAssetId, pendingKey.current)
      pendingKey.current = null
      setError(null)
      setGeneration(created)
      setModelVersion(null)
    } catch (error) {
      setError(errorMessage(error, '無法開始生成，請重試。'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section>
      <h2>{projectName ?? '專案'}</h2>
      <div className="field">
        <span>上傳圖片</span>
        <input
          type="file"
          aria-label="上傳圖片"
          accept="image/png,image/jpeg"
          onChange={handleUpload}
          disabled={busy}
        />
      </div>
      {error && <p role="alert">{error}</p>}
      <button
        type="button"
        onClick={handleGenerate}
        disabled={!sourceAssetId || busy || (generation !== null && !generationDone)}
      >
        {generationState === 'failed' ? '重新開始示範生成' : '開始示範生成'}
      </button>
      {generation && (
        <p>
          任務狀態：{STAGE_LABEL[generation.state]}
          {generation.state === 'failed' && generation.error && (
            <span role="alert"> {generation.error.message}</span>
          )}
        </p>
      )}
      {modelVersion && (
        <>
          <p data-testid="model-ready">模型已就緒</p>
          <ModelViewer url={modelVersion.asset_url} />
        </>
      )}
    </section>
  )
}

export function App() {
  const [projectId, selectProject] = useSelectedProject()
  return (
    <main>
      <h1>Picture to Model</h1>
      {projectId ? <Workspace projectId={projectId} /> : <Home onSelect={selectProject} />}
    </main>
  )
}
