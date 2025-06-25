"""
PDF Upload Page Object for E2E Tests
"""

from typing import Optional, List
from playwright.sync_api import Page, Locator, expect
from .base_page import BasePage

class PDFUploadPage(BasePage):
    """PDFアップロードページのPage Object"""
    
    def __init__(self, page: Page):
        super().__init__(page)
    
    def navigate_to_upload_page(self) -> None:
        """PDFアップロードページに移動"""
        self.navigate_to_page("📁 PDF文書アップロード")
    
    def verify_upload_page_loaded(self) -> None:
        """アップロードページが読み込まれたことを確認"""
        self.wait_for_text("📁 PDF文書アップロード")
        expect(self.page.get_by_text("PDFファイルを選択してください")).to_be_visible()
    
    def upload_pdf_file(self, file_path: str) -> None:
        """PDFファイルをアップロード"""
        # ファイルアップローダーを見つけて ファイルを設定
        file_input = self.page.locator("input[type='file']").first
        file_input.set_input_files(file_path)
        
        # アップロード完了まで待機
        self.wait_for_streamlit_refresh()
    
    def upload_multiple_pdf_files(self, file_paths: List[str]) -> None:
        """複数のPDFファイルをアップロード"""
        file_input = self.page.locator("input[type='file']").first
        file_input.set_input_files(file_paths)
        self.wait_for_streamlit_refresh()
    
    def verify_file_uploaded(self, filename: str) -> None:
        """ファイルがアップロードされたことを確認"""
        # ファイル名が表示されることを確認
        expect(self.page.get_by_text(filename)).to_be_visible()
        
        # アップロード成功メッセージを確認
        uploaded_message = self.page.get_by_text("ファイルがアップロードされました")
        expect(uploaded_message).to_be_visible()
    
    def set_chunk_size(self, size: int) -> None:
        """チャンクサイズを設定"""
        # 処理オプションエキスパンダーを展開
        self.expand_expander("⚙️ 処理オプション")
        
        # チャンクサイズスライダーを設定
        chunk_slider = self.page.get_by_text("チャンクサイズ（トークン数）").locator("..").locator("input")
        chunk_slider.fill(str(size))
    
    def set_overlap_ratio(self, ratio: float) -> None:
        """オーバーラップ率を設定"""
        # オーバーラップ率スライダーを設定
        overlap_slider = self.page.get_by_text("オーバーラップ率").locator("..").locator("input")
        overlap_slider.fill(str(ratio))
    
    def start_processing(self) -> None:
        """PDF処理を開始"""
        process_button = self.page.get_by_role("button", name="PDF処理を開始")
        process_button.click()
    
    def wait_for_processing_complete(self, timeout: int = 60000) -> None:
        """処理完了を待機"""
        # プログレスバーの出現を待つ
        try:
            self.page.wait_for_selector(
                "[data-testid='stProgress']",
                timeout=2000
            )
        except:
            pass
        
        # 処理完了メッセージを待つ
        self.page.wait_for_selector(
            "text=処理完了",
            timeout=timeout
        )
    
    def verify_processing_success(self, file_count: int = 1) -> None:
        """処理成功を確認"""
        # 成功メッセージを確認
        success_message = f"{file_count}個のPDFファイルの処理が完了しました"
        expect(self.page.get_by_text(success_message)).to_be_visible()
        
        # チャットページへの移動ボタンが表示されることを確認
        chat_button = self.page.get_by_role("button", name="チャットページに移動")
        expect(chat_button).to_be_visible()
    
    def verify_processing_error(self, filename: str) -> None:
        """処理エラーを確認"""
        error_message = f"ファイル {filename} の処理中にエラーが発生しました"
        expect(self.page.get_by_text(error_message, exact=False)).to_be_visible()
    
    def get_file_info(self, filename: str) -> dict:
        """アップロードされたファイルの情報を取得"""
        # ファイル情報表示エリアを見つける
        file_info_text = self.page.get_by_text(f"📄 {filename}").text_content()
        
        # ファイルサイズを抽出（例: "📄 sample.pdf (1.2 MB)"）
        import re
        size_match = re.search(r'\(([\d.]+) MB\)', file_info_text)
        size_mb = float(size_match.group(1)) if size_match else 0.0
        
        return {
            "filename": filename,
            "size_mb": size_mb
        }
    
    def get_total_file_size(self) -> float:
        """総ファイルサイズを取得"""
        total_size_text = self.page.get_by_text("総サイズ:", exact=False).text_content()
        import re
        size_match = re.search(r'総サイズ.*?([\d.]+) MB', total_size_text)
        return float(size_match.group(1)) if size_match else 0.0
    
    def navigate_to_chat_after_processing(self) -> None:
        """処理完了後にチャットページに移動"""
        chat_button = self.page.get_by_role("button", name="チャットページに移動")
        chat_button.click()
        self.wait_for_streamlit_refresh()
    
    def verify_service_requirements(self) -> None:
        """必要なサービスが利用可能であることを確認"""
        # サービス状態を確認（エラーがないこと）
        error_messages = [
            "PDF処理には以下のサービスが必要です",
            "設定ページでAPIキーを確認してください"
        ]
        
        for error_msg in error_messages:
            error_elements = self.page.get_by_text(error_msg)
            if error_elements.count() > 0:
                raise AssertionError(f"Service requirement error: {error_msg}")
    
    def get_processing_progress(self) -> Optional[float]:
        """処理進捗を取得（0.0-1.0）"""
        try:
            progress_bar = self.page.locator("[data-testid='stProgress']").first
            if progress_bar.is_visible():
                # プログレスバーの値を取得（実装依存）
                progress_value = progress_bar.get_attribute("aria-valuenow")
                if progress_value:
                    return float(progress_value) / 100.0
            return None
        except:
            return None
    
    def wait_for_processing_start(self, timeout: int = 5000) -> None:
        """処理開始を待機"""
        # 処理開始を示すメッセージやプログレスバーの出現を待つ
        try:
            self.page.wait_for_selector(
                "text=処理中, [data-testid='stProgress']",
                timeout=timeout
            )
        except:
            # 処理が即座に完了する場合もある
            pass
    
    def verify_chunk_generation_progress(self) -> None:
        """チャンク生成進捗を確認"""
        # チャンク生成メッセージの表示を確認
        chunk_messages = [
            "埋め込み生成中",
            "チャンク"
        ]
        
        for message in chunk_messages:
            try:
                self.page.wait_for_selector(
                    f"text*={message}",
                    timeout=2000
                )
                break
            except:
                continue