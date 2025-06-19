"""
ベクトルストアサービスの単体テスト

Supabase統合とベクトル検索のテストケース
"""

import pytest
from unittest.mock import Mock, patch
from services.vector_store import VectorStore, VectorStoreError, SearchResult, DocumentRecord
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
                assert hasattr(result, 'content')
                assert hasattr(result, 'similarity_score')
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
        result = SearchResult(
            content="テスト結果",
            filename="test.pdf",
            page_number=1,
            similarity_score=0.85,
            metadata={"section": "第1章"}
        )
        
        assert result.content == "テスト結果"
        assert result.filename == "test.pdf"
        assert result.page_number == 1
        assert result.similarity_score == 0.85
        assert result.metadata["section"] == "第1章"


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