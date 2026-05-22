CREATE EXTENSION IF NOT EXISTS vector;

DROP TABLE IF EXISTS logs CASCADE;

CREATE TABLE logs (
    id BIGSERIAL PRIMARY KEY,
    source TEXT,
    log_timestamp TIMESTAMP NULL,
    level TEXT NULL,
    raw_message TEXT NOT NULL,
    normalized_message TEXT,
    embedding VECTOR(384),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX logs_level_idx ON logs(level);
CREATE INDEX logs_time_idx ON logs(log_timestamp);

-- HNSW index for cosine similarity search
CREATE INDEX logs_embedding_hnsw_idx
ON logs
USING hnsw (embedding vector_cosine_ops);
