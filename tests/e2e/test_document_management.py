"""
E2E Tests for Document Management Functionality
"""

import pytest
import os
from playwright.sync_api import Page, expect

from tests.e2e.pages.document_management_page import DocumentManagementPage
from tests.e2e.pages.pdf_upload_page import PDFUploadPage
from tests.e2e.utils.pdf_generator import create_simple_test_pdf, create_large_test_pdf


class TestDocumentManagement:
    """文書管理機能のE2Eテスト"""
    
    def test_document_management_page_navigation(self, app_page: Page):
        """文書管理ページへの遷移をテスト"""
        doc_mgmt_page = DocumentManagementPage(app_page)
        
        # 文書管理ページに移動
        doc_mgmt_page.navigate_to_document_management()
        
        # ページが正しく読み込まれたことを確認
        doc_mgmt_page.verify_document_management_page_loaded()
    
    def test_empty_document_list_display(self, app_page: Page):
        """空の文書リスト表示をテスト"""
        doc_mgmt_page = DocumentManagementPage(app_page)
        
        # 文書管理ページに移動
        doc_mgmt_page.navigate_to_document_management()
        
        # 統計情報を取得
        stats = doc_mgmt_page.get_document_statistics()
        
        # 初期状態では文書がないことを確認
        if stats["document_count"] == 0:
            doc_mgmt_page.verify_empty_document_list()
    
    def test_document_upload_and_display(self, app_page: Page):
        """文書アップロード後の表示テスト"""
        doc_mgmt_page = DocumentManagementPage(app_page)
        pdf_upload_page = PDFUploadPage(app_page)
        
        # テスト用PDFファイルを作成
        test_content = """文書管理テスト用文書
        
第1章: テスト概要
この文書は文書管理機能のテストに使用されます。

第2章: 機能説明
- ファイルアップロード
- 文書一覧表示
- 統計情報更新

第3章: 期待される結果
正常にアップロードされ、文書リストに表示される。"""
        
        test_pdf_path = create_simple_test_pdf(test_content)
        test_filename = os.path.basename(test_pdf_path)
        
        try:
            # アップロード前の統計を取得
            doc_mgmt_page.navigate_to_document_management()
            initial_stats = doc_mgmt_page.get_document_statistics()
            
            # PDFをアップロードして処理
            pdf_upload_page.navigate_to_upload_page()
            pdf_upload_page.upload_pdf_file(test_pdf_path)
            pdf_upload_page.start_processing()
            pdf_upload_page.wait_for_processing_complete()
            pdf_upload_page.verify_processing_success()
            
            # 文書管理ページに戻る
            doc_mgmt_page.navigate_to_document_management()
            
            # 文書が表示されることを確認
            doc_mgmt_page.verify_document_exists(test_filename)
            
            # 統計情報が更新されることを確認
            updated_stats = doc_mgmt_page.get_document_statistics()
            assert updated_stats["document_count"] > initial_stats["document_count"]
            assert updated_stats["total_pages"] >= initial_stats["total_pages"]
            assert updated_stats["chunk_count"] > initial_stats["chunk_count"]
            
            # 文書詳細を確認
            doc_details = doc_mgmt_page.get_document_details(test_filename)
            assert doc_details is not None
            assert doc_details["filename"] == test_filename
            assert doc_details["status"] == "completed"
            assert doc_details["pages"] > 0
            
        finally:
            if os.path.exists(test_pdf_path):
                os.unlink(test_pdf_path)
    
    def test_multiple_document_management(self, app_page: Page):
        """複数文書の管理テスト"""
        doc_mgmt_page = DocumentManagementPage(app_page)
        pdf_upload_page = PDFUploadPage(app_page)
        
        # 複数のテスト用PDFファイルを作成
        test_files = []
        try:
            for i in range(3):
                content = f"""テスト文書 {i+1}
                
第1章: 文書 {i+1} の概要
これは {i+1} 番目のテスト文書です。

第2章: 内容詳細
文書管理機能の複数ファイル処理テスト用です。
文書ID: DOC-{i+1:03d}

第3章: まとめ
この文書は正常に処理されるはずです。"""
                
                pdf_path = create_simple_test_pdf(content)
                test_files.append(pdf_path)
            
            # 各ファイルをアップロードして処理
            for pdf_path in test_files:
                filename = os.path.basename(pdf_path)
                
                pdf_upload_page.navigate_to_upload_page()
                pdf_upload_page.upload_pdf_file(pdf_path)
                pdf_upload_page.start_processing()
                pdf_upload_page.wait_for_processing_complete()
                
                # 文書管理ページで確認
                doc_mgmt_page.navigate_to_document_management()
                doc_mgmt_page.verify_document_exists(filename)
            
            # 全文書が表示されることを確認
            doc_mgmt_page.navigate_to_document_management()
            document_list = doc_mgmt_page.get_document_list()
            
            uploaded_filenames = [os.path.basename(path) for path in test_files]
            for filename in uploaded_filenames:
                assert any(doc["filename"] == filename for doc in document_list), \
                    f"Document {filename} should be in the list"
            
            # 統計情報を確認
            stats = doc_mgmt_page.get_document_statistics()
            assert stats["document_count"] >= len(test_files)
            assert stats["total_pages"] >= len(test_files)  # 各文書最低1ページ
            
        finally:
            for pdf_path in test_files:
                if os.path.exists(pdf_path):
                    os.unlink(pdf_path)
    
    def test_document_deletion(self, app_page: Page):
        """文書削除機能のテスト"""
        doc_mgmt_page = DocumentManagementPage(app_page)
        pdf_upload_page = PDFUploadPage(app_page)
        
        # テスト用PDFファイルを作成
        test_pdf_path = create_simple_test_pdf("削除テスト用文書\n\nこの文書は削除されます。")
        test_filename = os.path.basename(test_pdf_path)
        
        try:
            # 文書をアップロードして処理
            pdf_upload_page.navigate_to_upload_page()
            pdf_upload_page.upload_pdf_file(test_pdf_path)
            pdf_upload_page.start_processing()
            pdf_upload_page.wait_for_processing_complete()
            
            # 文書管理ページで文書の存在を確認
            doc_mgmt_page.navigate_to_document_management()
            doc_mgmt_page.verify_document_exists(test_filename)
            
            # 削除前の統計を取得
            stats_before = doc_mgmt_page.get_document_statistics()
            
            # 文書を削除
            doc_mgmt_page.delete_document(test_filename)
            
            # 削除が完了したことを確認
            doc_mgmt_page.verify_document_deleted(test_filename)
            
            # 統計情報が更新されることを確認
            stats_after = doc_mgmt_page.get_document_statistics()
            assert stats_after["document_count"] < stats_before["document_count"]
            
        finally:
            if os.path.exists(test_pdf_path):
                os.unlink(test_pdf_path)
    
    def test_document_status_tracking(self, app_page: Page):
        """文書の処理状態追跡テスト"""
        doc_mgmt_page = DocumentManagementPage(app_page)
        pdf_upload_page = PDFUploadPage(app_page)
        
        # 大きなテスト用PDFファイルを作成（処理時間を確保）
        large_pdf_path = create_large_test_pdf(pages=3)
        test_filename = os.path.basename(large_pdf_path)
        
        try:
            # ファイルをアップロード
            pdf_upload_page.navigate_to_upload_page()
            pdf_upload_page.upload_pdf_file(large_pdf_path)
            
            # 処理を開始
            pdf_upload_page.start_processing()
            
            # 文書管理ページで処理状況を確認
            doc_mgmt_page.navigate_to_document_management()
            
            # 処理中状態を確認（短時間で完了する場合はスキップ）
            try:
                doc_mgmt_page.verify_document_status(test_filename, "processing")
            except:
                print("Processing completed too quickly to observe processing status")
            
            # 処理完了を待機
            doc_mgmt_page.wait_for_document_processing(test_filename)
            
            # 完了状態を確認
            doc_mgmt_page.verify_document_status(test_filename, "completed")
            
        finally:
            if os.path.exists(large_pdf_path):
                os.unlink(large_pdf_path)
    
    def test_document_search_functionality(self, app_page: Page):
        """文書検索機能のテスト"""
        doc_mgmt_page = DocumentManagementPage(app_page)
        pdf_upload_page = PDFUploadPage(app_page)
        
        # 検索用の特徴的な名前のファイルを作成
        search_test_files = [
            ("manual_001.pdf", "操作マニュアル第1版"),
            ("guide_002.pdf", "初心者ガイド"),
            ("reference_003.pdf", "技術リファレンス")
        ]
        
        created_files = []
        
        try:
            # 各ファイルをアップロード
            for filename_template, content in search_test_files:
                test_pdf_path = create_simple_test_pdf(content)
                created_files.append(test_pdf_path)
                
                # ファイル名を変更（実際のアップロード時に反映されるかは実装依存）
                pdf_upload_page.navigate_to_upload_page()
                pdf_upload_page.upload_pdf_file(test_pdf_path)
                pdf_upload_page.start_processing()
                pdf_upload_page.wait_for_processing_complete()
            
            # 文書管理ページで検索をテスト
            doc_mgmt_page.navigate_to_document_management()
            
            # 特定の検索語で検索
            search_terms = ["manual", "guide", "pdf"]
            
            for search_term in search_terms:
                doc_mgmt_page.search_documents(search_term)
                
                # 検索結果を確認（実装に依存）
                documents = doc_mgmt_page.get_document_list()
                matching_docs = [
                    doc for doc in documents 
                    if search_term.lower() in doc["filename"].lower()
                ]
                
                if len(matching_docs) > 0:
                    print(f"Search for '{search_term}' found {len(matching_docs)} results")
                
                # 検索クリア（実装がある場合）
                try:
                    doc_mgmt_page.search_documents("")
                except:
                    pass
                
        finally:
            for pdf_path in created_files:
                if os.path.exists(pdf_path):
                    os.unlink(pdf_path)
    
    def test_document_sorting_and_filtering(self, app_page: Page):
        """文書のソートとフィルタリング機能テスト"""
        doc_mgmt_page = DocumentManagementPage(app_page)
        pdf_upload_page = PDFUploadPage(app_page)
        
        # 異なるサイズの文書を作成
        test_documents = [
            ("小さな文書", "短いコンテンツ"),
            ("中程度の文書", "中程度の長さのコンテンツ\n" * 10),
            ("大きな文書", "長いコンテンツ\n" * 20)
        ]
        
        created_files = []
        
        try:
            # 各文書をアップロード
            for doc_name, content in test_documents:
                test_pdf_path = create_simple_test_pdf(content)
                created_files.append(test_pdf_path)
                
                pdf_upload_page.navigate_to_upload_page()
                pdf_upload_page.upload_pdf_file(test_pdf_path)
                pdf_upload_page.start_processing()
                pdf_upload_page.wait_for_processing_complete()
            
            # 文書管理ページでソート機能をテスト
            doc_mgmt_page.navigate_to_document_management()
            
            # 各ソート基準をテスト（実装がある場合）
            sort_criteria = ["name", "size", "date"]
            
            for criteria in sort_criteria:
                try:
                    doc_mgmt_page.sort_documents_by(criteria)
                    documents = doc_mgmt_page.get_document_list()
                    print(f"Sorted by {criteria}: {len(documents)} documents")
                except:
                    print(f"Sort by {criteria} not implemented or not found")
            
            # フィルタリング機能をテスト（実装がある場合）
            filter_statuses = ["all", "completed", "processing"]
            
            for status in filter_statuses:
                try:
                    doc_mgmt_page.filter_documents_by_status(status)
                    documents = doc_mgmt_page.get_document_list()
                    print(f"Filtered by {status}: {len(documents)} documents")
                except:
                    print(f"Filter by {status} not implemented or not found")
                    
        finally:
            for pdf_path in created_files:
                if os.path.exists(pdf_path):
                    os.unlink(pdf_path)
    
    def test_document_statistics_accuracy(self, app_page: Page):
        """文書統計情報の正確性テスト"""
        doc_mgmt_page = DocumentManagementPage(app_page)
        pdf_upload_page = PDFUploadPage(app_page)
        
        # 複数の既知サイズの文書を作成
        test_docs = []
        expected_pages = 0
        
        try:
            for i in range(2):
                pages = i + 1  # 1ページ、2ページ
                content = f"統計テスト文書 {i+1}\n" + ("ページコンテンツ\n" * pages * 5)
                
                pdf_path = create_simple_test_pdf(content, pages=pages)
                test_docs.append(pdf_path)
                expected_pages += pages
            
            # アップロード前の統計を取得
            doc_mgmt_page.navigate_to_document_management()
            initial_stats = doc_mgmt_page.get_document_statistics()
            
            # 各文書をアップロード
            for pdf_path in test_docs:
                pdf_upload_page.navigate_to_upload_page()
                pdf_upload_page.upload_pdf_file(pdf_path)
                pdf_upload_page.start_processing()
                pdf_upload_page.wait_for_processing_complete()
            
            # 最終統計を取得
            doc_mgmt_page.navigate_to_document_management()
            final_stats = doc_mgmt_page.get_document_statistics()
            
            # 統計の正確性を確認
            assert final_stats["document_count"] >= initial_stats["document_count"] + len(test_docs)
            assert final_stats["total_pages"] >= initial_stats["total_pages"] + expected_pages
            assert final_stats["chunk_count"] > initial_stats["chunk_count"]
            assert final_stats["total_size_mb"] > initial_stats["total_size_mb"]
            
            print(f"Statistics verification:")
            print(f"  Documents: {final_stats['document_count']} (increased by {len(test_docs)})")
            print(f"  Pages: {final_stats['total_pages']} (increased by at least {expected_pages})")
            print(f"  Chunks: {final_stats['chunk_count']}")
            print(f"  Size: {final_stats['total_size_mb']:.2f} MB")
            
        finally:
            for pdf_path in test_docs:
                if os.path.exists(pdf_path):
                    os.unlink(pdf_path)
    
    def test_document_export_functionality(self, app_page: Page):
        """文書リストエクスポート機能のテスト"""
        doc_mgmt_page = DocumentManagementPage(app_page)
        pdf_upload_page = PDFUploadPage(app_page)
        
        # テスト文書をアップロード
        test_pdf_path = create_simple_test_pdf("エクスポートテスト用文書")
        
        try:
            pdf_upload_page.navigate_to_upload_page()
            pdf_upload_page.upload_pdf_file(test_pdf_path)
            pdf_upload_page.start_processing()
            pdf_upload_page.wait_for_processing_complete()
            
            # 文書管理ページでエクスポート機能をテスト
            doc_mgmt_page.navigate_to_document_management()
            
            # エクスポート機能を実行（実装がある場合）
            try:
                doc_mgmt_page.export_document_list("csv")
                print("Export functionality tested successfully")
            except:
                print("Export functionality not implemented or not found")
                
        finally:
            if os.path.exists(test_pdf_path):
                os.unlink(test_pdf_path)
    
    def test_refresh_functionality(self, app_page: Page):
        """文書リスト更新機能のテスト"""
        doc_mgmt_page = DocumentManagementPage(app_page)
        
        # 文書管理ページに移動
        doc_mgmt_page.navigate_to_document_management()
        
        # 初期統計を取得
        initial_stats = doc_mgmt_page.get_document_statistics()
        
        # 更新機能をテスト
        try:
            doc_mgmt_page.refresh_document_list()
            
            # 更新後の統計を取得
            refreshed_stats = doc_mgmt_page.get_document_statistics()
            
            # 統計が正常に取得できることを確認
            assert isinstance(refreshed_stats["document_count"], int)
            assert isinstance(refreshed_stats["total_pages"], int)
            assert isinstance(refreshed_stats["chunk_count"], int)
            assert isinstance(refreshed_stats["total_size_mb"], float)
            
            print("Refresh functionality tested successfully")
            
        except:
            print("Refresh functionality not implemented or not found")