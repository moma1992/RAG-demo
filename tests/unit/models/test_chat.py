"""
チャットモデルのテスト

TDD Red-Green-Refactorサイクルでチャット機能をテスト
"""

import pytest
from datetime import datetime, timedelta
from models.chat import (
    ChatMessage, ChatSession, ChatHistory, DocumentReference, MessageRole
)


class TestDocumentReference:
    """文書参照テスト"""
    
    def test_document_reference_creation(self):
        """文書参照作成テスト"""
        ref = DocumentReference(
            filename="test.pdf",
            page_number=1,
            chunk_id="chunk-123",
            similarity_score=0.95,
            excerpt="テストテキスト"
        )
        
        assert ref.filename == "test.pdf"
        assert ref.page_number == 1
        assert ref.chunk_id == "chunk-123"
        assert ref.similarity_score == 0.95
        assert ref.excerpt == "テストテキスト"


class TestChatMessage:
    """チャットメッセージテスト"""
    
    def test_message_creation_with_defaults(self):
        """デフォルト値でのメッセージ作成テスト"""
        message = ChatMessage(content="テストメッセージ")
        
        assert message.content == "テストメッセージ"
        assert message.role == MessageRole.USER
        assert isinstance(message.id, str)
        assert isinstance(message.timestamp, datetime)
        assert message.references == []
        assert message.metadata == {}
    
    def test_message_creation_with_custom_values(self):
        """カスタム値でのメッセージ作成テスト"""
        custom_time = datetime.now() - timedelta(hours=1)
        message = ChatMessage(
            content="アシスタントメッセージ",
            role=MessageRole.ASSISTANT,
            timestamp=custom_time
        )
        
        assert message.content == "アシスタントメッセージ"
        assert message.role == MessageRole.ASSISTANT
        assert message.timestamp == custom_time
    
    def test_add_reference(self):
        """文書参照追加テスト"""
        message = ChatMessage(content="テスト")
        ref = DocumentReference(
            filename="doc.pdf",
            page_number=2,
            chunk_id="chunk-456",
            similarity_score=0.85,
            excerpt="参照テキスト"
        )
        
        message.add_reference(ref)
        
        assert len(message.references) == 1
        assert message.references[0] == ref
    
    def test_get_referenced_files(self):
        """参照ファイル一覧取得テスト"""
        message = ChatMessage(content="テスト")
        
        # 複数の参照を追加（重複あり）
        refs = [
            DocumentReference("file1.pdf", 1, "chunk1", 0.9, "text1"),
            DocumentReference("file2.pdf", 2, "chunk2", 0.8, "text2"),
            DocumentReference("file1.pdf", 3, "chunk3", 0.7, "text3"),  # 重複
        ]
        
        for ref in refs:
            message.add_reference(ref)
        
        files = message.get_referenced_files()
        assert len(files) == 2  # 重複除去
        assert "file1.pdf" in files
        assert "file2.pdf" in files


class TestChatSession:
    """チャットセッションテスト"""
    
    def test_session_creation_with_defaults(self):
        """デフォルト値でのセッション作成テスト"""
        session = ChatSession()
        
        assert isinstance(session.id, str)
        assert session.title == "新しいチャット"
        assert session.messages == []
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)
        assert session.metadata == {}
    
    def test_session_creation_with_custom_title(self):
        """カスタムタイトルでのセッション作成テスト"""
        session = ChatSession(title="カスタムタイトル")
        
        assert session.title == "カスタムタイトル"
    
    def test_add_message_updates_timestamp(self):
        """メッセージ追加時のタイムスタンプ更新テスト"""
        session = ChatSession()
        initial_updated_at = session.updated_at
        
        # 少し待ってからメッセージ追加
        import time
        time.sleep(0.001)
        
        message = ChatMessage(content="テスト")
        session.add_message(message)
        
        assert session.updated_at > initial_updated_at
        assert len(session.messages) == 1
        assert session.messages[0] == message
    
    def test_title_auto_update_from_first_user_message(self):
        """最初のユーザーメッセージからタイトル自動更新テスト"""
        session = ChatSession()
        
        # 最初のユーザーメッセージ
        user_message = ChatMessage(
            content="これは長いメッセージです。50文字を超える場合、省略されるはずです。",
            role=MessageRole.USER
        )
        session.add_message(user_message)
        
        # タイトルが更新され、50文字で切り詰められることを確認
        content = "これは長いメッセージです。50文字を超える場合、省略されるはずです。"
        expected_title = content[:50] + ("..." if len(content) > 50 else "")
        assert session.title == expected_title
    
    def test_title_not_updated_from_assistant_message(self):
        """アシスタントメッセージではタイトル更新されないテスト"""
        session = ChatSession()
        
        assistant_message = ChatMessage(
            content="アシスタントの回答",
            role=MessageRole.ASSISTANT
        )
        session.add_message(assistant_message)
        
        # タイトルは変更されない
        assert session.title == "新しいチャット"
    
    def test_get_message_count(self):
        """メッセージ数取得テスト"""
        session = ChatSession()
        assert session.get_message_count() == 0
        
        session.add_message(ChatMessage(content="メッセージ1"))
        assert session.get_message_count() == 1
        
        session.add_message(ChatMessage(content="メッセージ2"))
        assert session.get_message_count() == 2
    
    def test_get_last_message(self):
        """最後のメッセージ取得テスト"""
        session = ChatSession()
        
        # メッセージがない場合
        assert session.get_last_message() is None
        
        # メッセージを追加
        message1 = ChatMessage(content="最初のメッセージ")
        message2 = ChatMessage(content="最後のメッセージ")
        session.add_message(message1)
        session.add_message(message2)
        
        assert session.get_last_message() == message2
    
    def test_get_user_messages(self):
        """ユーザーメッセージのみ取得テスト"""
        session = ChatSession()
        
        user_msg1 = ChatMessage(content="ユーザー1", role=MessageRole.USER)
        assistant_msg = ChatMessage(content="アシスタント", role=MessageRole.ASSISTANT)
        user_msg2 = ChatMessage(content="ユーザー2", role=MessageRole.USER)
        
        session.add_message(user_msg1)
        session.add_message(assistant_msg)
        session.add_message(user_msg2)
        
        user_messages = session.get_user_messages()
        assert len(user_messages) == 2
        assert user_msg1 in user_messages
        assert user_msg2 in user_messages
        assert assistant_msg not in user_messages
    
    def test_get_assistant_messages(self):
        """アシスタントメッセージのみ取得テスト"""
        session = ChatSession()
        
        user_msg = ChatMessage(content="ユーザー", role=MessageRole.USER)
        assistant_msg1 = ChatMessage(content="アシスタント1", role=MessageRole.ASSISTANT)
        assistant_msg2 = ChatMessage(content="アシスタント2", role=MessageRole.ASSISTANT)
        
        session.add_message(user_msg)
        session.add_message(assistant_msg1)
        session.add_message(assistant_msg2)
        
        assistant_messages = session.get_assistant_messages()
        assert len(assistant_messages) == 2
        assert assistant_msg1 in assistant_messages
        assert assistant_msg2 in assistant_messages
        assert user_msg not in assistant_messages
    
    def test_clear_messages(self):
        """メッセージクリアテスト"""
        session = ChatSession()
        
        session.add_message(ChatMessage(content="メッセージ1"))
        session.add_message(ChatMessage(content="メッセージ2"))
        assert session.get_message_count() == 2
        
        initial_updated_at = session.updated_at
        import time
        time.sleep(0.001)
        
        session.clear_messages()
        
        assert session.get_message_count() == 0
        assert session.updated_at > initial_updated_at


class TestChatHistory:
    """チャット履歴テスト"""
    
    def test_history_creation_with_defaults(self):
        """デフォルト値での履歴作成テスト"""
        history = ChatHistory()
        
        assert history.sessions == []
        assert history.current_session_id is None
    
    def test_create_new_session(self):
        """新しいセッション作成テスト"""
        history = ChatHistory()
        
        session = history.create_new_session("テストセッション")
        
        assert len(history.sessions) == 1
        assert history.sessions[0] == session
        assert history.current_session_id == session.id
        assert session.title == "テストセッション"
    
    def test_create_new_session_with_default_title(self):
        """デフォルトタイトルでの新しいセッション作成テスト"""
        history = ChatHistory()
        
        session = history.create_new_session()
        
        assert session.title == "新しいチャット"
    
    def test_get_current_session(self):
        """現在のセッション取得テスト"""
        history = ChatHistory()
        
        # セッションがない場合
        assert history.get_current_session() is None
        
        # セッション作成後
        session = history.create_new_session()
        current = history.get_current_session()
        
        assert current == session
    
    def test_get_session_by_id(self):
        """IDでのセッション取得テスト"""
        history = ChatHistory()
        
        session1 = history.create_new_session("セッション1")
        session2 = history.create_new_session("セッション2")
        
        # 正しいIDで取得
        found = history.get_session_by_id(session1.id)
        assert found == session1
        
        # 存在しないIDで取得
        not_found = history.get_session_by_id("存在しないID")
        assert not_found is None
    
    def test_delete_session(self):
        """セッション削除テスト"""
        history = ChatHistory()
        
        session1 = history.create_new_session("セッション1")
        session2 = history.create_new_session("セッション2")
        
        # 現在のセッションを削除
        result = history.delete_session(session2.id)
        
        assert result is True
        assert len(history.sessions) == 1
        assert history.sessions[0] == session1
        assert history.current_session_id is None  # 現在のセッションIDがクリア
        
        # 存在しないセッションを削除
        result = history.delete_session("存在しないID")
        assert result is False
    
    def test_delete_non_current_session(self):
        """現在以外のセッション削除テスト"""
        history = ChatHistory()
        
        session1 = history.create_new_session("セッション1")
        session2 = history.create_new_session("セッション2")  # これが現在のセッション
        
        # 現在以外のセッションを削除
        result = history.delete_session(session1.id)
        
        assert result is True
        assert len(history.sessions) == 1
        assert history.sessions[0] == session2
        assert history.current_session_id == session2.id  # current_session_idは変更されない
    
    def test_get_recent_sessions(self):
        """最近のセッション取得テスト"""
        history = ChatHistory()
        
        # 複数のセッションを作成（時間差あり）
        sessions = []
        for i in range(5):
            session = history.create_new_session(f"セッション{i}")
            sessions.append(session)
            import time
            time.sleep(0.001)  # わずかな時間差を作る
        
        # 最新3つを取得
        recent = history.get_recent_sessions(limit=3)
        
        assert len(recent) == 3
        # 新しい順に並んでいることを確認
        assert recent[0] == sessions[-1]  # 最新
        assert recent[1] == sessions[-2]
        assert recent[2] == sessions[-3]
    
    def test_get_recent_sessions_with_updated_times(self):
        """更新時間を考慮した最近のセッション取得テスト"""
        history = ChatHistory()
        
        session1 = history.create_new_session("セッション1")
        session2 = history.create_new_session("セッション2")
        
        import time
        time.sleep(0.001)
        
        # session1に新しいメッセージを追加（updated_atが更新される）
        session1.add_message(ChatMessage(content="新しいメッセージ"))
        
        recent = history.get_recent_sessions(limit=2)
        
        # session1が最新になっているはず
        assert recent[0] == session1
        assert recent[1] == session2


class TestMessageRole:
    """メッセージロールテスト"""
    
    def test_message_role_values(self):
        """メッセージロール値テスト"""
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.SYSTEM.value == "system"