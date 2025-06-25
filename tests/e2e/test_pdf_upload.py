"""
E2E Tests for PDF Upload Functionality
"""

import pytest
import tempfile
import os
from pathlib import Path
from playwright.sync_api import Page, expect

from tests.e2e.pages.pdf_upload_page import PDFUploadPage
from tests.e2e.utils.pdf_generator import create_simple_test_pdf, create_large_test_pdf


class TestPDFUpload:
    """PDFアップロード機能のE2Eテスト"""
    
    def test_upload_page_navigation(self, app_page: Page):
        """PDFアップロードページへの遷移をテスト"""
        pdf_page = PDFUploadPage(app_page)
        
        # ページに移動
        pdf_page.navigate_to_upload_page()
        
        # ページが正しく読み込まれたことを確認
        pdf_page.verify_upload_page_loaded()
        
        # 必要なサービスが利用可能であることを確認
        pdf_page.verify_service_requirements()
    
    def test_single_pdf_upload_basic(self, app_page: Page):
        """単一PDFファイルの基本アップロードテスト"""
        pdf_page = PDFUploadPage(app_page)
        
        # テスト用PDFファイルを作成
        test_pdf_path = create_simple_test_pdf()
        test_filename = os.path.basename(test_pdf_path)
        
        try:
            # アップロードページに移動
            pdf_page.navigate_to_upload_page()
            
            # ファイルをアップロード
            pdf_page.upload_pdf_file(test_pdf_path)
            
            # アップロード成功を確認
            pdf_page.verify_file_uploaded(test_filename)
            
            # ファイル情報を確認
            file_info = pdf_page.get_file_info(test_filename)
            assert file_info["filename"] == test_filename
            assert file_info["size_mb"] > 0
            
        finally:
            # テスト用ファイルをクリーンアップ
            if os.path.exists(test_pdf_path):
                os.unlink(test_pdf_path)
    
    def test_pdf_processing_workflow(self, app_page: Page):
        """PDF処理の完全ワークフローテスト"""
        pdf_page = PDFUploadPage(app_page)
        
        # テスト用PDFファイルを作成
        test_pdf_path = create_simple_test_pdf(
            content="新入社員向け研修資料\n会社概要について\n業務フローの説明"
        )
        test_filename = os.path.basename(test_pdf_path)
        
        try:
            # アップロードページに移動
            pdf_page.navigate_to_upload_page()
            
            # ファイルをアップロード
            pdf_page.upload_pdf_file(test_pdf_path)
            pdf_page.verify_file_uploaded(test_filename)
            
            # 処理オプションを設定
            pdf_page.set_chunk_size(256)
            pdf_page.set_overlap_ratio(0.1)
            
            # 処理を開始
            pdf_page.start_processing()
            
            # 処理開始を確認
            pdf_page.wait_for_processing_start()
            
            # 処理完了を待機
            pdf_page.wait_for_processing_complete(timeout=60000)
            
            # 処理成功を確認
            pdf_page.verify_processing_success(file_count=1)
            
        finally:
            if os.path.exists(test_pdf_path):
                os.unlink(test_pdf_path)
    
    def test_multiple_pdf_upload(self, app_page: Page):
        """複数PDFファイルのアップロードテスト"""
        pdf_page = PDFUploadPage(app_page)
        
        # 複数のテスト用PDFファイルを作成
        test_files = []
        try:
            for i in range(2):
                pdf_path = create_simple_test_pdf(
                    content=f"テスト文書 {i+1}\n新入社員向け資料\n第{i+1}章の内容"
                )
                test_files.append(pdf_path)
            
            # アップロードページに移動
            pdf_page.navigate_to_upload_page()
            
            # 複数ファイルをアップロード
            pdf_page.upload_multiple_pdf_files(test_files)
            
            # 各ファイルのアップロードを確認
            for pdf_path in test_files:
                filename = os.path.basename(pdf_path)
                pdf_page.verify_file_uploaded(filename)
            
            # 総ファイルサイズを確認
            total_size = pdf_page.get_total_file_size()
            assert total_size > 0
            
            # 処理を開始
            pdf_page.start_processing()
            pdf_page.wait_for_processing_complete(timeout=90000)
            
            # 複数ファイルの処理成功を確認
            pdf_page.verify_processing_success(file_count=len(test_files))
            
        finally:
            # テスト用ファイルをクリーンアップ
            for pdf_path in test_files:
                if os.path.exists(pdf_path):
                    os.unlink(pdf_path)
    
    def test_large_pdf_upload(self, app_page: Page):
        """大きなPDFファイルのアップロードテスト"""
        pdf_page = PDFUploadPage(app_page)
        
        # 大きなテスト用PDFファイルを作成
        large_pdf_path = create_large_test_pdf(pages=5)
        test_filename = os.path.basename(large_pdf_path)
        
        try:
            # アップロードページに移動
            pdf_page.navigate_to_upload_page()
            
            # 大きなファイルをアップロード
            pdf_page.upload_pdf_file(large_pdf_path)
            pdf_page.verify_file_uploaded(test_filename)
            
            # ファイルサイズを確認（大きなファイルであることを確認）
            file_info = pdf_page.get_file_info(test_filename)
            assert file_info["size_mb"] > 0.1  # 100KB以上
            
            # 処理を開始
            pdf_page.start_processing()
            
            # チャンク生成進捗を確認
            pdf_page.verify_chunk_generation_progress()
            
            # 処理完了を待機（大きなファイルなので長めのタイムアウト）
            pdf_page.wait_for_processing_complete(timeout=120000)
            
            # 処理成功を確認
            pdf_page.verify_processing_success()
            
        finally:
            if os.path.exists(large_pdf_path):
                os.unlink(large_pdf_path)
    
    @pytest.mark.parametrize("chunk_size,overlap_ratio", [
        (256, 0.1),
        (512, 0.2),
        (1024, 0.3),
    ])
    def test_processing_options(self, app_page: Page, chunk_size: int, overlap_ratio: float):
        """異なる処理オプションでのテスト"""
        pdf_page = PDFUploadPage(app_page)
        
        test_pdf_path = create_simple_test_pdf()
        test_filename = os.path.basename(test_pdf_path)
        
        try:
            # アップロードページに移動
            pdf_page.navigate_to_upload_page()
            
            # ファイルをアップロード
            pdf_page.upload_pdf_file(test_pdf_path)
            pdf_page.verify_file_uploaded(test_filename)
            
            # 処理オプションを設定
            pdf_page.set_chunk_size(chunk_size)
            pdf_page.set_overlap_ratio(overlap_ratio)
            
            # 処理を実行
            pdf_page.start_processing()
            pdf_page.wait_for_processing_complete()
            pdf_page.verify_processing_success()
            
        finally:
            if os.path.exists(test_pdf_path):
                os.unlink(test_pdf_path)
    
    def test_invalid_file_upload(self, app_page: Page):
        """無効なファイルのアップロードエラーテスト"""
        pdf_page = PDFUploadPage(app_page)
        
        # テキストファイルを作成（PDFではない）
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp_file:
            tmp_file.write(b"This is not a PDF file")
            invalid_file_path = tmp_file.name
        
        try:
            # アップロードページに移動
            pdf_page.navigate_to_upload_page()
            
            # 無効なファイルをアップロードしようとする
            pdf_page.upload_pdf_file(invalid_file_path)
            
            # 処理を開始（エラーが発生するはず）
            pdf_page.start_processing()
            
            # エラーメッセージを確認
            test_filename = os.path.basename(invalid_file_path)
            pdf_page.verify_processing_error(test_filename)
            
        finally:
            if os.path.exists(invalid_file_path):
                os.unlink(invalid_file_path)
    
    def test_processing_progress_tracking(self, app_page: Page):
        """処理進捗の追跡テスト"""
        pdf_page = PDFUploadPage(app_page)
        
        test_pdf_path = create_simple_test_pdf()
        
        try:
            # アップロードページに移動
            pdf_page.navigate_to_upload_page()
            
            # ファイルをアップロード
            pdf_page.upload_pdf_file(test_pdf_path)
            
            # 処理を開始
            pdf_page.start_processing()
            
            # 進捗を追跡
            progress_checks = 0
            max_checks = 10
            
            while progress_checks < max_checks:
                progress = pdf_page.get_processing_progress()
                if progress is not None:
                    assert 0.0 <= progress <= 1.0
                    if progress >= 1.0:
                        break
                
                # 1秒待機
                app_page.wait_for_timeout(1000)
                progress_checks += 1
            
            # 最終的に処理完了を確認
            pdf_page.wait_for_processing_complete()
            pdf_page.verify_processing_success()
            
        finally:
            if os.path.exists(test_pdf_path):
                os.unlink(test_pdf_path)
    
    def test_chat_navigation_after_upload(self, app_page: Page):
        """アップロード後のチャットページ遷移テスト"""
        pdf_page = PDFUploadPage(app_page)
        
        test_pdf_path = create_simple_test_pdf()
        
        try:
            # 完全なアップロード〜処理フローを実行
            pdf_page.navigate_to_upload_page()
            pdf_page.upload_pdf_file(test_pdf_path)
            pdf_page.start_processing()
            pdf_page.wait_for_processing_complete()
            pdf_page.verify_processing_success()
            
            # チャットページに移動
            pdf_page.navigate_to_chat_after_processing()
            
            # チャットページが正しく表示されることを確認
            expect(app_page.get_by_text("💬 チャット")).to_be_visible()
            expect(app_page.get_by_placeholder("質問を入力してください")).to_be_visible()
            
        finally:
            if os.path.exists(test_pdf_path):
                os.unlink(test_pdf_path)
    
    def test_concurrent_upload_processing(self, app_page: Page):
        """並行アップロード処理のテスト（Edge Case）"""
        pdf_page = PDFUploadPage(app_page)
        
        # 複数の小さなPDFファイルを作成
        test_files = []
        try:
            for i in range(3):
                pdf_path = create_simple_test_pdf(
                    content=f"並行処理テスト {i+1}\n短いコンテンツ"
                )
                test_files.append(pdf_path)
            
            # アップロードページに移動
            pdf_page.navigate_to_upload_page()
            
            # すべてのファイルを一度にアップロード
            pdf_page.upload_multiple_pdf_files(test_files)
            
            # 処理を開始
            pdf_page.start_processing()
            
            # 処理完了を待機（複数ファイルなので長めのタイムアウト）
            pdf_page.wait_for_processing_complete(timeout=180000)
            
            # すべてのファイルの処理成功を確認
            pdf_page.verify_processing_success(file_count=len(test_files))
            
        finally:
            for pdf_path in test_files:
                if os.path.exists(pdf_path):
                    os.unlink(pdf_path)