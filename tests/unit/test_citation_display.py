"""
引用表示機能 TDD テストケース

Issue #51: 引用元表示機能実装
Red-Green-Refactor TDDサイクルによる実装
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import List, Dict, Any

from models.citation import Citation, CitationCollection
from components.citation_display import (
    filter_citations_by_confidence,
    get_top_citations_by_document,
    _get_confidence_color
)


class TestCitationModel:
    """Citation データモデル TDD テストクラス"""
    
    def test_citation_creation_basic(self):
        """基本的なCitation作成テスト"""
        citation = Citation(
            document_id="doc-123",
            filename="新入社員ハンドブック.pdf",
            page_number=15,
            chapter_number=2,
            section_name="2.3 勤務時間について",
            content_snippet="勤務時間は午前9時から午後6時までです。",
            similarity_score=0.92,
            start_position={"x": 100.0, "y": 750.0},
            end_position={"x": 500.0, "y": 770.0}
        )
        
        assert citation.document_id == "doc-123"
        assert citation.filename == "新入社員ハンドブック.pdf"
        assert citation.page_number == 15
        assert citation.chapter_number == 2
        assert citation.section_name == "2.3 勤務時間について"
        assert citation.similarity_score == 0.92
        assert citation.chunk_id is not None  # 自動生成される
        assert citation.created_at is not None  # 自動生成される
    
    def test_citation_confidence_percentage(self):
        """信頼度パーセンテージ計算テスト"""
        citation = Citation(
            document_id="doc-1",
            filename="test.pdf",
            page_number=1,
            chapter_number=None,
            section_name=None,
            content_snippet="テスト",
            similarity_score=0.8567,
            start_position={},
            end_position={}
        )
        
        assert citation.confidence_percentage == 85.7
    
    def test_citation_location_text_with_chapter(self):
        """章・セクション情報ありの場所テキストテスト"""
        citation = Citation(
            document_id="doc-1",
            filename="test.pdf",
            page_number=15,
            chapter_number=3,
            section_name="3.1 給与について",
            content_snippet="テスト",
            similarity_score=0.9,
            start_position={},
            end_position={}
        )
        
        expected = "第3章 > 3.1 給与について > p.15"
        assert citation.location_text == expected
    
    def test_citation_location_text_without_chapter(self):
        """章・セクション情報なしの場所テキストテスト"""
        citation = Citation(
            document_id="doc-1",
            filename="test.pdf",
            page_number=5,
            chapter_number=None,
            section_name=None,
            content_snippet="テスト",
            similarity_score=0.8,
            start_position={},
            end_position={}
        )
        
        assert citation.location_text == "p.5"
    
    def test_citation_display_snippet_truncation(self):
        """表示用スニペット省略テスト"""
        long_content = "これは非常に長いテキストです。" * 20  # 200文字超
        
        citation = Citation(
            document_id="doc-1",
            filename="test.pdf",
            page_number=1,
            chapter_number=None,
            section_name=None,
            content_snippet=long_content,
            similarity_score=0.8,
            start_position={},
            end_position={}
        )
        
        snippet = citation.display_snippet
        assert len(snippet) <= 203  # 200文字 + "..."
        assert snippet.endswith("...")
    
    def test_citation_full_context(self):
        """完全な文脈情報取得テスト"""
        citation = Citation(
            document_id="doc-1",
            filename="test.pdf",
            page_number=1,
            chapter_number=None,
            section_name=None,
            content_snippet="重要な情報です",
            similarity_score=0.9,
            start_position={},
            end_position={},
            context_before="前の文脈があります。",
            context_after="後の文脈があります。"
        )
        
        full_context = citation.get_full_context()
        assert "...前の文脈があります。" in full_context
        assert "**重要な情報です**" in full_context
        assert "後の文脈があります。..." in full_context
    
    def test_citation_to_dict(self):
        """辞書形式変換テスト"""
        citation = Citation(
            document_id="doc-1",
            filename="test.pdf",
            page_number=1,
            chapter_number=1,
            section_name="1.1 概要",
            content_snippet="テスト内容",
            similarity_score=0.85,
            start_position={"x": 100.0, "y": 200.0},
            end_position={"x": 300.0, "y": 220.0}
        )
        
        data = citation.to_dict()
        
        assert data["document_id"] == "doc-1"
        assert data["filename"] == "test.pdf"
        assert data["confidence_percentage"] == 85.0
        assert "created_at" in data
    
    def test_citation_from_dict(self):
        """辞書からCitation作成テスト"""
        data = {
            "document_id": "doc-1",
            "filename": "test.pdf",
            "page_number": 1,
            "chapter_number": 1,
            "section_name": "1.1 概要",
            "content_snippet": "テスト内容",
            "similarity_score": 0.85,
            "start_position": {"x": 100.0, "y": 200.0},
            "end_position": {"x": 300.0, "y": 220.0},
            "created_at": "2024-01-01T12:00:00"
        }
        
        citation = Citation.from_dict(data)
        
        assert citation.document_id == "doc-1"
        assert citation.filename == "test.pdf"
        assert citation.similarity_score == 0.85
        assert isinstance(citation.created_at, datetime)


class TestCitationCollection:
    """CitationCollection データモデル TDD テストクラス"""
    
    def create_sample_citations(self) -> List[Citation]:
        """サンプル引用リストを作成"""
        return [
            Citation(
                document_id="doc-1",
                filename="ハンドブック.pdf",
                page_number=10,
                chapter_number=1,
                section_name="1.1 概要",
                content_snippet="新入社員向けの情報です",
                similarity_score=0.95,
                start_position={},
                end_position={}
            ),
            Citation(
                document_id="doc-2",
                filename="規則.pdf",
                page_number=5,
                chapter_number=None,
                section_name=None,
                content_snippet="勤務時間について",
                similarity_score=0.88,
                start_position={},
                end_position={}
            ),
            Citation(
                document_id="doc-1",
                filename="ハンドブック.pdf",
                page_number=15,
                chapter_number=2,
                section_name="2.1 給与",
                content_snippet="給与の支払いについて",
                similarity_score=0.75,
                start_position={},
                end_position={}
            )
        ]
    
    def test_citation_collection_creation(self):
        """CitationCollection作成テスト"""
        citations = self.create_sample_citations()
        collection = CitationCollection(citations=citations, query="新入社員")
        
        assert len(collection.citations) == 3
        assert collection.query == "新入社員"
        assert collection.total_documents == 2  # doc-1, doc-2
    
    def test_sort_by_relevance(self):
        """関連度ソートテスト"""
        citations = self.create_sample_citations()
        collection = CitationCollection(citations=citations, query="test")
        
        sorted_collection = collection.sort_by_relevance()
        scores = [c.similarity_score for c in sorted_collection.citations]
        
        assert scores == [0.95, 0.88, 0.75]  # 降順
    
    def test_filter_by_threshold(self):
        """類似度閾値フィルタリングテスト"""
        citations = self.create_sample_citations()
        collection = CitationCollection(citations=citations, query="test")
        
        filtered = collection.filter_by_threshold(0.8)
        
        assert len(filtered.citations) == 2  # 0.95, 0.88のみ
        assert all(c.similarity_score >= 0.8 for c in filtered.citations)
    
    def test_group_by_document(self):
        """文書別グループ化テスト"""
        citations = self.create_sample_citations()
        collection = CitationCollection(citations=citations, query="test")
        
        groups = collection.group_by_document()
        
        assert len(groups) == 2
        assert "doc-1" in groups
        assert "doc-2" in groups
        assert len(groups["doc-1"]) == 2  # ハンドブックから2件
        assert len(groups["doc-2"]) == 1  # 規則から1件
    
    def test_get_top_citations(self):
        """上位引用取得テスト"""
        citations = self.create_sample_citations()
        collection = CitationCollection(citations=citations, query="test")
        
        top_2 = collection.get_top_citations(2)
        
        assert len(top_2) == 2
        assert top_2[0].similarity_score == 0.95
        assert top_2[1].similarity_score == 0.88
    
    def test_get_statistics(self):
        """統計情報取得テスト"""
        citations = self.create_sample_citations()
        collection = CitationCollection(citations=citations, query="test")
        
        stats = collection.get_statistics()
        
        assert stats["total_citations"] == 3
        assert stats["unique_documents"] == 2
        assert stats["avg_similarity"] == pytest.approx(0.86, rel=1e-2)
        assert stats["max_similarity"] == 0.95
        assert stats["min_similarity"] == 0.75
    
    def test_to_dict_and_from_dict(self):
        """辞書変換と復元テスト"""
        citations = self.create_sample_citations()
        original = CitationCollection(citations=citations, query="test")
        
        # 辞書に変換
        data = original.to_dict()
        
        # 辞書から復元
        restored = CitationCollection.from_dict(data)
        
        assert len(restored.citations) == len(original.citations)
        assert restored.query == original.query
        assert restored.total_documents == original.total_documents


class TestCitationDisplayUtils:
    """引用表示ユーティリティ TDD テストクラス"""
    
    def create_test_citations(self) -> List[Citation]:
        """テスト用引用リストを作成"""
        return [
            Citation(
                document_id="doc-1",
                filename="高信頼度.pdf",
                page_number=1,
                chapter_number=None,
                section_name=None,
                content_snippet="重要な情報",
                similarity_score=0.95,
                start_position={},
                end_position={}
            ),
            Citation(
                document_id="doc-2",
                filename="中信頼度.pdf", 
                page_number=1,
                chapter_number=None,
                section_name=None,
                content_snippet="普通の情報",
                similarity_score=0.75,
                start_position={},
                end_position={}
            ),
            Citation(
                document_id="doc-3",
                filename="低信頼度.pdf",
                page_number=1,
                chapter_number=None,
                section_name=None,
                content_snippet="参考情報",
                similarity_score=0.6,
                start_position={},
                end_position={}
            )
        ]
    
    def test_filter_citations_by_confidence(self):
        """信頼度フィルタリングテスト"""
        citations = self.create_test_citations()
        
        filtered = filter_citations_by_confidence(citations, min_confidence=0.7)
        
        assert len(filtered) == 2
        assert all(c.similarity_score >= 0.7 for c in filtered)
    
    def test_get_top_citations_by_document(self):
        """文書別上位引用取得テスト"""
        citations = [
            # doc-1から2件
            Citation("doc-1", "file1.pdf", 1, None, None, "content1", 0.9, {}, {}),
            Citation("doc-1", "file1.pdf", 2, None, None, "content2", 0.8, {}, {}),
            # doc-2から2件
            Citation("doc-2", "file2.pdf", 1, None, None, "content3", 0.85, {}, {}),
            Citation("doc-2", "file2.pdf", 2, None, None, "content4", 0.7, {}, {}),
        ]
        
        top_citations = get_top_citations_by_document(citations, top_n=1)
        
        # 各文書から最高スコアの1件ずつ取得
        assert len(top_citations) == 2
        scores = [c.similarity_score for c in top_citations]
        assert 0.9 in scores  # doc-1の最高スコア
        assert 0.85 in scores  # doc-2の最高スコア
    
    def test_get_confidence_color(self):
        """信頼度色分けテスト"""
        assert _get_confidence_color(0.95) == "green"    # 90%以上
        assert _get_confidence_color(0.85) == "blue"     # 80-89%
        assert _get_confidence_color(0.75) == "orange"   # 70-79%
        assert _get_confidence_color(0.65) == "red"      # 70%未満


class TestCitationDisplayComponents:
    """引用表示コンポーネント TDD テストクラス（モック版）"""
    
    @patch('streamlit.markdown')
    @patch('streamlit.info')
    def test_display_citations_empty_list(self, mock_info, mock_markdown):
        """空の引用リスト表示テスト"""
        from components.citation_display import display_citations
        
        display_citations([], query="test")
        
        mock_info.assert_called_once_with("📚 関連する文書が見つかりませんでした。")
    
    @patch('streamlit.expander')
    @patch('streamlit.markdown')
    @patch('streamlit.columns')
    @patch('streamlit.metric')
    def test_display_citations_with_data(
        self, 
        mock_metric, 
        mock_columns, 
        mock_markdown, 
        mock_expander
    ):
        """引用データありの表示テスト"""
        from components.citation_display import display_citations
        
        # モックのセットアップ
        mock_columns.return_value = [Mock(), Mock(), Mock(), Mock()]
        mock_expander.return_value.__enter__ = Mock()
        mock_expander.return_value.__exit__ = Mock()
        
        citations = [
            Citation(
                document_id="doc-1",
                filename="test.pdf",
                page_number=1,
                chapter_number=1,
                section_name="1.1 概要",
                content_snippet="テスト内容",
                similarity_score=0.9,
                start_position={},
                end_position={}
            )
        ]
        
        display_citations(citations, query="test")
        
        # マークダウンが呼び出されることを確認
        mock_markdown.assert_called()
        # メトリクスが呼び出されることを確認
        mock_metric.assert_called()


class TestCitationUtilities:
    """引用ユーティリティ TDD テストクラス"""
    
    def test_create_citation_from_search_result(self):
        """検索結果からCitation作成テスト"""
        from models.citation import create_citation_from_search_result
        
        search_result = {
            "document_id": "doc-123",
            "filename": "test.pdf",
            "page_number": 5,
            "chapter_number": 2,
            "section_name": "2.1 概要",
            "content": "テスト用の文書内容です。",
            "start_pos": {"x": 100.0, "y": 200.0},
            "end_pos": {"x": 300.0, "y": 220.0},
            "context_before": "前の文脈",
            "context_after": "後の文脈",
            "id": "chunk-456"
        }
        
        citation = create_citation_from_search_result(
            search_result, 
            query="テスト", 
            similarity_score=0.88
        )
        
        assert citation.document_id == "doc-123"
        assert citation.filename == "test.pdf"
        assert citation.page_number == 5
        assert citation.chapter_number == 2
        assert citation.section_name == "2.1 概要"
        assert citation.content_snippet == "テスト用の文書内容です。"
        assert citation.similarity_score == 0.88
        assert citation.chunk_id == "chunk-456"
    
    def test_merge_citation_collections(self):
        """CitationCollectionマージテスト"""
        from models.citation import merge_citation_collections
        
        collection1 = CitationCollection(
            citations=[
                Citation("doc-1", "file1.pdf", 1, None, None, "content1", 0.9, {}, {})
            ],
            query="query1"
        )
        
        collection2 = CitationCollection(
            citations=[
                Citation("doc-2", "file2.pdf", 1, None, None, "content2", 0.8, {}, {})
            ],
            query="query2"
        )
        
        merged = merge_citation_collections(collection1, collection2)
        
        assert len(merged.citations) == 2
        assert merged.query == "query1 | query2"


class TestCitationError:
    """Citation エラーハンドリング TDD テストクラス"""
    
    def test_citation_error_inheritance(self):
        """CitationErrorの継承確認"""
        from services.citation_service import CitationError
        
        error = CitationError("テストエラー")
        assert isinstance(error, Exception)
        assert str(error) == "テストエラー"
    
    def test_citation_error_with_cause(self):
        """CitationErrorの原因付きエラー"""
        from services.citation_service import CitationError
        
        original_error = ValueError("元のエラー")
        citation_error = CitationError("引用処理エラー") from original_error
        
        assert isinstance(citation_error, CitationError)
        assert citation_error.__cause__ == original_error