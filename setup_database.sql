-- Connect to the database
\c faq_db;

-- Enable pgvector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- Create tables
CREATE TABLE IF NOT EXISTS faqs (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    embedding vector(768),
    source TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS website_content (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for vector similarity search
CREATE INDEX IF NOT EXISTS faq_embedding_idx ON faqs USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS website_embedding_idx ON website_content USING ivfflat (embedding vector_cosine_ops);

-- Create unique constraint on website_content url
ALTER TABLE website_content ADD CONSTRAINT unique_url UNIQUE (url);

-- Grant permissions to faquser
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO faquser;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO faquser;