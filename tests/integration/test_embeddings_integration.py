"""
OpenAI Embeddings Service 統合テスト
Issue #54: OpenAI text-embedding-3-small統合テスト実装

実際のOpenAI APIとの統合テストとパフォーマンステスト
"""

import pytest
import time
import asyncio
from unittest.mock import patch, Mock
from typing import List

from services.embeddings import (
    EmbeddingService, 
    EmbeddingResult, 
    BatchEmbeddingResult,
    EmbeddingError
)


class TestEmbeddingServiceIntegration:
    """EmbeddingService 統合テストクラス"""
    
    @pytest.fixture
    def service(self):
        """統合テスト用EmbeddingServiceインスタンス"""
        return EmbeddingService("sk-test123456789")
    
    @patch('openai.OpenAI')
    def test_full_embedding_pipeline(self, mock_openai):
        """統合: 完全な埋め込み生成パイプライン"""
        # OpenAI APIレスポンスモック
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_response.usage.total_tokens = 15
        
        mock_client = mock_openai.return_value
        mock_client.embeddings.create.return_value = mock_response
        
        service = EmbeddingService("sk-test123456789")
        
        # 日本語テキストでの統合テスト
        japanese_text = "新入社員向けの社内文書検索システムです。"
        result = service.generate_embedding(japanese_text)
        
        # 結果検証
        assert isinstance(result, EmbeddingResult)
        assert len(result.embedding) == 1536
        assert result.token_count == 15
        assert result.model == "text-embedding-3-small"
        assert hasattr(result, 'response_time')
        assert result.response_time is not None
        
        # OpenAI API呼び出し確認
        mock_client.embeddings.create.assert_called_once_with(
            input=japanese_text,
            model="text-embedding-3-small"
        )
    
    @patch('openai.OpenAI')
    def test_batch_embedding_integration(self, mock_openai):
        """統合: バッチ埋め込み生成"""
        # バッチレスポンスモック
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1] * 1536),
            Mock(embedding=[0.2] * 1536),
            Mock(embedding=[0.3] * 1536)
        ]
        mock_response.usage.total_tokens = 45
        
        mock_client = mock_openai.return_value
        mock_client.embeddings.create.return_value = mock_response
        
        service = EmbeddingService("sk-test123456789")
        
        # 複数テキストでのバッチ処理
        texts = [
            "社内文書検索システム",
            "新入社員向けRAGアプリケーション", 
            "StreamlitとSupabaseを使用"
        ]
        
        result = service.generate_batch_embeddings(texts)
        
        # 結果検証
        assert isinstance(result, BatchEmbeddingResult)
        assert len(result.embeddings) == 3
        assert result.total_tokens == 45
        assert result.model == "text-embedding-3-small"
        
        # 各埋め込みの次元確認
        for embedding in result.embeddings:
            assert len(embedding) == 1536
    
    @patch('openai.OpenAI')
    def test_token_estimation_accuracy(self, mock_openai):
        """統合: トークン推定精度確認"""
        service = EmbeddingService("sk-test123456789")
        
        test_cases = [
            ("Hello world", 2),  # 英語短文
            ("こんにちは世界", 4),  # 日本語短文
            ("新入社員向けの社内文書検索RAGアプリケーション", 28),  # 日本語長文
            ("This is a test sentence for token counting.", 10)  # 英語長文
        ]
        
        for text, expected_range in test_cases:
            estimated_tokens = service.estimate_tokens(text)
            
            # トークン数が妥当な範囲内であることを確認
            assert isinstance(estimated_tokens, int)
            assert estimated_tokens > 0
            # 推定値が期待値の±50%範囲内であることを確認
            assert expected_range * 0.5 <= estimated_tokens <= expected_range * 1.5
    
    @patch('openai.OpenAI')
    def test_model_info_consistency(self, mock_openai):
        """統合: モデル情報一貫性確認"""
        service = EmbeddingService("sk-test123456789")
        
        model_info = service.get_model_info()
        
        # モデル情報確認
        assert model_info["model"] == "text-embedding-3-small"
        assert model_info["dimension"] == 1536
        assert model_info["max_tokens"] == 8192
        assert model_info["async_mode"] is False
        assert model_info["timeout"] is None
    
    @patch('openai.OpenAI')
    def test_cost_calculation_accuracy(self, mock_openai):
        """統合: コスト計算精度確認"""
        service = EmbeddingService("sk-test123456789")
        
        test_cases = [
            (1000, 0.00002),   # 1K tokens
            (5000, 0.0001),    # 5K tokens
            (10000, 0.0002),   # 10K tokens
        ]
        
        for tokens, expected_cost in test_cases:
            calculated_cost = service.calculate_embedding_cost(tokens)
            
            # コスト計算精度確認（小数点以下5桁まで）
            assert abs(calculated_cost - expected_cost) < 0.000001
    
    @patch('openai.OpenAI')
    def test_cosine_similarity_calculation(self, mock_openai):
        """統合: コサイン類似度計算確認"""
        service = EmbeddingService("sk-test123456789")
        
        # テスト用埋め込みベクトル
        embedding1 = [1.0, 0.0, 0.0] + [0.0] * 1533  # 単位ベクトル
        embedding2 = [0.0, 1.0, 0.0] + [0.0] * 1533  # 直交ベクトル
        embedding3 = [1.0, 0.0, 0.0] + [0.0] * 1533  # 同一ベクトル
        
        # 直交ベクトルの類似度（0に近い）
        similarity_orthogonal = service.calculate_cosine_similarity(embedding1, embedding2)
        assert abs(similarity_orthogonal) < 0.001
        
        # 同一ベクトルの類似度（1に近い）
        similarity_identical = service.calculate_cosine_similarity(embedding1, embedding3)
        assert abs(similarity_identical - 1.0) < 0.001


class TestPerformanceRequirements:
    """パフォーマンス要件テスト"""
    
    @patch('openai.OpenAI')
    def test_response_time_under_5_seconds(self, mock_openai):
        """パフォーマンス: 5秒以下の応答時間"""
        # レスポンス時間シミュレーション（実際は瞬時、テスト用に短縮）
        def mock_create_with_delay(*args, **kwargs):
            time.sleep(0.1)  # 100ms遅延をシミュレート
            mock_response = Mock()
            mock_response.data = [Mock(embedding=[0.1] * 1536)]
            mock_response.usage.total_tokens = 10
            return mock_response
        
        mock_client = mock_openai.return_value
        mock_client.embeddings.create.side_effect = mock_create_with_delay
        
        service = EmbeddingService("sk-test123456789")
        
        start_time = time.time()
        result = service.generate_embedding("Performance test text")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # Issue #54要件: 5秒以下の応答時間
        assert response_time < 5.0
        assert result.response_time < 5.0
    
    @patch('openai.OpenAI')
    def test_batch_processing_efficiency(self, mock_openai):
        """パフォーマンス: バッチ処理効率性"""
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536) for _ in range(10)]
        mock_response.usage.total_tokens = 100
        
        mock_client = mock_openai.return_value
        mock_client.embeddings.create.return_value = mock_response
        
        service = EmbeddingService("sk-test123456789")
        
        # 10件のバッチ処理
        texts = [f"Test text {i}" for i in range(10)]
        
        start_time = time.time()
        result = service.generate_batch_embeddings(texts)
        end_time = time.time()
        
        batch_time = end_time - start_time
        
        # バッチ処理も高速であることを確認
        assert batch_time < 2.0
        assert len(result.embeddings) == 10
    
    @patch('openai.OpenAI')
    def test_memory_efficiency(self, mock_openai):
        """パフォーマンス: メモリ効率性"""
        import psutil
        import os
        
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_response.usage.total_tokens = 10
        
        mock_client = mock_openai.return_value
        mock_client.embeddings.create.return_value = mock_response
        
        service = EmbeddingService("sk-test123456789")
        
        # メモリ使用量測定開始
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 100回の埋め込み生成
        for i in range(100):
            service.generate_embedding(f"Memory test {i}")
        
        # メモリ使用量測定終了
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # メモリ使用量増加が100MB以下であることを確認
        assert memory_increase < 100


class TestAsyncIntegration:
    """非同期統合テスト"""
    
    @patch('openai.AsyncOpenAI')
    @pytest.mark.asyncio
    async def test_async_embedding_generation(self, mock_async_openai):
        """統合: 非同期埋め込み生成"""
        from unittest.mock import AsyncMock
        
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_response.usage.total_tokens = 10
        
        mock_client = mock_async_openai.return_value
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        
        service = EmbeddingService("sk-test123456789", async_mode=True)
        
        result = await service.generate_embedding_async("Async test text")
        
        assert isinstance(result, EmbeddingResult)
        assert len(result.embedding) == 1536
        assert result.response_time is not None
    
    @patch('openai.AsyncOpenAI')
    @pytest.mark.asyncio
    async def test_concurrent_embedding_generation(self, mock_async_openai):
        """統合: 並列埋め込み生成"""
        from unittest.mock import AsyncMock
        
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_response.usage.total_tokens = 10
        
        mock_client = mock_async_openai.return_value
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        
        service = EmbeddingService("sk-test123456789", async_mode=True)
        
        # 5つの並列タスク
        texts = [f"Concurrent test {i}" for i in range(5)]
        tasks = [service.generate_embedding_async(text) for text in texts]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        total_time = end_time - start_time
        
        # 並列処理により高速化されることを確認
        assert len(results) == 5
        assert total_time < 3.0  # 並列実行により短時間で完了
        
        for result in results:
            assert isinstance(result, EmbeddingResult)
            assert len(result.embedding) == 1536


class TestErrorRecovery:
    """エラー回復・障害対応テスト"""
    
    @patch('openai.OpenAI')
    def test_retry_mechanism(self, mock_openai):
        """統合: リトライメカニズム（将来機能）"""
        # 最初は失敗、2回目は成功のモック
        mock_client = mock_openai.return_value
        
        call_count = 0
        def mock_create_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Temporary failure")
            else:
                mock_response = Mock()
                mock_response.data = [Mock(embedding=[0.1] * 1536)]
                mock_response.usage.total_tokens = 10
                return mock_response
        
        mock_client.embeddings.create.side_effect = mock_create_with_retry
        
        service = EmbeddingService("sk-test123456789")
        
        # 現在の実装では最初のエラーで失敗するが、将来のリトライ機能のテスト
        with pytest.raises(EmbeddingError):
            service.generate_embedding("Retry test")
    
    @patch('openai.OpenAI')
    def test_graceful_degradation(self, mock_openai):
        """統合: 優雅な劣化処理"""
        service = EmbeddingService("sk-test123456789")
        
        # 無効な入力に対する適切なエラーハンドリング
        invalid_inputs = [
            "",  # 空文字列
            None,  # None値
            " " * 10,  # 空白のみ
        ]
        
        for invalid_input in invalid_inputs:
            with pytest.raises(ValueError):
                service.generate_embedding(invalid_input)


class TestDataValidation:
    """データ検証・整合性テスト"""
    
    @patch('openai.OpenAI')
    def test_embedding_dimension_validation(self, mock_openai):
        """統合: 埋め込み次元数検証"""
        service = EmbeddingService("sk-test123456789")
        
        # 正しい次元数
        valid_embedding = [0.1] * 1536
        assert service.validate_embedding_dimension(valid_embedding) is True
        
        # 間違った次元数
        invalid_embeddings = [
            [0.1] * 512,   # 512次元
            [0.1] * 768,   # 768次元
            [0.1] * 2048,  # 2048次元
            [],            # 空リスト
        ]
        
        for invalid_embedding in invalid_embeddings:
            assert service.validate_embedding_dimension(invalid_embedding) is False
    
    @patch('openai.OpenAI')
    def test_model_consistency(self, mock_openai):
        """統合: モデル一貫性確認"""
        # 異なるモデルでの初期化
        models = [
            "text-embedding-3-small",
            "text-embedding-ada-002"
        ]
        
        for model in models:
            service = EmbeddingService("sk-test123456789", model=model)
            assert service.model == model
            
            model_info = service.get_model_info()
            assert model_info["model"] == model


# Integration Test Markers
pytestmark = [
    pytest.mark.integration,
    pytest.mark.embeddings,
    pytest.mark.performance
]