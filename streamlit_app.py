"""
新入社員向け社内文書検索RAGアプリケーション - メインアプリケーション

このモジュールはStreamlitを使用したRAGアプリケーションのメインエントリーポイントです。
Issue #66: 高度なチャットインターフェースとバックエンドサービスの統合
"""

import streamlit as st
from typing import Optional, List
import logging
import os
from dotenv import load_dotenv
from utils.streamlit_helpers import (
    get_user_friendly_error_message, 
    display_service_status_indicator,
    handle_api_errors
)

# 環境変数読み込み
load_dotenv()

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
    
    # サービス初期化確認
    services_ready = check_and_initialize_services()
    
    # サイドバー
    with st.sidebar:
        st.header("📋 メニュー")
        
        # サービス状態表示
        display_service_status_indicator(services_ready)
        
        page = st.radio(
            "ページを選択:",
            ["チャット", "文書管理", "PDFアップロード", "設定"]
        )
    
    # メインコンテンツ
    if page == "チャット":
        show_chat_page(services_ready)
    elif page == "文書管理":
        show_document_management_page(services_ready)
    elif page == "PDFアップロード":
        show_pdf_upload_page(services_ready)
    elif page == "設定":
        show_settings_page()

def check_and_initialize_services() -> dict:
    """サービスの初期化と状態確認"""
    services_status = {
        "openai_api": False,
        "claude_api": False,
        "supabase": False,
        "vector_store": False,
        "embedding_service": False,
        "claude_service": False
    }
    
    try:
        # OpenAI API確認
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            services_status["openai_api"] = True
        
        # Claude API確認
        claude_key = os.getenv("ANTHROPIC_API_KEY")
        if claude_key:
            services_status["claude_api"] = True
        
        # Supabase確認
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        if supabase_url and supabase_key:
            services_status["supabase"] = True
            
            # VectorStoreサービス初期化
            if "vector_store" not in st.session_state and services_status["supabase"]:
                try:
                    from services.vector_store import VectorStore
                    st.session_state.vector_store = VectorStore(
                        supabase_url=supabase_url,
                        supabase_key=supabase_key
                    )
                    services_status["vector_store"] = True
                    logger.info("VectorStore初期化完了")
                except Exception as e:
                    logger.error(f"VectorStore初期化エラー: {str(e)}")
            elif "vector_store" in st.session_state:
                services_status["vector_store"] = True
            
            # EmbeddingService初期化
            if "embedding_service" not in st.session_state and services_status["openai_api"]:
                try:
                    from services.embeddings import EmbeddingService
                    st.session_state.embedding_service = EmbeddingService(api_key=openai_key)
                    services_status["embedding_service"] = True
                    logger.info("EmbeddingService初期化完了")
                except Exception as e:
                    logger.error(f"EmbeddingService初期化エラー: {str(e)}")
            elif "embedding_service" in st.session_state:
                services_status["embedding_service"] = True
            
            # ClaudeService初期化
            if "claude_service" not in st.session_state and services_status["claude_api"]:
                try:
                    from services.claude_llm import ClaudeService
                    st.session_state.claude_service = ClaudeService(api_key=claude_key)
                    services_status["claude_service"] = True
                    logger.info("ClaudeService初期化完了")
                except Exception as e:
                    logger.error(f"ClaudeService初期化エラー: {str(e)}")
            elif "claude_service" in st.session_state:
                services_status["claude_service"] = True
        
    except Exception as e:
        logger.error(f"サービス初期化エラー: {str(e)}")
        st.error(get_user_friendly_error_message(e))
    
    return services_status

def show_chat_page(services_ready: dict) -> None:
    """チャットページ表示"""
    st.header("💬 文書検索チャット")
    
    # サービス状態確認
    required_services = ["vector_store", "embedding_service", "claude_service"]
    missing_services = [s for s in required_services if not services_ready.get(s, False)]
    
    if missing_services:
        st.error(f"チャット機能の利用には以下のサービスが必要です: {', '.join(missing_services)}")
        st.info("設定ページでAPIキーを確認してください。")
        return
    
    # 高度なチャットインターフェースを表示
    try:
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
            
            # 即座にユーザーメッセージを表示
            with st.chat_message("user"):
                st.markdown(user_input)
            
            # アシスタント回答を生成
            search_results = generate_response(user_input, services_ready)
            
            # 引用表示（改善版）
            if search_results:
                from components.citation_display import StreamlitCitationWidget
                StreamlitCitationWidget.render_citation_expander(
                    search_results, expanded=False, show_similarity_scores=True
                )
            
    except Exception as e:
        logger.error(f"チャットページエラー: {str(e)}")
        st.error(f"チャット機能でエラーが発生しました: {str(e)}")

@handle_api_errors
def generate_response(query: str, services_ready: dict) -> Optional[List]:
    """回答生成処理"""
    try:
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            
            # ローディング表示
            with st.spinner("関連文書を検索中..."):
                # 埋め込み生成
                embedding_service = st.session_state.embedding_service
                embedding_result = embedding_service.generate_embedding(query)
                
                # ベクター検索
                vector_store = st.session_state.vector_store
                search_results = vector_store.similarity_search(
                    embedding_result.embedding, k=5
                )
            
            # コンテキスト準備
            context_chunks = []
            sources = []
            
            for result in search_results:
                context_chunks.append(result.content)
                source_info = f"{result.filename} (ページ {result.page_number})"
                sources.append(source_info)
            
            # Claude回答生成
            with st.spinner("回答を生成中..."):
                claude_service = st.session_state.claude_service
                response = claude_service.generate_response(
                    query=query,
                    context_chunks=context_chunks
                )
            
            # 回答表示
            message_placeholder.markdown(response.content)
            
            # アシスタントメッセージを履歴に追加
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": response.content,
                "sources": sources
            })
            
            return search_results
        
    except Exception as e:
        logger.error(f"回答生成エラー: {str(e)}")
        st.error(f"回答生成中にエラーが発生しました: {str(e)}")
        return None

def show_document_management_page(services_ready: dict) -> None:
    """文書管理ページ表示"""
    from components.document_manager import document_manager_component
    document_manager_component()

def show_pdf_upload_page(services_ready: dict) -> None:
    """PDFアップロードページ表示"""
    from components.pdf_uploader import pdf_uploader_component
    pdf_uploader_component()

def show_settings_page() -> None:
    """設定ページ表示"""
    st.header("⚙️ 設定")
    
    st.subheader("📋 API設定")
    
    # 環境変数の状態表示
    st.markdown("### 現在の設定状態")
    
    openai_key = os.getenv("OPENAI_API_KEY")
    claude_key = os.getenv("ANTHROPIC_API_KEY")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**OpenAI API Key:**")
        if openai_key:
            st.success("✅ 設定済み")
        else:
            st.error("❌ 未設定")
        
        st.markdown("**Claude API Key:**")
        if claude_key:
            st.success("✅ 設定済み")
        else:
            st.error("❌ 未設定")
    
    with col2:
        st.markdown("**Supabase URL:**")
        if supabase_url:
            st.success("✅ 設定済み")
        else:
            st.error("❌ 未設定")
        
        st.markdown("**Supabase Key:**")
        if supabase_key:
            st.success("✅ 設定済み")
        else:
            st.error("❌ 未設定")
    
    st.markdown("### 📄 設定方法")
    st.markdown("""
    1. プロジェクトルートに `.env` ファイルを作成
    2. 以下の環境変数を設定:
    
    ```
    OPENAI_API_KEY=your_openai_api_key
    ANTHROPIC_API_KEY=your_claude_api_key
    SUPABASE_URL=your_supabase_url
    SUPABASE_ANON_KEY=your_supabase_anon_key
    ```
    
    3. アプリケーションを再起動
    """)
    
    # チャット履歴クリア
    st.markdown("### 🗑️ データ管理")
    if st.button("チャット履歴をクリア", type="secondary"):
        if "chat_history" in st.session_state:
            st.session_state.chat_history = []
            st.success("チャット履歴をクリアしました")
            st.rerun()


if __name__ == "__main__":
    main()