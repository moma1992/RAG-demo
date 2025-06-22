"""
ベクトルストアサービスのテスト

Supabase統合とベクトル検索のテストケース
"""

import pytest
from unittest.mock import Mock, patch
from services.vector_store import VectorStore, VectorStoreError, DocumentRecord
from models.document import SearchResult
import uuid


class TestVectorStore:
    """ベクトルストアテストクラス"""
    
    def test_init(self):
        """初期化テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        assert store.supabase_url == "https://test.supabase.co"
        assert store.supabase_key == "test-key"
    
    def test_store_document_success(self, mock_supabase_client):
        """文書保存成功テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        document_data = {
            "filename": "test.pdf",
            "original_filename": "テスト文書.pdf",
            "file_size": 1024,
            "total_pages": 10
        }
        
        document_id = store.store_document(document_data)
        
        assert document_id is not None
        assert isinstance(document_id, str)
        # UUIDフォーマットの確認
        assert len(document_id) == 36
    
    def test_store_document_failure(self, mock_supabase_client):
        """文書保存失敗テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # Supabaseエラーをシミュレート
        mock_supabase_client.table.return_value.insert.return_value.execute.side_effect = Exception("Database error")
        
        document_data = {"filename": "test.pdf"}
        
        with pytest.raises(VectorStoreError):
            store.store_document(document_data)
    
    def test_store_chunks_success(self, mock_supabase_client):
        """チャンク保存成功テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        chunks = [
            {
                "content": "テストチャンク1",
                "page_number": 1,
                "token_count": 10,
                "embedding": [0.1] * 1536
            },
            {
                "content": "テストチャンク2", 
                "page_number": 1,
                "token_count": 15,
                "embedding": [0.2] * 1536
            }
        ]
        
        document_id = str(uuid.uuid4())
        
        # エラーが発生しないことを確認
        store.store_chunks(chunks, document_id)
    
    def test_similarity_search_success(self, mock_supabase_client):
        """類似検索成功テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        query_embedding = [0.1] * 1536
        
        results = store.similarity_search(query_embedding, k=5)
        
        assert isinstance(results, list)
        assert len(results) >= 0
        
        # 結果が返される場合の検証
        if results:
            for result in results:
                assert isinstance(result, SearchResult)
                assert hasattr(result, 'chunk')
                assert hasattr(result, 'similarity_score')
                assert hasattr(result, 'rank')
                assert 0 <= result.similarity_score <= 1
    
    def test_similarity_search_with_threshold(self, mock_supabase_client):
        """閾値付き類似検索テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        query_embedding = [0.1] * 1536
        threshold = 0.8
        
        results = store.similarity_search(
            query_embedding, 
            k=3, 
            similarity_threshold=threshold
        )
        
        assert isinstance(results, list)
        # 返された結果が閾値以上であることを確認
        for result in results:
            assert result.similarity_score >= threshold
    
    def test_get_documents_success(self, mock_supabase_client):
        """文書一覧取得成功テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        documents = store.get_documents()
        
        assert isinstance(documents, list)
        
        # ダミーデータが返される場合の検証
        if documents:
            for doc in documents:
                assert isinstance(doc, DocumentRecord)
                assert hasattr(doc, 'id')
                assert hasattr(doc, 'filename')
                assert hasattr(doc, 'upload_date')
    
    def test_delete_document_success(self, mock_supabase_client):
        """文書削除成功テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        document_id = str(uuid.uuid4())
        
        # エラーが発生しないことを確認
        store.delete_document(document_id)
    
    def test_delete_document_failure(self, mock_supabase_client):
        """文書削除失敗テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # Supabaseエラーをシミュレート
        mock_supabase_client.table.return_value.delete.return_value.execute.side_effect = Exception("Delete error")
        
        document_id = str(uuid.uuid4())
        
        with pytest.raises(VectorStoreError):
            store.delete_document(document_id)


class TestSearchResult:
    """SearchResultテストクラス"""
    
    def test_search_result_creation(self):
        """SearchResult作成テスト"""
        from models.document import DocumentChunk, ChunkPosition
        
        # DocumentChunkを作成
        chunk = DocumentChunk(
            content="テスト結果",
            filename="test.pdf",
            page_number=1,
            chapter_number=1,
            section_name="第1章",
            start_pos=ChunkPosition(x=0, y=0, width=100, height=50),
            end_pos=ChunkPosition(x=100, y=50, width=100, height=50),
            token_count=20
        )
        
        # SearchResultを作成
        result = SearchResult(
            chunk=chunk,
            similarity_score=0.85,
            rank=1
        )
        
        assert result.chunk.content == "テスト結果"
        assert result.chunk.filename == "test.pdf"
        assert result.chunk.page_number == 1
        assert result.similarity_score == 0.85
        assert result.rank == 1


class TestDocumentRecord:
    """DocumentRecordテストクラス"""
    
    def test_document_record_creation(self):
        """DocumentRecord作成テスト"""
        record = DocumentRecord(
            id=str(uuid.uuid4()),
            filename="test.pdf",
            original_filename="テスト.pdf",
            upload_date="2024-01-15T10:00:00Z",
            file_size=1024000,
            total_pages=25,
            processing_status="completed"
        )
        
        assert record.filename == "test.pdf"
        assert record.original_filename == "テスト.pdf"
        assert record.file_size == 1024000
        assert record.total_pages == 25
        assert record.processing_status == "completed"


# 統合テスト
class TestVectorStoreIntegration:
    """ベクトルストア統合テスト"""
    
    def test_document_lifecycle(self, mock_supabase_client):
        """文書ライフサイクル統合テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # 1. 文書保存
        document_data = {
            "filename": "lifecycle_test.pdf",
            "file_size": 2048,
            "total_pages": 5
        }
        document_id = store.store_document(document_data)
        
        # 2. チャンク保存
        chunks = [
            {
                "content": f"テストチャンク{i}",
                "page_number": i % 5 + 1,
                "embedding": [0.1 + i * 0.01] * 1536
            }
            for i in range(10)
        ]
        store.store_chunks(chunks, document_id)
        
        # 3. 検索実行
        query_embedding = [0.1] * 1536
        results = store.similarity_search(query_embedding)
        
        # 4. 文書一覧確認
        documents = store.get_documents()
        
        # 5. 文書削除
        store.delete_document(document_id)
        
        # 全ての操作がエラーなしで完了することを確認
        assert document_id is not None
        assert isinstance(results, list)
        assert isinstance(documents, list)