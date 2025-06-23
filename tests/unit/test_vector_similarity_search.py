"""
ベクトル類似検索テスト

Issue #37: Vector Similarity Search Implementation
TDD Red フェーズ: 失敗テスト作成

このテストは、Issue #37で要求される全機能をテストします：
- SearchQuery/SearchResultデータクラス
- VectorSearchメインクラス
- 類似検索メソッド群
- ハイブリッド検索
- フィルタリング機能
- パフォーマンス要件
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

# 実装モジュールのインポート
from services.vector_similarity_search import (
    SearchQuery,
    SearchResult, 
    VectorSearch,
    VectorSearchError
)


class TestSearchQuery:
    """SearchQueryデータクラステスト"""
    
    def test_search_query_creation_with_required_fields(self):
        """必須フィールドでのSearchQuery作成テスト"""
        query = SearchQuery(
            text="Python機械学習について教えて",
            limit=5,
            similarity_threshold=0.7
        )
        assert query.text == "Python機械学習について教えて"
        assert query.limit == 5
        assert query.similarity_threshold == 0.7
        assert query.filters is None
        assert query.include_metadata is True
    
    def test_search_query_creation_with_optional_fields(self):
        """オプションフィールド付きSearchQuery作成テスト"""
        filters = {"filename": "guide.pdf", "page_number": {"$gte": 1}}
        query = SearchQuery(
            text="Streamlit使い方",
            limit=10,
            similarity_threshold=0.8,
            filters=filters,
            include_metadata=False
        )
        assert query.filters == filters
        assert query.include_metadata is False
    
    def test_search_query_validation_invalid_limit(self):
        """無効なlimit値のバリデーションテスト"""
        with pytest.raises(ValueError, match="limit は1以上100以下である必要があります"):
            SearchQuery(
                text="テスト",
                limit=0,  # 無効な値
                similarity_threshold=0.7
            )
    
    def test_search_query_validation_invalid_threshold(self):
        """無効な類似度閾値のバリデーションテスト"""
        with pytest.raises(ValueError, match="similarity_threshold は0.0-1.0の範囲である必要があります"):
            SearchQuery(
                text="テスト",
                limit=5,
                similarity_threshold=1.5  # 無効な値
            )
    
    def test_search_query_validation_empty_text(self):
        """空のテキストのバリデーションテスト"""
        with pytest.raises(ValueError, match="text は空でない文字列である必要があります"):
            SearchQuery(
                text="",  # 空文字
                limit=5,
                similarity_threshold=0.7
            )


class TestSearchResult:
    """SearchResultデータクラステスト"""
    
    def test_search_result_creation(self):
        """SearchResult作成テスト"""
        metadata = {
            "section_name": "第1章 概要",
            "chapter_number": 1,
            "start_pos": {"x": 100.0, "y": 200.0},
            "end_pos": {"x": 400.0, "y": 250.0}
        }
        
        result = SearchResult(
            chunk_id="chunk_123",
            content="Pythonは汎用プログラミング言語です",
            filename="python_guide.pdf",
            page_number=1,
            similarity_score=0.85,
            metadata=metadata
        )
        
        assert result.chunk_id == "chunk_123"
        assert result.content == "Pythonは汎用プログラミング言語です"
        assert result.filename == "python_guide.pdf"
        assert result.page_number == 1
        assert result.similarity_score == 0.85
        assert result.metadata == metadata
    
    def test_search_result_validation_invalid_score(self):
        """無効な類似度スコアのバリデーションテスト"""
        with pytest.raises(ValueError, match="similarity_score は0.0-1.0の範囲である必要があります"):
            SearchResult(
                chunk_id="chunk_123",
                content="テスト内容",
                filename="test.pdf",
                page_number=1,
                similarity_score=1.5,  # 無効な値
                metadata={}
            )
    
    def test_search_result_validation_invalid_page_number(self):
        """無効なページ番号のバリデーションテスト"""
        with pytest.raises(ValueError, match="page_number は正の整数である必要があります"):
            SearchResult(
                chunk_id="chunk_123",
                content="テスト内容",
                filename="test.pdf",
                page_number=0,  # 無効な値
                similarity_score=0.8,
                metadata={}
            )


class TestVectorSearch:
    """VectorSearchメインクラステスト"""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Supabaseクライアントのモック"""
        mock_client = Mock()
        return mock_client
    
    @pytest.fixture
    def mock_openai_embeddings(self):
        """OpenAI埋め込みのモック"""
        mock_embeddings = Mock()
        mock_embeddings.embed_query.return_value = [0.1] * 1536
        return mock_embeddings
    
    def test_vector_search_initialization(self, mock_supabase_client, mock_openai_embeddings):
        """VectorSearch初期化テスト"""
        search = VectorSearch(
            supabase_client=mock_supabase_client,
            embeddings=mock_openai_embeddings,
            table_name="document_chunks"
        )
        
        assert search.supabase_client == mock_supabase_client
        assert search.embeddings == mock_openai_embeddings
        assert search.table_name == "document_chunks"
    
    def test_search_similar_chunks_basic(self, mock_supabase_client, mock_openai_embeddings):
        """基本的な類似チャンク検索テスト"""

        # モックの設定
        mock_supabase_client.rpc.return_value.execute.return_value.data = [
            {
                "id": "chunk_1",
                "content": "Python機械学習の基礎",
                "filename": "ml_guide.pdf",
                "page_number": 1,
                "distance": 0.2,  # 類似度0.8相当
                "section_name": "第1章",
                "chapter_number": 1
            }
        ]
        
        search = VectorSearch(mock_supabase_client, mock_openai_embeddings)
        query = SearchQuery(
            text="機械学習について",
            limit=5,
            similarity_threshold=0.7
        )
        
        results = search.search_similar_chunks(query)
        
        assert len(results) == 1
        assert isinstance(results[0], SearchResult)
        assert results[0].chunk_id == "chunk_1"
        assert results[0].similarity_score == 0.8  # 1 - 0.2
    
    def test_search_similar_chunks_with_filters(self, mock_supabase_client, mock_openai_embeddings):
        """フィルタ付き類似チャンク検索テスト"""
        # モックの設定
        mock_supabase_client.rpc.return_value.execute.return_value.data = []
        
        search = VectorSearch(mock_supabase_client, mock_openai_embeddings)
        query = SearchQuery(
            text="Streamlit使い方",
            limit=5,
            similarity_threshold=0.7,
            filters={"filename": "streamlit_guide.pdf"}
        )
        
        results = search.search_similar_chunks(query)
        
        # RPC関数が呼ばれることを確認
        mock_supabase_client.rpc.assert_called_once()
        assert isinstance(results, list)
    
    def test_hybrid_search(self, mock_supabase_client, mock_openai_embeddings):
        """ハイブリッド検索テスト"""
        # モックの設定
        mock_supabase_client.rpc.return_value.execute.return_value.data = []
        
        search = VectorSearch(mock_supabase_client, mock_openai_embeddings)
        query = SearchQuery(
            text="Python データサイエンス",
            limit=10,
            similarity_threshold=0.6
        )
        
        results = search.hybrid_search(query)
        
        # ハイブリッド検索RPC関数が呼ばれることを確認
        assert mock_supabase_client.rpc.called
        assert isinstance(results, list)
    
    def test_search_by_filters_only(self, mock_supabase_client, mock_openai_embeddings):
        """フィルタのみでの検索テスト"""
        # モックの設定
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.limit.return_value.execute.return_value.data = []
        
        search = VectorSearch(mock_supabase_client, mock_openai_embeddings)
        filters = {
            "filename": "python_guide.pdf",
            "page_number": {"$gte": 1, "$lte": 10}
        }
        
        results = search.search_by_filters(filters, limit=20)
        
        # フィルタベース検索が実行されることを確認
        mock_supabase_client.table.assert_called_with("document_chunks")
        assert isinstance(results, list)
    
    def test_get_chunk_by_id(self, mock_supabase_client, mock_openai_embeddings):
        """ID指定チャンク取得テスト"""

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {
                "id": "chunk_123",
                "content": "指定されたチャンク内容",
                "filename": "test.pdf",
                "page_number": 5,
                "metadata": {}
            }
        ]
        
        search = VectorSearch(mock_supabase_client, mock_openai_embeddings)
        result = search.get_chunk_by_id("chunk_123")
        
        assert result is not None
        assert result.chunk_id == "chunk_123"
    
    def test_get_chunk_by_id_not_found(self, mock_supabase_client, mock_openai_embeddings):
        """存在しないIDでのチャンク取得テスト"""

        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        
        search = VectorSearch(mock_supabase_client, mock_openai_embeddings)
        result = search.get_chunk_by_id("nonexistent_id")
        
        assert result is None
    
    def test_calculate_similarity_score(self, mock_supabase_client, mock_openai_embeddings):
        """類似度スコア計算テスト"""

        search = VectorSearch(mock_supabase_client, mock_openai_embeddings)
        
        # pgvectorのコサイン距離から類似度スコアへの変換
        distance = 0.3
        expected_score = 1.0 - distance
        
        score = search.calculate_similarity_score(distance)
        assert score == expected_score
    
    def test_performance_requirement_under_500ms(self, mock_supabase_client, mock_openai_embeddings):
        """パフォーマンス要件(<500ms)テスト"""

        # 高速レスポンスをモック
        mock_supabase_client.rpc.return_value.execute.return_value.data = []
        
        search = VectorSearch(mock_supabase_client, mock_openai_embeddings)
        query = SearchQuery(
            text="パフォーマンステスト",
            limit=10,
            similarity_threshold=0.7
        )
        
        start_time = time.time()
        results = search.search_similar_chunks(query)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # ミリ秒
        assert response_time < 500  # 500ms未満
    
    def test_error_handling_invalid_embedding(self, mock_supabase_client, mock_openai_embeddings):
        """無効な埋め込みベクトルのエラーハンドリングテスト"""

        # 埋め込み生成エラーをモック
        mock_openai_embeddings.embed_query.side_effect = Exception("API Error")
        
        search = VectorSearch(mock_supabase_client, mock_openai_embeddings)
        query = SearchQuery(
            text="エラーテスト",
            limit=5,
            similarity_threshold=0.7
        )
        
        with pytest.raises(VectorSearchError, match="埋め込みベクトル生成エラー"):
            search.search_similar_chunks(query)
    
    def test_error_handling_database_error(self, mock_supabase_client, mock_openai_embeddings):
        """データベースエラーのハンドリングテスト"""

        # データベースエラーをモック
        mock_supabase_client.rpc.side_effect = Exception("Database connection error")
        
        search = VectorSearch(mock_supabase_client, mock_openai_embeddings)
        query = SearchQuery(
            text="データベースエラーテスト",
            limit=5,
            similarity_threshold=0.7
        )
        
        with pytest.raises(VectorSearchError, match="データベース検索エラー"):
            search.search_similar_chunks(query)
    
    def test_input_validation_security(self, mock_supabase_client, mock_openai_embeddings):
        """入力検証・セキュリティテスト"""
        search = VectorSearch(mock_supabase_client, mock_openai_embeddings)
        
        # SQLインジェクション攻撃を含むクエリ - SearchQueryの初期化時にエラーが発生する
        with pytest.raises(ValueError, match="セキュリティ違反"):
            SearchQuery(
                text="'; DROP TABLE documents; --",
                limit=5,
                similarity_threshold=0.7
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])