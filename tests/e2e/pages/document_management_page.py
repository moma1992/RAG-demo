"""
Document Management Page Object for E2E Tests
"""

from typing import Optional, List, Dict
from playwright.sync_api import Page, Locator, expect
from .base_page import BasePage

class DocumentManagementPage(BasePage):
    """文書管理ページのPage Object"""
    
    def __init__(self, page: Page):
        super().__init__(page)
    
    def navigate_to_document_management(self) -> None:
        """文書管理ページに移動"""
        self.navigate_to_page("📊 文書管理")
    
    def verify_document_management_page_loaded(self) -> None:
        """文書管理ページが読み込まれたことを確認"""
        self.wait_for_text("📊 文書管理")
        expect(self.page.get_by_text("登録済み文書一覧")).to_be_visible()
    
    def get_document_statistics(self) -> Dict[str, any]:
        """文書統計情報を取得"""
        stats = {}
        
        try:
            # 統計情報の各項目を取得
            stats_section = self.page.locator("text=統計情報").locator("..")
            
            # 文書数
            doc_count_text = stats_section.get_by_text("文書数:", exact=False).text_content()
            stats["document_count"] = self._extract_number(doc_count_text)
            
            # 総ページ数
            page_count_text = stats_section.get_by_text("総ページ数:", exact=False).text_content()
            stats["total_pages"] = self._extract_number(page_count_text)
            
            # 総ファイルサイズ
            size_text = stats_section.get_by_text("総ファイルサイズ:", exact=False).text_content()
            stats["total_size_mb"] = self._extract_size_mb(size_text)
            
            # チャンク数
            chunk_text = stats_section.get_by_text("チャンク数:", exact=False).text_content()
            stats["chunk_count"] = self._extract_number(chunk_text)
            
        except Exception as e:
            print(f"Error getting document statistics: {e}")
            # デフォルト値を設定
            stats = {
                "document_count": 0,
                "total_pages": 0,
                "total_size_mb": 0.0,
                "chunk_count": 0
            }
        
        return stats
    
    def _extract_number(self, text: str) -> int:
        """テキストから数値を抽出"""
        import re
        match = re.search(r'(\d+)', text)
        return int(match.group(1)) if match else 0
    
    def _extract_size_mb(self, text: str) -> float:
        """テキストからファイルサイズ（MB）を抽出"""
        import re
        match = re.search(r'([\d.]+)\s*MB', text)
        return float(match.group(1)) if match else 0.0
    
    def get_document_list(self) -> List[Dict[str, any]]:
        """登録済み文書一覧を取得"""
        documents = []
        
        try:
            # 文書リストのテーブルまたはリストを見つける
            doc_list_section = self.page.locator("text=登録済み文書一覧").locator("..")
            
            # 各文書エントリを取得
            doc_entries = doc_list_section.locator("[data-testid='stDataFrame'], .document-item, tbody tr")
            
            for i in range(doc_entries.count()):
                entry = doc_entries.nth(i)
                entry_text = entry.text_content()
                
                # 文書情報を解析（実装依存）
                doc_info = self._parse_document_entry(entry_text)
                if doc_info:
                    documents.append(doc_info)
                    
        except Exception as e:
            print(f"Error getting document list: {e}")
        
        return documents
    
    def _parse_document_entry(self, entry_text: str) -> Optional[Dict[str, any]]:
        """文書エントリのテキストを解析"""
        import re
        
        # ファイル名を抽出
        filename_match = re.search(r'([^/\\]+\.pdf)', entry_text, re.IGNORECASE)
        if not filename_match:
            return None
        
        filename = filename_match.group(1)
        
        # ページ数を抽出
        pages_match = re.search(r'(\d+)\s*ページ', entry_text)
        pages = int(pages_match.group(1)) if pages_match else 0
        
        # ファイルサイズを抽出
        size_match = re.search(r'([\d.]+)\s*MB', entry_text)
        size_mb = float(size_match.group(1)) if size_match else 0.0
        
        # 処理状態を抽出
        if "完了" in entry_text:
            status = "completed"
        elif "処理中" in entry_text:
            status = "processing"
        elif "エラー" in entry_text:
            status = "error"
        else:
            status = "unknown"
        
        return {
            "filename": filename,
            "pages": pages,
            "size_mb": size_mb,
            "status": status
        }
    
    def verify_document_exists(self, filename: str) -> None:
        """指定された文書が存在することを確認"""
        expect(self.page.get_by_text(filename)).to_be_visible()
    
    def verify_document_not_exists(self, filename: str) -> None:
        """指定された文書が存在しないことを確認"""
        doc_element = self.page.get_by_text(filename)
        expect(doc_element).not_to_be_visible()
    
    def delete_document(self, filename: str) -> None:
        """指定された文書を削除"""
        # 文書の削除ボタンを見つけてクリック
        doc_row = self.page.locator(f"text={filename}").locator("..")
        delete_button = doc_row.get_by_role("button", name="削除")
        
        if delete_button.is_visible():
            delete_button.click()
            
            # 確認ダイアログがある場合は確認
            confirm_button = self.page.get_by_role("button", name="確認")
            if confirm_button.is_visible():
                confirm_button.click()
            
            self.wait_for_streamlit_refresh()
    
    def verify_document_deleted(self, filename: str) -> None:
        """文書が削除されたことを確認"""
        # 削除成功メッセージを確認
        success_messages = [
            "削除されました",
            "削除完了",
            f"{filename} を削除しました"
        ]
        
        message_found = False
        for message in success_messages:
            try:
                expect(self.page.get_by_text(message, exact=False)).to_be_visible()
                message_found = True
                break
            except:
                continue
        
        if not message_found:
            # メッセージが見つからない場合は、リストから消えていることを確認
            self.verify_document_not_exists(filename)
    
    def get_document_details(self, filename: str) -> Optional[Dict[str, any]]:
        """特定の文書の詳細情報を取得"""
        documents = self.get_document_list()
        for doc in documents:
            if doc["filename"] == filename:
                return doc
        return None
    
    def verify_document_status(self, filename: str, expected_status: str) -> None:
        """文書の処理状態を確認"""
        doc_details = self.get_document_details(filename)
        assert doc_details is not None, f"Document {filename} not found"
        assert doc_details["status"] == expected_status, \
            f"Expected status {expected_status}, but got {doc_details['status']}"
    
    def refresh_document_list(self) -> None:
        """文書リストを更新"""
        refresh_button = self.page.get_by_role("button", name="更新")
        if refresh_button.is_visible():
            refresh_button.click()
            self.wait_for_streamlit_refresh()
    
    def sort_documents_by(self, sort_criteria: str) -> None:
        """文書を指定された基準でソート"""
        sort_options = {
            "name": "ファイル名",
            "size": "サイズ", 
            "date": "日付",
            "pages": "ページ数"
        }
        
        if sort_criteria in sort_options:
            sort_button = self.page.get_by_text(sort_options[sort_criteria])
            if sort_button.is_visible():
                sort_button.click()
                self.wait_for_streamlit_refresh()
    
    def filter_documents_by_status(self, status: str) -> None:
        """文書を状態でフィルタリング"""
        filter_options = {
            "all": "すべて",
            "completed": "完了",
            "processing": "処理中",
            "error": "エラー"
        }
        
        if status in filter_options:
            filter_dropdown = self.page.get_by_text("状態でフィルタ")
            if filter_dropdown.is_visible():
                filter_dropdown.click()
                option = self.page.get_by_text(filter_options[status])
                option.click()
                self.wait_for_streamlit_refresh()
    
    def search_documents(self, search_term: str) -> None:
        """文書を検索"""
        search_input = self.page.get_by_placeholder("文書を検索")
        if search_input.is_visible():
            search_input.fill(search_term)
            search_input.press("Enter")
            self.wait_for_streamlit_refresh()
    
    def verify_search_results(self, search_term: str, expected_count: int) -> None:
        """検索結果を確認"""
        documents = self.get_document_list()
        matching_docs = [
            doc for doc in documents 
            if search_term.lower() in doc["filename"].lower()
        ]
        
        assert len(matching_docs) == expected_count, \
            f"Expected {expected_count} search results, but got {len(matching_docs)}"
    
    def export_document_list(self, format_type: str = "csv") -> None:
        """文書リストをエクスポート"""
        export_button = self.page.get_by_role("button", name="エクスポート")
        if export_button.is_visible():
            export_button.click()
            
            # フォーマット選択
            format_option = self.page.get_by_text(format_type.upper())
            if format_option.is_visible():
                format_option.click()
                
            self.wait_for_streamlit_refresh()
    
    def verify_empty_document_list(self) -> None:
        """文書リストが空であることを確認"""
        empty_messages = [
            "文書がありません",
            "登録された文書はありません",
            "0件の文書"
        ]
        
        message_found = False
        for message in empty_messages:
            try:
                expect(self.page.get_by_text(message, exact=False)).to_be_visible()
                message_found = True
                break
            except:
                continue
        
        if not message_found:
            # 統計情報で確認
            stats = self.get_document_statistics()
            assert stats["document_count"] == 0, "Document count should be 0 for empty list"
    
    def wait_for_document_processing(self, filename: str, timeout: int = 120000) -> None:
        """文書の処理完了を待機"""
        start_time = self.page.evaluate("Date.now()")
        
        while True:
            current_time = self.page.evaluate("Date.now()")
            if current_time - start_time > timeout:
                raise TimeoutError(f"Document processing timeout for {filename}")
            
            doc_details = self.get_document_details(filename)
            if doc_details and doc_details["status"] == "completed":
                break
            elif doc_details and doc_details["status"] == "error":
                raise Exception(f"Document processing failed for {filename}")
            
            # 5秒間隔で確認
            self.page.wait_for_timeout(5000)
            self.refresh_document_list()
    
    def get_document_chunk_info(self, filename: str) -> Optional[Dict[str, any]]:
        """文書のチャンク情報を取得"""
        # 文書詳細画面に移動（実装がある場合）
        doc_link = self.page.get_by_text(filename)
        if doc_link.is_visible():
            doc_link.click()
            self.wait_for_streamlit_refresh()
            
            # チャンク情報を取得
            chunk_info = {
                "total_chunks": self._extract_number(
                    self.page.get_by_text("チャンク数:", exact=False).text_content()
                ),
                "average_tokens": self._extract_number(
                    self.page.get_by_text("平均トークン数:", exact=False).text_content()
                )
            }
            
            # 文書リストに戻る
            back_button = self.page.get_by_role("button", name="戻る")
            if back_button.is_visible():
                back_button.click()
                self.wait_for_streamlit_refresh()
            
            return chunk_info
        
        return None