"""
チャットインターフェースコンポーネントのテスト

TDD Red-Green-Refactorサイクルでチャット機能をテスト
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio
from datetime import datetime

from components.chat_interface import AdvancedChatInterface, chat_interface_component
from models.chat import ChatSession, ChatMessage, DocumentReference, MessageRole
from services.claude_llm import ClaudeService
from services.vector_store import VectorStore


class TestAdvancedChatInterface:
    """高度なチャットインターフェーステスト"""
    
    @pytest.fixture
    def mock_claude_service(self):
        """モックClaude サービス"""
        service = Mock(spec=ClaudeService)
        service.astream_response = AsyncMock()
        return service
    
    @pytest.fixture
    def mock_vector_store(self):
        """モックベクターストア"""
        store = Mock(spec=VectorStore)
        store.similarity_search = Mock(return_value=[])
        return store
    
    @pytest.fixture
    def chat_interface(self, mock_claude_service, mock_vector_store):
        """チャットインターフェースインスタンス"""
        return AdvancedChatInterface(mock_claude_service, mock_vector_store)
    
    @pytest.fixture
    def mock_session_state(self):
        """モックセッション状態"""
        return {
            "chat_session": ChatSession(),
            "chat_history": [],
            "streaming_response": None
        }
    
    def test_initialization(self, mock_claude_service, mock_vector_store):
        """初期化テスト"""
        interface = AdvancedChatInterface(mock_claude_service, mock_vector_store)
        
        assert interface.claude_service == mock_claude_service
        assert interface.vector_store == mock_vector_store
        assert interface.citation_display is not None
    
    @patch('components.chat_interface.st.session_state', new_callable=dict)
    def test_initialize_session_state(self, mock_session_state, chat_interface):
        """セッション状態初期化テスト"""
        chat_interface._initialize_session_state()
        
        assert "chat_session" in mock_session_state
        assert "chat_history" in mock_session_state
        assert "streaming_response" in mock_session_state
        assert isinstance(mock_session_state["chat_session"], ChatSession)
    
    @patch('components.chat_interface.st.session_state', new_callable=dict)
    @patch('streamlit.success')
    @patch('streamlit.rerun')
    def test_start_new_chat(self, mock_rerun, mock_success, mock_session_state, chat_interface):
        """新しいチャット開始テスト"""
        # 既存のセッションを設定
        old_session = ChatSession()
        old_session.add_message(ChatMessage(role=MessageRole.USER, content="古いメッセージ"))
        mock_session_state["chat_session"] = old_session
        
        chat_interface._start_new_chat()
        
        # 新しいセッションが作成されたことを確認
        new_session = mock_session_state["chat_session"]
        assert isinstance(new_session, ChatSession)
        assert new_session.get_message_count() == 0
        assert new_session != old_session
        
        # UIフィードバックが呼ばれたことを確認
        mock_success.assert_called_once_with("新しいチャットを開始しました")
        mock_rerun.assert_called_once()
    
    @patch('components.chat_interface.st.session_state', new_callable=dict)
    @patch('streamlit.success')
    @patch('streamlit.rerun')
    def test_clear_chat_history(self, mock_rerun, mock_success, mock_session_state, chat_interface):
        """チャット履歴クリアテスト"""
        # メッセージを含むセッションを設定
        session = ChatSession()
        session.add_message(ChatMessage(role=MessageRole.USER, content="テストメッセージ"))
        mock_session_state["chat_session"] = session
        
        assert session.get_message_count() == 1
        
        chat_interface._clear_chat_history()
        
        # メッセージがクリアされたことを確認
        assert session.get_message_count() == 0
        
        # UIフィードバックが呼ばれたことを確認
        mock_success.assert_called_once_with("チャット履歴をクリアしました")
        mock_rerun.assert_called_once()
    
    def test_create_document_references(self, chat_interface):
        """文書参照作成テスト"""
        # モック検索結果
        mock_result1 = Mock()
        mock_result1.page_content = "これは短いコンテンツです"
        mock_result1.metadata = {
            "filename": "test1.pdf",
            "page_number": 1,
            "chunk_id": "chunk-001"
        }
        mock_result1.similarity_score = 0.95
        
        mock_result2 = Mock()
        mock_result2.page_content = "これは非常に長いコンテンツです。" * 20  # 200文字超
        mock_result2.metadata = {
            "filename": "test2.pdf",
            "page_number": 5,
            "chunk_id": "chunk-002"
        }
        mock_result2.similarity_score = 0.87
        
        search_results = [mock_result1, mock_result2]
        
        references = chat_interface._create_document_references(search_results)
        
        # 2つの参照が作成されたことを確認
        assert len(references) == 2
        
        # 最初の参照を確認
        ref1 = references[0]
        assert ref1.filename == "test1.pdf"
        assert ref1.page_number == 1
        assert ref1.chunk_id == "chunk-001"
        assert ref1.similarity_score == 0.95
        assert ref1.excerpt == "これは短いコンテンツです"
        
        # 2番目の参照を確認（長いテキストが切り詰められる）
        ref2 = references[1]
        assert ref2.filename == "test2.pdf"
        assert ref2.page_number == 5
        assert ref2.similarity_score == 0.87
        assert len(ref2.excerpt) <= 203  # 200文字 + "..."
        assert ref2.excerpt.endswith("...")
    
    @patch('components.chat_interface.st.session_state', new_callable=dict)
    def test_prepare_chat_history(self, mock_session_state, chat_interface):
        """チャット履歴準備テスト"""
        # セッションに複数のメッセージを追加
        session = ChatSession()
        messages = [
            ChatMessage(role=MessageRole.USER, content=f"ユーザーメッセージ{i}")
            for i in range(10)
        ]
        
        for msg in messages:
            session.add_message(msg)
        
        mock_session_state["chat_session"] = session
        
        chat_history = chat_interface._prepare_chat_history()
        
        # 最新5つのメッセージから最後の1つを除いた4つが返されることを確認
        assert len(chat_history) == 4
        
        # Claudeサービス用のメッセージ形式になっていることを確認
        for i, msg in enumerate(chat_history):
            assert hasattr(msg, 'role')
            assert hasattr(msg, 'content')
            assert msg.role == "user"
            assert msg.content == f"ユーザーメッセージ{i + 5}"  # 5番目から8番目のメッセージ
    
    @patch('components.chat_interface.st.session_state', new_callable=dict)
    def test_prepare_chat_history_few_messages(self, mock_session_state, chat_interface):
        """少数メッセージでの履歴準備テスト"""
        session = ChatSession()
        session.add_message(ChatMessage(role=MessageRole.USER, content="メッセージ1"))
        session.add_message(ChatMessage(role=MessageRole.ASSISTANT, content="回答1"))
        
        mock_session_state["chat_session"] = session
        
        chat_history = chat_interface._prepare_chat_history()
        
        # 最後のメッセージを除いた1つが返される
        assert len(chat_history) == 1
        assert chat_history[0].content == "メッセージ1"
    
    @patch('components.chat_interface.st.session_state', new_callable=dict)
    @patch('streamlit.metric')
    @patch('streamlit.markdown')
    def test_display_chat_statistics(self, mock_markdown, mock_metric, mock_session_state, chat_interface):
        """チャット統計表示テスト"""
        # セッションにメッセージを追加
        session = ChatSession()
        session.add_message(ChatMessage(role=MessageRole.USER, content="ユーザー1"))
        session.add_message(ChatMessage(role=MessageRole.ASSISTANT, content="アシスタント1"))
        session.add_message(ChatMessage(role=MessageRole.USER, content="ユーザー2"))
        
        mock_session_state["chat_session"] = session
        
        chat_interface._display_chat_statistics()
        
        # 統計情報が表示されたことを確認
        assert mock_metric.call_count >= 3
        
        # メトリック呼び出しの確認
        metric_calls = [call[0] for call in mock_metric.call_args_list]
        assert ("メッセージ数", 3) in metric_calls
        assert ("ユーザーメッセージ", 2) in metric_calls
        assert ("アシスタントメッセージ", 1) in metric_calls
    
    def test_run_async_generator_success(self, chat_interface):
        """非同期ジェネレーター実行成功テスト"""
        # モック非同期ジェネレーター
        async def mock_async_gen():
            yield {"content": "chunk1"}
            yield {"content": "chunk2"}
            yield {"content": "chunk3"}
        
        loop = asyncio.new_event_loop()
        results = list(chat_interface._run_async_generator(mock_async_gen(), loop))
        loop.close()
        
        assert len(results) == 3
        assert results[0]["content"] == "chunk1"
        assert results[1]["content"] == "chunk2"
        assert results[2]["content"] == "chunk3"
    
    def test_run_async_generator_empty(self, chat_interface):
        """空の非同期ジェネレーター実行テスト"""
        async def empty_async_gen():
            return
            yield  # 到達しないコード
        
        loop = asyncio.new_event_loop()
        results = list(chat_interface._run_async_generator(empty_async_gen(), loop))
        loop.close()
        
        assert len(results) == 0
    
    def test_run_async_generator_error(self, chat_interface):
        """非同期ジェネレーターエラーテスト"""
        async def error_async_gen():
            yield {"content": "chunk1"}
            raise Exception("テストエラー")
        
        loop = asyncio.new_event_loop()
        
        with pytest.raises(Exception) as exc_info:
            list(chat_interface._run_async_generator(error_async_gen(), loop))
        
        loop.close()
        assert "テストエラー" in str(exc_info.value)


class TestLegacyChatInterface:
    """レガシーチャットインターフェーステスト"""
    
    @patch('components.chat_interface.st.session_state', new_callable=dict)
    @patch('streamlit.subheader')
    @patch('streamlit.chat_input')
    def test_chat_interface_component_no_input(self, mock_chat_input, mock_subheader, mock_session_state):
        """入力なしのチャットインターフェーステスト"""
        mock_chat_input.return_value = None
        
        result = chat_interface_component()
        
        assert result is None
        mock_subheader.assert_called_once_with("💬 文書検索チャット")
        assert "chat_history" in mock_session_state
        assert mock_session_state["chat_history"] == []
    
    @patch('components.chat_interface.st.session_state', new_callable=dict)
    @patch('streamlit.subheader')
    @patch('streamlit.chat_input')
    @patch('streamlit.chat_message')
    def test_chat_interface_component_with_input(self, mock_chat_message, mock_chat_input, mock_subheader, mock_session_state):
        """入力ありのチャットインターフェーステスト"""
        user_input = "テスト質問"
        mock_chat_input.return_value = user_input
        
        # チャットメッセージのモック設定
        mock_chat_message.return_value.__enter__ = Mock()
        mock_chat_message.return_value.__exit__ = Mock(return_value=None)
        
        result = chat_interface_component()
        
        assert result == user_input
        assert len(mock_session_state["chat_history"]) == 1
        assert mock_session_state["chat_history"][0] == {
            "role": "user",
            "content": user_input
        }
    
    @patch('components.chat_interface.st.session_state', new_callable=dict)
    @patch('streamlit.subheader')
    @patch('streamlit.chat_input')
    @patch('streamlit.chat_message')
    @patch('streamlit.markdown')
    @patch('streamlit.expander')
    def test_chat_interface_component_with_history(self, mock_expander, mock_markdown, mock_chat_message, mock_chat_input, mock_subheader, mock_session_state):
        """履歴ありのチャットインターフェーステスト"""
        # 既存の履歴を設定
        mock_session_state["chat_history"] = [
            {"role": "user", "content": "過去の質問"},
            {"role": "assistant", "content": "過去の回答", "sources": ["source1.pdf", "source2.pdf"]}
        ]
        
        mock_chat_input.return_value = None
        
        # モック設定
        mock_chat_message.return_value.__enter__ = Mock()
        mock_chat_message.return_value.__exit__ = Mock(return_value=None)
        mock_expander.return_value.__enter__ = Mock()
        mock_expander.return_value.__exit__ = Mock(return_value=None)
        
        result = chat_interface_component()
        
        assert result is None
        
        # チャット履歴が表示されたことを確認
        assert mock_chat_message.call_count == 2  # user + assistant
        assert mock_markdown.call_count >= 2  # 各メッセージの内容
        mock_expander.assert_called_once_with("📚 参考文書")


class TestChatInterfaceIntegration:
    """チャットインターフェース統合テスト"""
    
    @pytest.fixture
    def mock_services(self):
        """統合テスト用のモックサービス"""
        claude_service = Mock(spec=ClaudeService)
        vector_store = Mock(spec=VectorStore)
        
        # 非同期ストリーミングのモック
        async def mock_astream():
            yield {"content": "テスト"}
            yield {"content": "レスポンス"}
        
        claude_service.astream_response = AsyncMock(return_value=mock_astream())
        
        # ベクター検索のモック
        mock_result = Mock()
        mock_result.page_content = "テストコンテンツ"
        mock_result.metadata = {"filename": "test.pdf", "page_number": 1}
        vector_store.similarity_search = Mock(return_value=[mock_result])
        
        return claude_service, vector_store
    
    @patch('components.chat_interface.st.session_state', new_callable=dict)
    def test_full_chat_flow_integration(self, mock_session_state, mock_services):
        """完全なチャットフロー統合テスト"""
        claude_service, vector_store = mock_services
        interface = AdvancedChatInterface(claude_service, vector_store)
        
        # セッション状態初期化
        interface._initialize_session_state()
        
        # 文書参照作成テスト
        mock_result = Mock()
        mock_result.page_content = "統合テストコンテンツ"
        mock_result.metadata = {"filename": "integration.pdf", "page_number": 10}
        mock_result.similarity_score = 0.9
        
        references = interface._create_document_references([mock_result])
        
        assert len(references) == 1
        assert references[0].filename == "integration.pdf"
        assert references[0].similarity_score == 0.9
        
        # チャット履歴準備テスト
        session = mock_session_state["chat_session"]
        session.add_message(ChatMessage(role=MessageRole.USER, content="統合テスト質問"))
        
        chat_history = interface._prepare_chat_history()
        assert len(chat_history) == 0  # 最新メッセージは除外される
    
    def test_error_handling_integration(self, mock_services):
        """エラーハンドリング統合テスト"""
        claude_service, vector_store = mock_services
        interface = AdvancedChatInterface(claude_service, vector_store)
        
        # ベクター検索エラーをシミュレート
        vector_store.similarity_search.side_effect = Exception("検索エラー")
        
        # エラーが適切に処理されることを確認
        with pytest.raises(Exception):
            vector_store.similarity_search("テスト")
        
        # Claude APIエラーをシミュレート
        claude_service.astream_response.side_effect = Exception("Claude API エラー")
        
        # エラーが適切に処理されることを確認
        with pytest.raises(Exception):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(claude_service.astream_response("test", [], []))
            loop.close()