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

export function createProject(name: string): Promise<Project> {
  return parse(
    fetch('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    }),
  )
}

export function listProjects(): Promise<{ items: Project[] }> {
  return parse(fetch('/api/projects'))
}

export function getProject(projectId: string): Promise<ProjectDetail> {
  return parse(fetch(`/api/projects/${projectId}`))
}

export async function uploadImage(projectId: string, file: File): Promise<Asset> {
  const body = new FormData()
  body.append('file', file)
  return parse(fetch(`/api/projects/${projectId}/images`, { method: 'POST', body }))
}

export function createGeneration(
  projectId: string,
  sourceAssetId: string,
  idempotencyKey: string,
): Promise<Generation> {
  return parse(
    fetch(`/api/projects/${projectId}/generations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Idempotency-Key': idempotencyKey },
      body: JSON.stringify({ source_asset_id: sourceAssetId }),
    }),
  )
}

export function getGeneration(generationId: string): Promise<Generation> {
  return parse(fetch(`/api/generations/${generationId}`))
}

export function getModelVersion(versionId: string): Promise<ModelVersion> {
  return parse(fetch(`/api/model-versions/${versionId}`))
}
