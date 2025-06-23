-- RAGアプリケーション用テーブル作成スクリプト
-- 新入社員向け社内文書検索システム

-- pgvector拡張を有効化（ベクトル検索用）
CREATE EXTENSION IF NOT EXISTS vector;

-- 文書管理テーブル
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    upload_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    file_size BIGINT,
    total_pages INTEGER,
    processing_status TEXT DEFAULT 'processing' CHECK (processing_status IN ('processing', 'completed', 'failed')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- チャンクテーブル (ベクトル検索用)
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL CHECK (length(content) > 0),
    filename TEXT NOT NULL,
    page_number INTEGER CHECK (page_number > 0),
    chapter_number INTEGER CHECK (chapter_number > 0),
    section_name TEXT,
    start_pos JSONB,        -- {x, y} 座標
    end_pos JSONB,          -- {x, y} 座標
    embedding VECTOR(1536), -- OpenAI embedding dimension
    token_count INTEGER CHECK (token_count > 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
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

-- 自動更新トリガー関数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- トリガーを各テーブルに追加
CREATE OR REPLACE TRIGGER update_documents_updated_at 
    BEFORE UPDATE ON documents 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER update_document_chunks_updated_at 
    BEFORE UPDATE ON document_chunks 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ベクトル検索用RPC関数（入力検証付き）
CREATE OR REPLACE FUNCTION match_documents (
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.3,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id uuid,
    content text,
    filename text,
    page_number int,
    chapter_number int,
    section_name text,
    start_pos jsonb,
    end_pos jsonb,
    token_count int,
    distance float
)
LANGUAGE sql STABLE
AS $$
    -- 入力検証
    SELECT CASE 
        WHEN match_threshold < 0 OR match_threshold > 2 THEN
            (SELECT ERROR('match_threshold must be between 0 and 2'))
        WHEN match_count <= 0 OR match_count > 100 THEN
            (SELECT ERROR('match_count must be between 1 and 100'))
        ELSE NULL
    END;

    -- メインクエリ
    SELECT
        document_chunks.id,
        document_chunks.content,
        document_chunks.filename,
        document_chunks.page_number,
        document_chunks.chapter_number,
        document_chunks.section_name,
        document_chunks.start_pos,
        document_chunks.end_pos,
        document_chunks.token_count,
        document_chunks.embedding <=> query_embedding AS distance
    FROM document_chunks
    WHERE 
        document_chunks.embedding IS NOT NULL
        AND document_chunks.embedding <=> query_embedding < match_threshold
        AND EXISTS (
            SELECT 1 FROM documents 
            WHERE documents.id = document_chunks.document_id 
            AND documents.processing_status = 'completed'
        )
    ORDER BY document_chunks.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- 統計情報取得RPC関数
CREATE OR REPLACE FUNCTION get_database_stats()
RETURNS JSON
LANGUAGE sql STABLE
AS $$
    SELECT json_build_object(
        'total_documents', (SELECT COUNT(*) FROM documents),
        'total_chunks', (SELECT COUNT(*) FROM document_chunks),
        'status_breakdown', (
            SELECT json_object_agg(processing_status, count)
            FROM (
                SELECT processing_status, COUNT(*) as count
                FROM documents 
                GROUP BY processing_status
            ) sub
        ),
        'avg_chunks_per_document', (
            SELECT ROUND(
                CASE 
                    WHEN (SELECT COUNT(*) FROM documents) = 0 THEN 0
                    ELSE (SELECT COUNT(*) FROM document_chunks)::numeric / (SELECT COUNT(*) FROM documents)::numeric
                END, 2
            )
        ),
        'last_updated', NOW()
    );
$$;

-- 埋め込みベクトル検証関数
CREATE OR REPLACE FUNCTION validate_embedding(embedding_vector vector(1536))
RETURNS boolean
LANGUAGE sql IMMUTABLE
AS $$
    SELECT 
        embedding_vector IS NOT NULL 
        AND array_length(embedding_vector::float[], 1) = 1536
        AND NOT EXISTS (
            SELECT 1 
            FROM unnest(embedding_vector::float[]) AS val 
            WHERE val IS NULL OR val <> val  -- NaN check
        );
$$;

-- テーブル作成確認
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('documents', 'document_chunks');