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
import logging
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

# 実装モジュールのインポート
from services.vector_similarity_search import (
    SearchQuery,
    SearchResult, 
    VectorSearch,
    VectorSearchError,
    DatabaseConnectionError,
    EmbeddingGenerationError,
    QueryValidationError,
    PerformanceError,
    SecurityError,
    ErrorSeverity,
    StructuredLogger,
    retry_with_exponential_backoff
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
        
        with pytest.raises(EmbeddingGenerationError, match="埋め込み生成中にエラーが発生しました"):
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
        
        with pytest.raises(DatabaseConnectionError, match="データベース接続エラーが発生しました"):
            search.search_similar_chunks(query)
    
    def test_input_validation_security(self, mock_supabase_client, mock_openai_embeddings):
        """入力検証・セキュリティテスト"""
        search = VectorSearch(mock_supabase_client, mock_openai_embeddings)
        
        # SQLインジェクション攻撃を含むクエリ - SearchQueryの初期化時にエラーが発生する
        with pytest.raises(SecurityError, match="危険なコンテンツが検出されました"):
            SearchQuery(
                text="'; DROP TABLE documents; --",
                limit=5,
                similarity_threshold=0.7
            )


class TestErrorHandling:
    """エラーハンドリングテスト群"""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Supabaseクライアントのモック"""
        return Mock()
    
    @pytest.fixture
    def mock_openai_embeddings(self):
        """OpenAI埋め込みのモック"""
        mock_embeddings = Mock()
        mock_embeddings.embed_query.return_value = [0.1] * 1536
        return mock_embeddings
    
    def test_custom_error_classes_creation(self):
        """カスタムエラークラス作成テスト"""
        
        # DatabaseConnectionError
        db_error = DatabaseConnectionError(
            "接続タイムアウト",
            context={"host": "localhost", "port": 5432}
        )
        assert db_error.error_code == "DB_CONNECTION_ERROR"
        assert db_error.severity == ErrorSeverity.HIGH
        assert "接続タイムアウト" in str(db_error)
        
        # EmbeddingGenerationError
        embed_error = EmbeddingGenerationError(
            "API制限",
            context={"api_key": "masked"}
        )
        assert embed_error.error_code == "EMBEDDING_ERROR"
        assert embed_error.severity == ErrorSeverity.MEDIUM
        
        # SecurityError
        security_error = SecurityError(
            "SQLインジェクション検出",
            context={"query": "'; DROP TABLE"}
        )
        assert security_error.error_code == "SECURITY_ERROR"
        assert security_error.severity == ErrorSeverity.CRITICAL
    
    def test_vector_search_initialization_error_handling(self):
        """VectorSearch初期化エラーハンドリングテスト"""
        
        # Supabaseクライアントなし
        with pytest.raises(DatabaseConnectionError, match="Supabaseクライアントが設定されていません"):
            VectorSearch(
                supabase_client=None,
                embeddings=Mock(),
                table_name="test_table"
            )
        
        # 埋め込みモデルなし
        with pytest.raises(EmbeddingGenerationError, match="埋め込みモデルが設定されていません"):
            VectorSearch(
                supabase_client=Mock(),
                embeddings=None,
                table_name="test_table"
            )
    
    def test_security_validation_sql_injection(self, mock_supabase_client, mock_openai_embeddings):
        """SQLインジェクション検証テスト"""
        search = VectorSearch(mock_supabase_client, mock_openai_embeddings)
        
        # SQLインジェクション攻撃パターン
        malicious_queries = [
            "'; DROP TABLE documents; --",
            "UNION SELECT * FROM users",
            "DELETE FROM documents WHERE id=1",
            "INSERT INTO documents VALUES ('malicious')"
        ]
        
        for malicious_query in malicious_queries:
            with pytest.raises(SecurityError, match="危険なコンテンツが検出されました"):
                search._validate_search_query(SearchQuery(
                    text=malicious_query,
                    limit=5,
                    similarity_threshold=0.7
                ))
    
    def test_security_validation_xss_attempts(self, mock_supabase_client, mock_openai_embeddings):
        """XSS攻撃検証テスト"""
        
        # XSS攻撃パターン
        xss_queries = [
            "<script>alert('xss')</script>",
            "javascript:alert(1)",
            "vbscript:msgbox('xss')"
        ]
        
        for xss_query in xss_queries:
            with pytest.raises(SecurityError, match="危険なコンテンツが検出されました"):
                SearchQuery(
                    text=xss_query,
                    limit=5,
                    similarity_threshold=0.7
                )
    
    def test_query_validation_length_limit(self, mock_supabase_client, mock_openai_embeddings):
        """クエリ長制限テスト"""
        search = VectorSearch(mock_supabase_client, mock_openai_embeddings)
        
        # 10KB超過するクエリ
        long_query = "a" * 10001
        
        with pytest.raises(QueryValidationError, match="クエリテキストが長すぎます"):
            search._validate_search_query(SearchQuery(
                text=long_query,
                limit=5,
                similarity_threshold=0.7
            ))
    
    def test_embedding_generation_api_rate_limit_error(self, mock_supabase_client, mock_openai_embeddings):
        """埋め込み生成API制限エラーテスト"""
        mock_openai_embeddings.embed_query.side_effect = Exception("Rate limit exceeded")
        
        search = VectorSearch(mock_supabase_client, mock_openai_embeddings)
        
        with pytest.raises(EmbeddingGenerationError, match="API利用制限に達しました"):
            search._generate_embedding("テストクエリ")
    
    def test_embedding_generation_connection_error(self, mock_supabase_client, mock_openai_embeddings):
        """埋め込み生成接続エラーテスト"""
        mock_openai_embeddings.embed_query.side_effect = Exception("Connection timeout")
        
        search = VectorSearch(mock_supabase_client, mock_openai_embeddings)
        
        with pytest.raises(EmbeddingGenerationError, match="API接続エラーが発生しました"):
            search._generate_embedding("テストクエリ")
    
    def test_embedding_generation_empty_result(self, mock_supabase_client, mock_openai_embeddings):
        """空の埋め込み結果エラーテスト"""
        mock_openai_embeddings.embed_query.return_value = []
        
        search = VectorSearch(mock_supabase_client, mock_openai_embeddings)
        
        with pytest.raises(EmbeddingGenerationError, match="空の埋め込みベクトルが返されました"):
            search._generate_embedding("テストクエリ")
    
    def test_database_connection_error_handling(self, mock_supabase_client, mock_openai_embeddings):
        """データベース接続エラーハンドリングテスト"""
        mock_supabase_client.rpc.side_effect = Exception("Connection failed")
        
        search = VectorSearch(mock_supabase_client, mock_openai_embeddings)
        query = SearchQuery(
            text="テストクエリ",
            limit=5,
            similarity_threshold=0.7
        )
        
        with pytest.raises(DatabaseConnectionError, match="データベース接続エラーが発生しました"):
            search._execute_vector_search(query, [0.1] * 1536)
    
    def test_database_authentication_error(self, mock_supabase_client, mock_openai_embeddings):
        """データベース認証エラーテスト"""
        mock_supabase_client.rpc.side_effect = Exception("Authentication failed")
        
        search = VectorSearch(mock_supabase_client, mock_openai_embeddings)
        query = SearchQuery(
            text="テストクエリ",
            limit=5,
            similarity_threshold=0.7
        )
        
        with pytest.raises(DatabaseConnectionError, match="データベース認証エラーが発生しました"):
            search._execute_vector_search(query, [0.1] * 1536)


class TestRetryMechanism:
    """リトライ機構テスト群"""
    
    def test_retry_decorator_success_on_first_attempt(self):
        """初回成功時のリトライテスト"""
        call_count = 0
        
        @retry_with_exponential_backoff(max_retries=3)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_function()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_decorator_success_after_retries(self):
        """リトライ後成功テスト"""
        call_count = 0
        
        @retry_with_exponential_backoff(max_retries=3, base_delay=0.01)
        def retry_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"
        
        result = retry_then_success()
        assert result == "success"
        assert call_count == 3
    
    def test_retry_decorator_max_retries_exceeded(self):
        """最大リトライ回数超過テスト"""
        call_count = 0
        
        @retry_with_exponential_backoff(max_retries=2, base_delay=0.01)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Persistent failure")
        
        with pytest.raises(ConnectionError, match="Persistent failure"):
            always_fails()
        
        assert call_count == 3  # 初回 + 2回リトライ
    
    def test_retry_exponential_backoff_timing(self):
        """指数バックオフタイミングテスト"""
        call_times = []
        
        @retry_with_exponential_backoff(max_retries=2, base_delay=0.1, max_delay=1.0)
        def timed_failure():
            call_times.append(time.time())
            raise ConnectionError("Test failure")
        
        start_time = time.time()
        
        with pytest.raises(ConnectionError):
            timed_failure()
        
        # タイミング検証（大まかな確認）
        assert len(call_times) == 3  # 初回 + 2回リトライ
        
        # 1回目と2回目の間隔（約0.1秒）
        delay1 = call_times[1] - call_times[0]
        assert 0.08 <= delay1 <= 0.15
        
        # 2回目と3回目の間隔（約0.2秒）
        delay2 = call_times[2] - call_times[1]
        assert 0.18 <= delay2 <= 0.25


class TestStructuredLogging:
    """構造化ログテスト群"""
    
    @pytest.fixture
    def mock_logger(self):
        """ログのモック"""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger_instance = Mock()
            mock_get_logger.return_value = mock_logger_instance
            yield mock_logger_instance
    
    def test_structured_logger_search_start(self, mock_logger):
        """検索開始ログテスト"""
        structured_logger = StructuredLogger("test_logger")
        
        structured_logger.log_search_start(
            query="機械学習について",
            limit=10,
            threshold=0.8
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        
        assert "ベクトル検索開始" in call_args[0][0]
        assert call_args[1]["extra"]["event"] == "search_start"
        assert call_args[1]["extra"]["query_length"] == len("機械学習について")
        assert call_args[1]["extra"]["limit"] == 10
        assert call_args[1]["extra"]["threshold"] == 0.8
    
    def test_structured_logger_search_success(self, mock_logger):
        """検索成功ログテスト"""
        structured_logger = StructuredLogger("test_logger")
        
        structured_logger.log_search_success(
            results_count=5,
            response_time_ms=150.5,
            query="テストクエリ"
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        
        assert "5件取得" in call_args[0][0]
        assert call_args[1]["extra"]["event"] == "search_success"
        assert call_args[1]["extra"]["results_count"] == 5
        assert call_args[1]["extra"]["response_time_ms"] == 150.5
    
    def test_structured_logger_error_logging(self, mock_logger):
        """エラーログテスト"""
        structured_logger = StructuredLogger("test_logger")
        
        error = DatabaseConnectionError(
            "接続失敗",
            context={"host": "localhost"}
        )
        
        structured_logger.log_error(error)
        
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        
        # ログレベルがERRORであることを確認
        assert call_args[0][0] == logging.ERROR
        assert "エラー発生" in call_args[0][1]
        assert call_args[1]["extra"]["error_code"] == "DB_CONNECTION_ERROR"
        assert call_args[1]["extra"]["severity"] == "high"
    
    def test_structured_logger_performance_warning(self, mock_logger):
        """パフォーマンス警告ログテスト"""
        structured_logger = StructuredLogger("test_logger")
        
        # 閾値超過の場合
        structured_logger.log_performance_warning(
            operation="search_similar_chunks",
            response_time_ms=750.0,
            threshold_ms=500.0
        )
        
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        
        assert "パフォーマンス警告" in call_args[0][0]
        assert "750.00ms" in call_args[0][0]
        assert call_args[1]["extra"]["event"] == "performance_warning"
        
        # 閾値以下の場合は警告なし
        mock_logger.reset_mock()
        structured_logger.log_performance_warning(
            operation="fast_search",
            response_time_ms=300.0,
            threshold_ms=500.0
        )
        
        mock_logger.warning.assert_not_called()


class TestIntegratedErrorHandling:
    """統合エラーハンドリングテスト"""
    
    @pytest.fixture
    def mock_supabase_client(self):
        """Supabaseクライアントのモック"""
        return Mock()
    
    @pytest.fixture
    def mock_openai_embeddings(self):
        """OpenAI埋め込みのモック"""
        mock_embeddings = Mock()
        mock_embeddings.embed_query.return_value = [0.1] * 1536
        return mock_embeddings
    
    def test_full_search_flow_with_retry_success(self, mock_supabase_client, mock_openai_embeddings):
        """リトライありの完全検索フローテスト（成功ケース）"""
        
        # 初回失敗、2回目成功をモック
        call_count = 0
        def mock_rpc_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Temporary database error")
            return Mock(execute=Mock(return_value=Mock(data=[
                {
                    "id": "chunk_1",
                    "content": "テスト内容",
                    "filename": "test.pdf",
                    "page_number": 1,
                    "distance": 0.3
                }
            ])))
        
        mock_supabase_client.rpc.side_effect = mock_rpc_side_effect
        
        # リトライ有効で検索実行
        search = VectorSearch(
            mock_supabase_client,
            mock_openai_embeddings,
            enable_retry=True,
            max_retries=2
        )
        
        query = SearchQuery(
            text="テストクエリ",
            limit=5,
            similarity_threshold=0.7
        )
        
        # 短い遅延でテスト実行
        with patch('time.sleep'):
            results = search.search_similar_chunks(query)
        
        assert len(results) == 1
        assert results[0].chunk_id == "chunk_1"
        assert call_count == 2  # 初回失敗 + 1回リトライで成功
    
    def test_full_search_flow_max_retries_exceeded(self, mock_supabase_client, mock_openai_embeddings):
        """最大リトライ回数超過の完全検索フローテスト"""
        
        # 常に失敗するモック
        mock_supabase_client.rpc.side_effect = Exception("Persistent database error")
        
        search = VectorSearch(
            mock_supabase_client,
            mock_openai_embeddings,
            enable_retry=True,
            max_retries=2
        )
        
        query = SearchQuery(
            text="テストクエリ",
            limit=5,
            similarity_threshold=0.7
        )
        
        # 短い遅延でテスト実行
        with patch('time.sleep'):
            with pytest.raises(DatabaseConnectionError, match="データベース検索中にエラーが発生しました"):
                search.search_similar_chunks(query)
    
    def test_performance_monitoring_and_warning(self, mock_supabase_client, mock_openai_embeddings):
        """パフォーマンス監視・警告テスト"""
        
        # 遅いレスポンスをシミュレート
        def slow_rpc(*args, **kwargs):
            time.sleep(0.1)  # 100ms遅延
            return Mock(execute=Mock(return_value=Mock(data=[])))
        
        mock_supabase_client.rpc.side_effect = slow_rpc
        
        search = VectorSearch(
            mock_supabase_client,
            mock_openai_embeddings,
            performance_threshold_ms=50.0  # 50ms閾値
        )
        
        query = SearchQuery(
            text="パフォーマンステスト",
            limit=5,
            similarity_threshold=0.7
        )
        
        with patch.object(search.structured_logger, 'log_performance_warning') as mock_warning:
            results = search.search_similar_chunks(query)
            
            # パフォーマンス警告が呼ばれることを確認
            mock_warning.assert_called_once()
            call_args = mock_warning.call_args[0]
            assert call_args[0] == "search_similar_chunks"
            assert call_args[1] > 50.0  # 閾値超過
    
    def test_comprehensive_error_context_preservation(self, mock_supabase_client, mock_openai_embeddings):
        """包括的エラーコンテキスト保持テスト"""
        
        # エラーでコンテキスト情報をテスト
        mock_openai_embeddings.embed_query.side_effect = Exception("API quota exceeded")
        
        search = VectorSearch(mock_supabase_client, mock_openai_embeddings)
        query = SearchQuery(
            text="コンテキストテスト",
            limit=5,
            similarity_threshold=0.7
        )
        
        try:
            search.search_similar_chunks(query)
        except EmbeddingGenerationError as e:
            # エラー情報確認
            assert e.error_code == "EMBEDDING_ERROR"
            assert e.severity == ErrorSeverity.MEDIUM
            assert "API利用制限に達しました" in str(e)
            assert "original_error" in e.context
        else:
            pytest.fail("EmbeddingGenerationErrorが発生するべきです")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])