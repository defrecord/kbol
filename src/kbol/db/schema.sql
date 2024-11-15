CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS book_chunks (
    id SERIAL PRIMARY KEY,
    book_title TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(384),
    page_number INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS book_chunks_embedding_idx ON book_chunks 
USING ivfflat (embedding vector_cosine_ops);
