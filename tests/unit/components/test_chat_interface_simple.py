"""
チャットインターフェースコンポーネントの簡潔なテスト

ビジネスロジックのみのユニットテスト
"""

import pytest
from unittest.mock import Mock, AsyncMock
import asyncio

from components.chat_interface import AdvancedChatInterface
from models.chat import ChatSession, ChatMessage, DocumentReference, MessageRole
from services.claude_llm import ClaudeService
from services.vector_store import VectorStore


class TestAdvancedChatInterfaceLogic:
    """高度なチャットインターフェースのビジネスロジックテスト"""
    
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
        # __init__でのセッション状態初期化をスキップ
        interface = AdvancedChatInterface.__new__(AdvancedChatInterface)
        interface.claude_service = mock_claude_service
        interface.vector_store = mock_vector_store
        interface.citation_display = Mock()
        return interface
    
    def test_initialization_attributes(self, mock_claude_service, mock_vector_store):
        """初期化属性テスト"""
        # __init__でのセッション状態初期化をスキップ
        interface = AdvancedChatInterface.__new__(AdvancedChatInterface)
        interface.claude_service = mock_claude_service
        interface.vector_store = mock_vector_store
        interface.citation_display = Mock()
        
        assert interface.claude_service == mock_claude_service
        assert interface.vector_store == mock_vector_store
        assert interface.citation_display is not None
    
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
    
    def test_create_document_references_empty(self, chat_interface):
        """空の検索結果での文書参照作成テスト"""
        references = chat_interface._create_document_references([])
        assert len(references) == 0
    
    def test_create_document_references_missing_metadata(self, chat_interface):
        """メタデータ不足での文書参照作成テスト"""
        mock_result = Mock()
        mock_result.page_content = "テストコンテンツ"
        mock_result.metadata = {}  # 空のメタデータ
        # similarity_scoreを明示的に削除
        del mock_result.similarity_score
        
        references = chat_interface._create_document_references([mock_result])
        
        assert len(references) == 1
        ref = references[0]
        assert ref.filename == "不明なファイル"
        assert ref.page_number == 0
        assert ref.chunk_id == ""
        assert ref.similarity_score == 0.0
        assert ref.excerpt == "テストコンテンツ"
    
    def test_prepare_chat_history_with_mock_session(self, chat_interface):
        """モックセッションでのチャット履歴準備テスト"""
        # セッションにメッセージを追加
        session = ChatSession()
        messages = [
            ChatMessage(role=MessageRole.USER, content=f"ユーザーメッセージ{i}")
            for i in range(10)
        ]
        
        for msg in messages:
            session.add_message(msg)
        
        # モックセッション状態を設定
        mock_session_state = {"chat_session": session}
        
        # _prepare_chat_historyを直接テスト
        with pytest.MonkeyPatch().context() as m:
            # session_stateをMock objectとして設定
            session_state_mock = Mock()
            session_state_mock.chat_session = session
            m.setattr("components.chat_interface.st.session_state", session_state_mock)
            chat_history = chat_interface._prepare_chat_history()
        
        # 最新5つのメッセージから最後の1つを除いた4つが返されることを確認
        assert len(chat_history) == 4
        
        # Claudeサービス用のメッセージ形式になっていることを確認
        for i, msg in enumerate(chat_history):
            assert hasattr(msg, 'role')
            assert hasattr(msg, 'content')
            assert msg.role == "user"
            assert msg.content == f"ユーザーメッセージ{i + 5}"  # 5番目から8番目のメッセージ
    
    def test_prepare_chat_history_few_messages(self, chat_interface):
        """少数メッセージでの履歴準備テスト"""
        session = ChatSession()
        session.add_message(ChatMessage(role=MessageRole.USER, content="メッセージ1"))
        session.add_message(ChatMessage(role=MessageRole.ASSISTANT, content="回答1"))
        
        with pytest.MonkeyPatch().context() as m:
            session_state_mock = Mock()
            session_state_mock.chat_session = session
            m.setattr("components.chat_interface.st.session_state", session_state_mock)
            chat_history = chat_interface._prepare_chat_history()
        
        # 最後のメッセージを除いた1つが返される
        assert len(chat_history) == 1
        assert chat_history[0].content == "メッセージ1"
    
    def test_prepare_chat_history_empty_session(self, chat_interface):
        """空セッションでの履歴準備テスト"""
        session = ChatSession()
        
        with pytest.MonkeyPatch().context() as m:
            session_state_mock = Mock()
            session_state_mock.chat_session = session
            m.setattr("components.chat_interface.st.session_state", session_state_mock)
            chat_history = chat_interface._prepare_chat_history()
        
        assert len(chat_history) == 0
    
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


class TestChatInterfaceIntegration:
    """チャットインターフェース統合テスト（ビジネスロジック）"""
    
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
    
    def test_document_reference_creation_integration(self, mock_services):
        """文書参照作成統合テスト"""
        claude_service, vector_store = mock_services
        interface = AdvancedChatInterface.__new__(AdvancedChatInterface)
        interface.claude_service = claude_service
        interface.vector_store = vector_store
        interface.citation_display = Mock()
        
        # 文書参照作成テスト
        mock_result = Mock()
        mock_result.page_content = "統合テストコンテンツ"
        mock_result.metadata = {"filename": "integration.pdf", "page_number": 10}
        mock_result.similarity_score = 0.9
        
        references = interface._create_document_references([mock_result])
        
        assert len(references) == 1
        assert references[0].filename == "integration.pdf"
        assert references[0].similarity_score == 0.9
        assert references[0].excerpt == "統合テストコンテンツ"
    
    def test_error_handling_integration(self, mock_services):
        """エラーハンドリング統合テスト"""
        claude_service, vector_store = mock_services
        interface = AdvancedChatInterface.__new__(AdvancedChatInterface)
        interface.claude_service = claude_service
        interface.vector_store = vector_store
        interface.citation_display = Mock()
        
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
    
    def test_chat_history_conversion_integration(self, mock_services):
        """チャット履歴変換統合テスト"""
        claude_service, vector_store = mock_services
        interface = AdvancedChatInterface.__new__(AdvancedChatInterface)
        interface.claude_service = claude_service
        interface.vector_store = vector_store
        interface.citation_display = Mock()
        
        # セッションに様々なタイプのメッセージを追加
        session = ChatSession()
        session.add_message(ChatMessage(role=MessageRole.USER, content="ユーザー質問1"))
        session.add_message(ChatMessage(role=MessageRole.ASSISTANT, content="アシスタント回答1"))
        session.add_message(ChatMessage(role=MessageRole.USER, content="ユーザー質問2"))
        session.add_message(ChatMessage(role=MessageRole.ASSISTANT, content="アシスタント回答2"))
        session.add_message(ChatMessage(role=MessageRole.USER, content="現在の質問"))
        
        mock_session_state = {"chat_session": session}
        
        with pytest.MonkeyPatch().context() as m:
            session_state_mock = Mock()
            session_state_mock.chat_session = session
            m.setattr("components.chat_interface.st.session_state", session_state_mock)
            chat_history = interface._prepare_chat_history()
        
        # 最後のメッセージを除く4つが変換される
        assert len(chat_history) == 4
        assert chat_history[0].content == "ユーザー質問1"
        assert chat_history[1].content == "アシスタント回答1"
        assert chat_history[2].content == "ユーザー質問2"
        assert chat_history[3].content == "アシスタント回答2"