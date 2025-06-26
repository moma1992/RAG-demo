"""
Playwright E2E Test Fixtures for Streamlit RAG App
"""

import pytest
import subprocess
import time
import os
import signal
import asyncio
from typing import Generator, Dict, Any
from playwright.sync_api import Page, BrowserContext, Browser, Playwright
from playwright.async_api import async_playwright

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from playwright_config import (
        get_browser_config, 
        get_page_config, 
        get_test_config,
        get_selectors,
        get_streamlit_config,
        BASE_URL,
        TEST_ASSETS
    )
except ImportError:
    # Fallback configuration if playwright_config is not available
    BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8501")
    TEST_ASSETS = {
        "screenshots_dir": "test-results/screenshots",
        "videos_dir": "test-results/videos",
        "sample_pdf": "tests/e2e/fixtures/sample.pdf",
        "large_pdf": "tests/e2e/fixtures/large_sample.pdf"
    }
    
    def get_selectors():
        return {
            "app": "[data-testid='stApp']",
            "sidebar": "[data-testid='stSidebar']",
            "button": "[data-testid='stButton']",
            "file_uploader": "[data-testid='stFileUploader']",
            "chat_input": "[data-testid='stChatInput']",
            "chat_message": "[data-testid='stChatMessage']",
            "success": "[data-testid='stAlert']",
            "error": "[data-testid='stAlert']",
        }
    
    def get_streamlit_config():
        return {
            "app_load_timeout": 10000,
            "component_load_timeout": 5000,
            "api_response_timeout": 15000,
            "file_upload_timeout": 30000,
            "chat_response_timeout": 20000,
        }

# Global variables for process management
streamlit_process = None

@pytest.fixture(scope="session")
def streamlit_app() -> Generator[str, None, None]:
    """
    既存のStreamlitアプリケーションに接続するか、必要に応じて起動する
    セッション全体で1回だけ実行される
    """
    global streamlit_process
    
    print(f"\n🚀 Checking for existing Streamlit app...")
    
    # まず既存のアプリが起動しているかチェック
    try:
        import requests
        response = requests.get(BASE_URL, timeout=3)
        if response.status_code == 200:
            print(f"✅ Found existing Streamlit app at {BASE_URL}")
            yield BASE_URL
            return
    except:
        pass
    
    print(f"🚀 Starting new Streamlit app for E2E testing...")
    
    # 環境変数設定（テスト用）
    test_env = os.environ.copy()
    test_env.update({
        "STREAMLIT_SERVER_HEADLESS": "true",
        "STREAMLIT_SERVER_PORT": "8502",  # 別ポートを使用
        "STREAMLIT_SERVER_ENABLE_CORS": "false",
        "STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION": "false",
        "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
        "STREAMLIT_GLOBAL_DEVELOPMENT_MODE": "false",
        # 本物のAPIキーを使用（既存の環境変数から）
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "SUPABASE_URL": os.getenv("SUPABASE_URL"),
        "SUPABASE_ANON_KEY": os.getenv("SUPABASE_ANON_KEY"),
    })
    
    # テスト用のベースURLを更新
    test_base_url = "http://localhost:8502"
    
    try:
        # Streamlitプロセス起動
        streamlit_process = subprocess.Popen(
            [
                "streamlit", "run", "streamlit_app.py",
                "--server.headless", "true",
                "--server.port", "8502",
                "--server.enableCORS", "false",
                "--server.enableXsrfProtection", "false",
                "--browser.gatherUsageStats", "false"
            ],
            env=test_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid  # プロセスグループ作成
        )
        
        # アプリ起動を待機
        max_retries = 30
        for i in range(max_retries):
            try:
                import requests
                response = requests.get(test_base_url, timeout=2)
                if response.status_code == 200:
                    print(f"✅ Streamlit app started successfully at {test_base_url}")
                    break
            except:
                if i == max_retries - 1:
                    raise Exception(f"Failed to start Streamlit app at {test_base_url}")
                time.sleep(1)
                print(f"⏳ Waiting for app to start... ({i+1}/{max_retries})")
        
        yield test_base_url
        
    finally:
        # クリーンアップ
        if streamlit_process:
            print("\n🛑 Stopping Streamlit app...")
            try:
                # プロセスグループ全体を終了
                os.killpg(os.getpgid(streamlit_process.pid), signal.SIGTERM)
                streamlit_process.wait(timeout=5)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                # 強制終了
                try:
                    os.killpg(os.getpgid(streamlit_process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
            print("✅ Streamlit app stopped")

@pytest.fixture(scope="session")
def browser_context_args():
    """ブラウザコンテキストの引数を設定"""
    context_args = {
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
    }
    
    # E2E_RECORD_VIDEO環境変数が設定されている場合のみビデオ録画を有効化
    if os.getenv("E2E_RECORD_VIDEO", "false").lower() == "true":
        context_args.update({
            "record_video_dir": TEST_ASSETS["videos_dir"],
            "record_video_size": {"width": 1280, "height": 720},
        })
    
    return context_args

@pytest.fixture
def app_page(page: Page, streamlit_app: str) -> Page:
    """
    アプリページに移動し、初期化完了を待つ
    各テストで使用される
    """
    selectors = get_selectors()
    config = get_streamlit_config()
    
    # ページに移動
    page.goto(streamlit_app)
    
    # アプリの読み込み完了を待機
    page.wait_for_selector(
        selectors["app"], 
        timeout=config["app_load_timeout"]
    )
    
    # サイドバーの読み込み完了を待機
    page.wait_for_selector(
        selectors["sidebar"], 
        timeout=config["component_load_timeout"]
    )
    
    # 初期化処理の完了を待機（サービス状態表示が出るまで）
    try:
        page.wait_for_selector(
            "text=サービス状態", 
            timeout=config["component_load_timeout"]
        )
    except:
        # サービス状態表示がない場合はスキップ
        pass
    
    return page

@pytest.fixture
def mock_services(page: Page):
    """
    外部サービスをモックする（APIコール傍受）
    """
    # OpenAI API モック
    page.route("**/v1/embeddings", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='{"data": [{"embedding": ' + str([0.1] * 1536) + '}]}'
    ))
    
    # Claude API モック
    page.route("**/v1/messages", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='{"content": [{"text": "テスト回答です。"}]}'
    ))
    
    # Supabase API モック（必要に応じて）
    # page.route("**/rest/v1/**", lambda route: route.continue_())
    
    return page

@pytest.fixture
def test_pdf_file():
    """テスト用PDFファイルのパスを返す"""
    return TEST_ASSETS["sample_pdf"]

@pytest.fixture
def large_test_pdf_file():
    """大きなテスト用PDFファイルのパスを返す"""
    return TEST_ASSETS["large_pdf"]

@pytest.fixture
def page_helpers():
    """ページ操作ヘルパー関数を提供"""
    
    class PageHelpers:
        @staticmethod
        def wait_for_streamlit_refresh(page: Page, timeout: int = 5000):
            """Streamlitの再実行完了を待機"""
            # プログレスバーの出現と消失を待つ
            try:
                page.wait_for_selector(
                    "[data-testid='stProgressBar']", 
                    timeout=1000
                )
                page.wait_for_selector(
                    "[data-testid='stProgressBar']", 
                    state="detached",
                    timeout=timeout
                )
            except:
                # プログレスバーが表示されない場合は短時間待機
                page.wait_for_timeout(500)
        
        @staticmethod
        def navigate_to_page(page: Page, page_name: str):
            """特定のページに移動"""
            page.get_by_text(page_name).click()
            PageHelpers.wait_for_streamlit_refresh(page)
        
        @staticmethod
        def wait_for_success_message(page: Page, timeout: int = 10000):
            """成功メッセージの表示を待機"""
            return page.wait_for_selector(
                get_selectors()["success"],
                timeout=timeout
            )
        
        @staticmethod
        def wait_for_error_message(page: Page, timeout: int = 5000):
            """エラーメッセージの表示を待機"""
            return page.wait_for_selector(
                get_selectors()["error"],
                timeout=timeout
            )
        
        @staticmethod
        def clear_and_type(page: Page, selector: str, text: str):
            """入力フィールドをクリアして新しいテキストを入力"""
            element = page.locator(selector)
            element.click()
            element.fill("")  # クリア
            element.type(text)
    
    return PageHelpers

@pytest.fixture(autouse=True)
def setup_test_data():
    """各テストの前後でテストデータを準備・クリーンアップ"""
    # テスト前の準備
    yield
    # テスト後のクリーンアップ（必要に応じて）
    pass

# テストファイル作成用ヘルパー
def create_test_pdf():
    """簡単なテスト用PDFを作成"""
    import tempfile
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        c = canvas.Canvas(tmp_file.name, pagesize=letter)
        c.drawString(100, 750, "これはテスト用のPDFファイルです。")
        c.drawString(100, 700, "E2Eテストで使用されます。")
        c.drawString(100, 650, "新入社員向け研修資料")
        c.drawString(100, 600, "第1章: 会社概要")
        c.drawString(100, 550, "第2章: 業務内容")
        c.save()
        return tmp_file.name

# セッション終了時のクリーンアップ
def pytest_sessionfinish(session, exitstatus):
    """テストセッション終了時のクリーンアップ"""
    global streamlit_process
    if streamlit_process:
        try:
            os.killpg(os.getpgid(streamlit_process.pid), signal.SIGTERM)
        except:
            pass