"""
チャットデータモデル

チャット履歴と会話のデータ構造定義
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from enum import Enum

class MessageRole(Enum):
    """メッセージロール"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

@dataclass
class DocumentReference:
    """文書参照情報"""
    filename: str
    page_number: int
    chunk_id: str
    similarity_score: float
    excerpt: str  # 抜粋テキスト

@dataclass
class ChatMessage:
    """チャットメッセージ"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole = MessageRole.USER
    content: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    references: List[DocumentReference] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_reference(self, reference: DocumentReference) -> None:
        """文書参照を追加"""
        self.references.append(reference)
    
    def get_referenced_files(self) -> List[str]:
        """参照されたファイル名一覧を取得"""
        return list(set(ref.filename for ref in self.references))

@dataclass
class ChatSession:
    """チャットセッション"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "新しいチャット"
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, message: ChatMessage) -> None:
        """メッセージを追加"""
        self.messages.append(message)
        self.updated_at = datetime.now()
        
        # 最初のユーザーメッセージでタイトルを設定
        if not self.title or self.title == "新しいチャット":
            if message.role == MessageRole.USER and message.content:
                self.title = message.content[:50] + ("..." if len(message.content) > 50 else "")
    
    def get_message_count(self) -> int:
        """メッセージ数を取得"""
        return len(self.messages)
    
    def get_last_message(self) -> Optional[ChatMessage]:
        """最後のメッセージを取得"""
        return self.messages[-1] if self.messages else None
    
    def get_user_messages(self) -> List[ChatMessage]:
        """ユーザーメッセージのみを取得"""
        return [msg for msg in self.messages if msg.role == MessageRole.USER]
    
    def get_assistant_messages(self) -> List[ChatMessage]:
        """アシスタントメッセージのみを取得"""
        return [msg for msg in self.messages if msg.role == MessageRole.ASSISTANT]
    
    def clear_messages(self) -> None:
        """メッセージをクリア"""
        self.messages.clear()
        self.updated_at = datetime.now()

@dataclass
class ChatHistory:
    """チャット履歴管理"""
    sessions: List[ChatSession] = field(default_factory=list)
    current_session_id: Optional[str] = None
    
    def create_new_session(self, title: str = "新しいチャット") -> ChatSession:
        """新しいセッションを作成"""
        session = ChatSession(title=title)
        self.sessions.append(session)
        self.current_session_id = session.id
        return session
    
    def get_current_session(self) -> Optional[ChatSession]:
        """現在のセッションを取得"""
        if not self.current_session_id:
            return None
        return next(
            (session for session in self.sessions if session.id == self.current_session_id),
            None
        )
    
    def get_session_by_id(self, session_id: str) -> Optional[ChatSession]:
        """IDでセッションを取得"""
        return next(
            (session for session in self.sessions if session.id == session_id),
            None
        )
    
    def delete_session(self, session_id: str) -> bool:
        """セッションを削除"""
        session = self.get_session_by_id(session_id)
        if session:
            self.sessions.remove(session)
            if self.current_session_id == session_id:
                self.current_session_id = None
            return True
        return False
    
    def get_recent_sessions(self, limit: int = 10) -> List[ChatSession]:
        """最近のセッションを取得"""
        return sorted(
            self.sessions,
            key=lambda x: x.updated_at,
            reverse=True
        )[:limit]