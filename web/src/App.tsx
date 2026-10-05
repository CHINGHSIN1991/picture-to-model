import {
  lazy,
  Suspense,
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type FormEvent,
} from 'react'
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
const ModelViewer = lazy(() =>
  import('./ModelViewer').then((module) => ({ default: module.ModelViewer })),
)

const STAGE_LABEL: Record<Generation['state'], string> = {
  queued: '等待處理',
  submitting: '提交任務',
  generating: '準備示範模型',
  downloading: '取得模型',
  validating: '檢查模型',
  ready: '任務完成',
  failed: '任務失敗',
}
const STAGES = ['queued', 'submitting', 'generating', 'downloading', 'validating', 'ready'] as const

function useSelectedProject(): [string | null, (id: string | null) => void] {
  const [projectId, setProjectId] = useState(() =>
    new URLSearchParams(window.location.search).get('project'),
  )
  useEffect(() => {
    const onPopState = () =>
      setProjectId(new URLSearchParams(window.location.search).get('project'))
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])
  const select = (id: string | null) => {
    const url = new URL(window.location.href)
    if (id) url.searchParams.set('project', id)
    else url.searchParams.delete('project')
    window.history.pushState(null, '', url)
    setProjectId(id)
  }
  return [projectId, select]
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}

function CubeIcon({ className = '' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 40 40" fill="none" aria-hidden="true">
      <path d="m20 3 15 8.5v17L20 37 5 28.5v-17L20 3Z" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="m5 11.5 15 9 15-9M20 20.5V37M12.5 7.3l15 9"
        stroke="currentColor"
        strokeWidth="1.6"
      />
    </svg>
  )
}

function Home({ onSelect }: { onSelect: (id: string) => void }) {
  const [name, setName] = useState('')
  const [projects, setProjects] = useState<Project[]>([])
  const [error, setError] = useState<string | null>(null)
  const [listError, setListError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [attempt, setAttempt] = useState(0)
  const [busy, setBusy] = useState(false)
  const submitting = useRef(false)

  useEffect(() => {
    const controller = new AbortController()
    listProjects(controller.signal).then(
      (result) => {
        if (controller.signal.aborted) return
        setProjects(result.items)
        setListError(null)
        setLoading(false)
      },
      (error) => {
        if (controller.signal.aborted) return
        setListError(errorMessage(error, '無法取得專案，請確認本機服務已啟動。'))
        setLoading(false)
      },
    )
    return () => controller.abort()
  }, [attempt])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const trimmed = name.trim()
    if (!trimmed || submitting.current) return
    submitting.current = true
    setBusy(true)
    setError(null)
    try {
      const project = await createProject(trimmed)
      onSelect(project.id)
    } catch (error) {
      setError(errorMessage(error, '建立專案失敗，請確認本機服務後重試。'))
    } finally {
      submitting.current = false
      setBusy(false)
    }
  }

  return (
    <>
      <section className="intro">
        <p className="eyebrow">YOUR OBJECTS, A NEW DIMENSION</p>
        <h1>讓靈感，多一個維度。</h1>
        <p>從一張圖片開始，建立你的 3D 模型專案。</p>
      </section>
      <div className="home-layout">
        <section className="card create-card" aria-labelledby="create-title">
          <span className="section-number">01 / 開始探索</span>
          <h2 id="create-title">建立新專案</h2>
          <p className="muted">替你的物件取個名字，接著上傳參考圖片。</p>
          <form onSubmit={handleSubmit}>
            <label htmlFor="project-name">專案名稱</label>
            <input
              id="project-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="例如：桌上的小椅子"
              autoComplete="off"
              maxLength={100}
              required
            />
            <button className="button primary" type="submit" disabled={busy || !name.trim()}>
              {busy ? '建立中…' : '建立專案'} <span aria-hidden="true">↗</span>
            </button>
          </form>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <div className="demo-note">
            <span className="status-dot" />
            <div>
              <strong>先體驗完整流程</strong>
              <p>目前為本機示範模式，使用固定模型，無 AI 呼叫及費用。輸出不會依圖片改變。</p>
            </div>
          </div>
        </section>
        <section className="projects-section" aria-labelledby="projects-title" aria-busy={loading}>
          <div className="section-heading">
            <h2 id="projects-title">我的專案</h2>
            <span className="count">{projects.length}</span>
          </div>
          {loading && (
            <p className="muted" role="status">
              正在讀取專案…
            </p>
          )}
          {listError && (
            <div className="error-panel" role="alert">
              <p>{listError}</p>
              <button
                className="button secondary"
                onClick={() => {
                  setLoading(true)
                  setListError(null)
                  setAttempt((value) => value + 1)
                }}
              >
                重新載入專案
              </button>
            </div>
          )}
          {!loading && !listError && projects.length === 0 && (
            <div className="empty-projects">
              <CubeIcon />
              <h3>你的第一個物件，從這裡開始</h3>
              <p>建立專案後，就能在這裡繼續上次的進度。</p>
            </div>
          )}
          <ul className="project-list">
            {projects.map((project) => (
              <li key={project.id}>
                <button className="project-card" onClick={() => onSelect(project.id)}>
                  <span className="project-icon">
                    <CubeIcon />
                  </span>
                  <span className="project-text">
                    <strong>{project.name}</strong>
                    <small>
                      {project.source_asset_id ? '已有參考圖片' : '等待上傳圖片'} ·{' '}
                      {new Date(project.created_at).toLocaleDateString('zh-TW')}
                    </small>
                  </span>
                  <span className="project-arrow" aria-hidden="true">
                    ↗
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>
      <ol className="overview-steps" aria-label="示範流程">
        <li>
          <span>01</span>
          <div>
            <strong>上傳參考圖片</strong>
            <p>PNG 或 JPEG，清楚呈現單一物件。</p>
          </div>
        </li>
        <li>
          <span>02</span>
          <div>
            <strong>執行示範任務</strong>
            <p>追蹤背景任務，重新整理也能繼續。</p>
          </div>
        </li>
        <li>
          <span>03</span>
          <div>
            <strong>探索 3D 預覽</strong>
            <p>旋轉、縮放，從不同角度查看模型。</p>
          </div>
        </li>
      </ol>
    </>
  )
}

function SourcePreview({ assetId }: { assetId: string }) {
  const [failed, setFailed] = useState(false)
  const [attempt, setAttempt] = useState(0)
  return (
    <div className="source-preview">
      {failed ? (
        <div className="preview-error" role="alert">
          <p>圖片預覽載入失敗。</p>
          <button
            className="text-button"
            onClick={() => {
              setFailed(false)
              setAttempt((value) => value + 1)
            }}
          >
            重新載入圖片
          </button>
        </div>
      ) : (
        <img
          src={`/api/assets/${encodeURIComponent(assetId)}/content?attempt=${attempt}`}
          alt="已上傳的參考圖片"
          onError={() => setFailed(true)}
        />
      )}
      <span className="image-caption">參考圖片</span>
    </div>
  )
}

function Workspace({ projectId, onBack }: { projectId: string; onBack: () => void }) {
  const [projectName, setProjectName] = useState<string | null>(null)
  const [sourceAssetId, setSourceAssetId] = useState<string | null>(null)
  const [generation, setGeneration] = useState<Generation | null>(null)
  const [modelVersion, setModelVersion] = useState<ModelVersion | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [pollError, setPollError] = useState<string | null>(null)
  const [modelError, setModelError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  const [modelAttempt, setModelAttempt] = useState(0)
  const [busy, setBusy] = useState<'upload' | 'generate' | null>(null)
  const pendingKey = useRef<string | null>(null)
  const mutating = useRef(false)

  useEffect(() => {
    const controller = new AbortController()
    getProject(projectId, controller.signal).then(
      (detail) => {
        if (controller.signal.aborted) return
        setProjectName(detail.name)
        setSourceAssetId(detail.source_asset_id)
        setGeneration(
          detail.generations.find((item) => item.source_asset_id === detail.source_asset_id) ??
            null,
        )
        setLoadError(null)
      },
      (error) => {
        if (!controller.signal.aborted)
          setLoadError(errorMessage(error, '無法讀取專案，請確認本機服務後重試。'))
      },
    )
    return () => controller.abort()
  }, [projectId, attempt])

  const generationId = generation?.id ?? null
  const generationState = generation?.state ?? null
  const modelVersionId = generation?.model_version_id ?? null
  const generationDone = generationState === 'ready' || generationState === 'failed'
  const running = generation !== null && !generationDone

  useEffect(() => {
    if (!generationId || generationDone) return
    const controller = new AbortController()
    let timer = 0
    let failures = 0
    async function poll() {
      try {
        const updated = await getGeneration(generationId!, controller.signal)
        if (controller.signal.aborted) return
        setGeneration(updated)
        setPollError(null)
        failures = 0
        if (updated.state === 'ready' || updated.state === 'failed') return
      } catch (error) {
        if (controller.signal.aborted) return
        failures += 1
        setPollError(errorMessage(error, '暫時無法取得進度，正在自動重新連線。任務會保留。'))
      }
      timer = window.setTimeout(poll, Math.min(1000 * 2 ** failures, 10000))
    }
    timer = window.setTimeout(poll, 800)
    return () => {
      controller.abort()
      window.clearTimeout(timer)
    }
  }, [generationId, generationDone])

  useEffect(() => {
    if (generationState !== 'ready' || !modelVersionId) return
    const controller = new AbortController()
    getModelVersion(modelVersionId, controller.signal).then(
      (version) => {
        if (controller.signal.aborted) return
        setModelVersion(version)
        setModelError(null)
      },
      (error) => {
        if (!controller.signal.aborted)
          setModelError(errorMessage(error, '無法取得模型資訊，請重試。'))
      },
    )
    return () => controller.abort()
  }, [generationState, modelVersionId, modelAttempt])

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file || mutating.current) return
    if (file.size > 10 * 1024 * 1024) {
      setError('圖片不得超過 10 MB，請縮小後重新上傳。')
      return
    }
    if (!['image/png', 'image/jpeg'].includes(file.type)) {
      setError('請選擇 PNG 或 JPEG 圖片。')
      return
    }
    mutating.current = true
    setBusy('upload')
    setError(null)
    try {
      const asset = await uploadImage(projectId, file)
      setSourceAssetId(asset.id)
      setGeneration(null)
      setModelVersion(null)
      setModelError(null)
      setPollError(null)
      pendingKey.current = null
    } catch (error) {
      setError(errorMessage(error, '上傳失敗，請確認本機服務及圖片格式後重試。'))
    } finally {
      mutating.current = false
      setBusy(null)
    }
  }

  async function handleGenerate() {
    if (!sourceAssetId || mutating.current || running) return
    mutating.current = true
    setBusy('generate')
    setError(null)
    pendingKey.current ??= crypto.randomUUID()
    try {
      const created = await createGeneration(projectId, sourceAssetId, pendingKey.current)
      pendingKey.current = null
      setGeneration(created)
      setModelVersion(null)
      setModelError(null)
      setPollError(null)
    } catch (error) {
      setError(
        errorMessage(error, '無法開始生成，請重試。重試會沿用同一次請求，避免建立重複任務。'),
      )
    } finally {
      mutating.current = false
      setBusy(null)
    }
  }

  return (
    <>
      <div className="workspace-heading">
        <div>
          <button className="back-button" onClick={onBack}>
            ← 所有專案
          </button>
          <h1>{projectName ?? '載入專案中…'}</h1>
        </div>
        <span className="pill">單張圖片 · 示範流程</span>
      </div>
      {loadError ? (
        <div className="error-panel" role="alert">
          <p>{loadError}</p>
          <button
            className="button secondary"
            onClick={() => {
              setLoadError(null)
              setAttempt((value) => value + 1)
            }}
          >
            重新載入專案
          </button>
        </div>
      ) : !projectName ? (
        <p role="status" className="muted">
          正在恢復圖片與任務進度…
        </p>
      ) : (
        <div className="workspace-layout">
          <aside className="card input-panel" aria-labelledby="source-title">
            <span className="section-number">01 / 圖片輸入</span>
            <h2 id="source-title">你的參考圖片</h2>
            <p className="muted">選擇完整物件、輪廓清楚的照片。</p>
            {sourceAssetId ? (
              <SourcePreview key={sourceAssetId} assetId={sourceAssetId} />
            ) : (
              <div className="upload-placeholder">
                <span aria-hidden="true">＋</span>
                <p>從一張圖片開始</p>
                <small>簡單背景，讓物件更清楚</small>
              </div>
            )}
            <label className={`upload-button ${busy || running ? 'disabled' : ''}`}>
              {busy === 'upload' ? '上傳中…' : sourceAssetId ? '更換圖片' : '選擇圖片'}
              <input
                type="file"
                aria-label="上傳圖片"
                accept="image/png,image/jpeg"
                onChange={handleUpload}
                disabled={!!busy || running}
              />
            </label>
            <p className="file-hint">
              PNG / JPEG · 最高 10 MB
              <br />
              最長邊 4096 px · 最高 1600 萬像素
            </p>
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
            <div className="panel-divider" />
            <span className="section-number">02 / 生成模型</span>
            <div className="demo-note">
              <span className="status-dot" />
              <div>
                <strong>固定模型示範</strong>
                <p>不呼叫 AI、不產生費用。所有圖片皆取得相同的示範模型。</p>
              </div>
            </div>
            <button
              className="button primary generate-button"
              onClick={handleGenerate}
              disabled={!sourceAssetId || !!busy || running}
              aria-label="開始示範生成"
            >
              {busy === 'generate'
                ? '建立任務中…'
                : running
                  ? '任務處理中…'
                  : generationState === 'failed'
                    ? '重試示範生成'
                    : '開始示範生成'}
              <span aria-hidden="true">↗</span>
            </button>
            {!sourceAssetId && <p className="file-hint">先上傳圖片，即可開始。</p>}
          </aside>
          <section className="preview-panel" aria-labelledby="preview-title">
            <div className="preview-heading">
              <div>
                <span className="section-number">03 / 3D 預覽</span>
                <h2 id="preview-title">換個角度，看看你的物件</h2>
              </div>
              <span className="pill">GLB</span>
            </div>
            {modelVersion ? (
              <Suspense
                fallback={
                  <div className="viewer-placeholder" role="status">
                    正在準備 3D 預覽…
                  </div>
                }
              >
                <ModelViewer key={modelVersion.id} url={modelVersion.asset_url} />
              </Suspense>
            ) : (
              <div className="viewer-placeholder">
                <CubeIcon className={running ? 'waiting-cube' : ''} />
                <h3>
                  {modelError
                    ? '模型資訊尚未載入'
                    : generationState === 'ready'
                      ? '正在取得模型…'
                      : running
                        ? STAGE_LABEL[generation!.state]
                        : generationState === 'failed'
                          ? '這次任務未完成'
                          : '你的 3D 預覽空間'}
                </h3>
                <p>
                  {running
                    ? '你可以重新整理頁面，回來後會繼續追蹤進度。'
                    : generationState === 'failed'
                      ? '請查看下方原因，再重新開始示範生成。'
                      : generationState === 'ready'
                        ? '任務已完成，正在準備顯示模型。'
                        : '上傳參考圖片並開始示範，模型就會出現在這裡。'}
                </p>
                {modelError && (
                  <div className="error" role="alert">
                    <p>{modelError}</p>
                    <button
                      className="button secondary"
                      onClick={() => {
                        setModelError(null)
                        setModelAttempt((value) => value + 1)
                      }}
                    >
                      重新載入模型
                    </button>
                  </div>
                )}
              </div>
            )}
            {generation && (
              <div className="task-panel" aria-live="polite">
                <div className="task-heading">
                  <strong>任務狀態：{STAGE_LABEL[generation.state]}</strong>
                  <span className="muted">示範任務</span>
                </div>
                <ol className="stage-list" aria-label="生成階段">
                  {STAGES.map((stage, index) => (
                    <li
                      key={stage}
                      className={
                        generation.state === 'failed'
                          ? ''
                          : index <= STAGES.indexOf(generation.state)
                            ? 'reached'
                            : ''
                      }
                      aria-current={stage === generation.state ? 'step' : undefined}
                    >
                      <span />
                      {STAGE_LABEL[stage]}
                    </li>
                  ))}
                </ol>
                {generation.state === 'queued' && (
                  <p className="file-hint">若持續等待，請確認背景 worker 已啟動。</p>
                )}
                {generation.state === 'failed' && (
                  <p role="alert" className="error">
                    {generation.error?.message ?? '任務處理失敗，請重試。'}
                  </p>
                )}
                {pollError && (
                  <p role="alert" className="error">
                    {pollError} 系統會自動重試查詢。
                  </p>
                )}
              </div>
            )}
            {modelVersion && (
              <div className="model-meta">
                <span>{modelVersion.metrics.triangles.toLocaleString('zh-TW')} 三角面</span>
                <span>{(modelVersion.metrics.bytes / 1024).toFixed(1)} KB</span>
                <span>固定示範模型</span>
              </div>
            )}
            <p className="phase-note">
              此階段提供圖片上傳、示範任務與模型預覽。AI 生成、模型調整及三種匯出將於後續階段開放。
            </p>
          </section>
        </div>
      )}
    </>
  )
}

export function App() {
  const [projectId, selectProject] = useSelectedProject()
  return (
    <div className="app-shell">
      <header className="site-header">
        <button
          className="brand"
          onClick={() => selectProject(null)}
          aria-label="Picture to Model 首頁"
        >
          <CubeIcon />
          <span>
            picture<span className="brand-to"> to </span>model
          </span>
        </button>
        <span className="environment-label">
          <span className="status-dot" />
          本機示範 <span className="environment-detail">/ PHASE 01</span>
        </span>
      </header>
      <main>
        {projectId ? (
          <Workspace key={projectId} projectId={projectId} onBack={() => selectProject(null)} />
        ) : (
          <Home onSelect={selectProject} />
        )}
      </main>
      <footer className="site-footer">
        <span>Picture to Model</span>
        <span>從平面靈感，到立體可能。</span>
      </footer>
    </div>
  )
}
