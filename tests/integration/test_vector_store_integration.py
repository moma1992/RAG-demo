"""
ベクトルストアサービスの統合テスト - Issue #57 実装検証

PDF→embedding→保存→検索の完全なフローテスト
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from services.vector_store import VectorStore, VectorStoreError, SearchResult


class TestPDFToSearchIntegration:
    """PDF処理から検索までの統合テストクラス"""
    
    @pytest.mark.asyncio
    async def test_full_pipeline_pdf_to_search(self, mock_supabase_client):
        """統合テスト: PDF→embedding→保存→検索の完全フロー"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # Step 1: PDF処理結果のモック（実際はpdf_processor.pyが生成）
        pdf_chunks = [
            {
                "content": "新入社員研修では、会社の基本理念と業務プロセスを学習します。",
                "filename": "新入社員マニュアル.pdf",
                "page_number": 1,
                "chapter_number": 1,
                "section_name": "研修概要",
                "start_pos": {"x": 100, "y": 200},
                "end_pos": {"x": 400, "y": 250},
                "token_count": 25
            },
            {
                "content": "セキュリティポリシーでは、パスワード管理と情報漏洩防止について規定しています。",
                "filename": "新入社員マニュアル.pdf",
                "page_number": 2,
                "chapter_number": 2,
                "section_name": "セキュリティ",
                "start_pos": {"x": 100, "y": 300},
                "end_pos": {"x": 450, "y": 350},
                "token_count": 30
            },
            {
                "content": "業務効率化のため、タスク管理ツールとコミュニケーションツールの使用を推奨します。",
                "filename": "新入社員マニュアル.pdf",
                "page_number": 3,
                "chapter_number": 3,
                "section_name": "ツール利用",
                "start_pos": {"x": 100, "y": 400},
                "end_pos": {"x": 500, "y": 450},
                "token_count": 35
            }
        ]
        
        # Step 2: 埋め込み生成結果のモック（実際はembeddings.pyが生成）
        embeddings = [
            Mock(embedding=[0.1, 0.2, 0.3] + [0.0] * 1533, metadata={"chunk_id": "0"}),
            Mock(embedding=[0.2, 0.3, 0.4] + [0.0] * 1533, metadata={"chunk_id": "1"}),
            Mock(embedding=[0.3, 0.4, 0.5] + [0.0] * 1533, metadata={"chunk_id": "2"})
        ]
        
        # Step 3: バルク保存の実行
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = Mock()
        
        bulk_result = await store.bulk_insert_embeddings(embeddings, pdf_chunks)
        assert bulk_result is True
        
        # Step 4: 類似検索の実行
        # "パスワード管理について教えて"のクエリをシミュレート
        query_embedding = [0.15, 0.25, 0.35] + [0.0] * 1533  # セキュリティ関連に類似
        
        # 検索結果モック設定
        search_mock_result = Mock()
        search_mock_result.data = [
            {
                "content": "セキュリティポリシーでは、パスワード管理と情報漏洩防止について規定しています。",
                "filename": "新入社員マニュアル.pdf",
                "page_number": 2,
                "distance": 0.1,  # 高い類似度
                "section_name": "セキュリティ",
                "chapter_number": 2,
                "start_pos": {"x": 100, "y": 300},
                "end_pos": {"x": 450, "y": 350},
                "token_count": 30
            },
            {
                "content": "新入社員研修では、会社の基本理念と業務プロセスを学習します。",
                "filename": "新入社員マニュアル.pdf",
                "page_number": 1,
                "distance": 0.3,  # 中程度の類似度
                "section_name": "研修概要",
                "chapter_number": 1,
                "start_pos": {"x": 100, "y": 200},
                "end_pos": {"x": 400, "y": 250},
                "token_count": 25
            }
        ]
        
        mock_supabase_client.rpc.return_value.execute.return_value = search_mock_result
        
        # 検索実行
        search_results = await store.search_similar_embeddings(query_embedding, limit=5)
        
        # Step 5: 統合結果の検証
        assert len(search_results) == 2
        
        # 最も関連性の高い結果（セキュリティ関連）が最初に返されることを確認
        top_result = search_results[0]
        assert "パスワード管理" in top_result.content
        assert top_result.similarity_score == 0.9  # 1.0 - 0.1
        assert top_result.filename == "新入社員マニュアル.pdf"
        assert top_result.page_number == 2
        assert top_result.metadata["section_name"] == "セキュリティ"
        assert top_result.metadata["chapter_number"] == 2
        
        # 2番目の結果検証
        second_result = search_results[1]
        assert second_result.similarity_score == 0.7  # 1.0 - 0.3
        assert second_result.page_number == 1
    
    @pytest.mark.asyncio
    async def test_multilingual_content_integration(self, mock_supabase_client):
        """多言語コンテンツ統合テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # 日英混在のPDFチャンク
        multilingual_chunks = [
            {
                "content": "Employee training covers company values and work processes. 社員研修では会社の価値観を学びます。",
                "filename": "multilingual_manual.pdf",
                "page_number": 1,
                "token_count": 45
            },
            {
                "content": "Security policy requires strong passwords. セキュリティポリシーでは強力なパスワードが必要です。",
                "filename": "multilingual_manual.pdf", 
                "page_number": 2,
                "token_count": 40
            }
        ]
        
        embeddings = [
            Mock(embedding=[0.5, 0.6, 0.7] + [0.0] * 1533, metadata={"chunk_id": "0"}),
            Mock(embedding=[0.6, 0.7, 0.8] + [0.0] * 1533, metadata={"chunk_id": "1"})
        ]
        
        # バルク保存
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = Mock()
        result = await store.bulk_insert_embeddings(embeddings, multilingual_chunks)
        assert result is True
        
        # 英語クエリでの検索
        english_query = [0.55, 0.65, 0.75] + [0.0] * 1533
        
        search_mock = Mock()
        search_mock.data = [
            {
                "content": "Security policy requires strong passwords. セキュリティポリシーでは強力なパスワードが必要です。",
                "filename": "multilingual_manual.pdf",
                "page_number": 2,
                "distance": 0.05,
                "section_name": None,
                "chapter_number": None,
                "start_pos": None,
                "end_pos": None,
                "token_count": 40
            }
        ]
        
        mock_supabase_client.rpc.return_value.execute.return_value = search_mock
        
        results = await store.search_similar_embeddings(english_query, limit=3)
        
        # 検証
        assert len(results) == 1
        assert "Security policy" in results[0].content
        assert "セキュリティポリシー" in results[0].content
        assert results[0].similarity_score == 0.95  # 1.0 - 0.05
    
    @pytest.mark.asyncio 
    async def test_error_recovery_integration(self, mock_supabase_client):
        """エラー回復統合テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # 一部チャンクに無効データが含まれるケース
        mixed_chunks = [
            {
                "content": "正常なチャンク1",
                "filename": "test.pdf",
                "page_number": 1,
                "token_count": 10
            },
            {
                "content": "",  # 空のコンテンツ（無効）
                "filename": "test.pdf",
                "page_number": 2,
                "token_count": 0
            },
            {
                "content": "正常なチャンク3",
                "filename": "test.pdf",
                "page_number": 3,
                "token_count": 15
            }
        ]
        
        embeddings = [
            Mock(embedding=[0.1] * 1536, metadata={"chunk_id": "0"}),
            Mock(embedding=[0.2] * 1536, metadata={"chunk_id": "1"}),
            Mock(embedding=[0.3] * 1536, metadata={"chunk_id": "2"})
        ]
        
        # 無効なチャンクによりエラーが発生することを確認
        with pytest.raises(VectorStoreError, match="contentは空でない文字列である必要があります"):
            await store.bulk_insert_embeddings(embeddings, mixed_chunks)
    
    @pytest.mark.asyncio
    async def test_large_document_integration(self, mock_supabase_client):
        """大規模文書統合テスト"""
        store = VectorStore("https://test.supabase.co", "test-key")
        
        # 500チャンクの大規模文書
        large_chunks = [
            {
                "content": f"大規模文書のチャンク{i}: この部分では重要な情報について説明します。",
                "filename": "大規模マニュアル.pdf",
                "page_number": i // 10 + 1,  # 10チャンクごとに1ページ
                "chapter_number": i // 50 + 1,  # 50チャンクごとに1章
                "section_name": f"第{i//50+1}章-セクション{(i%50)//10+1}",
                "token_count": 35
            }
            for i in range(500)
        ]
        
        embeddings = [
            Mock(embedding=[0.001 * i] * 1536, metadata={"chunk_id": str(i)})
            for i in range(500)
        ]
        
        # バルク保存
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = Mock()
        result = await store.bulk_insert_embeddings(embeddings, large_chunks)
        assert result is True
        
        # 大規模データからの検索
        query_embedding = [0.25] * 1536  # 中間的な値での検索
        
        # 10件の検索結果をモック
        large_search_mock = Mock()
        large_search_mock.data = [
            {
                "content": f"大規模文書のチャンク{250+i}: この部分では重要な情報について説明します。",
                "filename": "大規模マニュアル.pdf",
                "page_number": (250+i) // 10 + 1,
                "distance": 0.01 * i,
                "section_name": f"第{(250+i)//50+1}章-セクション{((250+i)%50)//10+1}",
                "chapter_number": (250+i) // 50 + 1,
                "start_pos": None,
                "end_pos": None,
                "token_count": 35
            }
            for i in range(10)
        ]
        
        mock_supabase_client.rpc.return_value.execute.return_value = large_search_mock
        
        results = await store.search_similar_embeddings(query_embedding, limit=10)
        
        # 検証
        assert len(results) == 10
        assert all("大規模文書のチャンク" in r.content for r in results)
        assert all(r.filename == "大規模マニュアル.pdf" for r in results)
        
        # 類似度順序の確認（距離の小さい順）
        for i in range(len(results) - 1):
            assert results[i].similarity_score >= results[i + 1].similarity_score