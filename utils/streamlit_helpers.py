"""
Streamlit用ヘルパー関数 - Issue #66

エラーハンドリング、ユーザーフィードバック、日本語メッセージ対応
"""

import streamlit as st
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps

logger = logging.getLogger(__name__)


def handle_api_errors(func: Callable) -> Callable:
    """
    API呼び出しエラーのデコレータ
    
    Args:
        func: デコレートする関数
        
    Returns:
        Callable: ラップされた関数
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_message = get_user_friendly_error_message(e)
            st.error(error_message)
            logger.error(f"API呼び出しエラー in {func.__name__}: {str(e)}", exc_info=True)
            return None
    return wrapper


def get_user_friendly_error_message(error: Exception) -> str:
    """
    ユーザーフレンドリーなエラーメッセージを生成
    
    Args:
        error: 発生したエラー
        
    Returns:
        str: 日本語のエラーメッセージ
    """
    error_str = str(error).lower()
    
    # OpenAI API関連エラー
    if "openai" in error_str:
        if "api key" in error_str or "authentication" in error_str:
            return "❌ OpenAI APIキーが正しく設定されていません。設定ページで確認してください。"
        elif "rate limit" in error_str or "quota" in error_str:
            return "⏱️ OpenAI APIの利用制限に達しました。しばらく時間をおいてから再度お試しください。"
        elif "connection" in error_str or "timeout" in error_str:
            return "🌐 OpenAI APIへの接続に失敗しました。インターネット接続を確認してください。"
        else:
            return f"🔧 OpenAI APIでエラーが発生しました: {str(error)}"
    
    # Claude API関連エラー
    elif "anthropic" in error_str or "claude" in error_str:
        if "api key" in error_str or "authentication" in error_str:
            return "❌ Claude APIキーが正しく設定されていません。設定ページで確認してください。"
        elif "rate limit" in error_str:
            return "⏱️ Claude APIの利用制限に達しました。しばらく時間をおいてから再度お試しください。"
        elif "connection" in error_str or "timeout" in error_str:
            return "🌐 Claude APIへの接続に失敗しました。インターネット接続を確認してください。"
        else:
            return f"🔧 Claude APIでエラーが発生しました: {str(error)}"
    
    # Supabase関連エラー
    elif "supabase" in error_str:
        if "url" in error_str or "key" in error_str:
            return "❌ Supabaseの設定が正しくありません。設定ページで確認してください。"
        elif "connection" in error_str:
            return "🌐 Supabaseへの接続に失敗しました。インターネット接続を確認してください。"
        else:
            return f"🗄️ データベースエラーが発生しました: {str(error)}"
    
    # PDF処理関連エラー
    elif "pdf" in error_str:
        if "corrupt" in error_str or "invalid" in error_str:
            return "📄 PDFファイルが破損しているか、無効な形式です。別のファイルをお試しください。"
        elif "password" in error_str or "encrypted" in error_str:
            return "🔒 パスワード保護されたPDFは現在サポートされていません。"
        elif "size" in error_str:
            return "📊 PDFファイルのサイズが大きすぎます。小さいファイルをお試しください。"
        else:
            return f"📄 PDF処理中にエラーが発生しました: {str(error)}"
    
    # 一般的なエラー
    elif "memory" in error_str or "ram" in error_str:
        return "💾 メモリ不足です。ファイルサイズを小さくするか、処理を分割してください。"
    elif "timeout" in error_str:
        return "⏱️ 処理がタイムアウトしました。もう一度お試しください。"
    elif "permission" in error_str:
        return "🔐 アクセス権限がありません。設定を確認してください。"
    else:
        return f"⚠️ エラーが発生しました: {str(error)}"


def display_service_status_indicator(services_ready: Dict[str, bool]) -> None:
    """
    サービス状態インジケーターを表示
    
    Args:
        services_ready: サービス状態辞書
    """
    all_ready = all(services_ready.values())
    
    if all_ready:
        st.success("✅ すべてのサービスが利用可能です")
    else:
        missing_services = [name for name, ready in services_ready.items() if not ready]
        st.warning(f"⚠️ 未設定のサービス: {', '.join(missing_services)}")
        
        with st.expander("設定方法を見る"):
            st.markdown("""
            ### 📋 必要な設定
            
            1. **OpenAI API Key** - 埋め込み生成用
            2. **Claude API Key** - 回答生成用  
            3. **Supabase URL & Key** - データストア用
            
            ### 🔧 設定手順
            1. プロジェクトルートに `.env` ファイルを作成
            2. 必要なAPIキーを取得して設定
            3. アプリケーションを再起動
            """)


def display_loading_with_progress(task_name: str, steps: list) -> dict:
    """
    プログレス付きローディング表示
    
    Args:
        task_name: タスク名
        steps: ステップリスト
        
    Returns:
        dict: プログレス表示用のコンテナ
    """
    st.markdown(f"### {task_name}")
    
    progress_container = {
        "progress_bar": st.progress(0),
        "status_text": st.empty(),
        "step_container": st.container(),
        "total_steps": len(steps),
        "current_step": 0
    }
    
    with progress_container["step_container"]:
        for i, step in enumerate(steps):
            st.markdown(f"{i+1}. {step}")
    
    return progress_container


def update_progress(container: dict, step: int, message: str) -> None:
    """
    プログレス更新
    
    Args:
        container: プログレスコンテナ
        step: 現在のステップ
        message: 状態メッセージ
    """
    progress = step / container["total_steps"]
    container["progress_bar"].progress(progress)
    container["status_text"].text(f"Step {step}/{container['total_steps']}: {message}")


def show_api_usage_info() -> None:
    """API利用状況情報を表示"""
    with st.expander("💰 API利用状況"):
        st.markdown("""
        ### 推定コスト
        - **OpenAI Embeddings**: $0.0001 / 1Kトークン
        - **Claude API**: $0.003 / 1Kトークン (入力), $0.015 / 1Kトークン (出力)
        
        ### 節約のコツ
        - 短い質問を心がける
        - 必要以上に長いPDFのアップロードを避ける
        - チャット履歴を定期的にクリアする
        """)


def display_tips_and_tricks() -> None:
    """利用のコツを表示"""
    with st.expander("💡 利用のコツ"):
        st.markdown("""
        ### 効果的な質問方法
        - 具体的な質問をする
        - 複数の観点から質問を分ける
        - 参照文書を確認して追加質問する
        
        ### PDF準備のコツ  
        - OCR済みのPDFを使用する
        - 文字がクリアに読めるPDFを準備する
        - ファイルサイズは適切な範囲に抑える
        
        ### トラブルシューティング
        - エラーが発生したら設定ページを確認
        - APIキーの有効期限をチェック
        - インターネット接続を確認
        """)


def safe_execute_with_fallback(
    primary_func: Callable,
    fallback_func: Optional[Callable] = None,
    error_message: str = "処理中にエラーが発生しました"
) -> Any:
    """
    安全な実行とフォールバック処理
    
    Args:
        primary_func: メイン処理関数
        fallback_func: フォールバック関数
        error_message: エラーメッセージ
        
    Returns:
        Any: 実行結果
    """
    try:
        return primary_func()
    except Exception as e:
        logger.error(f"Primary function failed: {str(e)}", exc_info=True)
        st.error(get_user_friendly_error_message(e))
        
        if fallback_func:
            try:
                st.info("代替方法で処理を続行します...")
                return fallback_func()
            except Exception as fallback_error:
                logger.error(f"Fallback failed: {str(fallback_error)}", exc_info=True)
                st.error(f"代替処理も失敗しました: {get_user_friendly_error_message(fallback_error)}")
        
        return None