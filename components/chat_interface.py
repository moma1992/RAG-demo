"""
チャット UI コンポーネント

RAGチャットインターフェースを提供するStreamlitコンポーネント
"""

import streamlit as st
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

def chat_interface_component() -> Optional[str]:
    """
    チャットインターフェースコンポーネント
    
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