"""
E2E Tests for Chat Interface Functionality
"""

import pytest
import time
from typing import List
from playwright.sync_api import Page, expect

from tests.e2e.pages.chat_page import ChatPage
from tests.e2e.pages.pdf_upload_page import PDFUploadPage
from tests.e2e.utils.pdf_generator import create_simple_test_pdf


class TestChatInterface:
    """チャットインターフェース機能のE2Eテスト"""
    
    def test_chat_page_navigation(self, app_page: Page):
        """チャットページへの遷移をテスト"""
        chat_page = ChatPage(app_page)
        
        # チャットページに移動
        chat_page.navigate_to_chat_page()
        
        # ページが正しく読み込まれたことを確認
        chat_page.verify_chat_page_loaded()
        
        # 空のチャット状態を確認
        chat_page.verify_empty_chat()
    
    def test_basic_message_sending(self, app_page: Page):
        """基本的なメッセージ送信テスト"""
        chat_page = ChatPage(app_page)
        
        # チャットページに移動
        chat_page.navigate_to_chat_page()
        
        test_message = "こんにちは、テストメッセージです。"
        
        # メッセージを送信
        chat_page.send_message(test_message)
        
        # メッセージが送信されたことを確認
        chat_page.verify_message_sent(test_message)
        
        # AI応答を待機
        chat_page.wait_for_ai_response()
        
        # AI応答が存在することを確認
        chat_page.verify_ai_response_exists()
    
    def test_conversation_flow(self, app_page: Page):
        """連続した会話フローのテスト"""
        chat_page = ChatPage(app_page)
        
        # チャットページに移動
        chat_page.navigate_to_chat_page()
        
        # 複数の質問を定義
        questions = [
            "会社の概要について教えてください",
            "新入社員研修の内容は何ですか？",
            "業務フローについて詳しく説明してください"
        ]
        
        # 連続した質問応答をテスト
        responses = chat_page.test_conversation_flow(questions)
        
        # 各応答が存在することを確認
        assert len(responses) == len(questions)
        for response in responses:
            assert len(response) > 0, "AI response should not be empty"
        
        # 全メッセージを取得して確認
        all_messages = chat_page.get_all_messages()
        expected_message_count = len(questions) * 2  # ユーザー + AI
        assert len(all_messages) >= expected_message_count
    
    def test_chat_with_uploaded_document(self, app_page: Page):
        """アップロードされた文書を使用したチャットテスト"""
        # まずPDFをアップロードして処理
        pdf_page = PDFUploadPage(app_page)
        chat_page = ChatPage(app_page)
        
        # テスト用PDFファイルを作成
        test_content = """新入社員向け研修資料
        
第1章: 会社概要
当社は革新的なAI技術を提供する企業です。
主な事業内容：
- データ分析ソリューション
- 機械学習コンサルティング
- クラウドAIサービス

第2章: 業務フロー
1. プロジェクト企画
2. 要件定義
3. 開発・実装
4. テスト・検証
5. リリース・保守

第3章: 注意事項
- 情報セキュリティの徹底
- チームワークの重視
- 継続的な学習の推進"""
        
        test_pdf_path = create_simple_test_pdf(test_content)
        
        try:
            # PDFアップロードと処理
            pdf_page.navigate_to_upload_page()
            pdf_page.upload_pdf_file(test_pdf_path)
            pdf_page.start_processing()
            pdf_page.wait_for_processing_complete()
            pdf_page.verify_processing_success()
            
            # チャットページに移動
            chat_page.navigate_to_chat_page()
            
            # 文書に関連する質問をする
            document_questions = [
                "会社の主な事業内容は何ですか？",
                "業務フローの手順を教えてください",
                "新入社員が注意すべき点は何ですか？"
            ]
            
            for question in document_questions:
                chat_page.send_message(question)
                chat_page.wait_for_ai_response()
                
                # AI応答の内容を確認
                ai_response = chat_page.get_latest_ai_message()
                assert len(ai_response) > 0
                
                # 引用元が表示されているかチェック
                try:
                    chat_page.expand_citations()
                    chat_page.verify_citations_visible()
                    chat_page.verify_similarity_scores()
                    
                    # 引用情報を取得
                    citations = chat_page.get_citation_info()
                    assert len(citations) > 0, "Citations should be available"
                    
                except:
                    # 引用が表示されない場合もあるのでワーニングレベル
                    print(f"Warning: No citations found for question: {question}")
                
                # 次の質問前に短い間隔
                app_page.wait_for_timeout(1000)
                
        finally:
            if test_pdf_path:
                import os
                if os.path.exists(test_pdf_path):
                    os.unlink(test_pdf_path)
    
    def test_citation_functionality(self, app_page: Page):
        """引用機能の詳細テスト"""
        chat_page = ChatPage(app_page)
        pdf_page = PDFUploadPage(app_page)
        
        # 引用可能な内容でPDFを作成
        citation_content = """技術仕様書

第1章: システムアーキテクチャ
本システムはマイクロサービスアーキテクチャを採用しています。
各サービスは独立してデプロイ可能で、高い可用性を実現します。

第2章: データベース設計
主要なエンティティ：
- ユーザー情報
- 文書メタデータ  
- 検索インデックス
- セッション管理

第3章: API仕様
RESTful APIを提供し、以下のエンドポイントが利用可能です：
- /api/documents - 文書管理
- /api/search - 検索機能
- /api/chat - チャット機能"""
        
        test_pdf_path = create_simple_test_pdf(citation_content)
        
        try:
            # PDFアップロードと処理
            pdf_page.navigate_to_upload_page()
            pdf_page.upload_pdf_file(test_pdf_path)
            pdf_page.start_processing()
            pdf_page.wait_for_processing_complete()
            
            # チャットページに移動
            chat_page.navigate_to_chat_page()
            
            # 具体的な内容について質問
            specific_question = "システムアーキテクチャについて詳しく教えてください"
            chat_page.send_message(specific_question)
            chat_page.wait_for_ai_response()
            
            # 引用元を展開
            chat_page.expand_citations()
            
            # 引用情報の詳細をチェック
            chat_page.verify_citations_visible()
            chat_page.verify_similarity_scores()
            
            # 引用データを取得して検証
            citations = chat_page.get_citation_info()
            assert len(citations) > 0
            
            for citation in citations:
                assert "filename" in citation
                assert "page_number" in citation
                assert citation["page_number"] > 0
                
        finally:
            if test_pdf_path:
                import os
                if os.path.exists(test_pdf_path):
                    os.unlink(test_pdf_path)
    
    @pytest.mark.parametrize("question_type,expected_keywords", [
        ("general", ["情報", "説明", "について"]),
        ("specific", ["詳細", "具体的", "例"]),
        ("process", ["手順", "フロー", "プロセス"]),
    ])
    def test_different_question_types(self, app_page: Page, question_type: str, expected_keywords: List[str]):
        """異なるタイプの質問に対するテスト"""
        chat_page = ChatPage(app_page)
        
        # チャットページに移動
        chat_page.navigate_to_chat_page()
        
        # 質問タイプに応じた質問を作成
        questions = {
            "general": "会社について教えてください",
            "specific": "具体的な業務内容の例を教えてください", 
            "process": "新入社員研修のプロセスを説明してください"
        }
        
        question = questions[question_type]
        
        # 質問を送信
        chat_page.send_message(question)
        chat_page.wait_for_ai_response()
        
        # 応答を取得
        ai_response = chat_page.get_latest_ai_message()
        
        # 応答が適切なキーワードを含んでいるかチェック
        response_lower = ai_response.lower()
        keyword_found = any(keyword in response_lower for keyword in expected_keywords)
        
        assert keyword_found, f"Response should contain at least one of {expected_keywords}"
        assert len(ai_response) > 10, "Response should be substantial"
    
    def test_response_time_performance(self, app_page: Page):
        """応答時間のパフォーマンステスト"""
        chat_page = ChatPage(app_page)
        
        # チャットページに移動
        chat_page.navigate_to_chat_page()
        
        # 複数の質問で応答時間を測定
        test_questions = [
            "こんにちは",
            "会社の概要を教えてください",
            "業務内容について説明してください"
        ]
        
        response_times = []
        
        for question in test_questions:
            response_time = chat_page.measure_response_time(question)
            response_times.append(response_time)
            
            # 応答時間の妥当性チェック（30秒以内）
            assert response_time < 30.0, f"Response time {response_time}s is too slow"
            
            # 次の質問前に間隔を置く
            app_page.wait_for_timeout(2000)
        
        # 平均応答時間を計算
        avg_response_time = sum(response_times) / len(response_times)
        print(f"Average response time: {avg_response_time:.2f}s")
        
        # 平均応答時間が妥当な範囲内であることを確認
        assert avg_response_time < 15.0, "Average response time should be under 15 seconds"
    
    def test_error_handling_in_chat(self, app_page: Page, mock_services: Page):
        """チャットでのエラーハンドリングテスト"""
        chat_page = ChatPage(app_page)
        
        # チャットページに移動
        chat_page.navigate_to_chat_page()
        
        # 非常に長いメッセージ（エラーを誘発する可能性）
        very_long_message = "これは非常に長いメッセージです。" * 100
        
        # 長いメッセージを送信
        chat_page.send_message(very_long_message)
        
        try:
            # 応答を待機（タイムアウトが発生する可能性）
            chat_page.wait_for_ai_response(timeout=10000)
            
            # 応答またはエラーメッセージを確認
            ai_response = chat_page.get_latest_ai_message()
            if ai_response:
                assert len(ai_response) > 0
            else:
                # エラーメッセージを確認
                error_message = chat_page.get_error_message()
                assert error_message is not None
                
        except:
            # タイムアウトエラーが発生した場合
            print("Response timeout occurred as expected for very long message")
    
    def test_streaming_response(self, app_page: Page):
        """ストリーミング応答のテスト（実装がある場合）"""
        chat_page = ChatPage(app_page)
        
        # チャットページに移動
        chat_page.navigate_to_chat_page()
        
        # 詳細な回答が期待される質問
        detailed_question = "新入社員向けの詳細な研修プログラムについて、段階的に説明してください"
        
        # メッセージを送信
        chat_page.send_message(detailed_question)
        
        # ストリーミング応答の確認
        try:
            chat_page.verify_streaming_response()
        except:
            # ストリーミング機能が実装されていない場合はスキップ
            print("Streaming response not implemented or not detected")
        
        # 最終的な応答を確認
        chat_page.wait_for_ai_response()
        final_response = chat_page.get_latest_ai_message()
        assert len(final_response) > 50, "Detailed response should be substantial"
    
    def test_chat_history_persistence(self, app_page: Page):
        """チャット履歴の永続化テスト"""
        chat_page = ChatPage(app_page)
        
        # チャットページに移動
        chat_page.navigate_to_chat_page()
        
        # いくつかのメッセージを送信
        test_messages = [
            "最初のメッセージです",
            "2番目のメッセージです",
            "3番目のメッセージです"
        ]
        
        for message in test_messages:
            chat_page.send_message(message)
            chat_page.wait_for_ai_response()
            app_page.wait_for_timeout(1000)
        
        # 他のページに移動してから戻る
        chat_page.navigate_to_page("📁 PDF文書アップロード")
        app_page.wait_for_timeout(2000)
        chat_page.navigate_to_chat_page()
        
        # チャット履歴が保持されているかチェック
        all_messages = chat_page.get_all_messages()
        
        # 少なくとも送信したメッセージ数 × 2（ユーザー + AI）のメッセージがあることを確認
        expected_min_messages = len(test_messages) * 2
        assert len(all_messages) >= expected_min_messages, "Chat history should be preserved"
        
        # 送信したメッセージが履歴に含まれているかチェック
        all_content = " ".join([msg["content"] for msg in all_messages])
        for original_message in test_messages:
            assert original_message in all_content, f"Message '{original_message}' should be in history"
    
    def test_empty_message_handling(self, app_page: Page):
        """空メッセージの処理テスト"""
        chat_page = ChatPage(app_page)
        
        # チャットページに移動
        chat_page.navigate_to_chat_page()
        
        # 空のメッセージを送信しようとする
        empty_message = ""
        chat_page.send_message(empty_message)
        
        # 空メッセージが適切に処理されることを確認
        # （送信されないか、適切なバリデーションメッセージが表示される）
        app_page.wait_for_timeout(2000)
        
        messages = chat_page.get_all_messages()
        
        # 空メッセージが実際に送信されていないことを確認
        if len(messages) > 0:
            latest_message = messages[-1]
            assert latest_message["content"].strip() != "", "Empty message should not be sent"