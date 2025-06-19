"""
新入社員向け社内文書検索RAGアプリケーション - メインアプリケーション

このモジュールはStreamlitを使用したRAGアプリケーションのメインエントリーポイントです。
"""

import streamlit as st
from typing import Optional
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main() -> None:
    """メインアプリケーション関数"""
    st.set_page_config(
        page_title="社内文書検索RAG",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("📚 社内文書検索RAGシステム")
    st.markdown("新入社員向け社内文書検索アプリケーション")
    
    # サイドバー
    with st.sidebar:
        st.header("📋 メニュー")
        page = st.radio(
            "ページを選択:",
            ["チャット", "文書管理", "設定"]
        )
    
    # メインコンテンツ
    if page == "チャット":
        show_chat_page()
    elif page == "文書管理":
        show_document_management_page()
    elif page == "設定":
        show_settings_page()

def show_chat_page() -> None:
    """チャットページ表示"""
    st.header("💬 文書検索チャット")
    st.info("現在開発中です。PDF文書をアップロードして質問できるようになります。")

def show_document_management_page() -> None:
    """文書管理ページ表示"""
    st.header("📄 文書管理")
    st.info("現在開発中です。PDF文書のアップロードと管理ができるようになります。")

def show_settings_page() -> None:
    """設定ページ表示"""
    st.header("⚙️ 設定")
    st.info("現在開発中です。APIキーやその他の設定を管理できるようになります。")

if __name__ == "__main__":
    main()