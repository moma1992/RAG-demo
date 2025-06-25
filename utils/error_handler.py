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

class LLMError(RAGError):
    """LLM関連エラー"""
    pass

class PromptError(RAGError):
    """プロンプト関連エラー"""
    pass

class ValidationError(RAGError):
    """バリデーションエラー"""
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
        "claude_api_error": "Claude APIでエラーが発生しました。{error_details}",
        "claude_rate_limit": "Claude APIの利用制限に達しました。{retry_after}秒後に再度お試しください。",
        "claude_token_limit": "トークン制限を超えています。質問やコンテキストを短くしてください。",
        "claude_timeout": "Claude APIがタイムアウトしました。再度お試しください。",
        "prompt_validation_failed": "プロンプトの検証に失敗しました。{missing_variables}",
        "template_not_found": "指定されたテンプレートが見つかりません: {template_name}",
        "template_render_failed": "テンプレートのレンダリングに失敗しました。",
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
        elif "RateLimitError" in error_type:
            return "API利用制限に達しました。しばらく時間をおいてから再度お試しください。"
        elif "TokenLimitError" in error_type:
            return "トークン制限を超えています。質問やコンテキストを短くしてください。"
        elif "PromptValidationError" in error_type:
            return "プロンプトの検証に失敗しました。設定を確認してください。"
        elif "TemplateNotFoundError" in error_type:
            return "テンプレートが見つかりません。設定を確認してください。"
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
    
    @classmethod
    def handle_claude_error(cls, error: Exception, context: Optional[str] = None) -> str:
        """
        Claude関連エラーを処理
        
        Args:
            error: Claude関連エラー
            context: エラーコンテキスト
            
        Returns:
            str: ユーザー向けエラーメッセージ
        """
        error_type = type(error).__name__
        
        if "RateLimitError" in error_type:
            retry_after = getattr(error, 'retry_after', None)
            if retry_after:
                return cls.get_formatted_message("claude_rate_limit", retry_after=retry_after)
            else:
                return cls.ERROR_MESSAGES["claude_rate_limit"].format(retry_after="60")
        
        elif "TokenLimitError" in error_type:
            return cls.ERROR_MESSAGES["claude_token_limit"]
        
        elif "TimeoutError" in error_type or "timeout" in str(error).lower():
            return cls.ERROR_MESSAGES["claude_timeout"]
        
        elif "APIError" in error_type or "api" in str(error).lower():
            return cls.get_formatted_message("claude_api_error", error_details=str(error))
        
        else:
            logger.error(f"未知のClaude関連エラー: {error}", exc_info=True)
            return cls.ERROR_MESSAGES["llm_response_failed"]
    
    @classmethod
    def handle_prompt_error(cls, error: Exception) -> str:
        """
        プロンプト関連エラーを処理
        
        Args:
            error: プロンプト関連エラー
            
        Returns:
            str: ユーザー向けエラーメッセージ
        """
        error_type = type(error).__name__
        
        if "PromptValidationError" in error_type:
            missing_vars = getattr(error, 'missing_variables', [])
            if missing_vars:
                return cls.get_formatted_message(
                    "prompt_validation_failed", 
                    missing_variables=", ".join(missing_vars)
                )
            else:
                return cls.ERROR_MESSAGES["template_render_failed"]
        
        elif "TemplateNotFoundError" in error_type:
            template_name = getattr(error, 'template_name', '不明')
            return cls.get_formatted_message("template_not_found", template_name=template_name)
        
        else:
            return cls.ERROR_MESSAGES["template_render_failed"]
    
    @classmethod
    def handle_llm_pipeline_error(cls, error: Exception, operation: str = "LLM処理") -> str:
        """
        LLMパイプライン全体のエラーを処理
        
        Args:
            error: 発生したエラー
            operation: 実行していた操作名
            
        Returns:
            str: ユーザー向けエラーメッセージ
        """
        error_type = type(error).__name__
        
        # Claude関連エラー
        if any(keyword in error_type for keyword in ["Claude", "RateLimit", "Token", "API"]):
            return cls.handle_claude_error(error)
        
        # プロンプト関連エラー
        elif any(keyword in error_type for keyword in ["Prompt", "Template", "Validation"]):
            return cls.handle_prompt_error(error)
        
        # 一般的なLLMエラー
        elif "LLMError" in error_type:
            return cls.ERROR_MESSAGES["llm_response_failed"]
        
        # その他のエラー
        else:
            logger.error(f"{operation}中に予期しないエラーが発生: {error}", exc_info=True)
            return cls.ERROR_MESSAGES["unknown_error"]

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

def claude_error_handler(
    operation: str = "Claude処理",
    show_user_message: bool = True,
    raise_on_error: bool = False
) -> Callable:
    """
    Claude LLM専用エラーハンドリングデコレータ
    
    Args:
        operation: 実行している操作名
        show_user_message: ユーザーメッセージ表示フラグ
        raise_on_error: エラー時に再発生させるか
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Claude関連エラーの専用処理
                user_message = ErrorHandler.handle_llm_pipeline_error(e, operation)
                
                # ログ記録
                logger.error(f"{operation}エラー ({func.__name__}): {str(e)}", exc_info=True)
                
                # ユーザーメッセージ表示
                if show_user_message:
                    st.error(user_message)
                
                if raise_on_error:
                    raise
                return None
        return wrapper
    return decorator

def async_claude_error_handler(
    operation: str = "非同期Claude処理",
    show_user_message: bool = True,
    raise_on_error: bool = False
) -> Callable:
    """
    非同期Claude LLM専用エラーハンドリングデコレータ
    
    Args:
        operation: 実行している操作名
        show_user_message: ユーザーメッセージ表示フラグ
        raise_on_error: エラー時に再発生させるか
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Claude関連エラーの専用処理
                user_message = ErrorHandler.handle_llm_pipeline_error(e, operation)
                
                # ログ記録
                logger.error(f"{operation}エラー ({func.__name__}): {str(e)}", exc_info=True)
                
                # ユーザーメッセージ表示
                if show_user_message:
                    st.error(user_message)
                
                if raise_on_error:
                    raise
                return None
        return wrapper
    return decorator

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

def safe_llm_execute(func: Callable, *args, **kwargs) -> tuple[bool, Any, Optional[str]]:
    """
    安全なLLM関数実行
    
    Args:
        func: 実行するLLM関数
        *args: 関数の引数
        **kwargs: 関数のキーワード引数
        
    Returns:
        tuple[bool, Any, Optional[str]]: (成功フラグ, 結果, エラーメッセージ)
    """
    try:
        result = func(*args, **kwargs)
        return True, result, None
    except Exception as e:
        error_message = ErrorHandler.handle_llm_pipeline_error(e, func.__name__)
        logger.error(f"LLM実行エラー ({func.__name__}): {str(e)}", exc_info=True)
        return False, None, error_message