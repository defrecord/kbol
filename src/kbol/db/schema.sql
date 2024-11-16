-- Extension for hashing
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Track processed documents and their state
CREATE TABLE IF NOT EXISTS processed_documents (
    id SERIAL PRIMARY KEY,
    file_path TEXT UNIQUE NOT NULL,
    file_hash TEXT NOT NULL,  -- SHA-256 hash of file content
    chunk_size INTEGER NOT NULL,
    chunk_overlap INTEGER NOT NULL,
    embed_model TEXT NOT NULL,
    processor_version TEXT NOT NULL,  -- Version hash of processing logic
    chunks_count INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'completed',
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indices for common queries
CREATE INDEX IF NOT EXISTS idx_processed_docs_path ON processed_documents(file_path);
CREATE INDEX IF NOT EXISTS idx_processed_docs_hash ON processed_documents(file_hash);

-- Track processing configuration to detect implementation changes
CREATE TABLE IF NOT EXISTS processor_versions (
    id SERIAL PRIMARY KEY,
    version_hash TEXT UNIQUE NOT NULL,
    config_json JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);
