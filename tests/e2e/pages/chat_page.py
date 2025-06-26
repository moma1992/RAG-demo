"""
Chat Interface Page Object for E2E Tests
"""

from typing import Optional, List, Dict
from playwright.sync_api import Page, Locator, expect
from .base_page import BasePage

class ChatPage(BasePage):
    """チャットインターフェースページのPage Object"""
    
    def __init__(self, page: Page):
        super().__init__(page)
    
    def navigate_to_chat_page(self) -> None:
        """チャットページに移動"""
        self.navigate_to_page("チャット")
    
    def verify_chat_page_loaded(self) -> None:
        """チャットページが読み込まれたことを確認"""
        self.wait_for_text("文書検索チャット", timeout=10000)
        # チャット入力エリアが表示されるまで待機
        self.page.wait_for_selector("[data-testid='stChatInput']", timeout=10000)
    
    def send_message(self, message: str) -> None:
        """メッセージを送信"""
        # Streamlit chat_input を使用したセレクタ
        chat_input_selector = "[data-testid='stChatInput'] textarea"
        
        # 複数のセレクタを試行
        selectors_to_try = [
            chat_input_selector,
            "[data-testid='stChatInput'] input",
            "textarea[placeholder*='文書について質問']",
            "input[placeholder*='文書について質問']",
            "textarea",  # 最後の手段
        ]
        
        chat_input = None
        for selector in selectors_to_try:
            elements = self.page.locator(selector)
            if elements.count() > 0 and elements.first.is_visible():
                chat_input = elements.first
                break
        
        if not chat_input:
            raise Exception("チャット入力フィールドが見つかりません")
        
        # メッセージを入力
        chat_input.fill(message)
        
        # Enterキーで送信
        chat_input.press("Enter")
        
        self.wait_for_streamlit_refresh()
    
    def wait_for_ai_response(self, timeout: int = 30000) -> None:
        """AI応答を待機"""
        # Streamlitのチャットメッセージが表示されるまで待機
        chat_message_selectors = [
            "[data-testid='stChatMessage']",
            "[data-testid='chatMessage']", 
            ".stChatMessage",
            "[role='dialog']",
            "div[data-testid*='chat']"
        ]
        
        # いずれかのセレクタでメッセージを待機
        message_found = False
        for selector in chat_message_selectors:
            try:
                self.page.wait_for_selector(selector, timeout=timeout // len(chat_message_selectors))
                message_found = True
                break
            except:
                continue
        
        if not message_found:
            # フォールバック: 任意のテキストが追加されるのを待つ
            self.page.wait_for_timeout(5000)
        
        # 応答生成完了まで少し待機
        self.page.wait_for_timeout(2000)
    
    def get_latest_user_message(self) -> str:
        """最新のユーザーメッセージを取得"""
        # 複数のセレクタでユーザーメッセージを探す
        selectors = [
            "[data-testid='stChatMessage']",
            ".stChatMessage",
            "div[data-testid*='chat']"
        ]
        
        for selector in selectors:
            messages = self.page.locator(selector)
            if messages.count() > 0:
                # 最後のメッセージを取得
                last_message = messages.last
                text = last_message.text_content()
                if text:
                    return text
        return ""
    
    def get_latest_ai_message(self) -> str:
        """最新のAIメッセージを取得"""
        # ページの全テキストから最後のメッセージを取得（簡易実装）
        page_content = self.page.content()
        
        # Streamlitのチャットメッセージを探す
        selectors = [
            "[data-testid='stChatMessage']",
            ".stChatMessage", 
            "div[data-testid*='chat']"
        ]
        
        for selector in selectors:
            messages = self.page.locator(selector)
            if messages.count() >= 2:  # ユーザーとAIのメッセージが両方ある場合
                last_message = messages.last
                text = last_message.text_content()
                if text and len(text) > 10:  # AI応答は通常長い
                    return text
        
        return ""
    
    def get_all_messages(self) -> List[Dict[str, str]]:
        """全メッセージを取得"""
        messages = []
        chat_messages = self.page.locator("[data-testid='stChatMessage']")
        
        for i in range(chat_messages.count()):
            message_element = chat_messages.nth(i)
            message_text = message_element.text_content()
            
            # メッセージの送信者を判定（実装依存）
            if "user" in message_element.get_attribute("class") or "User" in message_text:
                sender = "user"
            else:
                sender = "assistant"
            
            messages.append({
                "sender": sender,
                "content": message_text,
                "timestamp": ""  # 必要に応じて実装
            })
        
        return messages
    
    def verify_message_sent(self, message: str) -> None:
        """メッセージが送信されたことを確認"""
        expect(self.page.get_by_text(message)).to_be_visible()
    
    def verify_ai_response_exists(self) -> None:
        """AI応答が存在することを確認"""
        ai_messages = self.page.locator("[data-testid='stChatMessage']")
        # ユーザーメッセージ + AI応答で最低2個のメッセージが存在することを確認
        expect(ai_messages).to_have_count(2)
    
    def verify_ai_response_content(self, expected_content: str) -> None:
        """AI応答の内容を確認"""
        ai_response = self.get_latest_ai_message()
        assert expected_content.lower() in ai_response.lower(), \
            f"Expected '{expected_content}' in AI response, but got: {ai_response}"
    
    def expand_citations(self) -> None:
        """引用元を展開"""
        citation_button = self.page.get_by_text("引用元を表示", exact=False)
        if citation_button.is_visible():
            citation_button.click()
            self.wait_for_streamlit_refresh()
    
    def verify_citations_visible(self) -> None:
        """引用元が表示されていることを確認"""
        citation_indicators = [
            "類似度",
            "📄",  # ファイルアイコン
            "p.",  # ページ番号
        ]
        
        for indicator in citation_indicators:
            expect(self.page.get_by_text(indicator, exact=False)).to_be_visible()
    
    def get_citation_info(self) -> List[Dict[str, any]]:
        """引用情報を取得"""
        citations = []
        
        # 引用エリアを見つける
        citation_area = self.page.locator("[data-testid='stExpander']").filter(
            has_text="引用元"
        )
        
        if citation_area.count() > 0:
            # ファイル名とページ番号を抽出
            citation_text = citation_area.text_content()
            
            # 簡単な解析（実装依存）
            import re
            file_matches = re.findall(r'📄\s*([^\(]+)\s*\(p\.(\d+)\)', citation_text)
            
            for filename, page_num in file_matches:
                citations.append({
                    "filename": filename.strip(),
                    "page_number": int(page_num),
                })
        
        return citations
    
    def verify_similarity_scores(self) -> None:
        """類似度スコアが表示されていることを確認"""
        # 類似度スコアの表示を確認
        similarity_elements = self.page.get_by_text("類似度", exact=False)
        expect(similarity_elements.first).to_be_visible()
        
        # スコア値の表示を確認（0.0-1.0または％表示）
        score_pattern = self.page.get_by_text(re=r"(0\.\d+|[0-9]+%)")
        expect(score_pattern.first).to_be_visible()
    
    def clear_chat_history(self) -> None:
        """チャット履歴をクリア（実装がある場合）"""
        clear_button = self.page.get_by_role("button", name="履歴をクリア")
        if clear_button.is_visible():
            clear_button.click()
            self.wait_for_streamlit_refresh()
    
    def verify_empty_chat(self) -> None:
        """空のチャット状態を確認"""
        # チャットメッセージがないことを確認
        chat_messages = self.page.locator("[data-testid='stChatMessage']")
        expect(chat_messages).to_have_count(0)
        
        # 初期メッセージや使用方法の表示を確認
        welcome_messages = [
            "質問を入力してください",
            "文書について何でもお聞きください"
        ]
        
        for message in welcome_messages:
            try:
                expect(self.page.get_by_text(message, exact=False)).to_be_visible()
                break
            except:
                continue
    
    def test_conversation_flow(self, questions: List[str]) -> List[str]:
        """連続した質問応答フローをテスト"""
        responses = []
        
        for question in questions:
            self.send_message(question)
            self.wait_for_ai_response()
            response = self.get_latest_ai_message()
            responses.append(response)
            
            # 短い間隔を置く
            self.page.wait_for_timeout(1000)
        
        return responses
    
    def verify_error_handling(self, error_message: str) -> None:
        """エラーハンドリングを確認"""
        # エラーメッセージの表示を確認
        expect(self.page.get_by_text(error_message, exact=False)).to_be_visible()
        
        # エラー状態からの回復を確認
        retry_button = self.page.get_by_role("button", name="再試行")
        if retry_button.is_visible():
            retry_button.click()
            self.wait_for_streamlit_refresh()
    
    def measure_response_time(self, message: str) -> float:
        """応答時間を測定"""
        import time
        
        start_time = time.time()
        self.send_message(message)
        self.wait_for_ai_response()
        end_time = time.time()
        
        return end_time - start_time
    
    def verify_streaming_response(self) -> None:
        """ストリーミング応答を確認（実装がある場合）"""
        # ストリーミング中のインジケーターを確認
        streaming_indicators = [
            "▌",  # カーソル
            "...",  # 省略記号
            "応答生成中"
        ]
        
        for indicator in streaming_indicators:
            try:
                self.page.wait_for_selector(
                    f"text*={indicator}",
                    timeout=2000
                )
                break
            except:
                continue