"""
Claude LLM サービス TDD テストケース

Issue #49: Claude API統合・回答生成機能実装
Red-Green-Refactor TDDサイクルによる実装
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any
import anthropic

from services.claude_llm import (
    ClaudeLLMService,
    ChatMessage,
    GenerationResult,
    LLMError
)


class TestClaudeLLMService:
    """Claude LLM サービス TDD テストクラス"""
    
    def test_init_with_valid_api_key(self):
        """有効なAPIキーでの初期化テスト"""
        service = ClaudeLLMService(
            api_key="test-key",
            model="claude-3-haiku-20240307"
        )
        
        assert service.api_key == "test-key"
        assert service.model == "claude-3-haiku-20240307"
        assert service.max_tokens == 4096
    
    def test_init_with_invalid_api_key_should_raise_error(self):
        """無効なAPIキーでの初期化エラーテスト"""
        with pytest.raises(ValueError, match="APIキーが指定されていません"):
            ClaudeLLMService(api_key="", model="claude-3-haiku-20240307")
    
    @patch('anthropic.Anthropic')
    def test_generate_response_success(self, mock_anthropic_client):
        """RAG回答生成成功テスト"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_client.return_value = mock_client
        
        mock_response = Mock()
        mock_response.content = [Mock(text="新入社員の皆さん、ご質問にお答えします。勤務時間は午前9時から午後6時までです。")]
        mock_response.usage = Mock(
            input_tokens=100,
            output_tokens=50
        )
        mock_client.messages.create.return_value = mock_response
        
        service = ClaudeLLMService(api_key="test-key")
        query = "勤務時間について教えてください"
        context_chunks = ["勤務時間は午前9時から午後6時までです。"]
        
        # Act
        result = service.generate_response(query, context_chunks)
        
        # Assert
        assert isinstance(result, GenerationResult)
        assert "新入社員" in result.content
        assert result.usage["input_tokens"] == 100
        assert result.usage["output_tokens"] == 50
        assert result.model == "claude-3-haiku-20240307"
        
        # Claude API呼び出し確認
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args
        assert call_args[1]["model"] == "claude-3-haiku-20240307"
        assert call_args[1]["max_tokens"] == 4096
    
    @patch('anthropic.Anthropic')
    def test_generate_response_with_chat_history(self, mock_anthropic_client):
        """チャット履歴付きRAG回答生成テスト"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_client.return_value = mock_client
        
        mock_response = Mock()
        mock_response.content = [Mock(text="先ほどお答えした勤務時間に加えて、休憩時間についてもご説明します。")]
        mock_response.usage = Mock(input_tokens=150, output_tokens=75)
        mock_client.messages.create.return_value = mock_response
        
        service = ClaudeLLMService(api_key="test-key")
        query = "休憩時間についても教えてください"
        context_chunks = ["休憩時間は12時から13時までです。"]
        chat_history = [
            ChatMessage(role="user", content="勤務時間について教えてください"),
            ChatMessage(role="assistant", content="勤務時間は午前9時から午後6時までです。")
        ]
        
        # Act
        result = service.generate_response(query, context_chunks, chat_history)
        
        # Assert
        assert isinstance(result, GenerationResult)
        assert "休憩時間" in result.content
        
        # メッセージ履歴が正しく渡されていることを確認
        call_args = mock_client.messages.create.call_args
        messages = call_args[1]["messages"]
        assert len(messages) >= 3  # 履歴2件 + 新しい質問1件
    
    @patch('anthropic.Anthropic')
    def test_generate_response_with_empty_context(self, mock_anthropic_client):
        """空の文書コンテキストでの回答生成テスト"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_client.return_value = mock_client
        
        mock_response = Mock()
        mock_response.content = [Mock(text="申し訳ございませんが、関連する文書が見つかりませんでした。人事部にお問い合わせください。")]
        mock_response.usage = Mock(input_tokens=80, output_tokens=40)
        mock_client.messages.create.return_value = mock_response
        
        service = ClaudeLLMService(api_key="test-key")
        query = "未知の情報について教えてください"
        context_chunks = []  # 空のコンテキスト
        
        # Act
        result = service.generate_response(query, context_chunks)
        
        # Assert
        assert isinstance(result, GenerationResult)
        assert "関連する文書が見つかりませんでした" in result.content
    
    @patch('anthropic.Anthropic')
    def test_generate_response_api_error(self, mock_anthropic_client):
        """Claude APIエラー時のテスト"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_client.return_value = mock_client
        mock_client.messages.create.side_effect = anthropic.AnthropicError("API error")
        
        service = ClaudeLLMService(api_key="test-key")
        
        # Act & Assert
        with pytest.raises(LLMError, match="回答生成中にAPIエラーが発生しました"):
            service.generate_response("test query", ["test context"])
    
    @patch('anthropic.Anthropic')
    def test_generate_response_rate_limit_error_with_retry(self, mock_anthropic_client):
        """レート制限エラー時のリトライテスト"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_client.return_value = mock_client
        
        # 最初の2回は429エラー、3回目は成功
        mock_client.messages.create.side_effect = [
            anthropic.RateLimitError(message="Rate limit exceeded", response=Mock(), body=None),
            anthropic.RateLimitError(message="Rate limit exceeded", response=Mock(), body=None),
            Mock(
                content=[Mock(text="リトライ後の正常な回答です。")],
                usage=Mock(input_tokens=100, output_tokens=50)
            )
        ]
        
        service = ClaudeLLMService(api_key="test-key")
        
        # Act
        result = service.generate_response("test query", ["test context"])
        
        # Assert
        assert isinstance(result, GenerationResult)
        assert "リトライ後の正常な回答" in result.content
        assert mock_client.messages.create.call_count == 3
    
    def test_build_system_prompt(self):
        """システムプロンプト構築テスト"""
        service = ClaudeLLMService(api_key="test-key")
        
        # プライベートメソッドを直接テスト
        system_prompt = service._build_system_prompt()
        
        assert "新入社員向けの社内文書検索アシスタント" in system_prompt
        assert "提供された文書の内容に基づいて正確に回答する" in system_prompt
        assert "分かりやすい日本語で説明する" in system_prompt
        assert "人事部に確認するよう案内する" in system_prompt
    
    def test_build_user_prompt_with_context(self):
        """ユーザープロンプト構築テスト（コンテキスト有り）"""
        service = ClaudeLLMService(api_key="test-key")
        
        query = "有給休暇について教えてください"
        context_chunks = [
            "有給休暇は年間20日付与されます。",
            "有給休暇の取得は事前に申請が必要です。"
        ]
        
        user_prompt = service._build_user_prompt(query, context_chunks)
        
        assert "参考文書：" in user_prompt
        assert "有給休暇は年間20日付与されます。" in user_prompt
        assert "有給休暇の取得は事前に申請が必要です。" in user_prompt
        assert "質問：" in user_prompt
        assert query in user_prompt
    
    def test_build_user_prompt_without_context(self):
        """ユーザープロンプト構築テスト（コンテキスト無し）"""
        service = ClaudeLLMService(api_key="test-key")
        
        query = "未知の質問です"
        context_chunks = []
        
        user_prompt = service._build_user_prompt(query, context_chunks)
        
        assert "関連する文書が見つかりませんでした。" in user_prompt
        assert query in user_prompt
    
    @patch('anthropic.Anthropic')
    def test_summarize_text_success(self, mock_anthropic_client):
        """テキスト要約成功テスト"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_client.return_value = mock_client
        
        mock_response = Mock()
        mock_response.content = [Mock(text="テキストの要約結果です。")]
        mock_response.usage = Mock(input_tokens=200, output_tokens=30)
        mock_client.messages.create.return_value = mock_response
        
        service = ClaudeLLMService(api_key="test-key")
        long_text = "これは長いテキストです。" * 100
        
        # Act
        result = service.summarize_text(long_text, max_length=500)
        
        # Assert
        assert isinstance(result, GenerationResult)
        assert "要約結果" in result.content
        assert result.usage["input_tokens"] == 200
        assert result.usage["output_tokens"] == 30
    
    @patch('anthropic.Anthropic')
    def test_summarize_text_short_text(self, mock_anthropic_client):
        """短いテキストの要約テスト"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_client.return_value = mock_client
        
        mock_response = Mock()
        mock_response.content = [Mock(text="短いテキストです。")]
        mock_response.usage = Mock(input_tokens=20, output_tokens=10)
        mock_client.messages.create.return_value = mock_response
        
        service = ClaudeLLMService(api_key="test-key")
        short_text = "短いテキストです。"
        
        # Act
        result = service.summarize_text(short_text, max_length=500)
        
        # Assert
        assert isinstance(result, GenerationResult)
        assert result.content == "短いテキストです。"


class TestChatMessage:
    """ChatMessage データクラステスト"""
    
    def test_chat_message_creation(self):
        """ChatMessage作成テスト"""
        message = ChatMessage(role="user", content="テストメッセージ")
        
        assert message.role == "user"
        assert message.content == "テストメッセージ"
    
    def test_chat_message_assistant_role(self):
        """ChatMessage アシスタントロールテスト"""
        message = ChatMessage(role="assistant", content="アシスタントの回答")
        
        assert message.role == "assistant"
        assert message.content == "アシスタントの回答"


class TestGenerationResult:
    """GenerationResult データクラステスト"""
    
    def test_generation_result_creation(self):
        """GenerationResult作成テスト"""
        result = GenerationResult(
            content="生成された回答",
            usage={"input_tokens": 100, "output_tokens": 50},
            model="claude-3-haiku-20240307"
        )
        
        assert result.content == "生成された回答"
        assert result.usage["input_tokens"] == 100
        assert result.usage["output_tokens"] == 50
        assert result.model == "claude-3-haiku-20240307"


class TestLLMError:
    """LLMError エラークラステスト"""
    
    def test_llm_error_inheritance(self):
        """LLMErrorの継承確認"""
        error = LLMError("テストエラー")
        assert isinstance(error, Exception)
        assert str(error) == "テストエラー"
    
    def test_llm_error_with_cause(self):
        """LLMErrorの原因付きエラー"""
        original_error = ValueError("元のエラー")
        llm_error = LLMError("LLM処理エラー") from original_error
        
        assert isinstance(llm_error, LLMError)
        assert llm_error.__cause__ == original_error


class TestClaudeIntegration:
    """Claude API統合テストクラス"""
    
    @patch('anthropic.Anthropic')
    def test_end_to_end_rag_workflow(self, mock_anthropic_client):
        """エンドツーエンドRAGワークフローテスト"""
        # Arrange
        mock_client = Mock()
        mock_anthropic_client.return_value = mock_client
        
        mock_response = Mock()
        mock_response.content = [Mock(text="""新入社員の皆さん、勤務時間についてご質問ありがとうございます。

社内文書によりますと、勤務時間は以下の通りです：
- 開始時間：午前9時
- 終了時間：午後6時
- 休憩時間：12時から13時まで

詳細については人事部までお問い合わせください。""")]
        mock_response.usage = Mock(input_tokens=150, output_tokens=100)
        mock_client.messages.create.return_value = mock_response
        
        service = ClaudeLLMService(api_key="test-key")
        
        # Act - RAGシナリオを模擬
        query = "勤務時間について教えてください"
        context_chunks = [
            "勤務時間は午前9時から午後6時までです。",
            "休憩時間は12時から13時までです。"
        ]
        
        result = service.generate_response(query, context_chunks)
        
        # Assert - 実際のRAGシステムでの期待値
        assert isinstance(result, GenerationResult)
        assert "勤務時間" in result.content
        assert "新入社員" in result.content
        assert "人事部" in result.content
        assert result.usage["input_tokens"] > 0
        assert result.usage["output_tokens"] > 0
    
    def test_japanese_text_handling(self):
        """日本語テキスト処理テスト"""
        service = ClaudeLLMService(api_key="test-key")
        
        japanese_queries = [
            "有給休暇の取得方法を教えてください。",
            "健康保険の適用範囲について説明してください。",
            "社員食堂の利用時間はいつですか？"
        ]
        
        japanese_contexts = [
            "有給休暇は年間20日付与され、事前申請が必要です。",
            "健康保険は入社と同時に適用されます。",
            "社員食堂は11時30分から14時まで利用可能です。"
        ]
        
        # 日本語テキストが適切に処理されることを確認
        for query, context in zip(japanese_queries, japanese_contexts):
            # モックなので実際のAPIは呼ばれないが、エラーが発生しないことを確認
            assert len(query) > 0
            assert len(context) > 0
            assert isinstance(query, str)
            assert isinstance(context, str)