"""
Streamlitヘルパー関数のテスト - Issue #66
"""

import pytest
from unittest.mock import Mock, patch
from utils.streamlit_helpers import (
    get_user_friendly_error_message,
    safe_execute_with_fallback
)


class TestErrorHandling:
    """エラーハンドリング関数のテスト"""
    
    def test_openai_api_key_error(self):
        """OpenAI APIキーエラーのテスト"""
        error = Exception("openai api key authentication failed")
        message = get_user_friendly_error_message(error)
        assert "OpenAI APIキーが正しく設定されていません" in message
    
    def test_openai_rate_limit_error(self):
        """OpenAI レート制限エラーのテスト"""
        error = Exception("openai rate limit exceeded")
        message = get_user_friendly_error_message(error)
        assert "利用制限に達しました" in message
    
    def test_claude_api_error(self):
        """Claude APIエラーのテスト"""
        error = Exception("anthropic api authentication failed")
        message = get_user_friendly_error_message(error)
        assert "Claude APIキーが正しく設定されていません" in message
    
    def test_supabase_connection_error(self):
        """Supabase接続エラーのテスト"""
        error = Exception("supabase connection failed")
        message = get_user_friendly_error_message(error)
        assert "Supabaseへの接続に失敗しました" in message
    
    def test_pdf_processing_error(self):
        """PDF処理エラーのテスト"""
        error = Exception("pdf file is corrupt")
        message = get_user_friendly_error_message(error)
        assert "PDFファイルが破損している" in message
    
    def test_memory_error(self):
        """メモリエラーのテスト"""
        error = Exception("insufficient memory available")
        message = get_user_friendly_error_message(error)
        assert "メモリ不足です" in message
    
    def test_timeout_error(self):
        """タイムアウトエラーのテスト"""
        error = Exception("request timeout occurred")
        message = get_user_friendly_error_message(error)
        assert "タイムアウトしました" in message
    
    def test_generic_error(self):
        """一般的なエラーのテスト"""
        error = Exception("unknown error occurred")
        message = get_user_friendly_error_message(error)
        assert "エラーが発生しました" in message


class TestSafeExecution:
    """安全な実行機能のテスト"""
    
    def test_successful_execution(self):
        """正常実行のテスト"""
        def success_func():
            return "success"
        
        result = safe_execute_with_fallback(success_func)
        assert result == "success"
    
    @patch('streamlit.error')
    @patch('utils.streamlit_helpers.logger')
    def test_execution_with_exception(self, mock_logger, mock_error):
        """例外発生時のテスト"""
        def failing_func():
            raise Exception("test error")
        
        result = safe_execute_with_fallback(failing_func)
        assert result is None
        mock_error.assert_called_once()
        mock_logger.error.assert_called_once()
    
    @patch('streamlit.info')
    @patch('streamlit.error')
    @patch('utils.streamlit_helpers.logger')
    def test_execution_with_fallback(self, mock_logger, mock_error, mock_info):
        """フォールバック実行のテスト"""
        def failing_func():
            raise Exception("primary failed")
        
        def fallback_func():
            return "fallback_result"
        
        result = safe_execute_with_fallback(failing_func, fallback_func)
        assert result == "fallback_result"
        mock_info.assert_called_once_with("代替方法で処理を続行します...")
    
    @patch('streamlit.error')
    @patch('utils.streamlit_helpers.logger')  
    def test_execution_with_failing_fallback(self, mock_logger, mock_error):
        """フォールバックも失敗した場合のテスト"""
        def failing_func():
            raise Exception("primary failed")
        
        def failing_fallback():
            raise Exception("fallback failed")
        
        result = safe_execute_with_fallback(failing_func, failing_fallback)
        assert result is None
        assert mock_error.call_count == 2  # Primary + fallback errors


class TestAPIErrorMapping:
    """API エラーマッピングのテスト"""
    
    @pytest.mark.parametrize("error_string,expected_keyword", [
        ("openai api key invalid", "OpenAI APIキー"),
        ("anthropic authentication failed", "Claude APIキー"),
        ("supabase url not found", "Supabase"),
        ("pdf corrupt file", "PDFファイル"),
        ("memory insufficient", "メモリ不足"),
        ("connection timeout", "タイムアウト"),
    ])
    def test_error_message_mapping(self, error_string, expected_keyword):
        """エラーメッセージマッピングのテスト"""
        error = Exception(error_string)
        message = get_user_friendly_error_message(error)
        assert expected_keyword in message


@pytest.fixture
def mock_streamlit():
    """Streamlitモック"""
    with patch('streamlit.success'), \
         patch('streamlit.error'), \
         patch('streamlit.warning'), \
         patch('streamlit.info'), \
         patch('streamlit.markdown'), \
         patch('streamlit.expander'):
        yield


class TestDisplayFunctions:
    """表示関数のテスト"""
    
    @patch('streamlit.success')
    @patch('streamlit.warning')
    def test_display_service_status_all_ready(self, mock_warning, mock_success):
        """全サービス利用可能時の表示テスト"""
        from utils.streamlit_helpers import display_service_status_indicator
        
        services = {
            "openai_api": True,
            "claude_api": True,
            "supabase": True
        }
        
        display_service_status_indicator(services)
        mock_success.assert_called_once()
        mock_warning.assert_not_called()
    
    @patch('streamlit.success')
    @patch('streamlit.warning')
    @patch('streamlit.expander')
    def test_display_service_status_missing(self, mock_expander, mock_warning, mock_success):
        """一部サービス未設定時の表示テスト"""
        from utils.streamlit_helpers import display_service_status_indicator
        
        services = {
            "openai_api": True,
            "claude_api": False,
            "supabase": True
        }
        
        display_service_status_indicator(services)
        mock_warning.assert_called_once()
        mock_success.assert_not_called()
        mock_expander.assert_called_once()