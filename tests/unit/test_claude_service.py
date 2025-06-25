"""
Claude LLMサービスのユニットテスト

TDD Red段階 - 失敗するテストケースを先に作成
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import asyncio

from services.claude_llm import (
    ClaudeService, 
    GenerationResult, 
    ChatMessage,
    ClaudeError,
    RateLimitError,
    TokenLimitError
)


class TestClaudeService:
    """ClaudeServiceクラステスト"""
    
    @pytest.fixture
    def mock_anthropic_client(self):
        """AnthropicクライアントのMock"""
        with patch('anthropic.Anthropic') as mock:
            mock_instance = Mock()
            mock_instance.messages.create.return_value = Mock(
                content=[Mock(text="テスト回答")],
                usage=Mock(input_tokens=100, output_tokens=50),
                model="claude-3-sonnet-20240229"
            )
            mock.return_value = mock_instance
            yield mock_instance
    
    @pytest.fixture
    def claude_service(self, mock_anthropic_client):
        """ClaudeServiceインスタンス"""
        return ClaudeService(
            api_key="test-api-key",
            model="claude-3-sonnet-20240229"
        )
    
    def test_init_with_default_model(self):
        """デフォルトモデルでの初期化テスト"""
        with patch('anthropic.Anthropic'):
            service = ClaudeService(api_key="test-key")
            
            assert service.api_key == "test-key"
            assert service.model == "claude-3-sonnet-20240229"
            assert service.max_tokens == 2048
            assert service.temperature == 0
            assert service.timeout == 30
    
    def test_init_with_custom_parameters(self):
        """カスタムパラメータでの初期化テスト"""
        with patch('anthropic.Anthropic'):
            service = ClaudeService(
                api_key="custom-key",
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                temperature=0.7,
                timeout=60
            )
            
            assert service.model == "claude-3-haiku-20240307"
            assert service.max_tokens == 1024
            assert service.temperature == 0.7
            assert service.timeout == 60
    
    def test_generate_response_basic(self, claude_service, mock_anthropic_client):
        """基本的な回答生成テスト"""
        query = "新入社員の研修について教えてください"
        context_chunks = ["研修は3日間実施されます", "初日はオリエンテーションです"]
        
        result = claude_service.generate_response(query, context_chunks)
        
        assert isinstance(result, GenerationResult)
        assert result.content == "テスト回答"
        assert result.usage["input_tokens"] == 100
        assert result.usage["output_tokens"] == 50
        assert result.model == "claude-3-sonnet-20240229"
        
        # APIが適切に呼ばれたことを確認
        mock_anthropic_client.messages.create.assert_called_once()
    
    def test_generate_response_with_chat_history(self, claude_service, mock_anthropic_client):
        """チャット履歴付き回答生成テスト"""
        query = "さらに詳しく教えてください"
        context_chunks = ["詳細情報"]
        chat_history = [
            ChatMessage(role="user", content="前の質問"),
            ChatMessage(role="assistant", content="前の回答")
        ]
        
        result = claude_service.generate_response(query, context_chunks, chat_history)
        
        assert isinstance(result, GenerationResult)
        
        # チャット履歴が含まれた呼び出しを確認
        call_args = mock_anthropic_client.messages.create.call_args
        assert len(call_args[1]["messages"]) == 3  # 履歴2つ + 新しい質問1つ
    
    def test_generate_response_empty_context(self, claude_service, mock_anthropic_client):
        """空のコンテキストでの回答生成テスト"""
        query = "テスト質問"
        context_chunks = []
        
        result = claude_service.generate_response(query, context_chunks)
        
        assert isinstance(result, GenerationResult)
        # 空のコンテキストでも適切に処理される
        mock_anthropic_client.messages.create.assert_called_once()
    
    def test_generate_response_rate_limit_error(self, claude_service, mock_anthropic_client):
        """レート制限エラーのテスト"""
        from anthropic import RateLimitError as AnthropicRateLimitError
        
        mock_anthropic_client.messages.create.side_effect = AnthropicRateLimitError(
            "Rate limit exceeded",
            response=Mock(status_code=429),
            body={}
        )
        
        with pytest.raises(RateLimitError) as exc_info:
            claude_service.generate_response("質問", ["コンテキスト"])
        
        assert "レート制限に達しました" in str(exc_info.value)
    
    def test_generate_response_api_error(self, claude_service, mock_anthropic_client):
        """API エラーのテスト"""
        from anthropic import APIError
        
        mock_anthropic_client.messages.create.side_effect = APIError(
            "API Error",
            response=Mock(status_code=500),
            body={}
        )
        
        with pytest.raises(ClaudeError) as exc_info:
            claude_service.generate_response("質問", ["コンテキスト"])
        
        assert "Claude API" in str(exc_info.value)
    
    def test_generate_response_token_limit_exceeded(self, claude_service, mock_anthropic_client):
        """トークン制限超過エラーのテスト"""
        # 非常に長いコンテキスト（トークン制限を超える想定）
        very_long_context = ["非常に長いテキスト" * 10000]
        
        # トークン数計算をモック
        with patch.object(claude_service, '_count_tokens', return_value=200000):
            with pytest.raises(TokenLimitError) as exc_info:
                claude_service.generate_response("質問", very_long_context)
        
        assert "トークン制限を超えています" in str(exc_info.value)
    
    def test_generate_response_timeout(self, claude_service, mock_anthropic_client):
        """タイムアウトエラーのテスト"""
        import asyncio
        
        mock_anthropic_client.messages.create.side_effect = asyncio.TimeoutError()
        
        with pytest.raises(ClaudeError) as exc_info:
            claude_service.generate_response("質問", ["コンテキスト"])
        
        assert "タイムアウト" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_agenerate_response_basic(self, claude_service, mock_anthropic_client):
        """非同期回答生成の基本テスト"""
        # 非同期メソッドのモック設定
        mock_anthropic_client.messages.create = AsyncMock(return_value=Mock(
            content=[Mock(text="非同期テスト回答")],
            usage=Mock(input_tokens=80, output_tokens=40),
            model="claude-3-sonnet-20240229"
        ))
        
        result = await claude_service.agenerate_response("非同期質問", ["コンテキスト"])
        
        assert isinstance(result, GenerationResult)
        assert result.content == "非同期テスト回答"
        assert result.usage["input_tokens"] == 80
        assert result.usage["output_tokens"] == 40
    
    @pytest.mark.asyncio
    async def test_astream_response_basic(self, claude_service, mock_anthropic_client):
        """非同期ストリームレスポンスの基本テスト"""
        # ストリームレスポンスのモック設定
        async def mock_stream():
            chunks = [
                Mock(delta=Mock(text="Hello"), usage=None),
                Mock(delta=Mock(text=" World"), usage=None),
                Mock(delta=Mock(text="!"), usage=Mock(input_tokens=50, output_tokens=25))
            ]
            for chunk in chunks:
                yield chunk
        
        mock_anthropic_client.messages.stream = AsyncMock(return_value=mock_stream())
        
        chunks = []
        async for chunk in claude_service.astream_response("ストリーム質問", ["コンテキスト"]):
            chunks.append(chunk)
        
        assert len(chunks) == 3
        assert chunks[0]["content"] == "Hello"
        assert chunks[1]["content"] == " World"
        assert chunks[2]["content"] == "!"
        assert chunks[2]["usage"]["input_tokens"] == 50
    
    def test_summarize_text_basic(self, claude_service, mock_anthropic_client):
        """テキスト要約の基本テスト"""
        long_text = "これは要約対象の長いテキストです。" * 100
        
        mock_anthropic_client.messages.create.return_value = Mock(
            content=[Mock(text="要約結果")],
            usage=Mock(input_tokens=200, output_tokens=30),
            model="claude-3-sonnet-20240229"
        )
        
        result = claude_service.summarize_text(long_text, max_length=200)
        
        assert isinstance(result, GenerationResult)
        assert result.content == "要約結果"
        assert result.usage["input_tokens"] == 200
        assert result.usage["output_tokens"] == 30
    
    def test_validate_request_parameters(self, claude_service):
        """リクエストパラメータ検証テスト"""
        # 空のクエリ
        with pytest.raises(ValueError) as exc_info:
            claude_service.generate_response("", ["コンテキスト"])
        assert "空の質問" in str(exc_info.value)
        
        # Noneクエリ
        with pytest.raises(ValueError) as exc_info:
            claude_service.generate_response(None, ["コンテキスト"])
        assert "質問が指定されていません" in str(exc_info.value)
    
    def test_build_system_prompt(self, claude_service):
        """システムプロンプト構築テスト"""
        system_prompt = claude_service._build_system_prompt()
        
        assert "新入社員向け" in system_prompt
        assert "社内文書検索アシスタント" in system_prompt
        assert "提供された文書の内容に基づいて" in system_prompt
        assert "親切で丁寧な口調" in system_prompt
    
    def test_build_user_prompt(self, claude_service):
        """ユーザープロンプト構築テスト"""
        query = "研修について教えてください"
        context_chunks = ["研修情報1", "研修情報2"]
        
        user_prompt = claude_service._build_user_prompt(query, context_chunks)
        
        assert "参考文書：" in user_prompt
        assert "研修情報1" in user_prompt
        assert "研修情報2" in user_prompt
        assert "質問：" in user_prompt
        assert query in user_prompt
    
    def test_build_user_prompt_empty_context(self, claude_service):
        """空コンテキストでのユーザープロンプト構築テスト"""
        query = "質問"
        context_chunks = []
        
        user_prompt = claude_service._build_user_prompt(query, context_chunks)
        
        assert "関連する文書が見つかりませんでした" in user_prompt
        assert query in user_prompt
    
    def test_count_tokens(self, claude_service):
        """トークン数カウントテスト"""
        with patch('tiktoken.get_encoding') as mock_tiktoken:
            mock_encoder = Mock()
            mock_encoder.encode.return_value = [1, 2, 3, 4, 5]
            mock_tiktoken.return_value = mock_encoder
            
            token_count = claude_service._count_tokens("テストテキスト")
            
            assert token_count == 5
            mock_encoder.encode.assert_called_once_with("テストテキスト")
    
    def test_usage_tracking(self, claude_service, mock_anthropic_client):
        """使用量追跡テスト"""
        # 複数回の呼び出し
        for i in range(3):
            claude_service.generate_response(f"質問{i}", ["コンテキスト"])
        
        usage_stats = claude_service.get_usage_stats()
        
        assert usage_stats["total_requests"] == 3
        assert usage_stats["total_input_tokens"] == 300  # 100 * 3
        assert usage_stats["total_output_tokens"] == 150  # 50 * 3
        assert usage_stats["estimated_cost"] > 0
    
    def test_reset_usage_stats(self, claude_service):
        """使用量統計リセットテスト"""
        # 使用量を蓄積
        claude_service.generate_response("質問", ["コンテキスト"])
        
        # リセット前の確認
        stats_before = claude_service.get_usage_stats()
        assert stats_before["total_requests"] > 0
        
        # リセット
        claude_service.reset_usage_stats()
        
        # リセット後の確認
        stats_after = claude_service.get_usage_stats()
        assert stats_after["total_requests"] == 0
        assert stats_after["total_input_tokens"] == 0
        assert stats_after["total_output_tokens"] == 0


class TestChatMessage:
    """ChatMessageクラステスト"""
    
    def test_chat_message_creation(self):
        """ChatMessage作成テスト"""
        message = ChatMessage(role="user", content="テストメッセージ")
        
        assert message.role == "user"
        assert message.content == "テストメッセージ"
    
    def test_chat_message_validation(self):
        """ChatMessageバリデーションテスト"""
        # 不正なrole
        with pytest.raises(ValueError):
            ChatMessage(role="invalid", content="内容")
        
        # 空のcontent
        with pytest.raises(ValueError):
            ChatMessage(role="user", content="")


class TestGenerationResult:
    """GenerationResultクラステスト"""
    
    def test_generation_result_creation(self):
        """GenerationResult作成テスト"""
        result = GenerationResult(
            content="生成された回答",
            usage={"input_tokens": 100, "output_tokens": 50},
            model="claude-3-sonnet-20240229",
            metadata={"processing_time": 2.5}
        )
        
        assert result.content == "生成された回答"
        assert result.usage["input_tokens"] == 100
        assert result.usage["output_tokens"] == 50
        assert result.model == "claude-3-sonnet-20240229"
        assert result.metadata["processing_time"] == 2.5


class TestClaudeErrors:
    """Claude エラークラステスト"""
    
    def test_claude_error_creation(self):
        """ClaudeError作成テスト"""
        error = ClaudeError("エラーメッセージ", {"error_code": "TEST_ERROR"})
        
        assert str(error) == "エラーメッセージ"
        assert error.details["error_code"] == "TEST_ERROR"
    
    def test_rate_limit_error_creation(self):
        """RateLimitError作成テスト"""
        error = RateLimitError("レート制限エラー", retry_after=60)
        
        assert str(error) == "レート制限エラー"
        assert error.retry_after == 60
    
    def test_token_limit_error_creation(self):
        """TokenLimitError作成テスト"""
        error = TokenLimitError("トークン制限エラー", current_tokens=100000, max_tokens=90000)
        
        assert str(error) == "トークン制限エラー"
        assert error.current_tokens == 100000
        assert error.max_tokens == 90000