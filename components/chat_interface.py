"""
チャット UI コンポーネント

RAGチャットインターフェースを提供するStreamlitコンポーネント
"""

import streamlit as st
from typing import List, Dict, Optional, AsyncIterator, Any
import logging
import asyncio
import time
from datetime import datetime

from models.chat import ChatSession, ChatMessage, DocumentReference, MessageRole
from components.citation_display import CitationDisplay, StreamlitCitationWidget
from services.claude_llm import ClaudeService
from services.vector_store import VectorStore
from services.embeddings import EmbeddingService
from utils.error_handler import RAGError

logger = logging.getLogger(__name__)

class AdvancedChatInterface:
    """高度なチャットインターフェースクラス"""
    
    def __init__(self, claude_service: ClaudeService, vector_store: VectorStore, embedding_service: Optional[EmbeddingService] = None):
        """
        初期化
        
        Args:
            claude_service: Claude LLMサービス
            vector_store: ベクターストア
            embedding_service: 埋め込みサービス（省略時は環境変数から自動初期化）
        """
        self.claude_service = claude_service
        self.vector_store = vector_store
        
        # 埋め込みサービスの初期化
        if embedding_service is None:
            try:
                import os
                openai_api_key = os.getenv("OPENAI_API_KEY")
                if not openai_api_key:
                    raise ValueError("OPENAI_API_KEY環境変数が設定されていません")
                self.embedding_service = EmbeddingService(api_key=openai_api_key)
                logger.info("EmbeddingService自動初期化完了")
            except Exception as e:
                logger.error(f"EmbeddingService初期化エラー: {str(e)}")
                self.embedding_service = None
        else:
            self.embedding_service = embedding_service
        self.citation_display = CitationDisplay(theme="default")
        
        # セッション状態の初期化
        self._initialize_session_state()
    
    def _initialize_session_state(self) -> None:
        """セッション状態を初期化"""
        if "chat_session" not in st.session_state:
            st.session_state.chat_session = ChatSession()
        
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        
        if "streaming_response" not in st.session_state:
            st.session_state.streaming_response = None
    
    def render_chat_interface(self) -> None:
        """チャットインターフェースをレンダリング"""
        st.subheader("💬 高度な文書検索チャット")
        
        # サイドバーにチャット管理機能
        self._render_chat_management_sidebar()
        
        # メインチャット表示
        self._render_chat_history()
        
        # ユーザー入力とリアルタイム処理
        self._handle_user_input()
    
    def _render_chat_management_sidebar(self) -> None:
        """チャット管理サイドバーをレンダリング"""
        with st.sidebar:
            st.subheader("🔧 チャット管理")
            
            # 新しいチャット開始
            if st.button("🆕 新しいチャット", type="primary"):
                self._start_new_chat()
            
            # チャット履歴クリア
            if st.button("🗑️ 履歴クリア"):
                self._clear_chat_history()
            
            # チャット統計
            self._display_chat_statistics()
    
    def _render_chat_history(self) -> None:
        """チャット履歴をレンダリング"""
        session = st.session_state.chat_session
        
        for message in session.messages:
            with st.chat_message(message.role.value):
                st.markdown(message.content)
                
                # 引用表示（アシスタントメッセージのみ）
                if message.role == MessageRole.ASSISTANT and message.references:
                    StreamlitCitationWidget.render_citation_expander(
                        message.references, expanded=False
                    )
    
    def _handle_user_input(self) -> None:
        """ユーザー入力を処理"""
        user_input = st.chat_input("文書について質問してください...")
        
        if user_input:
            # ユーザーメッセージを追加
            user_message = ChatMessage(
                role=MessageRole.USER,
                content=user_input
            )
            st.session_state.chat_session.add_message(user_message)
            
            # 即座にユーザーメッセージを表示
            with st.chat_message("user"):
                st.markdown(user_input)
            
            # アシスタント回答をストリーミング生成
            self._generate_streaming_response(user_input)
    
    def _generate_streaming_response(self, query: str) -> None:
        """ストリーミング回答を生成"""
        try:
            # プレースホルダーでローディング表示
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                citation_placeholder = st.empty()
                
                # 関連文書検索
                with st.spinner("関連文書を検索中..."):
                    if self.embedding_service is None:
                        st.error("埋め込みサービスが利用できません。OPENAI_API_KEYを確認してください。")
                        return
                    
                    # クエリを埋め込みベクトルに変換
                    try:
                        embedding_result = self.embedding_service.generate_embedding(query)
                        search_results = self.vector_store.similarity_search(
                            embedding_result.embedding, k=5
                        )
                    except Exception as e:
                        logger.error(f"埋め込み生成またはベクター検索エラー: {str(e)}")
                        st.error(f"検索中にエラーが発生しました: {str(e)}")
                        return
                
                # コンテキスト準備
                context_chunks = [result.content for result in search_results]
                
                # 文書参照作成
                references = self._create_document_references(search_results)
                
                # チャット履歴準備
                chat_history = self._prepare_chat_history()
                
                # ストリーミング回答生成
                full_response = ""
                
                # 非同期処理をStreamlitで実行
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    async_gen = self.claude_service.astream_response(
                        query, context_chunks, chat_history
                    )
                    
                    for chunk in self._run_async_generator(async_gen, loop):
                        if chunk.get("content"):
                            full_response += chunk["content"]
                            message_placeholder.markdown(full_response + "▌")
                            time.sleep(0.01)  # 視覚効果のための短い遅延
                
                finally:
                    loop.close()
                
                # 最終的なレスポンス表示
                message_placeholder.markdown(full_response)
                
                # 引用表示
                if references:
                    with citation_placeholder.container():
                        StreamlitCitationWidget.render_citation_expander(
                            references, expanded=False
                        )
                
                # アシスタントメッセージを履歴に追加
                assistant_message = ChatMessage(
                    role=MessageRole.ASSISTANT,
                    content=full_response,
                    references=references
                )
                st.session_state.chat_session.add_message(assistant_message)
                
        except Exception as e:
            logger.error(f"ストリーミング回答生成エラー: {str(e)}")
            st.error(f"回答生成中にエラーが発生しました: {str(e)}")
    
    def _run_async_generator(self, async_gen: AsyncIterator, loop: asyncio.AbstractEventLoop):
        """非同期ジェネレーターを同期的に実行"""
        try:
            while True:
                try:
                    chunk = loop.run_until_complete(async_gen.__anext__())
                    yield chunk
                except StopAsyncIteration:
                    break
        except Exception as e:
            logger.error(f"非同期ジェネレーター実行エラー: {str(e)}")
            raise
    
    def _create_document_references(self, search_results) -> List[DocumentReference]:
        """検索結果から文書参照を作成"""
        references = []
        
        for result in search_results:
            metadata = result.metadata
            reference = DocumentReference(
                filename=result.filename,
                page_number=result.page_number,
                chunk_id=metadata.get("chunk_id", ""),
                similarity_score=getattr(result, "similarity_score", 0.0),
                excerpt=result.content[:200] + "..." if len(result.content) > 200 else result.content
            )
            references.append(reference)
        
        return references
    
    def _prepare_chat_history(self) -> List[Any]:
        """チャット履歴をClaude API用に変換"""
        from services.claude_llm import ChatMessage as ClaudeChatMessage
        
        session = st.session_state.chat_session
        chat_history = []
        
        # 最新の5つのメッセージのみを使用
        recent_messages = session.messages[-5:] if len(session.messages) > 5 else session.messages
        
        for message in recent_messages[:-1]:  # 最新のメッセージは除外
            claude_message = ClaudeChatMessage(
                role=message.role.value,
                content=message.content
            )
            chat_history.append(claude_message)
        
        return chat_history
    
    def _start_new_chat(self) -> None:
        """新しいチャットを開始"""
        st.session_state.chat_session = ChatSession()
        st.success("新しいチャットを開始しました")
        st.rerun()
    
    def _clear_chat_history(self) -> None:
        """チャット履歴をクリア"""
        st.session_state.chat_session.clear_messages()
        st.success("チャット履歴をクリアしました")
        st.rerun()
    
    def _display_chat_statistics(self) -> None:
        """チャット統計を表示"""
        session = st.session_state.chat_session
        
        st.markdown("### 📊 チャット統計")
        st.metric("メッセージ数", session.get_message_count())
        st.metric("ユーザーメッセージ", len(session.get_user_messages()))
        st.metric("アシスタント回答", len(session.get_assistant_messages()))
        
        if session.messages:
            last_message = session.get_last_message()
            if last_message:
                st.markdown(f"**最後の更新:** {last_message.timestamp.strftime('%H:%M')}")


def chat_interface_component() -> Optional[str]:
    """
    レガシーチャットインターフェースコンポーネント（後方互換性のため保持）
    
    Returns:
        Optional[str]: ユーザーの入力メッセージ
    """
    st.subheader("💬 文書検索チャット")
    
    # チャット履歴の初期化
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # チャット履歴表示
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                with st.expander("📚 参考文書"):
                    for source in message["sources"]:
                        st.markdown(f"- {source}")
    
    # ユーザー入力
    user_input = st.chat_input("文書について質問してください...")
    
    if user_input:
        # ユーザーメッセージを履歴に追加
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_input
        })
        
        return user_input
    
    return None

def add_assistant_message(content: str, sources: Optional[List[str]] = None) -> None:
    """
    アシスタントメッセージをチャット履歴に追加
    
    Args:
        content: メッセージ内容
        sources: 参考文書リスト
    """
    message = {
        "role": "assistant",
        "content": content
    }
    
    if sources:
        message["sources"] = sources
    
    st.session_state.chat_history.append(message)

def clear_chat_history() -> None:
    """チャット履歴をクリア"""
    st.session_state.chat_history = []
    st.success("チャット履歴がクリアされました")