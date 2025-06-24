"""
ベクトルストアサービスの新機能成功テスト - Issue #57 TDD Green Phase

実装された bulk_insert_embeddings および search_similar_embeddings の成功テスト
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from services.vector_store import VectorStore, VectorStoreError, SearchResult


class TestBulkInsertEmbeddingsGreen:
    """bulk_insert_embeddings Green Phase テスト"""
    
    @pytest.mark.asyncio
    async def test_bulk_insert_embeddings_success(self, mock_supabase_client):
        """TDD Green: bulk_insert_embeddings 成功テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # モック設定
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = Mock()
        
        embedding_results = [
            Mock(embedding=[0.1] * 1536, metadata={"id": "1"}),
            Mock(embedding=[0.2] * 1536, metadata={"id": "2"})
        ]
        
        document_chunks = [
            {
                "content": "テストチャンク1",
                "filename": "test.pdf", 
                "page_number": 1,
                "token_count": 10
            },
            {
                "content": "テストチャンク2",
                "filename": "test.pdf",
                "page_number": 2, 
                "token_count": 15
            }
        ]
        
        # 実行
        result = await store.bulk_insert_embeddings(embedding_results, document_chunks)
        
        # 検証
        assert result is True
        mock_supabase_client.table.assert_called_with("document_chunks")
    
    @pytest.mark.asyncio
    async def test_bulk_insert_embeddings_empty_error(self, mock_supabase_client):
        """TDD Green: 空リストエラーハンドリング"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        with pytest.raises(VectorStoreError, match="埋め込みまたはチャンクリストが空です"):
            await store.bulk_insert_embeddings([], [])
    
    @pytest.mark.asyncio
    async def test_bulk_insert_embeddings_length_mismatch_error(self, mock_supabase_client):
        """TDD Green: リスト長不一致エラーハンドリング"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        embedding_results = [Mock(embedding=[0.1] * 1536)]
        document_chunks = [
            {"content": "chunk1", "filename": "test.pdf"},
            {"content": "chunk2", "filename": "test.pdf"}
        ]
        
        with pytest.raises(VectorStoreError, match="埋め込み数\\(1\\)とチャンク数\\(2\\)が一致しません"):
            await store.bulk_insert_embeddings(embedding_results, document_chunks)
    
    @pytest.mark.asyncio
    async def test_bulk_insert_embeddings_1000_chunks(self, mock_supabase_client):
        """TDD Green: 1000件一括挿入成功テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # モック設定
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = Mock()
        
        # 1000件のテストデータ生成
        embedding_results = [
            Mock(embedding=[0.1] * 1536, metadata={"id": str(i)})
            for i in range(1000)
        ]
        document_chunks = [
            {
                "content": f"テストチャンク{i}",
                "filename": "test.pdf",
                "page_number": i % 100 + 1,
                "token_count": 10
            }
            for i in range(1000)
        ]
        
        # 実行
        result = await store.bulk_insert_embeddings(embedding_results, document_chunks)
        
        # 検証
        assert result is True
        # insert呼び出しの引数を確認
        call_args = mock_supabase_client.table.return_value.insert.call_args[0][0]
        assert len(call_args) == 1000


class TestSearchSimilarEmbeddingsGreen:
    """search_similar_embeddings Green Phase テスト"""
    
    @pytest.mark.asyncio
    async def test_search_similar_embeddings_success(self, mock_supabase_client):
        """TDD Green: search_similar_embeddings 成功テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # モック結果設定
        mock_result = Mock()
        mock_result.data = [
            {
                "content": "テスト結果1",
                "filename": "test.pdf",
                "page_number": 1,
                "distance": 0.2,  # 0.8の類似度
                "section_name": "第1章",
                "chapter_number": 1,
                "start_pos": {"x": 100, "y": 200},
                "end_pos": {"x": 300, "y": 250},
                "token_count": 25
            },
            {
                "content": "テスト結果2", 
                "filename": "test.pdf",
                "page_number": 2,
                "distance": 0.3,  # 0.7の類似度
                "section_name": "第2章",
                "chapter_number": 2,
                "start_pos": {"x": 50, "y": 100},
                "end_pos": {"x": 250, "y": 150},
                "token_count": 30
            }
        ]
        
        mock_supabase_client.rpc.return_value.execute.return_value = mock_result
        
        query_embedding = [0.1] * 1536
        
        # 実行
        results = await store.search_similar_embeddings(query_embedding, limit=10)
        
        # 検証
        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)
        
        # 第1件目の詳細検証
        result1 = results[0]
        assert result1.content == "テスト結果1"
        assert result1.filename == "test.pdf"
        assert result1.page_number == 1
        assert result1.similarity_score == 0.8  # 1.0 - 0.2
        assert result1.metadata["section_name"] == "第1章"
        assert result1.metadata["chapter_number"] == 1
        assert result1.metadata["token_count"] == 25
        
        # RPC呼び出し検証
        mock_supabase_client.rpc.assert_called_with(
            "match_documents",
            {
                "query_embedding": query_embedding,
                "match_threshold": 0.0,
                "match_count": 10,
            }
        )
    
    @pytest.mark.asyncio
    async def test_search_similar_embeddings_invalid_embedding_error(self, mock_supabase_client):
        """TDD Green: 無効な埋め込みベクトルエラーハンドリング"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # 次元数が間違っている埋め込みベクトル
        invalid_embedding = [0.1] * 512  # 1536ではなく512次元
        
        with pytest.raises(VectorStoreError, match="埋め込みベクトルは1536次元である必要があります"):
            await store.search_similar_embeddings(invalid_embedding, limit=10)
    
    @pytest.mark.asyncio
    async def test_search_similar_embeddings_limit_validation_error(self, mock_supabase_client):
        """TDD Green: limit パラメータ検証エラーハンドリング"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        query_embedding = [0.1] * 1536
        
        # 無効なlimit値のテスト
        with pytest.raises(VectorStoreError, match="limit は正の整数である必要があります"):
            await store.search_similar_embeddings(query_embedding, limit=-1)
        
        with pytest.raises(VectorStoreError, match="limit は正の整数である必要があります"):
            await store.search_similar_embeddings(query_embedding, limit=0)
        
        with pytest.raises(VectorStoreError, match="limit は100以下である必要があります"):
            await store.search_similar_embeddings(query_embedding, limit=1001)
    
    @pytest.mark.asyncio
    async def test_search_similar_embeddings_empty_result(self, mock_supabase_client):
        """TDD Green: 空結果処理テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # 空結果のモック設定
        mock_result = Mock()
        mock_result.data = []
        mock_supabase_client.rpc.return_value.execute.return_value = mock_result
        
        query_embedding = [0.1] * 1536
        
        # 実行
        results = await store.search_similar_embeddings(query_embedding, limit=10)
        
        # 検証
        assert len(results) == 0
        assert isinstance(results, list)