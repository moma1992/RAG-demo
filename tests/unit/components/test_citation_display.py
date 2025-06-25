"""
引用表示コンポーネントのテスト - Issue #66
"""

import pytest
from unittest.mock import Mock, patch
from components.citation_display import CitationDisplay, StreamlitCitationWidget


class TestCitationDisplay:
    """CitationDisplayクラスのテスト"""
    
    def test_init(self):
        """初期化テスト"""
        citation_display = CitationDisplay()
        assert citation_display.theme == "default"
        
        citation_display_compact = CitationDisplay(theme="compact")
        assert citation_display_compact.theme == "compact"
    
    def test_format_page_ranges(self):
        """ページ範囲フォーマットテスト"""
        citation_display = CitationDisplay()
        
        # 単一ページ
        assert citation_display._format_page_ranges([1]) == "p.1"
        
        # 連続ページ
        assert citation_display._format_page_ranges([1, 2, 3]) == "p.1-3"
        
        # 不連続ページ
        assert citation_display._format_page_ranges([1, 3, 5]) == "p.1, p.3, p.5"
        
        # 混合ページ
        assert citation_display._format_page_ranges([1, 2, 4, 5, 6, 8]) == "p.1-2, p.4-6, p.8"
        
        # 空リスト
        assert citation_display._format_page_ranges([]) == ""
    
    def test_get_score_color(self):
        """スコア色取得テスト"""
        citation_display = CitationDisplay()
        
        assert citation_display._get_score_color(0.95) == "#00C851"  # 緑
        assert citation_display._get_score_color(0.85) == "#33B679"  # 薄緑
        assert citation_display._get_score_color(0.75) == "#FFBB33"  # 黄
        assert citation_display._get_score_color(0.65) == "#FF8800"  # オレンジ
        assert citation_display._get_score_color(0.55) == "#FF4444"  # 赤
    
    def test_truncate_text(self):
        """テキスト切り詰めテスト"""
        citation_display = CitationDisplay()
        
        # 短いテキスト
        short_text = "短いテキスト"
        assert citation_display._truncate_text(short_text, 100) == short_text
        
        # 長いテキスト
        long_text = "これは非常に長いテキストの例です。" * 10
        truncated = citation_display._truncate_text(long_text, 50)
        assert len(truncated) <= 53  # "..." を含む
        assert truncated.endswith("...")
    
    @patch('streamlit.info')
    def test_display_compact_references_empty(self, mock_info):
        """空の検索結果の表示テスト"""
        citation_display = CitationDisplay()
        citation_display.display_compact_references([])
        mock_info.assert_called_once_with("参照文書はありません")
    
    @patch('streamlit.markdown')
    def test_display_compact_references_with_data(self, mock_markdown):
        """検索結果ありの表示テスト"""
        citation_display = CitationDisplay()
        
        # モック検索結果
        mock_results = [
            Mock(filename="test1.pdf", page_number=1),
            Mock(filename="test1.pdf", page_number=2),
            Mock(filename="test2.pdf", page_number=5)
        ]
        
        citation_display.display_compact_references(mock_results)
        mock_markdown.assert_called_once()
        
        # 呼び出された引数を確認
        call_args = mock_markdown.call_args[0][0]
        assert "test1.pdf" in call_args
        assert "test2.pdf" in call_args
        assert "p.1-2" in call_args
        assert "p.5" in call_args


class TestStreamlitCitationWidget:
    """StreamlitCitationWidgetクラスのテスト"""
    
    @patch('streamlit.expander')
    @patch.object(CitationDisplay, 'display_detailed_references')
    def test_render_citation_expander(self, mock_display, mock_expander):
        """引用エクスパンダー表示テスト"""
        mock_results = [Mock()]
        mock_context = Mock()
        mock_expander.return_value.__enter__ = Mock(return_value=mock_context)
        mock_expander.return_value.__exit__ = Mock(return_value=None)
        
        StreamlitCitationWidget.render_citation_expander(mock_results)
        
        mock_expander.assert_called_once()
        mock_display.assert_called_once()
    
    def test_render_citation_expander_empty(self):
        """空の検索結果でのエクスパンダー表示テスト"""
        # 空リストを渡してもエラーが発生しないことを確認
        StreamlitCitationWidget.render_citation_expander([])


@pytest.fixture
def sample_search_results():
    """サンプル検索結果"""
    return [
        Mock(
            filename="document1.pdf",
            page_number=1,
            content="サンプルコンテンツ1",
            similarity_score=0.95
        ),
        Mock(
            filename="document1.pdf", 
            page_number=2,
            content="サンプルコンテンツ2",
            similarity_score=0.85
        ),
        Mock(
            filename="document2.pdf",
            page_number=1, 
            content="サンプルコンテンツ3",
            similarity_score=0.75
        )
    ]


class TestCitationDisplayIntegration:
    """統合テスト"""
    
    def test_full_citation_workflow(self, sample_search_results):
        """完全な引用表示ワークフローテスト"""
        citation_display = CitationDisplay()
        
        # 各種メソッドが例外なく実行できることを確認
        try:
            citation_display._format_page_ranges([1, 2, 3])
            citation_display._get_score_color(0.8)
            citation_display._truncate_text("テストテキスト", 10)
        except Exception as e:
            pytest.fail(f"Citation display methods failed: {e}")