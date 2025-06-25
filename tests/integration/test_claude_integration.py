"""
Claude LLMサービス統合テスト

実際のAPI統合とエンドツーエンドワークフローのテスト
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any
import time

from services.claude_llm import (
    ClaudeService,
    GenerationResult,
    ChatMessage,
    ClaudeError,
    RateLimitError,
    TokenLimitError
)
from utils.prompt_templates import PromptTemplateManager, RAGPromptBuilder
from utils.error_handler import ErrorHandler


class TestClaudeServiceIntegration:
    """ClaudeService統合テスト"""
    
    @pytest.fixture
    def mock_env_config(self):
        """モック環境設定"""
        return {
            "ANTHROPIC_API_KEY": "test-api-key",
            "CLAUDE_MODEL": "claude-3-sonnet-20240229"
        }
    
    @pytest.fixture
    def claude_service(self, mock_env_config):
        """モック設定でClaudeServiceを初期化"""
        with patch.dict('os.environ', mock_env_config):
            with patch('anthropic.Anthropic'):
                return ClaudeService(
                    api_key=mock_env_config["ANTHROPIC_API_KEY"],
                    model=mock_env_config["CLAUDE_MODEL"]
                )
    
    @pytest.fixture
    def sample_rag_context(self):
        """サンプルRAGコンテキスト"""
        return [
            "新入社員研修は3日間実施されます。初日はオリエンテーション、2日目は基本業務研修、3日目は実践研修です。",
            "研修期間中は人事部の田中が担当者として対応します。質問がある場合は内線1234までご連絡ください。",
            "研修終了後は各部署に配属され、2週間のOJTが実施されます。"
        ]
    
    @pytest.fixture
    def sample_chat_history(self):
        """サンプルチャット履歴"""
        return [
            ChatMessage(role="user", content="新入社員研修について教えてください"),
            ChatMessage(role="assistant", content="新入社員研修は3日間のプログラムで構成されています。")
        ]
    
    def test_full_rag_pipeline_integration(self, claude_service, sample_rag_context):
        """完全なRAGパイプライン統合テスト"""
        # モックレスポンス設定
        mock_response = Mock()
        mock_response.content = "新入社員研修は3日間実施され、初日はオリエンテーション、2日目は基本業務研修、3日目は実践研修です。担当者は人事部の田中（内線1234）です。"
        mock_response.usage_metadata = {"input_tokens": 150, "output_tokens": 80}
        
        with patch.object(claude_service.llm_with_retry, 'invoke', return_value=mock_response):
            # RAG質問実行
            query = "新入社員研修の期間と担当者を教えてください"
            result = claude_service.generate_response(query, sample_rag_context)
            
            # 結果検証
            assert isinstance(result, GenerationResult)
            assert "3日間" in result.content
            assert "田中" in result.content
            assert result.usage["input_tokens"] == 150
            assert result.usage["output_tokens"] == 80
            assert result.model == "claude-3-sonnet-20240229"
            assert "processing_time" in result.metadata
    
    def test_conversational_rag_integration(self, claude_service, sample_rag_context, sample_chat_history):
        """会話型RAG統合テスト"""
        mock_response = Mock()
        mock_response.content = "OJTについてですが、研修終了後に各部署で2週間実施されます。"
        mock_response.usage_metadata = {"input_tokens": 200, "output_tokens": 50}
        
        with patch.object(claude_service.llm_with_retry, 'invoke', return_value=mock_response):
            # 継続会話
            query = "OJTについても教えてください"
            result = claude_service.generate_response(
                query, 
                sample_rag_context, 
                chat_history=sample_chat_history
            )
            
            # 結果検証
            assert isinstance(result, GenerationResult)
            assert "OJT" in result.content
            assert "2週間" in result.content
    
    @pytest.mark.asyncio
    async def test_async_generation_integration(self, claude_service, sample_rag_context):
        """非同期生成統合テスト"""
        mock_response = Mock()
        mock_response.content = "非同期で生成された回答です。"
        mock_response.usage_metadata = {"input_tokens": 100, "output_tokens": 30}
        
        # 非同期メソッドのモック
        claude_service.llm_with_retry.ainvoke = AsyncMock(return_value=mock_response)
        
        query = "非同期テスト質問"
        result = await claude_service.agenerate_response(query, sample_rag_context)
        
        # 結果検証
        assert isinstance(result, GenerationResult)
        assert result.content == "非同期で生成された回答です。"
        assert result.metadata["async"] is True
    
    @pytest.mark.asyncio
    async def test_streaming_integration(self, claude_service, sample_rag_context):
        """ストリーミング統合テスト"""
        # ストリーミングチャンクのモック
        async def mock_stream():
            chunks = [
                Mock(content="Hello"),
                Mock(content=" World"),
                Mock(content="!")
            ]
            for chunk in chunks:
                yield chunk
        
        claude_service.llm_with_retry.astream = AsyncMock(return_value=mock_stream())
        
        # ストリーミング実行
        chunks = []
        async for chunk in claude_service.astream_response("テスト質問", sample_rag_context):
            chunks.append(chunk)
        
        # 結果検証
        assert len(chunks) == 3
        assert chunks[0]["content"] == "Hello"
        assert chunks[1]["content"] == " World"
        assert chunks[2]["content"] == "!"
    
    def test_summarization_integration(self, claude_service):
        """要約機能統合テスト"""
        long_text = """新入社員研修プログラムについて詳しく説明いたします。
当社の新入社員研修は、新しく入社した社員が円滑に業務を開始できるよう設計された3日間の包括的なプログラムです。
初日はオリエンテーションとして、会社の歴史、企業理念、組織構造について学びます。
2日目は基本業務研修として、各部署の業務内容、社内システムの使い方、ビジネスマナーを習得します。
3日目は実践研修として、実際の業務シミュレーションと先輩社員との交流を行います。""" * 10  # より長いテキスト
        
        mock_response = Mock()
        mock_response.content = """新入社員研修プログラムの要約：
• 3日間の包括的な研修プログラム
• 初日：オリエンテーション（会社概要、理念、組織）
• 2日目：基本業務研修（業務内容、システム、マナー）
• 3日目：実践研修（シミュレーション、先輩交流）"""
        mock_response.usage_metadata = {"input_tokens": 800, "output_tokens": 120}
        
        with patch.object(claude_service.llm_with_retry, 'invoke', return_value=mock_response):
            result = claude_service.summarize_text(long_text, max_length=200)
            
            # 結果検証
            assert isinstance(result, GenerationResult)
            assert "3日間" in result.content
            assert "要約" in result.content
            assert result.metadata["operation"] == "summarization"
            assert result.metadata["original_length"] > 500
    
    def test_error_handling_integration(self, claude_service, sample_rag_context):
        """エラーハンドリング統合テスト"""
        # API エラーのシミュレーション
        with patch.object(claude_service.llm_with_retry, 'invoke') as mock_invoke:
            # レート制限エラー
            mock_invoke.side_effect = RateLimitError("Rate limit exceeded", retry_after=60)
            
            with pytest.raises(RateLimitError) as exc_info:
                claude_service.generate_response("質問", sample_rag_context)
            
            assert exc_info.value.retry_after == 60
    
    def test_token_limit_validation_integration(self, claude_service):
        """トークン制限検証統合テスト"""
        # 非常に長いコンテキスト（トークン制限超過をシミュレート）
        very_long_context = ["非常に長いテキスト" * 10000]
        
        # トークン計算をモック
        with patch.object(claude_service, '_count_tokens', return_value=50000):
            with pytest.raises(TokenLimitError) as exc_info:
                claude_service.generate_response("質問", very_long_context)
            
            assert exc_info.value.current_tokens > 90000
    
    def test_usage_tracking_integration(self, claude_service, sample_rag_context):
        """使用量追跡統合テスト"""
        mock_response = Mock()
        mock_response.content = "テスト回答"
        mock_response.usage_metadata = {"input_tokens": 100, "output_tokens": 50}
        
        with patch.object(claude_service.llm_with_retry, 'invoke', return_value=mock_response):
            # 複数回実行
            for i in range(3):
                claude_service.generate_response(f"質問{i}", sample_rag_context)
            
            # 使用量統計確認
            stats = claude_service.get_usage_stats()
            assert stats["total_requests"] == 3
            assert stats["total_input_tokens"] == 300
            assert stats["total_output_tokens"] == 150
            assert stats["total_cost"] > 0
    
    def test_retry_mechanism_integration(self, claude_service, sample_rag_context):
        """リトライ機構統合テスト"""
        mock_response = Mock()
        mock_response.content = "リトライ後の成功回答"
        mock_response.usage_metadata = {"input_tokens": 100, "output_tokens": 50}
        
        # 最初の2回は失敗、3回目で成功
        side_effects = [Exception("一時的エラー"), Exception("一時的エラー"), mock_response]
        
        with patch.object(claude_service.llm_with_retry, 'invoke', side_effect=side_effects):
            result = claude_service.generate_response("質問", sample_rag_context)
            
            # リトライ後に成功
            assert result.content == "リトライ後の成功回答"


class TestPromptTemplateIntegration:
    """プロンプトテンプレート統合テスト"""
    
    @pytest.fixture
    def template_manager(self):
        """テンプレートマネージャー"""
        return PromptTemplateManager()
    
    @pytest.fixture
    def rag_builder(self, template_manager):
        """RAGプロンプトビルダー"""
        return RAGPromptBuilder(template_manager)
    
    def test_template_claude_integration(self, claude_service, rag_builder):
        """テンプレート・Claude統合テスト"""
        # プロンプトテンプレートを使用して質問生成
        query = "研修について教えてください"
        context = ["研修は3日間です"]
        
        user_prompt = rag_builder.build_user_prompt(query, context)
        
        # Claude APIモック
        mock_response = Mock()
        mock_response.content = "テンプレートベースの回答"
        mock_response.usage_metadata = {"input_tokens": 80, "output_tokens": 40}
        
        with patch.object(claude_service.llm_with_retry, 'invoke', return_value=mock_response):
            result = claude_service.generate_response(query, context)
            
            assert isinstance(result, GenerationResult)
            assert result.content == "テンプレートベースの回答"
    
    def test_conversation_template_integration(self, claude_service, rag_builder):
        """会話テンプレート統合テスト"""
        query = "さらに詳しく教えて"
        context = ["詳細情報"]
        history = [
            {"role": "user", "content": "最初の質問"},
            {"role": "assistant", "content": "最初の回答"}
        ]
        
        # 会話プロンプト生成
        messages = rag_builder.build_conversation_prompt(query, context, history)
        
        # メッセージ構造検証
        assert len(messages) == 4  # system + history(2) + new user
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"


class TestErrorHandlerIntegration:
    """エラーハンドラー統合テスト"""
    
    def test_claude_error_handling_integration(self):
        """Claude エラーハンドリング統合テスト"""
        # レート制限エラー
        rate_limit_error = RateLimitError("Rate limited", retry_after=120)
        message = ErrorHandler.handle_claude_error(rate_limit_error)
        assert "120秒後" in message
        
        # トークン制限エラー
        token_error = TokenLimitError("Token limit", 100000, 90000)
        message = ErrorHandler.handle_claude_error(token_error)
        assert "トークン制限" in message
    
    def test_llm_pipeline_error_integration(self):
        """LLMパイプラインエラー統合テスト"""
        # 各種エラーの統合処理
        claude_error = ClaudeError("Claude API error")
        message = ErrorHandler.handle_llm_pipeline_error(claude_error)
        assert "AI応答の生成に失敗" in message
        
        # 一般的なエラー
        general_error = Exception("Unknown error")
        message = ErrorHandler.handle_llm_pipeline_error(general_error)
        assert "予期しないエラー" in message


class TestPerformanceIntegration:
    """パフォーマンス統合テスト"""
    
    @pytest.fixture
    def performance_claude_service(self):
        """パフォーマンステスト用ClaudeService"""
        with patch('anthropic.Anthropic'):
            return ClaudeService(
                api_key="test-key",
                model="claude-3-haiku-20240307",  # 高速モデル
                timeout=5  # 短いタイムアウト
            )
    
    def test_response_time_performance(self, performance_claude_service):
        """レスポンス時間パフォーマンステスト"""
        mock_response = Mock()
        mock_response.content = "高速レスポンス"
        mock_response.usage_metadata = {"input_tokens": 50, "output_tokens": 20}
        
        with patch.object(performance_claude_service.llm_with_retry, 'invoke', return_value=mock_response):
            start_time = time.time()
            
            result = performance_claude_service.generate_response(
                "簡単な質問", 
                ["短いコンテキスト"]
            )
            
            end_time = time.time()
            
            # パフォーマンス検証
            processing_time = end_time - start_time
            assert processing_time < 1.0  # 1秒以内
            assert result.metadata["processing_time"] < 1.0
    
    def test_concurrent_requests_performance(self, performance_claude_service):
        """並行リクエストパフォーマンステスト"""
        mock_response = Mock()
        mock_response.content = "並行レスポンス"
        mock_response.usage_metadata = {"input_tokens": 30, "output_tokens": 15}
        
        async def async_test():
            with patch.object(performance_claude_service.llm_with_retry, 'ainvoke', AsyncMock(return_value=mock_response)):
                # 並行リクエスト実行
                tasks = []
                for i in range(5):
                    task = performance_claude_service.agenerate_response(f"質問{i}", [f"コンテキスト{i}"])
                    tasks.append(task)
                
                start_time = time.time()
                results = await asyncio.gather(*tasks)
                end_time = time.time()
                
                # 並行実行時間検証
                total_time = end_time - start_time
                assert total_time < 2.0  # 2秒以内で5つのリクエスト完了
                assert len(results) == 5
                assert all(isinstance(r, GenerationResult) for r in results)
        
        # 非同期テスト実行
        asyncio.run(async_test())
    
    def test_memory_usage_performance(self, performance_claude_service):
        """メモリ使用量パフォーマンステスト"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        mock_response = Mock()
        mock_response.content = "メモリテスト回答"
        mock_response.usage_metadata = {"input_tokens": 100, "output_tokens": 50}
        
        with patch.object(performance_claude_service.llm_with_retry, 'invoke', return_value=mock_response):
            # 大量リクエスト実行
            for i in range(50):
                performance_claude_service.generate_response(f"質問{i}", [f"コンテキスト{i}"])
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # メモリ使用量検証（50MB以下の増加）
        assert memory_increase < 50, f"メモリ使用量が{memory_increase}MB増加しました"
    
    def test_token_counting_performance(self, performance_claude_service):
        """トークン計算パフォーマンステスト"""
        # 大量テキストのトークン計算
        large_text = "これは大量のテキストです。" * 1000
        
        start_time = time.time()
        token_count = performance_claude_service._count_tokens(large_text)
        end_time = time.time()
        
        # トークン計算時間検証
        calculation_time = end_time - start_time
        assert calculation_time < 0.1  # 100ms以内
        assert token_count > 0
        assert isinstance(token_count, int)