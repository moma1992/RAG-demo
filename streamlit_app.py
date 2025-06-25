"""
新入社員向け社内文書検索RAGアプリケーション - メインアプリケーション

このモジュールはStreamlitを使用したRAGアプリケーションのメインエントリーポイントです。
"""

import streamlit as st
from typing import Optional
import logging
import os
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

# 実装したコンポーネントをインポート
from components.chat_interface import AdvancedChatInterface, chat_interface_component
from components.pdf_uploader import pdf_uploader_component
from components.document_manager import document_manager_component
from services.claude_llm import ClaudeService
from services.vector_store import VectorStore
from services.embeddings import EmbeddingService

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
    try:
        # APIキーの確認
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if not all([anthropic_api_key, supabase_url, supabase_anon_key, openai_api_key]):
            st.error("⚠️ 必要な環境変数が設定されていません")
            st.info("以下の環境変数を.envファイルに設定してください:")
            st.code("""
ANTHROPIC_API_KEY=your_claude_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
OPENAI_API_KEY=your_openai_api_key
            """)
            return
        
        # サービスの初期化
        if "chat_services_initialized" not in st.session_state:
            try:
                claude_service = ClaudeService(api_key=anthropic_api_key)
                vector_store = VectorStore(
                    supabase_url=supabase_url,
                    supabase_key=supabase_anon_key
                )
                embedding_service = EmbeddingService(api_key=openai_api_key)
                
                chat_interface = AdvancedChatInterface(claude_service, vector_store, embedding_service)
                
                st.session_state.claude_service = claude_service
                st.session_state.vector_store = vector_store
                st.session_state.embedding_service = embedding_service
                st.session_state.chat_interface = chat_interface
                st.session_state.chat_services_initialized = True
                
                st.success("✅ サービスが正常に初期化されました")
                
            except Exception as e:
                st.error(f"❌ サービス初期化エラー: {str(e)}")
                st.info("デモモードとして基本的なチャット機能を表示します")
                # レガシーチャットインターフェースを表示
                user_input = chat_interface_component()
                if user_input:
                    st.chat_message("assistant").write("申し訳ございませんが、現在システムに接続できません。")
                return
        
        # 高度なチャットインターフェースを表示
        st.session_state.chat_interface.render_chat_interface()
        
    except Exception as e:
        logger.error(f"チャットページエラー: {str(e)}")
        st.error(f"❌ エラーが発生しました: {str(e)}")
        st.info("デモモードとして基本的なチャット機能を表示します")
        
        # フォールバック: レガシーチャットインターフェース
        user_input = chat_interface_component()
        if user_input:
            st.chat_message("assistant").write(f"入力を受け取りました: {user_input}")
            st.info("本来はここでRAG検索と Claude API による回答生成が行われます。")

def show_document_management_page() -> None:
    """文書管理ページ表示"""
    st.header("📄 文書管理")
    
    # PDF アップローダー
    try:
        uploaded_file = pdf_uploader_component()
        if uploaded_file:
            st.success(f"✅ ファイル '{uploaded_file.name}' がアップロードされました")
            st.info("実装完了後、このファイルが自動的に処理され、検索可能になります。")
    except Exception as e:
        st.error(f"PDF アップロード機能でエラーが発生しました: {str(e)}")
    
    # 文書管理機能
    try:
        document_manager_component()
    except Exception as e:
        st.error(f"文書管理機能でエラーが発生しました: {str(e)}")
        st.info("デモモードとして基本的な情報を表示します")
        
        st.subheader("📊 文書統計")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("総文書数", "0", "件")
        with col2:
            st.metric("処理済み", "0", "件")  
        with col3:
            st.metric("インデックス済み", "0", "件")

def show_settings_page() -> None:
    """設定ページ表示"""
    st.header("⚙️ 設定")
    
    st.subheader("🔑 API設定")
    
    # 環境変数の状態を確認
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    supabase_url = os.getenv("SUPABASE_URL") 
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 設定状況")
        st.write("**Anthropic API Key:**", "✅ 設定済み" if anthropic_key else "❌ 未設定")
        st.write("**Supabase URL:**", "✅ 設定済み" if supabase_url else "❌ 未設定")
        st.write("**Supabase Key:**", "✅ 設定済み" if supabase_key else "❌ 未設定")
    
    with col2:
        st.subheader("⚙️ アプリケーション設定")
        
        # チャット設定
        st.write("**チャット設定**")
        max_messages = st.slider("履歴保持メッセージ数", 5, 20, 10)
        show_citations = st.checkbox("引用表示", True)
        streaming_enabled = st.checkbox("ストリーミング表示", True)
        
        # 検索設定
        st.write("**検索設定**")
        similarity_threshold = st.slider("類似度閾値", 0.0, 1.0, 0.7, 0.1)
        max_results = st.slider("最大検索結果数", 1, 10, 5)
    
    st.subheader("📋 環境変数設定手順")
    st.info("環境変数は.envファイルで設定してください:")
    
    st.code("""
# .envファイルの例
ANTHROPIC_API_KEY=your_claude_api_key_here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key_here
    """)
    
    # 実装状況
    st.subheader("🏗️ 実装状況")
    
    features = [
        ("チャット履歴管理", "✅", "完了"),
        ("Claude APIストリーミング", "✅", "完了"),
        ("引用表示機能", "✅", "完了"),
        ("高度なチャットUI", "✅", "完了"),
        ("PDF アップロード", "🔄", "一部実装"),
        ("ベクター検索", "🔄", "一部実装"),
        ("文書管理", "🔄", "一部実装"),
    ]
    
    for feature, status, description in features:
        col1, col2, col3 = st.columns([3, 1, 2])
        with col1:
            st.write(feature)
        with col2:
            st.write(status)
        with col3:
            st.write(description)

if __name__ == "__main__":
    main()