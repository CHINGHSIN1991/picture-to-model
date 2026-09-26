CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    name TEXT NOT NULL,
    source_asset_id TEXT REFERENCES assets(id),
    created_at TEXT NOT NULL
);
CREATE INDEX projects_owner ON projects(owner_id, created_at);

CREATE TABLE assets (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    kind TEXT NOT NULL CHECK (kind IN ('image', 'model')),
    storage_key TEXT NOT NULL UNIQUE,
    sha256 TEXT NOT NULL,
    mime TEXT NOT NULL,
    bytes INTEGER NOT NULL CHECK (bytes > 0),
    created_at TEXT NOT NULL
);

CREATE TABLE generations (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    owner_id TEXT NOT NULL,
    source_asset_id TEXT NOT NULL REFERENCES assets(id),
    provider TEXT NOT NULL,
    provider_model TEXT NOT NULL,
    parameters TEXT NOT NULL DEFAULT '{}',
    provider_task_id TEXT,
    state TEXT NOT NULL CHECK (state IN (
        'queued', 'submitting', 'generating', 'downloading', 'validating', 'ready', 'failed'
    )),
    idempotency_key TEXT NOT NULL,
    result_storage_key TEXT,
    model_version_id TEXT REFERENCES model_versions(id),
    error_code TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(owner_id, idempotency_key)
);
CREATE INDEX generations_project ON generations(project_id, created_at);

CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    generation_id TEXT NOT NULL UNIQUE REFERENCES generations(id),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed')),
    next_run_at REAL NOT NULL,
    lease_token TEXT,
    lease_expires_at REAL,
    attempt INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX jobs_claim ON jobs(status, next_run_at, lease_expires_at);

CREATE TABLE model_versions (
    id TEXT PRIMARY KEY,
    generation_id TEXT NOT NULL UNIQUE REFERENCES generations(id),
    original_asset_id TEXT NOT NULL REFERENCES assets(id),
    metrics TEXT NOT NULL,
    created_at TEXT NOT NULL
);
