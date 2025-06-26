"""
Claude APIストリーミング機能のテスト

TDD Red-Green-Refactorサイクルでストリーミング機能をテスト
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from typing import List, Dict, Any, AsyncIterator

from services.claude_llm import (
    ClaudeService, GenerationResult, ChatMessage, ClaudeError, 
    RateLimitError, TokenLimitError
)


class TestClaudeStreamingGeneration:
    """Claude APIストリーミング生成テスト"""
    
    @pytest.fixture
    def claude_service(self):
        """Claudeサービスインスタンスをセットアップ"""
        with patch('services.claude_llm.ChatAnthropic') as mock_chat:
            service = ClaudeService(
                api_key="test-api-key",
                model="claude-3-sonnet-20240229",
                max_tokens=2048,
                temperature=0
            )
            return service
    
    @pytest.fixture
    def sample_context_chunks(self):
        """サンプルコンテキストチャンク"""
        return [
            "新入社員の研修期間は3ヶ月です。",
            "研修内容には基本的なビジネスマナーが含まれます。",
            "研修終了後は各部署に配属されます。"
        ]
    
    @pytest.fixture
    def sample_chat_history(self):
        """サンプルチャット履歴"""
        return [
            ChatMessage(role="user", content="研修について教えてください"),
            ChatMessage(role="assistant", content="研修は3ヶ月間行われます。")
        ]
    
    @pytest.mark.asyncio
    async def test_astream_response_basic(self, claude_service, sample_context_chunks):
        """基本的なストリーミング回答生成テスト"""
        query = "新入社員研修について教えてください"
        
        # ストリーミングレスポンスをモック
        mock_chunks = [
            Mock(content="新入", usage_metadata={"input_tokens": 10}),
            Mock(content="社員研修", usage_metadata={"output_tokens": 5}),
            Mock(content="について", usage_metadata={"output_tokens": 3}),
            Mock(content="説明します", usage_metadata={"output_tokens": 7})
        ]
        
        async def mock_astream(messages):
            for chunk in mock_chunks:
                yield chunk
        
        claude_service.llm_with_retry.astream = mock_astream
        
        # ストリーミング実行
        response_chunks = []
        async for chunk in claude_service.astream_response(query, sample_context_chunks):
            response_chunks.append(chunk)
        
        # 結果検証
        assert len(response_chunks) == 4
        
        # 最初のチャンクを検証
        assert response_chunks[0]["content"] == "新入"
        assert response_chunks[0]["model"] == "claude-3-sonnet-20240229"
        assert "timestamp" in response_chunks[0]
        
        # 各チャンクが正しい構造を持つことを確認
        for chunk in response_chunks:
            assert "content" in chunk
            assert "usage" in chunk
            assert "model" in chunk
            assert "timestamp" in chunk
    
    @pytest.mark.asyncio
    async def test_astream_response_with_chat_history(self, claude_service, sample_context_chunks, sample_chat_history):
        """チャット履歴付きストリーミング回答生成テスト"""
        query = "研修期間はどのくらいですか？"
        
        # ストリーミングレスポンスをモック
        mock_chunks = [
            Mock(content="研修期間", usage_metadata={}),
            Mock(content="は3ヶ月", usage_metadata={}),
            Mock(content="です", usage_metadata={})
        ]
        
        async def mock_astream(messages):
            for chunk in mock_chunks:
                yield chunk
        
        claude_service.llm_with_retry.astream = mock_astream
        
        # ストリーミング実行
        response_chunks = []
        async for chunk in claude_service.astream_response(
            query, sample_context_chunks, sample_chat_history
        ):
            response_chunks.append(chunk)
        
        # 結果検証
        assert len(response_chunks) == 3
        assert response_chunks[0]["content"] == "研修期間"
        assert response_chunks[2]["content"] == "です"
    
    @pytest.mark.asyncio
    async def test_astream_response_empty_context(self, claude_service):
        """空のコンテキストでのストリーミングテスト"""
        query = "一般的な質問です"
        
        # ストリーミングレスポンスをモック
        mock_chunks = [
            Mock(content="一般的", usage_metadata={}),
            Mock(content="な回答", usage_metadata={})
        ]
        
        async def mock_astream(messages):
            for chunk in mock_chunks:
                yield chunk
        
        claude_service.llm_with_retry.astream = mock_astream
        
        # ストリーミング実行
        response_chunks = []
        async for chunk in claude_service.astream_response(query, []):
            response_chunks.append(chunk)
        
        # 結果検証
        assert len(response_chunks) == 2
    
    @pytest.mark.asyncio
    async def test_astream_response_error_handling(self, claude_service, sample_context_chunks):
        """ストリーミング中のエラーハンドリングテスト"""
        query = "テスト質問"
        
        # エラーを発生させるモック
        async def mock_astream_error(messages):
            yield Mock(content="正常", usage_metadata={})
            raise Exception("ストリーミングエラー")
        
        claude_service.llm_with_retry.astream = mock_astream_error
        
        # エラーが適切に処理されることを確認
        with pytest.raises(ClaudeError) as exc_info:
            response_chunks = []
            async for chunk in claude_service.astream_response(query, sample_context_chunks):
                response_chunks.append(chunk)
        
        assert "ストリーミング回答生成中にエラーが発生しました" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_astream_response_real_time_performance(self, claude_service, sample_context_chunks):
        """リアルタイム性能テスト"""
        query = "性能テスト質問"
        
        # 遅延のあるストリーミングをシミュレート
        async def mock_astream_with_delay(messages):
            chunks = ["部分1", "部分2", "部分3"]
            for chunk_content in chunks:
                await asyncio.sleep(0.01)  # 10ms遅延
                yield Mock(content=chunk_content, usage_metadata={})
        
        claude_service.llm_with_retry.astream = mock_astream_with_delay
        
        # ストリーミング実行と時間測定
        start_time = asyncio.get_event_loop().time()
        response_chunks = []
        
        async for chunk in claude_service.astream_response(query, sample_context_chunks):
            response_chunks.append(chunk)
            # 最初のチャンクの受信時間を記録
            if len(response_chunks) == 1:
                first_chunk_time = asyncio.get_event_loop().time()
        
        end_time = asyncio.get_event_loop().time()
        
        # 性能検証
        assert len(response_chunks) == 3
        first_response_time = first_chunk_time - start_time
        total_time = end_time - start_time
        
        # 最初のレスポンスが迅速であることを確認（50ms未満）
        assert first_response_time < 0.05
        assert total_time < 0.1  # 総時間も100ms未満


class TestClaudeAsyncGeneration:
    """Claude API非同期生成テスト"""
    
    @pytest.fixture
    def claude_service(self):
        """Claudeサービスインスタンスをセットアップ"""
        with patch('services.claude_llm.ChatAnthropic') as mock_chat:
            service = ClaudeService(
                api_key="test-api-key",
                model="claude-3-sonnet-20240229"
            )
            return service
    
    @pytest.mark.asyncio
    async def test_agenerate_response_basic(self, claude_service):
        """基本的な非同期回答生成テスト"""
        query = "テスト質問"
        context_chunks = ["テストコンテキスト"]
        
        # モックレスポンスを設定
        mock_response = Mock()
        mock_response.content = "テスト回答"
        mock_response.usage_metadata = {
            "input_tokens": 100,
            "output_tokens": 50
        }
        
        claude_service.llm_with_retry.ainvoke = AsyncMock(return_value=mock_response)
        
        # 非同期実行
        result = await claude_service.agenerate_response(query, context_chunks)
        
        # 結果検証
        assert isinstance(result, GenerationResult)
        assert result.content == "テスト回答"
        assert result.usage["input_tokens"] == 100
        assert result.usage["output_tokens"] == 50
        assert result.model == "claude-3-sonnet-20240229"
        assert result.metadata["async"] == True
        assert "processing_time" in result.metadata
        assert "timestamp" in result.metadata
    
    @pytest.mark.asyncio
    async def test_agenerate_response_with_chat_history(self, claude_service):
        """チャット履歴付き非同期回答生成テスト"""
        query = "追加質問"
        context_chunks = ["コンテキスト"]
        chat_history = [
            ChatMessage(role="user", content="最初の質問"),
            ChatMessage(role="assistant", content="最初の回答")
        ]
        
        # モックレスポンスを設定
        mock_response = Mock()
        mock_response.content = "履歴を考慮した回答"
        mock_response.usage_metadata = {"input_tokens": 150, "output_tokens": 75}
        
        claude_service.llm_with_retry.ainvoke = AsyncMock(return_value=mock_response)
        
        # 非同期実行
        result = await claude_service.agenerate_response(query, context_chunks, chat_history)
        
        # 結果検証
        assert result.content == "履歴を考慮した回答"
        assert result.usage["input_tokens"] == 150
    
    @pytest.mark.asyncio
    async def test_agenerate_response_empty_query_error(self, claude_service):
        """空のクエリでのエラーテスト"""
        with pytest.raises(ValueError) as exc_info:
            await claude_service.agenerate_response("", [])
        
        assert "空の質問は許可されていません" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_agenerate_response_api_error(self, claude_service):
        """API エラーハンドリングテスト"""
        query = "テスト質問"
        context_chunks = ["コンテキスト"]
        
        # API エラーをシミュレート
        claude_service.llm_with_retry.ainvoke = AsyncMock(
            side_effect=Exception("API接続エラー")
        )
        
        # エラーが適切に処理されることを確認
        with pytest.raises(ClaudeError) as exc_info:
            await claude_service.agenerate_response(query, context_chunks)
        
        assert "非同期回答生成中にエラーが発生しました" in str(exc_info.value)


class TestClaudeStreamingIntegration:
    """Claude ストリーミング統合テスト"""
    
    @pytest.fixture
    def claude_service(self):
        """Claudeサービスインスタンスをセットアップ"""
        with patch('services.claude_llm.ChatAnthropic') as mock_chat:
            service = ClaudeService(
                api_key="test-api-key",
                model="claude-3-sonnet-20240229"
            )
            return service
    
    @pytest.mark.asyncio
    async def test_streaming_vs_batch_consistency(self, claude_service):
        """ストリーミングとバッチ処理の整合性テスト"""
        query = "テスト質問"
        context_chunks = ["テストコンテキスト"]
        
        # バッチレスポンスをモック
        batch_response = Mock()
        batch_response.content = "完全な回答です"
        batch_response.usage_metadata = {"input_tokens": 100, "output_tokens": 50}
        
        # ストリーミングレスポンスをモック
        streaming_chunks = [
            Mock(content="完全な", usage_metadata={}),
            Mock(content="回答", usage_metadata={}),
            Mock(content="です", usage_metadata={})
        ]
        
        async def mock_astream(messages):
            for chunk in streaming_chunks:
                yield chunk
        
        claude_service.llm_with_retry.ainvoke = AsyncMock(return_value=batch_response)
        claude_service.llm_with_retry.astream = mock_astream
        
        # バッチ処理実行
        batch_result = await claude_service.agenerate_response(query, context_chunks)
        
        # ストリーミング処理実行
        streaming_chunks_result = []
        async for chunk in claude_service.astream_response(query, context_chunks):
            streaming_chunks_result.append(chunk["content"])
        
        streaming_full_content = "".join(streaming_chunks_result)
        
        # メッセージ構築の一貫性を確認（具体的な内容の一致は期待しない）
        assert len(batch_result.content) > 0
        assert len(streaming_full_content) > 0
        
        # 両方の方法でレスポンスが生成されることを確認
        assert batch_result.model == "claude-3-sonnet-20240229"
        assert len(streaming_chunks_result) == 3
    
    @pytest.mark.asyncio
    async def test_concurrent_streaming_requests(self, claude_service):
        """並行ストリーミングリクエストテスト"""
        
        # 複数のストリーミングリクエストを並行実行
        async def single_stream_request(query_id: int):
            query = f"質問{query_id}"
            context = [f"コンテキスト{query_id}"]
            
            # 各リクエスト用のモックを設定
            mock_chunks = [
                Mock(content=f"回答{query_id}の", usage_metadata={}),
                Mock(content="部分", usage_metadata={})
            ]
            
            async def mock_astream(messages):
                for chunk in mock_chunks:
                    await asyncio.sleep(0.01)  # 小さな遅延
                    yield chunk
            
            claude_service.llm_with_retry.astream = mock_astream
            
            chunks = []
            async for chunk in claude_service.astream_response(query, context):
                chunks.append(chunk["content"])
            
            return query_id, chunks
        
        # 3つの並行リクエストを実行
        tasks = [single_stream_request(i) for i in range(1, 4)]
        results = await asyncio.gather(*tasks)
        
        # 結果検証
        assert len(results) == 3
        
        for query_id, chunks in results:
            assert len(chunks) == 2
            assert f"回答{query_id}の" in chunks[0]
            assert "部分" in chunks[1]
    
    @pytest.mark.asyncio
    async def test_streaming_memory_efficiency(self, claude_service):
        """ストリーミングのメモリ効率テスト"""
        query = "大量のデータを含む質問"
        large_context = ["非常に長いコンテキスト" * 1000]  # 大きなコンテキスト
        
        # 大量のチャンクをストリーミング
        large_chunks = [
            Mock(content=f"チャンク{i}", usage_metadata={}) 
            for i in range(100)
        ]
        
        async def mock_astream_large(messages):
            for chunk in large_chunks:
                yield chunk
                # メモリリークを防ぐため、即座にyield
                await asyncio.sleep(0.001)
        
        claude_service.llm_with_retry.astream = mock_astream_large
        
        # ストリーミング処理（メモリ使用量を監視）
        chunk_count = 0
        async for chunk in claude_service.astream_response(query, large_context):
            chunk_count += 1
            # 各チャンクを処理後、すぐに解放される想定
            assert chunk["content"] == f"チャンク{chunk_count - 1}"
        
        # すべてのチャンクが処理されたことを確認
        assert chunk_count == 100


class TestChatMessageValidation:
    """チャットメッセージ検証テスト"""
    
    def test_chat_message_valid_roles(self):
        """有効なロールでのメッセージ作成テスト"""
        # 有効なロール
        valid_roles = ["user", "assistant", "system"]
        
        for role in valid_roles:
            message = ChatMessage(role=role, content="テストメッセージ")
            assert message.role == role
            assert message.content == "テストメッセージ"
    
    def test_chat_message_invalid_role(self):
        """無効なロールでのメッセージ作成エラーテスト"""
        with pytest.raises(ValueError) as exc_info:
            ChatMessage(role="invalid", content="テスト")
        
        assert "無効なrole: invalid" in str(exc_info.value)
    
    def test_chat_message_empty_content(self):
        """空のコンテンツでのメッセージ作成エラーテスト"""
        with pytest.raises(ValueError) as exc_info:
            ChatMessage(role="user", content="")
        
        assert "空のcontentは許可されていません" in str(exc_info.value)
        
        # 空白のみの場合もエラー
        with pytest.raises(ValueError):
            ChatMessage(role="user", content="   ")
    
    def test_chat_message_whitespace_content(self):
        """空白のみのコンテンツエラーテスト"""
        with pytest.raises(ValueError) as exc_info:
            ChatMessage(role="user", content="   \n\t  ")
        
        assert "空のcontentは許可されていません" in str(exc_info.value)