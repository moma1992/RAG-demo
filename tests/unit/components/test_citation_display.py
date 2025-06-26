"""
引用表示コンポーネントのテスト - Issue #66

TDD Red-Green-Refactorサイクルで引用表示機能をテスト
"""

import pytest
from unittest.mock import patch, Mock
from typing import List

from components.citation_display import (
    CitationDisplay, CitationGroup, StreamlitCitationWidget, create_sample_references
)
from models.chat import DocumentReference


class TestCitationDisplay:
    """引用表示コンポーネントテスト"""
    
    @pytest.fixture
    def citation_display(self):
        """CitationDisplayインスタンス"""
        return CitationDisplay(theme="default")
    
    @pytest.fixture
    def sample_references(self):
        """サンプル文書参照データ"""
        return [
            DocumentReference(
                filename="マニュアル.pdf",
                page_number=10,
                chunk_id="chunk-001",
                similarity_score=0.95,
                excerpt="これは重要な情報です。新入社員は必ず確認してください。"
            ),
            DocumentReference(
                filename="マニュアル.pdf",
                page_number=11,
                chunk_id="chunk-002",
                similarity_score=0.87,
                excerpt="追加の情報です。研修期間中に学習する内容について説明します。"
            ),
            DocumentReference(
                filename="規程.pdf",
                page_number=5,
                chunk_id="chunk-003",
                similarity_score=0.82,
                excerpt="規程に関する重要事項です。必ず遵守してください。"
            )
        ]
    
    def test_citation_display_initialization(self):
        """CitationDisplay初期化テスト"""
        # デフォルトテーマ
        display = CitationDisplay()
        assert display.theme == "default"
        
        # カスタムテーマ
        display_compact = CitationDisplay(theme="compact")
        assert display_compact.theme == "compact"
        
        display_detailed = CitationDisplay(theme="detailed")
        assert display_detailed.theme == "detailed"
    
    @patch('streamlit.info')
    def test_display_references_empty_list(self, mock_info, citation_display):
        """空の参照リストでの表示テスト"""
        citation_display.display_references([])
        
        mock_info.assert_called_once_with("参照文書はありません")
    
    @patch('streamlit.markdown')
    @patch('streamlit.expander')
    def test_display_references_with_data(self, mock_expander, mock_markdown, citation_display, sample_references):
        """データありでの参照表示テスト"""
        # モックエクスパンダーのセットアップ
        mock_expander_context = Mock()
        mock_expander.return_value.__enter__.return_value = mock_expander_context
        mock_expander.return_value.__exit__.return_value = None
        
        citation_display.display_references(sample_references)
        
        # markdownが呼ばれたことを確認
        assert mock_markdown.called
        
        # 呼び出し内容を検証
        markdown_calls = [call[0][0] for call in mock_markdown.call_args_list]
        
        # ファイル名が含まれていることを確認
        assert any("マニュアル.pdf" in call for call in markdown_calls)
        assert any("規程.pdf" in call for call in markdown_calls)
    
    def test_group_references_by_file(self, citation_display, sample_references):
        """ファイル別グループ化テスト"""
        groups = citation_display._group_references_by_file(sample_references)
        
        # 2つのファイルグループが作成される
        assert len(groups) == 2
        
        # グループ内容を検証
        filenames = [group.filename for group in groups]
        assert "マニュアル.pdf" in filenames
        assert "規程.pdf" in filenames
        
        # マニュアル.pdfグループの検証
        manual_group = next(group for group in groups if group.filename == "マニュアル.pdf")
        assert len(manual_group.references) == 2
        assert manual_group.page_numbers == [10, 11]
        assert manual_group.total_score == (0.95 + 0.87) / 2
        
        # 規程.pdfグループの検証
        rule_group = next(group for group in groups if group.filename == "規程.pdf")
        assert len(rule_group.references) == 1
        assert rule_group.page_numbers == [5]
        assert rule_group.total_score == 0.82
    
    def test_format_page_ranges(self, citation_display):
        """ページ範囲フォーマットテスト"""
        # 単一ページ
        assert citation_display._format_page_ranges([5]) == "p.5"
        
        # 連続ページ
        assert citation_display._format_page_ranges([1, 2, 3]) == "p.1-3"
        
        # 非連続ページ
        assert citation_display._format_page_ranges([1, 3, 5]) == "p.1, p.3, p.5"
        
        # 混合パターン
        assert citation_display._format_page_ranges([1, 2, 5, 6, 7, 10]) == "p.1-2, p.5-7, p.10"
        
        # 空リスト
        assert citation_display._format_page_ranges([]) == ""
    
    def test_get_score_color(self, citation_display):
        """スコア色判定テスト"""
        # 高スコア（緑）
        assert citation_display._get_score_color(0.95) == "#00C851"
        assert citation_display._get_score_color(0.90) == "#00C851"
        
        # 中高スコア（薄緑）
        assert citation_display._get_score_color(0.85) == "#33B679"
        assert citation_display._get_score_color(0.80) == "#33B679"
        
        # 中スコア（黄）
        assert citation_display._get_score_color(0.75) == "#FFBB33"
        assert citation_display._get_score_color(0.70) == "#FFBB33"
        
        # 中低スコア（オレンジ）
        assert citation_display._get_score_color(0.65) == "#FF8800"
        assert citation_display._get_score_color(0.60) == "#FF8800"
        
        # 低スコア（赤）
        assert citation_display._get_score_color(0.55) == "#FF4444"
        assert citation_display._get_score_color(0.40) == "#FF4444"
    
    def test_truncate_text(self, citation_display):
        """テキスト切り詰めテスト"""
        # 短いテキスト（切り詰めなし）
        short_text = "短いテキスト"
        assert citation_display._truncate_text(short_text, 100) == short_text
        
        # 長いテキスト（切り詰めあり）
        long_text = "これは非常に長いテキストです。" * 10
        truncated = citation_display._truncate_text(long_text, 50)
        assert len(truncated) <= 53  # "..." 分を考慮
        assert truncated.endswith("...")
        
        # 単語境界での切り詰め
        text_with_spaces = "This is a very long text with many words that should be truncated"
        truncated = citation_display._truncate_text(text_with_spaces, 30)
        assert truncated.endswith("...")
        assert " " in truncated[:-3]  # "..."を除いた部分に空白があることを確認
    
    @patch('streamlit.markdown')
    def test_display_compact_references(self, mock_markdown, citation_display, sample_references):
        """コンパクト参照表示テスト"""
        citation_display.display_compact_references(sample_references)
        
        # markdownが呼ばれたことを確認
        mock_markdown.assert_called_once()
        
        # 呼び出し内容を検証
        call_content = mock_markdown.call_args[0][0]
        assert "参照文書:" in call_content
        assert "マニュアル.pdf" in call_content
        assert "規程.pdf" in call_content
        assert "p.10-11" in call_content or ("p.10" in call_content and "p.11" in call_content)
        assert "p.5" in call_content
    
    def test_display_compact_references_empty(self, citation_display):
        """空リストでのコンパクト表示テスト"""
        # 例外が発生しないことを確認
        citation_display.display_compact_references([])
    
    @patch('streamlit.bar_chart')
    @patch('streamlit.subheader')
    def test_display_similarity_histogram(self, mock_subheader, mock_bar_chart, citation_display, sample_references):
        """類似度ヒストグラム表示テスト"""
        citation_display.display_similarity_histogram(sample_references)
        
        # サブヘッダーとバーチャートが呼ばれたことを確認
        mock_subheader.assert_called_once_with("類似度分布")
        mock_bar_chart.assert_called_once()
        
        # バーチャートのデータを検証
        chart_data = mock_bar_chart.call_args[0][0]
        assert "類似度範囲" in chart_data
        assert "文書数" in chart_data
        
        # データの内容を検証（サンプルデータに基づく）
        counts = chart_data["文書数"]
        assert counts[0] == 1  # 0.9-1.0: 0.95のみ
        assert counts[1] == 2  # 0.8-0.9: 0.87, 0.82
    
    def test_display_similarity_histogram_empty(self, citation_display):
        """空リストでのヒストグラム表示テスト"""
        # 例外が発生しないことを確認
        citation_display.display_similarity_histogram([])


class TestCitationGroup:
    """CitationGroupテスト"""
    
    def test_citation_group_creation(self):
        """CitationGroup作成テスト"""
        references = [
            DocumentReference("test.pdf", 1, "chunk1", 0.9, "text1"),
            DocumentReference("test.pdf", 2, "chunk2", 0.8, "text2")
        ]
        
        group = CitationGroup(
            filename="test.pdf",
            references=references,
            total_score=0.85,
            page_numbers=[1, 2]
        )
        
        assert group.filename == "test.pdf"
        assert len(group.references) == 2
        assert group.total_score == 0.85
        assert group.page_numbers == [1, 2]


class TestStreamlitCitationWidget:
    """StreamlitCitationWidgetテスト"""
    
    @pytest.fixture
    def sample_references(self):
        """サンプル文書参照データ"""
        return [
            DocumentReference("test.pdf", 1, "chunk1", 0.9, "text1"),
            DocumentReference("test.pdf", 2, "chunk2", 0.8, "text2")
        ]
    
    @patch('streamlit.sidebar')
    @patch('streamlit.subheader')
    def test_render_citation_sidebar(self, mock_subheader, mock_sidebar, sample_references):
        """サイドバー引用表示テスト"""
        # サイドバーコンテキストをモック
        mock_sidebar_context = Mock()
        mock_sidebar.__enter__.return_value = mock_sidebar_context
        mock_sidebar.__exit__.return_value = None
        
        StreamlitCitationWidget.render_citation_sidebar(sample_references)
        
        # サイドバーが使用されたことを確認
        mock_sidebar.__enter__.assert_called_once()
    
    def test_render_citation_sidebar_empty(self):
        """空リストでのサイドバー表示テスト"""
        # 例外が発生しないことを確認
        StreamlitCitationWidget.render_citation_sidebar([])
    
    @patch('streamlit.expander')
    def test_render_citation_expander(self, mock_expander, sample_references):
        """エクスパンダー引用表示テスト"""
        # エクスパンダーコンテキストをモック
        mock_expander_context = Mock()
        mock_expander.return_value.__enter__.return_value = mock_expander_context
        mock_expander.return_value.__exit__.return_value = None
        
        StreamlitCitationWidget.render_citation_expander(sample_references, expanded=True)
        
        # エクスパンダーが呼ばれたことを確認（複数回呼ばれる可能性があるため、最初の呼び出しをチェック）
        first_call = mock_expander.call_args_list[0]
        assert first_call[0][0] == "📄 参照文書 (2件)"
        assert first_call[1]["expanded"] == True
    
    def test_render_citation_expander_empty(self):
        """空リストでのエクスパンダー表示テスト"""
        # 例外が発生しないことを確認
        StreamlitCitationWidget.render_citation_expander([])
    
    @patch('components.citation_display.CitationDisplay.display_compact_references')
    def test_render_inline_citations(self, mock_display, sample_references):
        """インライン引用表示テスト"""
        StreamlitCitationWidget.render_inline_citations(sample_references)
        
        # display_compact_referencesが呼ばれたことを確認
        mock_display.assert_called_once_with(sample_references)
    
    def test_render_inline_citations_empty(self):
        """空リストでのインライン表示テスト"""
        # 例外が発生しないことを確認
        StreamlitCitationWidget.render_inline_citations([])


class TestSampleDataGeneration:
    """サンプルデータ生成テスト"""
    
    def test_create_sample_references(self):
        """サンプル引用データ生成テスト"""
        references = create_sample_references()
        
        assert len(references) == 3
        assert all(isinstance(ref, DocumentReference) for ref in references)
        
        # 最初の参照の検証
        first_ref = references[0]
        assert first_ref.filename == "新入社員マニュアル.pdf"
        assert first_ref.page_number == 15
        assert first_ref.chunk_id == "chunk-001"
        assert first_ref.similarity_score == 0.95
        assert "新入社員の研修期間" in first_ref.excerpt
        
        # スコアが降順になっていることを確認
        scores = [ref.similarity_score for ref in references]
        assert scores == sorted(scores, reverse=True)


class TestCitationDisplayEdgeCases:
    """CitationDisplay エッジケーステスト"""
    
    @pytest.fixture
    def citation_display(self):
        """CitationDisplayインスタンス"""
        return CitationDisplay()
    
    def test_format_page_ranges_edge_cases(self, citation_display):
        """ページ範囲フォーマットのエッジケーステスト"""
        # 重複ページ番号
        assert citation_display._format_page_ranges([1, 1, 2, 2, 3]) == "p.1-3"
        
        # 逆順ページ番号
        assert citation_display._format_page_ranges([5, 3, 1, 2, 4]) == "p.1-5"
        
        # 大きなギャップ
        assert citation_display._format_page_ranges([1, 100, 200]) == "p.1, p.100, p.200"
    
    def test_get_score_color_boundary_values(self, citation_display):
        """スコア色判定の境界値テスト"""
        # 境界値でのテスト
        assert citation_display._get_score_color(1.0) == "#00C851"
        assert citation_display._get_score_color(0.89999) == "#33B679"
        assert citation_display._get_score_color(0.79999) == "#FFBB33"
        assert citation_display._get_score_color(0.69999) == "#FF8800"
        assert citation_display._get_score_color(0.59999) == "#FF4444"
        assert citation_display._get_score_color(0.0) == "#FF4444"
    
    def test_truncate_text_edge_cases(self, citation_display):
        """テキスト切り詰めのエッジケーステスト"""
        # ちょうど境界値のテキスト
        boundary_text = "a" * 50
        assert citation_display._truncate_text(boundary_text, 50) == boundary_text
        
        # 空白のないテキスト
        no_space_text = "a" * 100
        truncated = citation_display._truncate_text(no_space_text, 50)
        assert len(truncated) == 53  # 50 + "..."
        
        # 空文字
        assert citation_display._truncate_text("", 50) == ""
        
        # 非常に短い最大長
        long_text = "This is a long text"
        truncated = citation_display._truncate_text(long_text, 5)
        assert len(truncated) <= 8  # 5 + "..."
