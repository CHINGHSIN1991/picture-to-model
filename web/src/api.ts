export interface Project {
  id: string
  name: string
  created_at: string
  source_asset_id: string | null
}

export type GenerationState =
  'queued' | 'submitting' | 'generating' | 'downloading' | 'validating' | 'ready' | 'failed'

export interface Generation {
  id: string
  project_id: string
  source_asset_id: string
  state: GenerationState
  provider: 'fake'
  created_at: string
  model_version_id: string | null
  error: { code: string; message: string } | null
}

export interface ProjectDetail extends Project {
  generations: Generation[]
}

export interface Asset {
  id: string
  url: string
  mime: string
  bytes: number
}

export interface ModelVersion {
  id: string
  asset_url: string
  provider: 'fake'
  metrics: { triangles: number; bytes: number }
}

export class ApiError extends Error {
  code: string
  status: number

  constructor(message: string, code: string, status: number) {
    super(message)
    this.code = code
    this.status = status
  }
}

async function parse<T>(pending: Promise<Response>): Promise<T> {
  const response = await pending
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(
      body?.message ?? '請求無法處理。',
      body?.code ?? 'unknown_error',
      response.status,
    )
  }
  return (await response.json()) as T
}

function request(url: string, init?: RequestInit): Promise<Response> {
  const timeout = AbortSignal.timeout(20000)
  return fetch(url, {
    ...init,
    signal: init?.signal ? AbortSignal.any([init.signal, timeout]) : timeout,
  })
}

export function createProject(name: string): Promise<Project> {
  return parse(
    request('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    }),
  )
}

export function listProjects(signal?: AbortSignal): Promise<{ items: Project[] }> {
  return parse(request('/api/projects', { signal }))
}

export function getProject(projectId: string, signal?: AbortSignal): Promise<ProjectDetail> {
  return parse(request(`/api/projects/${encodeURIComponent(projectId)}`, { signal }))
}

export async function uploadImage(projectId: string, file: File): Promise<Asset> {
  const body = new FormData()
  body.append('file', file)
  return parse(
    request(`/api/projects/${encodeURIComponent(projectId)}/images`, { method: 'POST', body }),
  )
}

export function createGeneration(
  projectId: string,
  sourceAssetId: string,
  idempotencyKey: string,
): Promise<Generation> {
  return parse(
    request(`/api/projects/${encodeURIComponent(projectId)}/generations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Idempotency-Key': idempotencyKey },
      body: JSON.stringify({ source_asset_id: sourceAssetId }),
    }),
  )
}

export function getGeneration(generationId: string, signal?: AbortSignal): Promise<Generation> {
  return parse(request(`/api/generations/${encodeURIComponent(generationId)}`, { signal }))
}

export function getModelVersion(versionId: string, signal?: AbortSignal): Promise<ModelVersion> {
  return parse(request(`/api/model-versions/${encodeURIComponent(versionId)}`, { signal }))
}
