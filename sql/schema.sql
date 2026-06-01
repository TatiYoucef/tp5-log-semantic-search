CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

DROP TABLE IF EXISTS pipeline_runs CASCADE;
DROP TABLE IF EXISTS message_embeddings CASCADE;
DROP TABLE IF EXISTS log_entries CASCADE;
DROP TABLE IF EXISTS event_templates CASCADE;

CREATE TABLE event_templates (
    event_id TEXT PRIMARY KEY,
    event_template TEXT NOT NULL,
    occurrences INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE log_entries (
    id BIGSERIAL PRIMARY KEY,
    line_id BIGINT NOT NULL UNIQUE,
    source TEXT NOT NULL DEFAULT 'OpenSSH',
    log_timestamp TIMESTAMP NULL,
    month TEXT NULL,
    day INTEGER NULL,
    time_text TEXT NULL,
    host TEXT NULL,
    service TEXT NULL,
    process_id INTEGER NULL,
    level TEXT NOT NULL,
    event_id TEXT NULL REFERENCES event_templates(event_id),
    raw_message TEXT NOT NULL,
    normalized_message TEXT NOT NULL,
    event_template TEXT NULL,
    inserted_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE message_embeddings (
    normalized_message TEXT PRIMARY KEY,
    representative_event_id TEXT NULL,
    representative_level TEXT NULL,
    occurrences BIGINT NOT NULL DEFAULT 0,
    embedding VECTOR(384) NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE pipeline_runs (
    id BIGSERIAL PRIMARY KEY,
    command TEXT NOT NULL,
    status TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMP NULL
);

CREATE INDEX log_entries_level_idx ON log_entries(level);
CREATE INDEX log_entries_event_id_idx ON log_entries(event_id);
CREATE INDEX log_entries_time_idx ON log_entries(log_timestamp);
CREATE INDEX log_entries_line_id_idx ON log_entries(line_id);
CREATE INDEX log_entries_normalized_message_idx ON log_entries(normalized_message);
CREATE INDEX log_entries_raw_message_trgm_idx
    ON log_entries USING gin (raw_message gin_trgm_ops);

CREATE INDEX message_embeddings_embedding_hnsw_idx
    ON message_embeddings USING hnsw (embedding vector_cosine_ops);
