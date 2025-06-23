-- RAGアプリケーション用テーブル作成スクリプト
-- 新入社員向け社内文書検索システム

-- pgvector拡張を有効化（ベクトル検索用）
CREATE EXTENSION IF NOT EXISTS vector;

-- 文書管理テーブル
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    upload_date TIMESTAMP DEFAULT NOW(),
    file_size BIGINT,
    total_pages INTEGER,
    processing_status TEXT DEFAULT 'processing',
    created_at TIMESTAMP DEFAULT NOW()
);

-- チャンクテーブル (ベクトル検索用)
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    filename TEXT NOT NULL,
    page_number INTEGER,
    chapter_number INTEGER,
    section_name TEXT,
    start_pos JSONB,        -- {x, y} 座標
    end_pos JSONB,          -- {x, y} 座標
    embedding VECTOR(1536), -- OpenAI embedding dimension
    token_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ベクトル検索用インデックス
CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx 
ON document_chunks USING ivfflat (embedding vector_cosine_ops);

-- 一般的な検索用インデックス
CREATE INDEX IF NOT EXISTS documents_filename_idx ON documents(filename);
CREATE INDEX IF NOT EXISTS documents_processing_status_idx ON documents(processing_status);
CREATE INDEX IF NOT EXISTS document_chunks_document_id_idx ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS document_chunks_filename_idx ON document_chunks(filename);
CREATE INDEX IF NOT EXISTS document_chunks_page_number_idx ON document_chunks(page_number);

-- Row Level Security (RLS) 設定
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;

-- 基本的なRLSポリシー（開発初期は全アクセス許可）
CREATE POLICY "Allow all operations on documents" ON documents
    FOR ALL USING (true);

CREATE POLICY "Allow all operations on document_chunks" ON document_chunks
    FOR ALL USING (true);

-- テーブル作成確認
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('documents', 'document_chunks');