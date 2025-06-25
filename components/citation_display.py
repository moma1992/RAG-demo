"""
引用表示コンポーネント - Issue #66

文書参照と類似度スコア表示のためのStreamlitコンポーネント
"""

import streamlit as st
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class CitationDisplay:
    """引用表示コンポーネントクラス"""
    
    def __init__(self, theme: str = "default"):
        """
        初期化
        
        Args:
            theme: 表示テーマ（"default", "compact", "detailed"）
        """
        self.theme = theme
    
    def display_compact_references(
        self, 
        search_results: List[Any]
    ) -> None:
        """
        検索結果からコンパクトな引用表示
        
        Args:
            search_results: ベクター検索結果
        """
        if not search_results:
            st.info("参照文書はありません")
            return
        
        try:
            # ファイル名とページ番号のリストを作成
            file_info = {}
            for result in search_results:
                filename = result.filename
                page_number = result.page_number
                
                if filename not in file_info:
                    file_info[filename] = []
                if page_number not in file_info[filename]:
                    file_info[filename].append(page_number)
            
            # コンパクト表示
            citation_text = []
            for filename, pages in file_info.items():
                pages.sort()
                if len(pages) == 1:
                    citation_text.append(f"📄 {filename} (p.{pages[0]})")
                else:
                    page_ranges = self._format_page_ranges(pages)
                    citation_text.append(f"📄 {filename} ({page_ranges})")
            
            st.markdown("**参照文書:** " + " | ".join(citation_text))
            
        except Exception as e:
            logger.error(f"コンパクト引用表示エラー: {str(e)}")
    
    def display_detailed_references(
        self,
        search_results: List[Any],
        show_similarity_scores: bool = True,
        show_excerpts: bool = True,
        max_excerpt_length: int = 200
    ) -> None:
        """
        詳細な引用表示
        
        Args:
            search_results: ベクター検索結果
            show_similarity_scores: 類似度スコア表示フラグ
            show_excerpts: 抜粋表示フラグ
            max_excerpt_length: 抜粋最大文字数
        """
        if not search_results:
            st.info("参照文書はありません")
            return
        
        try:
            for i, result in enumerate(search_results):
                # 類似度スコア表示
                if show_similarity_scores and hasattr(result, 'similarity_score'):
                    score_color = self._get_score_color(result.similarity_score)
                    st.markdown(
                        f"📄 **{result.filename}** (ページ {result.page_number}) "
                        f"<span style='color:{score_color}'>類似度: {result.similarity_score:.2f}</span>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(f"📄 **{result.filename}** (ページ {result.page_number})")
                
                # 抜粋表示
                if show_excerpts:
                    excerpt = self._truncate_text(result.content, max_excerpt_length)
                    with st.expander(f"抜粋 {i+1}", expanded=(i == 0)):
                        st.markdown(f"*{excerpt}*")
                
                if i < len(search_results) - 1:
                    st.markdown("---")
                    
        except Exception as e:
            logger.error(f"詳細引用表示エラー: {str(e)}")
    
    def _format_page_ranges(self, pages: List[int]) -> str:
        """
        ページ番号を範囲形式でフォーマット
        
        Args:
            pages: ページ番号リスト
            
        Returns:
            str: フォーマットされたページ範囲
        """
        if not pages:
            return ""
        
        # 重複を除去してソート
        unique_pages = sorted(list(set(pages)))
        
        if len(unique_pages) == 1:
            return f"p.{unique_pages[0]}"
        
        # 連続するページをグループ化
        ranges = []
        start = unique_pages[0]
        end = unique_pages[0]
        
        for i in range(1, len(unique_pages)):
            if unique_pages[i] == end + 1:
                end = unique_pages[i]
            else:
                if start == end:
                    ranges.append(f"p.{start}")
                else:
                    ranges.append(f"p.{start}-{end}")
                start = end = unique_pages[i]
        
        # 最後の範囲を追加
        if start == end:
            ranges.append(f"p.{start}")
        else:
            ranges.append(f"p.{start}-{end}")
        
        return ", ".join(ranges)
    
    def _get_score_color(self, score: float) -> str:
        """
        類似度スコアに基づいて色を決定
        
        Args:
            score: 類似度スコア
            
        Returns:
            str: CSSカラーコード
        """
        if score >= 0.9:
            return "#00C851"  # 緑
        elif score >= 0.8:
            return "#33B679"  # 薄緑
        elif score >= 0.7:
            return "#FFBB33"  # 黄
        elif score >= 0.6:
            return "#FF8800"  # オレンジ
        else:
            return "#FF4444"  # 赤
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """
        テキストを指定文字数で切り詰め
        
        Args:
            text: 対象テキスト
            max_length: 最大文字数
            
        Returns:
            str: 切り詰められたテキスト
        """
        if len(text) <= max_length:
            return text
        
        # 単語境界で切り詰め
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        
        if last_space > max_length * 0.8:  # 80%以上の位置に空白がある場合
            truncated = truncated[:last_space]
        
        return truncated + "..."


class StreamlitCitationWidget:
    """Streamlit用引用表示ウィジェット"""
    
    @staticmethod
    def render_citation_expander(
        search_results: List[Any],
        expanded: bool = False,
        show_similarity_scores: bool = True
    ) -> None:
        """
        エクスパンダーで引用を表示
        
        Args:
            search_results: ベクター検索結果
            expanded: 初期展開状態
            show_similarity_scores: 類似度スコア表示フラグ
        """
        if not search_results:
            return
        
        with st.expander(f"📄 参照文書 ({len(search_results)}件)", expanded=expanded):
            citation_display = CitationDisplay(theme="detailed")
            citation_display.display_detailed_references(
                search_results, 
                show_similarity_scores=show_similarity_scores
            )
    
    @staticmethod
    def render_inline_citations(search_results: List[Any]) -> None:
        """
        インライン引用を表示
        
        Args:
            search_results: ベクター検索結果
        """
        if not search_results:
            return
        
        citation_display = CitationDisplay(theme="compact")
        citation_display.display_compact_references(search_results)