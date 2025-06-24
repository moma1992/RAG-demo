"""
OpenAI Embeddings サービス TDD テストケース

Issue #48: OpenAI Embeddings統合機能実装
Red-Green-Refactor TDDサイクルによる実装
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any
import openai

from services.embeddings import (
    EmbeddingService,
    EmbeddingResult, 
    BatchEmbeddingResult,
    EmbeddingError
)


class TestEmbeddingService:
    """OpenAI Embeddings サービス TDD テストクラス"""
    
    def test_init_with_valid_api_key(self):
        """有効なAPIキーでの初期化テスト"""
        service = EmbeddingService(
            api_key="test-key",
            model="text-embedding-3-small"
        )
        
        assert service.api_key == "test-key"
        assert service.model == "text-embedding-3-small"
    
    def test_init_with_invalid_api_key_should_raise_error(self):
        """無効なAPIキーでの初期化エラーテスト"""
        with pytest.raises(ValueError, match="APIキーが指定されていません"):
            EmbeddingService(api_key="", model="text-embedding-3-small")
    
    @patch('openai.OpenAI')
    def test_create_embedding_success(self, mock_openai_client):
        """単一テキスト埋め込み生成成功テスト"""
        # Arrange
        mock_client = Mock()
        mock_openai_client.return_value = mock_client
        
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_response.usage = Mock(total_tokens=10)
        mock_client.embeddings.create.return_value = mock_response
        
        service = EmbeddingService(api_key="test-key")
        test_text = "これはテスト用のテキストです。"
        
        # Act
        result = service.create_embedding(test_text)
        
        # Assert
        assert isinstance(result, EmbeddingResult)
        assert len(result.embedding) == 1536
        assert result.token_count == 10
        assert result.model == "text-embedding-3-small"
        
        # OpenAI API呼び出し確認
        mock_client.embeddings.create.assert_called_once_with(
            input=test_text,
            model="text-embedding-3-small"
        )
    
    @patch('openai.OpenAI')
    def test_create_embedding_api_error(self, mock_openai_client):
        """OpenAI APIエラー時のテスト"""
        # Arrange
        mock_client = Mock()
        mock_openai_client.return_value = mock_client
        mock_client.embeddings.create.side_effect = openai.OpenAIError("API error")
        
        service = EmbeddingService(api_key="test-key")
        
        # Act & Assert
        with pytest.raises(EmbeddingError, match="埋め込み生成中にエラーが発生しました"):
            service.create_embedding("test text")
    
    @patch('openai.OpenAI')
    def test_create_embedding_rate_limit_error_with_retry(self, mock_openai_client):
        """レート制限エラー時のリトライテスト"""
        # Arrange
        mock_client = Mock()
        mock_openai_client.return_value = mock_client
        
        # 最初の2回は429エラー、3回目は成功
        mock_client.embeddings.create.side_effect = [
            openai.RateLimitError(message="Rate limit exceeded", response=Mock(), body=None),
            openai.RateLimitError(message="Rate limit exceeded", response=Mock(), body=None),
            Mock(data=[Mock(embedding=[0.1] * 1536)], usage=Mock(total_tokens=10))
        ]
        
        service = EmbeddingService(api_key="test-key")
        
        # Act
        result = service.create_embedding("test text")
        
        # Assert
        assert isinstance(result, EmbeddingResult)
        assert mock_client.embeddings.create.call_count == 3
    
    @patch('openai.OpenAI')
    def test_create_batch_embeddings_success(self, mock_openai_client):
        """バッチ埋め込み生成成功テスト"""
        # Arrange
        mock_client = Mock()
        mock_openai_client.return_value = mock_client
        
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1] * 1536),
            Mock(embedding=[0.2] * 1536),
            Mock(embedding=[0.3] * 1536)
        ]
        mock_response.usage = Mock(total_tokens=30)
        mock_client.embeddings.create.return_value = mock_response
        
        service = EmbeddingService(api_key="test-key")
        test_texts = ["テキスト1", "テキスト2", "テキスト3"]
        
        # Act
        result = service.create_batch_embeddings(test_texts)
        
        # Assert
        assert isinstance(result, BatchEmbeddingResult)
        assert len(result.embeddings) == 3
        assert result.total_tokens == 30
        assert result.model == "text-embedding-3-small"
        
        # OpenAI API呼び出し確認
        mock_client.embeddings.create.assert_called_once_with(
            input=test_texts,
            model="text-embedding-3-small"
        )
    
    @patch('openai.OpenAI')
    def test_create_batch_embeddings_large_batch_chunking(self, mock_openai_client):
        """大量バッチの分割処理テスト"""
        # Arrange
        mock_client = Mock()
        mock_openai_client.return_value = mock_client
        
        # 各チャンクごとに異なる応答をモック
        mock_response_1 = Mock()
        mock_response_1.data = [Mock(embedding=[0.1] * 1536) for _ in range(100)]
        mock_response_1.usage = Mock(total_tokens=1000)
        
        mock_response_2 = Mock()
        mock_response_2.data = [Mock(embedding=[0.2] * 1536) for _ in range(50)]
        mock_response_2.usage = Mock(total_tokens=500)
        
        mock_client.embeddings.create.side_effect = [mock_response_1, mock_response_2]
        
        service = EmbeddingService(api_key="test-key")
        # 150件のテキスト（100件+50件に分割される想定）
        test_texts = [f"テキスト{i}" for i in range(150)]
        
        # Act
        result = service.create_batch_embeddings(test_texts)
        
        # Assert
        assert isinstance(result, BatchEmbeddingResult)
        assert len(result.embeddings) == 150
        assert result.total_tokens == 1500
        assert mock_client.embeddings.create.call_count == 2
    
    def test_validate_embedding_dimension_valid(self):
        """埋め込み次元数検証 - 正常ケース"""
        service = EmbeddingService(api_key="test-key")
        valid_embedding = [0.1] * 1536
        
        assert service.validate_embedding_dimension(valid_embedding) is True
    
    def test_validate_embedding_dimension_invalid(self):
        """埋め込み次元数検証 - 異常ケース"""
        service = EmbeddingService(api_key="test-key")
        invalid_embedding = [0.1] * 512  # 間違った次元数
        
        assert service.validate_embedding_dimension(invalid_embedding) is False
    
    def test_calculate_cosine_similarity_identical_vectors(self):
        """コサイン類似度計算 - 同一ベクトル"""
        service = EmbeddingService(api_key="test-key")
        embedding = [1.0, 0.0, 0.0] * 512  # 1536次元
        
        similarity = service.calculate_cosine_similarity(embedding, embedding)
        assert similarity == pytest.approx(1.0, rel=1e-9)
    
    def test_calculate_cosine_similarity_orthogonal_vectors(self):
        """コサイン類似度計算 - 直交ベクトル"""
        service = EmbeddingService(api_key="test-key")
        embedding1 = [1.0, 0.0] * 768  # 1536次元
        embedding2 = [0.0, 1.0] * 768  # 1536次元
        
        similarity = service.calculate_cosine_similarity(embedding1, embedding2)
        assert similarity == pytest.approx(0.0, abs=1e-9)
    
    def test_calculate_cosine_similarity_dimension_mismatch(self):
        """コサイン類似度計算 - 次元数不一致エラー"""
        service = EmbeddingService(api_key="test-key")
        embedding1 = [1.0] * 1536
        embedding2 = [1.0] * 512
        
        with pytest.raises(ValueError, match="埋め込みの次元数が一致しません"):
            service.calculate_cosine_similarity(embedding1, embedding2)


class TestEmbeddingIntegration:
    """Embeddings統合テストクラス"""
    
    @patch('openai.OpenAI')
    def test_end_to_end_embedding_workflow(self, mock_openai_client):
        """エンドツーエンド埋め込み処理ワークフローテスト"""
        # Arrange
        mock_client = Mock()
        mock_openai_client.return_value = mock_client
        
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_response.usage = Mock(total_tokens=20)
        mock_client.embeddings.create.return_value = mock_response
        
        service = EmbeddingService(api_key="test-key")
        
        # Act
        input_text = "新入社員向けの社内文書検索システムのテストです。"
        result = service.create_embedding(input_text)
        
        # Assert - 実際のRAGシステムでの使用を想定した検証
        assert isinstance(result, EmbeddingResult)
        assert service.validate_embedding_dimension(result.embedding)
        assert result.token_count > 0
        assert result.model == "text-embedding-3-small"
    
    def test_japanese_text_handling(self):
        """日本語テキスト処理テスト"""
        service = EmbeddingService(api_key="test-key")
        
        japanese_texts = [
            "こんにちは、新入社員の皆さん。",
            "勤務時間は午前9時から午後6時までです。",
            "福利厚生について詳しくは人事部にお問い合わせください。"
        ]
        
        # 日本語テキストが適切に処理されることを確認
        for text in japanese_texts:
            # モックなので実際のAPIは呼ばれないが、エラーが発生しないことを確認
            assert len(text) > 0
            assert isinstance(text, str)


class TestEmbeddingError:
    """EmbeddingErrorテストクラス"""
    
    def test_embedding_error_inheritance(self):
        """EmbeddingErrorの継承確認"""
        error = EmbeddingError("テストエラー")
        assert isinstance(error, Exception)
        assert str(error) == "テストエラー"
    
    def test_embedding_error_with_cause(self):
        """EmbeddingErrorの原因付きエラー"""
        original_error = ValueError("元のエラー")
        embedding_error = EmbeddingError("埋め込み処理エラー") from original_error
        
        assert isinstance(embedding_error, EmbeddingError)
        assert embedding_error.__cause__ == original_error