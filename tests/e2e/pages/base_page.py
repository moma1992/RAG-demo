"""
Base Page Object for Streamlit E2E Tests
"""

from typing import Optional, Union
from playwright.sync_api import Page, Locator, expect
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

try:
    from playwright_config import get_selectors, get_streamlit_config
except ImportError:
    # Fallback configuration
    def get_selectors():
        return {
            "app": "[data-testid='stApp']",
            "sidebar": "[data-testid='stSidebar']",
            "main": "[data-testid='stMain']",
            "button": "[data-testid='stButton']",
            "file_uploader": "[data-testid='stFileUploader']",
            "chat_input": "[data-testid='stChatInput']",
            "chat_message": "[data-testid='stChatMessage']",
            "success": "[data-testid='stAlert']",
            "error": "[data-testid='stAlert']",
        }
    
    def get_streamlit_config():
        return {
            "app_load_timeout": 5000,
            "component_load_timeout": 3000,
            "api_response_timeout": 10000,
            "file_upload_timeout": 15000,
            "chat_response_timeout": 10000,
        }

class BasePage:
    """Streamlitアプリの基本ページオブジェクト"""
    
    def __init__(self, page: Page):
        self.page = page
        self.selectors = get_selectors()
        self.config = get_streamlit_config()
    
    def wait_for_app_load(self) -> None:
        """アプリケーションの読み込み完了を待機"""
        self.page.wait_for_selector(
            self.selectors["app"],
            timeout=self.config["app_load_timeout"]
        )
    
    def wait_for_sidebar_load(self) -> None:
        """サイドバーの読み込み完了を待機"""
        self.page.wait_for_selector(
            self.selectors["sidebar"],
            timeout=self.config["component_load_timeout"]
        )
    
    def wait_for_streamlit_refresh(self, timeout: int = 5000) -> None:
        """Streamlitの再実行完了を待機"""
        try:
            # プログレスバーまたはSpinnerの出現を待つ
            self.page.wait_for_selector(
                "[data-testid='stProgressBar'], [data-testid='stSpinner']",
                timeout=1000
            )
            # プログレスバーまたはSpinnerの消失を待つ
            self.page.wait_for_selector(
                "[data-testid='stProgressBar'], [data-testid='stSpinner']",
                state="detached",
                timeout=timeout
            )
        except:
            # プログレスバーが表示されない場合は短時間待機
            self.page.wait_for_timeout(500)
    
    def navigate_to_page(self, page_name: str) -> None:
        """サイドバーで特定のページに移動"""
        # 複数のサイドバーセレクタを試行
        sidebar_selectors = [
            "[data-testid='stSidebar']",
            ".stSidebar",
            "[class*='sidebar']",
            "section[data-testid='stSidebar']"
        ]
        
        sidebar_found = False
        for selector in sidebar_selectors:
            sidebar = self.page.locator(selector)
            if sidebar.count() > 0:
                # サイドバー内でページリンクを探す
                page_link = sidebar.get_by_text(page_name, exact=False)
                if page_link.count() > 0:
                    page_link.first.click()
                    sidebar_found = True
                    break
        
        if not sidebar_found:
            # フォールバック: ページ全体でリンクを探す
            page_link = self.page.get_by_text(page_name, exact=False)
            if page_link.count() > 0:
                page_link.first.click()
        
        self.wait_for_streamlit_refresh()
    
    def get_success_message(self) -> Optional[str]:
        """成功メッセージを取得"""
        try:
            success_element = self.page.locator(self.selectors["success"]).first
            return success_element.text_content()
        except:
            return None
    
    def get_error_message(self) -> Optional[str]:
        """エラーメッセージを取得"""
        try:
            error_element = self.page.locator(self.selectors["error"]).first
            return error_element.text_content()
        except:
            return None
    
    def wait_for_success_message(self, timeout: int = 10000) -> str:
        """成功メッセージの表示を待機して取得"""
        success_locator = self.page.locator(self.selectors["success"])
        success_locator.wait_for(timeout=timeout)
        return success_locator.first.text_content()
    
    def wait_for_error_message(self, timeout: int = 5000) -> str:
        """エラーメッセージの表示を待機して取得"""
        error_locator = self.page.locator(self.selectors["error"])
        error_locator.wait_for(timeout=timeout)
        return error_locator.first.text_content()
    
    def click_button(self, button_text: str) -> None:
        """指定されたテキストのボタンをクリック"""
        button = self.page.get_by_role("button", name=button_text)
        button.click()
        self.wait_for_streamlit_refresh()
    
    def fill_text_input(self, label: str, value: str) -> None:
        """テキスト入力フィールドに値を入力"""
        # ラベルでテキスト入力を見つけて入力
        input_field = self.page.get_by_label(label)
        input_field.fill(value)
    
    def get_text_input_value(self, label: str) -> str:
        """テキスト入力フィールドの値を取得"""
        input_field = self.page.get_by_label(label)
        return input_field.input_value()
    
    def expand_expander(self, title: str) -> None:
        """エキスパンダーを展開"""
        expander = self.page.get_by_text(title)
        expander.click()
        self.wait_for_streamlit_refresh()
    
    def wait_for_element(self, selector: str, timeout: int = 5000) -> Locator:
        """要素の表示を待機"""
        element = self.page.locator(selector)
        element.wait_for(timeout=timeout)
        return element
    
    def wait_for_text(self, text: str, timeout: int = 5000) -> Locator:
        """特定のテキストを含む要素の表示を待機"""
        element = self.page.get_by_text(text)
        element.wait_for(timeout=timeout)
        return element
    
    def scroll_to_bottom(self) -> None:
        """ページの最下部にスクロール"""
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    
    def scroll_to_top(self) -> None:
        """ページの最上部にスクロール"""
        self.page.evaluate("window.scrollTo(0, 0)")
    
    def take_screenshot(self, name: str) -> bytes:
        """スクリーンショットを撮影"""
        return self.page.screenshot(path=f"test-results/screenshots/{name}.png")
    
    def get_page_title(self) -> str:
        """ページタイトルを取得"""
        return self.page.title()
    
    def wait_for_api_response(self, url_pattern: str, timeout: int = 15000) -> None:
        """特定のAPIレスポンスを待機"""
        with self.page.expect_response(url_pattern, timeout=timeout) as response_info:
            pass
        return response_info.value
    
    def verify_page_loaded(self) -> None:
        """ページが正しく読み込まれたことを検証"""
        # アプリケーション本体が表示されていることを確認
        expect(self.page.locator(self.selectors["app"])).to_be_visible()
        
        # サイドバーが表示されていることを確認
        expect(self.page.locator(self.selectors["sidebar"])).to_be_visible()
        
        # メインコンテンツエリアが表示されていることを確認
        expect(self.page.locator(self.selectors["main"])).to_be_visible()
    
    def get_console_errors(self) -> list:
        """コンソールエラーを取得"""
        # この機能はページ初期化時にリスナーを設定する必要がある
        # 実装は具体的なテストケースで行う
        pass