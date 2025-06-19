"""
エラーハンドリングユーティリティ

アプリケーション全体のエラー処理と日本語エラーメッセージ機能
"""

import logging
import traceback
from typing import Optional, Dict, Any, Callable
from functools import wraps
import streamlit as st

logger = logging.getLogger(__name__)

class RAGError(Exception):
    """RAGアプリケーション基底エラー"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class FileProcessingError(RAGError):
    """ファイル処理エラー"""
    pass

class DatabaseError(RAGError):
    """データベースエラー"""
    pass

class APIError(RAGError):
    """外部APIエラー"""
    pass

class ConfigurationError(RAGError):
    """設定エラー"""
    pass

class ErrorHandler:
    """エラーハンドラークラス"""
    
    # エラーメッセージマッピング（日本語）
    ERROR_MESSAGES = {
        "file_too_large": "ファイルサイズが大きすぎます。{max_size}MB以下のファイルをアップロードしてください。",
        "file_type_not_supported": "サポートされていないファイル形式です。PDFファイルをアップロードしてください。",
        "pdf_processing_failed": "PDFファイルの処理中にエラーが発生しました。ファイルが破損している可能性があります。",
        "api_key_invalid": "APIキーが無効です。設定を確認してください。",
        "api_rate_limit": "APIの利用制限に達しました。しばらく時間をおいてから再度お試しください。",
        "database_connection_failed": "データベースへの接続に失敗しました。ネットワーク接続を確認してください。",
        "search_failed": "検索処理中にエラーが発生しました。再度お試しください。",
        "embedding_generation_failed": "テキストの埋め込み生成に失敗しました。",
        "llm_response_failed": "AI応答の生成に失敗しました。",
        "unknown_error": "予期しないエラーが発生しました。管理者に連絡してください。"
    }
    
    @classmethod
    def handle_error(
        cls,
        error: Exception,
        context: Optional[str] = None,
        show_user_message: bool = True
    ) -> None:
        """
        エラーを処理
        
        Args:
            error: 発生したエラー
            context: エラーが発生したコンテキスト
            show_user_message: ユーザーにメッセージを表示するか
        """
        # ログに記録
        error_msg = f"エラー発生"
        if context:
            error_msg += f" ({context})"
        error_msg += f": {str(error)}"
        
        logger.error(error_msg, exc_info=True)
        
        # ユーザー向けメッセージを表示
        if show_user_message:
            user_message = cls._get_user_friendly_message(error)
            st.error(user_message)
    
    @classmethod
    def _get_user_friendly_message(cls, error: Exception) -> str:
        """ユーザー向けエラーメッセージを取得"""
        if isinstance(error, RAGError):
            return error.message
        
        # 一般的なエラーのマッピング
        error_type = type(error).__name__
        
        if "FileNotFoundError" in error_type:
            return "指定されたファイルが見つかりません。"
        elif "PermissionError" in error_type:
            return "ファイルへのアクセス権限がありません。"
        elif "ConnectionError" in error_type:
            return "ネットワーク接続エラーが発生しました。インターネット接続を確認してください。"
        elif "TimeoutError" in error_type:
            return "処理がタイムアウトしました。再度お試しください。"
        elif "ValueError" in error_type:
            return "入力値に問題があります。内容を確認してください。"
        else:
            return cls.ERROR_MESSAGES["unknown_error"]
    
    @classmethod
    def get_formatted_message(cls, error_key: str, **kwargs) -> str:
        """フォーマット済みエラーメッセージを取得"""
        template = cls.ERROR_MESSAGES.get(error_key, cls.ERROR_MESSAGES["unknown_error"])
        try:
            return template.format(**kwargs)
        except KeyError:
            logger.warning(f"エラーメッセージテンプレートのフォーマットに失敗: {error_key}")
            return template

def error_handler(
    context: Optional[str] = None,
    show_user_message: bool = True,
    raise_on_error: bool = False
) -> Callable:
    """
    エラーハンドリングデコレータ
    
    Args:
        context: エラーコンテキスト
        show_user_message: ユーザーメッセージ表示フラグ
        raise_on_error: エラー時に再発生させるか
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                ErrorHandler.handle_error(
                    error=e,
                    context=context or func.__name__,
                    show_user_message=show_user_message
                )
                if raise_on_error:
                    raise
                return None
        return wrapper
    return decorator

def validate_file_upload(uploaded_file, max_size_mb: int = 50) -> None:
    """
    アップロードファイルを検証
    
    Args:
        uploaded_file: アップロードされたファイル
        max_size_mb: 最大ファイルサイズ（MB）
        
    Raises:
        FileProcessingError: ファイル検証エラーの場合
    """
    if not uploaded_file:
        raise FileProcessingError("ファイルがアップロードされていません。")
    
    # ファイルサイズチェック
    if uploaded_file.size > max_size_mb * 1024 * 1024:
        raise FileProcessingError(
            ErrorHandler.get_formatted_message("file_too_large", max_size=max_size_mb)
        )
    
    # ファイル形式チェック
    if not uploaded_file.name.lower().endswith('.pdf'):
        raise FileProcessingError(
            ErrorHandler.get_formatted_message("file_type_not_supported")
        )
    
    logger.info(f"ファイル検証完了: {uploaded_file.name}")

def safe_execute(func: Callable, *args, **kwargs) -> tuple[bool, Any]:
    """
    安全な関数実行
    
    Args:
        func: 実行する関数
        *args: 関数の引数
        **kwargs: 関数のキーワード引数
        
    Returns:
        tuple[bool, Any]: (成功フラグ, 結果)
    """
    try:
        result = func(*args, **kwargs)
        return True, result
    except Exception as e:
        ErrorHandler.handle_error(e, context=func.__name__)
        return False, None