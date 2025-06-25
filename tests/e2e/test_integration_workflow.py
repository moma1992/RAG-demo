"""
Integration Workflow E2E Tests
完全なユーザージャーニーをテストする統合テスト
"""

import pytest
import os
from playwright.sync_api import Page, expect

from tests.e2e.pages.pdf_upload_page import PDFUploadPage
from tests.e2e.pages.chat_page import ChatPage
from tests.e2e.pages.document_management_page import DocumentManagementPage
from tests.e2e.utils.pdf_generator import create_simple_test_pdf


class TestIntegrationWorkflow:
    """完全なユーザージャーニーの統合テスト"""
    
    @pytest.mark.e2e
    @pytest.mark.smoke
    def test_complete_user_journey(self, app_page: Page):
        """新入社員の完全な利用フローをテスト"""
        
        # Page Objectsを初期化
        pdf_upload_page = PDFUploadPage(app_page)
        chat_page = ChatPage(app_page)
        doc_mgmt_page = DocumentManagementPage(app_page)
        
        # テスト用の会社資料PDFを作成
        company_manual_content = """新入社員向け会社マニュアル
        
第1章: 会社概要
株式会社テストカンパニーは、AI技術を活用したソリューションを提供する企業です。
設立: 2020年4月
従業員数: 150名
本社所在地: 東京都渋谷区

事業内容:
- AI・機械学習ソリューション開発
- データ分析コンサルティング
- クラウドインフラ構築・運用

第2章: 組織構造
- 技術部門: 開発、品質保証、インフラ
- 営業部門: 企画営業、カスタマーサクセス
- 管理部門: 人事、経理、総務

第3章: 勤務制度
勤務時間: 9:00-18:00（フレックスタイム制）
休憩時間: 12:00-13:00
休日: 土日祝日
有給休暇: 入社時10日、以降年間20日付与

福利厚生:
- 社会保険完備
- 交通費全額支給
- 健康診断年1回
- 研修支援制度

第4章: セキュリティポリシー
- PCの持ち出し禁止
- USBメモリ使用禁止
- 情報の外部漏洩厳禁
- パスワードの定期変更義務

第5章: 業務フロー
プロジェクト開始時:
1. キックオフミーティング
2. 要件定義
3. 設計・開発
4. テスト・検証
5. リリース・保守

第6章: 連絡先
人事部: hr@testcompany.co.jp
IT部: it@testcompany.co.jp
総務部: general@testcompany.co.jp"""
        
        test_pdf_path = create_simple_test_pdf(company_manual_content, pages=2)
        test_filename = os.path.basename(test_pdf_path)
        
        try:
            # === Step 1: PDFアップロードフロー ===
            app_page.wait_for_timeout(2000)  # 初期ロード待機
            
            pdf_upload_page.navigate_to_upload_page()
            pdf_upload_page.verify_upload_page_loaded()
            
            # ファイルをアップロード
            pdf_upload_page.upload_pdf_file(test_pdf_path)
            pdf_upload_page.verify_file_uploaded(test_filename)
            
            # 処理オプションを設定
            pdf_upload_page.set_chunk_size(512)
            pdf_upload_page.set_overlap_ratio(0.1)
            
            # 処理を実行
            pdf_upload_page.start_processing()
            pdf_upload_page.wait_for_processing_complete(timeout=90000)
            pdf_upload_page.verify_processing_success()
            
            # === Step 2: 文書管理での確認 ===
            doc_mgmt_page.navigate_to_document_management()
            doc_mgmt_page.verify_document_management_page_loaded()
            
            # アップロードした文書が表示されることを確認
            doc_mgmt_page.verify_document_exists(test_filename)
            
            # 統計情報を確認
            stats = doc_mgmt_page.get_document_statistics()
            assert stats["document_count"] >= 1
            assert stats["total_pages"] >= 2
            assert stats["chunk_count"] > 0
            
            # === Step 3: チャットでの質疑応答 ===
            chat_page.navigate_to_chat_page()
            chat_page.verify_chat_page_loaded()
            
            # 新入社員が聞きそうな質問をテスト
            user_questions = [
                "会社の設立年と従業員数を教えてください",
                "勤務時間と休憩時間について教えてください", 
                "有給休暇は何日もらえますか？",
                "セキュリティポリシーで禁止されていることは何ですか？",
                "プロジェクトの業務フローを教えてください"
            ]
            
            for i, question in enumerate(user_questions):
                print(f"\n--- 質問 {i+1}: {question} ---")
                
                # 質問を送信
                chat_page.send_message(question)
                chat_page.verify_message_sent(question)
                
                # AI応答を待機
                chat_page.wait_for_ai_response(timeout=30000)
                chat_page.verify_ai_response_exists()
                
                # 応答内容の妥当性をチェック
                ai_response = chat_page.get_latest_ai_message()
                assert len(ai_response) > 20, f"AI response should be substantial for question: {question}"
                
                # 引用元が表示されるかチェック
                try:
                    chat_page.expand_citations()
                    chat_page.verify_citations_visible()
                    
                    # 引用情報を取得
                    citations = chat_page.get_citation_info()
                    if len(citations) > 0:
                        print(f"Citations found: {len(citations)}")
                        for citation in citations:
                            print(f"  - {citation.get('filename', 'Unknown')} p.{citation.get('page_number', 'N/A')}")
                
                except Exception as e:
                    print(f"Warning: Citation verification failed: {str(e)}")
                
                # 質問間の待機時間
                app_page.wait_for_timeout(2000)
            
            # === Step 4: 会話履歴の確認 ===
            all_messages = chat_page.get_all_messages()
            expected_messages = len(user_questions) * 2  # ユーザー + AI
            assert len(all_messages) >= expected_messages, f"Expected at least {expected_messages} messages"
            
            # === Step 5: 文書管理での最終確認 ===
            doc_mgmt_page.navigate_to_document_management()
            
            # 文書詳細を確認
            doc_details = doc_mgmt_page.get_document_details(test_filename)
            assert doc_details is not None
            assert doc_details["status"] == "completed"
            assert doc_details["pages"] >= 2
            
            print("\n✅ Complete user journey test passed!")
            print(f"   - Document uploaded: {test_filename}")
            print(f"   - Questions answered: {len(user_questions)}")
            print(f"   - Total messages: {len(all_messages)}")
            print(f"   - Document status: {doc_details['status']}")
            
        finally:
            # クリーンアップ
            if os.path.exists(test_pdf_path):
                os.unlink(test_pdf_path)
    
    @pytest.mark.e2e
    def test_error_recovery_workflow(self, app_page: Page):
        """エラー発生からの回復フローをテスト"""
        
        pdf_upload_page = PDFUploadPage(app_page)
        chat_page = ChatPage(app_page)
        
        # 無効なファイルでエラーをテスト
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp_file:
            tmp_file.write(b"This is not a PDF file")
            invalid_file_path = tmp_file.name
        
        try:
            # 無効ファイルのアップロード
            pdf_upload_page.navigate_to_upload_page()
            pdf_upload_page.upload_pdf_file(invalid_file_path)
            pdf_upload_page.start_processing()
            
            # エラーが適切に処理されることを確認
            filename = os.path.basename(invalid_file_path)
            pdf_upload_page.verify_processing_error(filename)
            
            # 正常なファイルでリカバリーテスト
            valid_pdf_path = create_simple_test_pdf("リカバリーテスト用文書")
            
            pdf_upload_page.upload_pdf_file(valid_pdf_path)
            pdf_upload_page.start_processing()
            pdf_upload_page.wait_for_processing_complete()
            pdf_upload_page.verify_processing_success()
            
            # チャットでの動作確認
            chat_page.navigate_to_chat_page()
            chat_page.send_message("テスト質問です")
            chat_page.wait_for_ai_response()
            chat_page.verify_ai_response_exists()
            
            print("✅ Error recovery workflow test passed!")
            
        finally:
            # クリーンアップ
            for file_path in [invalid_file_path, valid_pdf_path]:
                if file_path and os.path.exists(file_path):
                    os.unlink(file_path)
    
    @pytest.mark.e2e
    @pytest.mark.performance
    def test_performance_workflow(self, app_page: Page):
        """パフォーマンス要件のテスト"""
        
        pdf_upload_page = PDFUploadPage(app_page)
        chat_page = ChatPage(app_page)
        
        # 中程度のサイズのPDFを作成
        content = "パフォーマンステスト用文書\n" + ("テストコンテンツ行\n" * 100)
        test_pdf_path = create_simple_test_pdf(content, pages=3)
        
        try:
            import time
            
            # PDF処理時間を測定
            start_time = time.time()
            
            pdf_upload_page.navigate_to_upload_page()
            pdf_upload_page.upload_pdf_file(test_pdf_path)
            pdf_upload_page.start_processing()
            pdf_upload_page.wait_for_processing_complete(timeout=120000)
            
            processing_time = time.time() - start_time
            
            # 処理時間の確認（2分以内）
            assert processing_time < 120, f"PDF processing took too long: {processing_time:.2f}s"
            
            # チャット応答時間を測定
            chat_page.navigate_to_chat_page()
            
            response_times = []
            test_questions = [
                "この文書について教えてください",
                "主要な内容は何ですか？",
                "詳細情報を教えてください"
            ]
            
            for question in test_questions:
                response_time = chat_page.measure_response_time(question)
                response_times.append(response_time)
                
                # 各応答が30秒以内であることを確認
                assert response_time < 30, f"Response time too slow: {response_time:.2f}s"
                
                app_page.wait_for_timeout(1000)
            
            avg_response_time = sum(response_times) / len(response_times)
            
            print("✅ Performance workflow test passed!")
            print(f"   - PDF processing time: {processing_time:.2f}s")
            print(f"   - Average chat response time: {avg_response_time:.2f}s")
            print(f"   - Individual response times: {[f'{t:.2f}s' for t in response_times]}")
            
            # パフォーマンス要件の確認
            assert processing_time < 120, "PDF processing should complete within 2 minutes"
            assert avg_response_time < 15, "Average chat response should be under 15 seconds"
            
        finally:
            if os.path.exists(test_pdf_path):
                os.unlink(test_pdf_path)
    
    @pytest.mark.e2e
    @pytest.mark.smoke
    def test_multi_document_workflow(self, app_page: Page):
        """複数文書を使用したワークフローテスト"""
        
        pdf_upload_page = PDFUploadPage(app_page)
        chat_page = ChatPage(app_page)
        doc_mgmt_page = DocumentManagementPage(app_page)
        
        # 異なるトピックの文書を作成
        documents = [
            ("人事規定", "人事規定\n勤務時間: 9:00-18:00\n有給休暇: 年20日\n社会保険完備"),
            ("技術ガイドライン", "技術ガイドライン\nプログラミング言語: Python, JavaScript\nフレームワーク: React, FastAPI\nデータベース: PostgreSQL"),
            ("セキュリティポリシー", "セキュリティポリシー\nパスワード要件: 8文字以上\nUSB使用禁止\n定期的なセキュリティ研修実施")
        ]
        
        created_files = []
        
        try:
            # 各文書をアップロード
            for doc_name, content in documents:
                pdf_path = create_simple_test_pdf(content)
                created_files.append(pdf_path)
                
                pdf_upload_page.navigate_to_upload_page()
                pdf_upload_page.upload_pdf_file(pdf_path)
                pdf_upload_page.start_processing()
                pdf_upload_page.wait_for_processing_complete()
                pdf_upload_page.verify_processing_success()
            
            # 文書管理ページで全文書を確認
            doc_mgmt_page.navigate_to_document_management()
            stats = doc_mgmt_page.get_document_statistics()
            assert stats["document_count"] >= len(documents)
            
            # 複数文書にまたがる質問をテスト
            chat_page.navigate_to_chat_page()
            
            cross_document_questions = [
                "勤務時間について教えてください",
                "使用している技術について教えてください",
                "セキュリティ要件について教えてください",
                "USB使用に関するルールはありますか？"
            ]
            
            for question in cross_document_questions:
                chat_page.send_message(question)
                chat_page.wait_for_ai_response()
                
                ai_response = chat_page.get_latest_ai_message()
                assert len(ai_response) > 10, f"Response should not be empty for: {question}"
                
                # 引用元の確認
                try:
                    chat_page.expand_citations()
                    citations = chat_page.get_citation_info()
                    print(f"Question: {question}")
                    print(f"Citations: {len(citations)} documents referenced")
                except:
                    pass
                
                app_page.wait_for_timeout(1500)
            
            print("✅ Multi-document workflow test passed!")
            print(f"   - Documents uploaded: {len(documents)}")
            print(f"   - Cross-document questions: {len(cross_document_questions)}")
            
        finally:
            for pdf_path in created_files:
                if os.path.exists(pdf_path):
                    os.unlink(pdf_path)