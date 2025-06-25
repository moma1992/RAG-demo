"""
Playwright E2E Test Configuration for Streamlit RAG App
"""

from playwright.sync_api import Playwright
import os

# 基本設定
BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8501")
HEADLESS = os.getenv("E2E_HEADLESS", "true").lower() == "true"
SLOW_MO = int(os.getenv("E2E_SLOW_MO", "0"))  # ミリ秒
TIMEOUT = int(os.getenv("E2E_TIMEOUT", "30000"))  # 30秒

# ブラウザ設定
BROWSER_CONFIG = {
    "headless": HEADLESS,
    "slow_mo": SLOW_MO,
    "args": [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-web-security",
        "--allow-running-insecure-content",
    ] if os.getenv("CI") else []
}

# ページ設定
PAGE_CONFIG = {
    "viewport": {"width": 1280, "height": 720},
    "ignore_https_errors": True,
    "java_script_enabled": True,
}

# テスト設定
TEST_CONFIG = {
    "base_url": BASE_URL,
    "timeout": TIMEOUT,
    "video_retention": "retain-on-failure",
    "screenshot_on_failure": True,
    "trace_on_failure": True,
}

# ファイルパス設定
TEST_ASSETS = {
    "fixtures_dir": "tests/e2e/fixtures",
    "sample_pdf": "tests/e2e/fixtures/sample.pdf",
    "large_pdf": "tests/e2e/fixtures/large_sample.pdf",
    "outputs_dir": "test-results",
    "screenshots_dir": "test-results/screenshots",
    "videos_dir": "test-results/videos",
    "traces_dir": "test-results/traces",
}

# Streamlit特有の設定
STREAMLIT_CONFIG = {
    "app_load_timeout": 10000,  # アプリ読み込み待機時間
    "component_load_timeout": 5000,  # コンポーネント読み込み待機時間
    "api_response_timeout": 15000,  # API応答待機時間
    "file_upload_timeout": 30000,  # ファイルアップロード待機時間
    "chat_response_timeout": 20000,  # チャット応答待機時間
}

# セレクタ設定（Streamlit特有のdata-testid）
SELECTORS = {
    "app": "[data-testid='stApp']",
    "sidebar": "[data-testid='stSidebar']",
    "main": "[data-testid='stMain']",
    "file_uploader": "[data-testid='stFileUploader']",
    "button": "[data-testid='stButton']",
    "text_input": "[data-testid='stTextInput']",
    "chat_input": "[data-testid='stChatInput']",
    "chat_message": "[data-testid='stChatMessage']",
    "success": "[data-testid='stSuccess']",
    "error": "[data-testid='stError']",
    "warning": "[data-testid='stWarning']",
    "info": "[data-testid='stInfo']",
    "progress": "[data-testid='stProgress']",
    "expander": "[data-testid='stExpander']",
    "columns": "[data-testid='stColumns']",
    "tabs": "[data-testid='stTabs']",
}

# エラーハンドリング設定
ERROR_CONFIG = {
    "retry_attempts": 3,
    "retry_delay": 1000,  # ミリ秒
    "ignore_errors": [
        "net::ERR_ABORTED",  # キャンセルされたリクエスト
        "favicon.ico",  # ファビコンエラーを無視
    ],
    "expected_console_errors": [
        "Failed to load resource",
        "favicon.ico",
    ]
}

# デバッグ設定
DEBUG_CONFIG = {
    "console_logging": os.getenv("E2E_DEBUG", "false").lower() == "true",
    "network_logging": False,
    "trace_enabled": True,
    "video_enabled": True,
}

def get_browser_config():
    """ブラウザ設定を取得"""
    return BROWSER_CONFIG

def get_page_config():
    """ページ設定を取得"""
    return PAGE_CONFIG

def get_test_config():
    """テスト設定を取得"""
    return TEST_CONFIG

def get_selectors():
    """セレクタ設定を取得"""
    return SELECTORS

def get_streamlit_config():
    """Streamlit設定を取得"""
    return STREAMLIT_CONFIG