"""
OpenAI Embeddings Service テスト
Issue #54: OpenAI text-embedding-3-small完全実装テスト

TDD Red Phase: 失敗テストケース作成
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from typing import List, Dict, Any
import time

from services.embeddings import (
    EmbeddingService, 
    EmbeddingResult, 
    BatchEmbeddingResult,
    EmbeddingError
)


class TestEmbeddingService:
    """EmbeddingService テストクラス"""
    
    def test_init_with_valid_api_key(self):
        """正常: 有効なAPIキーでの初期化"""
        service = EmbeddingService("sk-test123456789")
        assert service.api_key == "sk-test123456789"
        assert service.model == "text-embedding-3-small"
        
    def test_init_with_custom_model(self):
        """正常: カスタムモデル指定での初期化"""
        custom_model = "text-embedding-ada-002"
        service = EmbeddingService("sk-test123456789", model=custom_model)
        assert service.model == custom_model
    
    def test_init_requires_api_key(self):
        """異常: APIキー未指定での初期化失敗"""
        with pytest.raises(TypeError):
            EmbeddingService()  # api_key必須パラメータ
    
    def test_init_with_empty_api_key(self):
        """異常: 空APIキーでの初期化失敗"""
        with pytest.raises(ValueError, match="APIキーが空です"):
            EmbeddingService("")
    
    def test_init_with_invalid_api_key_format(self):
        """異常: 不正形式APIキーでの初期化失敗"""
        with pytest.raises(ValueError, match="APIキー形式が不正です"):
            EmbeddingService("invalid-key-format")


class TestOpenAIClientInitialization:
    """OpenAIクライアント初期化テスト"""
    
    @patch('openai.OpenAI')
    def test_openai_client_initialization(self, mock_openai):
        """正常: OpenAIクライアント正常初期化"""
        service = EmbeddingService("sk-test123456789")
        mock_openai.assert_called_once_with(api_key="sk-test123456789", timeout=None)
    
    @patch('openai.OpenAI')
    def test_openai_client_initialization_with_timeout(self, mock_openai):
        """正常: タイムアウト設定付きクライアント初期化"""
        service = EmbeddingService("sk-test123456789", timeout=30)
        mock_openai.assert_called_once_with(
            api_key="sk-test123456789",
            timeout=30
        )
    
    @patch('openai.OpenAI', side_effect=Exception("OpenAI初期化エラー"))
    def test_openai_client_initialization_failure(self, mock_openai):
        """異常: OpenAIクライアント初期化失敗"""
        with pytest.raises(EmbeddingError, match="OpenAIクライアント初期化に失敗しました"):
            EmbeddingService("sk-test123456789")


class TestEmbeddingGeneration:
    """埋め込み生成テスト"""
    
    @pytest.fixture
    def service(self):
        """テスト用EmbeddingServiceインスタンス"""
        with patch('openai.OpenAI'):
            return EmbeddingService("sk-test123456789")
    
    @patch('openai.OpenAI')
    def test_generate_embedding_success_english(self, mock_openai):
        """正常: 英語テキスト埋め込み生成成功"""
        # OpenAI API レスポンスモック
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_response.usage.total_tokens = 10
        
        mock_client = mock_openai.return_value
        mock_client.embeddings.create.return_value = mock_response
        
        service = EmbeddingService("sk-test123456789")
        result = service.generate_embedding("Hello world")
        
        assert isinstance(result, EmbeddingResult)
        assert len(result.embedding) == 1536
        assert result.token_count == 10
        assert result.model == "text-embedding-3-small"
        
        # API呼び出し確認
        mock_client.embeddings.create.assert_called_once_with(
            input="Hello world",
            model="text-embedding-3-small"
        )
    
    @patch('openai.OpenAI')
    def test_generate_embedding_success_japanese(self, mock_openai):
        """正常: 日本語テキスト埋め込み生成成功"""
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.2] * 1536)]
        mock_response.usage.total_tokens = 15
        
        mock_client = mock_openai.return_value
        mock_client.embeddings.create.return_value = mock_response
        
        service = EmbeddingService("sk-test123456789")
        result = service.generate_embedding("こんにちは世界")
        
        assert isinstance(result, EmbeddingResult)
        assert len(result.embedding) == 1536
        assert result.token_count == 15
        assert result.model == "text-embedding-3-small"
    
    def test_generate_embedding_empty_text(self, service):
        """異常: 空テキストでの埋め込み生成失敗"""
        with pytest.raises(ValueError, match="テキストが空です"):
            service.generate_embedding("")
    
    def test_generate_embedding_none_text(self, service):
        """異常: Noneテキストでの埋め込み生成失敗"""
        with pytest.raises(ValueError, match="テキストがNoneです"):
            service.generate_embedding(None)
    
    def test_generate_embedding_too_long_text(self, service):
        """異常: 長すぎるテキストでの埋め込み生成失敗"""
        # tiktokenエンコーダーでトークン数が8192を超えるテキストを作成  
        # 各文章は約4トークン、8192 / 4 = 2048文章 + α で制限超過
        long_text = "This is a test sentence for token counting. " * 3000  # 十分に長いテキスト
        with pytest.raises(ValueError, match="テキストが長すぎます"):
            service.generate_embedding(long_text)
    
    @patch('openai.OpenAI')
    def test_generate_embedding_api_error(self, mock_openai):
        """異常: OpenAI API エラー"""
        mock_client = mock_openai.return_value
        mock_client.embeddings.create.side_effect = Exception("API Error")
        
        service = EmbeddingService("sk-test123456789")
        
        with pytest.raises(EmbeddingError, match="埋め込み生成中にエラーが発生しました"):
            service.generate_embedding("test text")
    
    @patch('openai.OpenAI')
    def test_generate_embedding_authentication_error(self, mock_openai):
        """異常: 認証エラー"""
        mock_client = mock_openai.return_value
        
        # AuthenticationErrorのモック作成
        class MockAuthError(Exception):
            def __init__(self, message):
                super().__init__(message)
                self.__class__.__name__ = "AuthenticationError"
        
        mock_client.embeddings.create.side_effect = MockAuthError("Invalid API key")
        
        service = EmbeddingService("sk-invalid-key")
        
        with pytest.raises(EmbeddingError, match="認証に失敗しました"):
            service.generate_embedding("test text")
    
    @patch('openai.OpenAI')
    def test_generate_embedding_rate_limit_error(self, mock_openai):
        """異常: レート制限エラー"""
        mock_client = mock_openai.return_value
        
        # RateLimitErrorのモック作成
        class MockRateLimitError(Exception):
            def __init__(self, message):
                super().__init__(message)
                self.__class__.__name__ = "RateLimitError"
        
        mock_client.embeddings.create.side_effect = MockRateLimitError("Rate limit exceeded")
        
        service = EmbeddingService("sk-test123456789")
        
        with pytest.raises(EmbeddingError, match="レート制限に達しました"):
            service.generate_embedding("test text")
    
    @patch('openai.OpenAI')
    def test_generate_embedding_timeout_error(self, mock_openai):
        """異常: タイムアウトエラー"""
        mock_client = mock_openai.return_value
        
        # Timeoutエラーのモック作成
        class MockTimeoutError(Exception):
            def __init__(self, message):
                super().__init__(message)
                self.__class__.__name__ = "Timeout"
        
        mock_client.embeddings.create.side_effect = MockTimeoutError("Request timeout")
        
        service = EmbeddingService("sk-test123456789")
        
        with pytest.raises(EmbeddingError, match="リクエストがタイムアウトしました"):
            service.generate_embedding("test text")


class TestAsyncEmbeddingGeneration:
    """非同期埋め込み生成テスト"""
    
    @pytest.fixture
    def async_service(self):
        """非同期テスト用EmbeddingServiceインスタンス"""
        with patch('openai.AsyncOpenAI'):
            return EmbeddingService("sk-test123456789", async_mode=True)
    
    @patch('openai.AsyncOpenAI')
    @pytest.mark.asyncio
    async def test_async_generate_embedding_success(self, mock_async_openai):
        """正常: 非同期埋め込み生成成功"""
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_response.usage.total_tokens = 10
        
        mock_client = mock_async_openai.return_value
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        
        service = EmbeddingService("sk-test123456789", async_mode=True)
        result = await service.generate_embedding_async("Hello world")
        
        assert isinstance(result, EmbeddingResult)
        assert len(result.embedding) == 1536
        assert result.token_count == 10
    
    @patch('openai.AsyncOpenAI')
    @pytest.mark.asyncio
    async def test_async_generate_embedding_concurrent(self, mock_async_openai):
        """正常: 並列非同期埋め込み生成"""
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_response.usage.total_tokens = 10
        
        mock_client = mock_async_openai.return_value
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        
        service = EmbeddingService("sk-test123456789", async_mode=True)
        
        texts = ["text1", "text2", "text3"]
        tasks = [service.generate_embedding_async(text) for text in texts]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        for result in results:
            assert isinstance(result, EmbeddingResult)
            assert len(result.embedding) == 1536


class TestTokenEstimation:
    """トークン推定テスト"""
    
    @pytest.fixture
    def service(self):
        """テスト用EmbeddingServiceインスタンス"""
        with patch('openai.OpenAI'):
            return EmbeddingService("sk-test123456789")
    
    def test_estimate_tokens_english(self, service):
        """正常: 英語テキストトークン推定"""
        text = "Hello world"
        tokens = service.estimate_tokens(text)
        assert isinstance(tokens, int)
        assert tokens > 0
        assert tokens < len(text)  # トークン数は文字数より少ない
    
    def test_estimate_tokens_japanese(self, service):
        """正常: 日本語テキストトークン推定"""
        text = "こんにちは世界"
        tokens = service.estimate_tokens(text)
        assert isinstance(tokens, int)
        assert tokens > 0
    
    def test_estimate_tokens_empty_text(self, service):
        """異常: 空テキストトークン推定"""
        with pytest.raises(ValueError, match="テキストが空です"):
            service.estimate_tokens("")
    
    def test_estimate_tokens_mixed_language(self, service):
        """正常: 混合言語テキストトークン推定"""
        text = "Hello こんにちは world 世界"
        tokens = service.estimate_tokens(text)
        assert isinstance(tokens, int)
        assert tokens > 0


class TestPerformanceMonitoring:
    """パフォーマンス監視テスト"""
    
    @pytest.fixture
    def service(self):
        """テスト用EmbeddingServiceインスタンス"""
        with patch('openai.OpenAI'):
            return EmbeddingService("sk-test123456789")
    
    @patch('openai.OpenAI')
    def test_response_time_monitoring(self, mock_openai):
        """正常: レスポンス時間監視"""
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_response.usage.total_tokens = 10
        
        mock_client = mock_openai.return_value
        mock_client.embeddings.create.return_value = mock_response
        
        service = EmbeddingService("sk-test123456789")
        
        start_time = time.time()
        result = service.generate_embedding("test text")
        end_time = time.time()
        
        response_time = end_time - start_time
        assert response_time < 5.0  # Issue要件: 5秒以下
        assert hasattr(result, 'response_time')
    
    @patch('openai.OpenAI')
    def test_performance_under_5_seconds(self, mock_openai):
        """正常: 5秒以下のパフォーマンス要件確認"""
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_response.usage.total_tokens = 10
        
        mock_client = mock_openai.return_value
        
        # 模擬遅延追加（4秒）
        def slow_create(*args, **kwargs):
            time.sleep(0.1)  # テスト用短縮遅延
            return mock_response
        
        mock_client.embeddings.create.side_effect = slow_create
        
        service = EmbeddingService("sk-test123456789")
        
        start_time = time.time()
        result = service.generate_embedding("test text")
        end_time = time.time()
        
        response_time = end_time - start_time
        assert response_time < 5.0  # Issue要件確認
    
    @patch('openai.OpenAI')
    def test_timeout_configuration(self, mock_openai):
        """正常: タイムアウト設定可能"""
        service = EmbeddingService("sk-test123456789", timeout=10)
        mock_openai.assert_called_once_with(
            api_key="sk-test123456789",
            timeout=10
        )


class TestBatchEmbeddingGeneration:
    """バッチ埋め込み生成テスト（将来機能）"""
    
    @pytest.fixture
    def service(self):
        """テスト用EmbeddingServiceインスタンス"""
        with patch('openai.OpenAI'):
            return EmbeddingService("sk-test123456789")
    
    @patch('openai.OpenAI')
    def test_batch_generate_embeddings_success(self, mock_openai):
        """正常: バッチ埋め込み生成成功"""
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1] * 1536),
            Mock(embedding=[0.2] * 1536),
            Mock(embedding=[0.3] * 1536)
        ]
        mock_response.usage.total_tokens = 30
        
        mock_client = mock_openai.return_value
        mock_client.embeddings.create.return_value = mock_response
        
        service = EmbeddingService("sk-test123456789")
        texts = ["text1", "text2", "text3"]
        result = service.generate_batch_embeddings(texts)
        
        assert isinstance(result, BatchEmbeddingResult)
        assert len(result.embeddings) == 3
        assert result.total_tokens == 30
        
        mock_client.embeddings.create.assert_called_once_with(
            input=texts,
            model="text-embedding-3-small"
        )
    
    def test_batch_generate_embeddings_empty_list(self, service):
        """異常: 空リストでのバッチ埋め込み生成失敗"""
        with pytest.raises(ValueError, match="テキストリストが空です"):
            service.generate_batch_embeddings([])
    
    def test_batch_generate_embeddings_too_many_texts(self, service):
        """異常: 大量テキストでのバッチ埋め込み生成失敗"""
        texts = ["text"] * 2049  # OpenAI制限超過
        with pytest.raises(ValueError, match="バッチサイズが制限を超えています"):
            service.generate_batch_embeddings(texts)


class TestValidationAndUtilities:
    """検証・ユーティリティ機能テスト"""
    
    @pytest.fixture
    def service(self):
        """テスト用EmbeddingServiceインスタンス"""
        with patch('openai.OpenAI'):
            return EmbeddingService("sk-test123456789")
    
    def test_validate_embedding_dimension_correct(self, service):
        """正常: 正しい次元数埋め込み検証"""
        embedding = [0.1] * 1536
        assert service.validate_embedding_dimension(embedding) is True
    
    def test_validate_embedding_dimension_incorrect(self, service):
        """異常: 間違った次元数埋め込み検証"""
        embedding = [0.1] * 512  # 間違った次元数
        assert service.validate_embedding_dimension(embedding) is False
    
    def test_validate_embedding_dimension_empty(self, service):
        """異常: 空埋め込み検証"""
        embedding = []
        assert service.validate_embedding_dimension(embedding) is False
    
    def test_get_model_info(self, service):
        """正常: モデル情報取得"""
        info = service.get_model_info()
        assert info["model"] == "text-embedding-3-small"
        assert info["dimension"] == 1536
        assert info["max_tokens"] == 8192
    
    def test_calculate_embedding_cost(self, service):
        """正常: 埋め込みコスト計算"""
        tokens = 1000
        cost = service.calculate_embedding_cost(tokens)
        assert isinstance(cost, float)
        assert cost > 0
    
    def test_calculate_embedding_cost_zero_tokens(self, service):
        """正常: ゼロトークンコスト計算"""
        cost = service.calculate_embedding_cost(0)
        assert cost == 0.0


class TestErrorScenarios:
    """エラーシナリオテスト"""
    
    def test_network_connection_error(self):
        """異常: ネットワーク接続エラー"""
        with patch('openai.OpenAI') as mock_openai:
            mock_client = mock_openai.return_value
            connection_error = Exception("Connection failed")
            mock_client.embeddings.create.side_effect = connection_error
            
            service = EmbeddingService("sk-test123456789")
            
            with pytest.raises(EmbeddingError, match="ネットワーク接続エラーが発生しました"):
                service.generate_embedding("test text")
    
    def test_server_internal_error(self):
        """異常: サーバー内部エラー"""
        with patch('openai.OpenAI') as mock_openai:
            mock_client = mock_openai.return_value
            
            class MockInternalServerError(Exception):
                def __init__(self, message):
                    super().__init__(message)
                    self.__class__.__name__ = "InternalServerError"
            
            mock_client.embeddings.create.side_effect = MockInternalServerError("Internal server error")
            
            service = EmbeddingService("sk-test123456789")
            
            with pytest.raises(EmbeddingError, match="サーバーエラーが発生しました"):
                service.generate_embedding("test text")
    
    def test_quota_exceeded_error(self):
        """異常: クォータ超過エラー"""
        with patch('openai.OpenAI') as mock_openai:
            mock_client = mock_openai.return_value
            
            class MockQuotaError(Exception):
                def __init__(self, message):
                    super().__init__(message)
                    self.__class__.__name__ = "RateLimitError"
            
            mock_client.embeddings.create.side_effect = MockQuotaError("Quota exceeded")
            
            service = EmbeddingService("sk-test123456789")
            
            with pytest.raises(EmbeddingError, match="APIクォータを超過しました"):
                service.generate_embedding("test text")


class TestSupabaseIntegration:
    """Supabase統合テスト（Issue #48追加機能）"""
    
    @pytest.fixture
    def service(self):
        """テスト用EmbeddingServiceインスタンス"""
        with patch('openai.OpenAI'):
            return EmbeddingService("sk-test123456789")
    
    @patch('openai.OpenAI')
    def test_store_embeddings_to_supabase(self, mock_openai):
        """正常: Supabaseへの埋め込み保存"""
        # OpenAI APIレスポンスモック
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_response.usage.total_tokens = 10
        
        mock_client = mock_openai.return_value
        mock_client.embeddings.create.return_value = mock_response
        
        
        service = EmbeddingService("sk-test123456789")
        
        # Supabase保存機能をテスト
        with patch('services.embeddings.VectorStore') as mock_vector_store:
            mock_store_instance = mock_vector_store.return_value
            mock_store_instance.store_document.return_value = "test-doc-123"
            mock_store_instance.store_chunks.return_value = ["chunk_uuid_1"]
            
            result = service.store_embeddings_to_supabase(
                texts=["テストテキスト"],
                supabase_url="https://test.supabase.co",
                supabase_key="test-key",
                document_id="test-doc-123"
            )
            
            # 結果確認
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0] == "chunk_uuid_1"
            
            # VectorStoreの呼び出し確認
            mock_vector_store.assert_called_once_with("https://test.supabase.co", "test-key")
            mock_store_instance.store_chunks.assert_called_once()
    
    @patch('openai.OpenAI')
    def test_batch_store_embeddings_to_supabase(self, mock_openai):
        """正常: バッチでSupabaseへの埋め込み保存"""
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1] * 1536),
            Mock(embedding=[0.2] * 1536)
        ]
        mock_response.usage.total_tokens = 20
        
        mock_client = mock_openai.return_value
        mock_client.embeddings.create.return_value = mock_response
        
        
        service = EmbeddingService("sk-test123456789")
        
        # バッチSupabase保存機能をテスト
        with patch('services.embeddings.VectorStore') as mock_vector_store:
            mock_store_instance = mock_vector_store.return_value
            mock_store_instance.store_document.return_value = "test-doc-123"
            mock_store_instance.store_chunks.return_value = ["chunk_uuid_1", "chunk_uuid_2"]
            
            result = service.batch_store_embeddings_to_supabase(
                texts=["テキスト1", "テキスト2"],
                supabase_url="https://test.supabase.co",
                supabase_key="test-key",
                document_id="test-doc-123"
            )
            
            # 結果確認
            assert isinstance(result, list)
            assert len(result) == 2
            assert result[0] == "chunk_uuid_1"
            assert result[1] == "chunk_uuid_2"
            
            # VectorStoreの呼び出し確認
            mock_vector_store.assert_called_once_with("https://test.supabase.co", "test-key")
            mock_store_instance.store_chunks.assert_called_once()
    
    def test_supabase_store_with_invalid_params(self, service):
        """異常: 無効なSupabaseパラメータ"""
        with pytest.raises(ValueError, match="テキストリストが空です"):
            service.store_embeddings_to_supabase(
                texts=[],  # 空リスト
                supabase_url="https://test.supabase.co",
                supabase_key="test-key",
                document_id="test-doc-123"
            )
        
        with pytest.raises(ValueError, match="Supabaseパラメータが不正です"):
            service.store_embeddings_to_supabase(
                texts=["テストテキスト"],
                supabase_url="",  # 空URL
                supabase_key="test-key",
                document_id="test-doc-123"
            )


class TestLoggingAndMonitoring:
    """ログ・監視テスト"""
    
    @patch('openai.OpenAI')
    def test_logging_enabled(self, mock_openai):
        """正常: ログ出力確認"""
        with patch('services.embeddings.logger') as mock_logger:
            service = EmbeddingService("sk-test123456789")
            
            # 初期化ログ確認
            mock_logger.info.assert_called_with("EmbeddingService初期化完了: model=text-embedding-3-small")
    
    @patch('openai.OpenAI')
    def test_error_logging(self, mock_openai):
        """正常: エラーログ出力確認"""
        with patch('services.embeddings.logger') as mock_logger:
            mock_client = mock_openai.return_value
            mock_client.embeddings.create.side_effect = Exception("Test error")
            
            service = EmbeddingService("sk-test123456789")
            
            with pytest.raises(EmbeddingError):
                service.generate_embedding("test text")
            
            # エラーログ確認
            mock_logger.error.assert_called()


# Integration Test Markers
pytestmark = [
    pytest.mark.unit,
    pytest.mark.embeddings,
    pytest.mark.tdd_red_phase
]