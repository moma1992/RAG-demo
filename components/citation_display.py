"""
引用表示コンポーネント - Issue #66

文書参照と類似度スコア表示のためのStreamlitコンポーネント
"""

import streamlit as st
from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass
from models.chat import DocumentReference

logger = logging.getLogger(__name__)


@dataclass
class CitationGroup:
    """引用グループ"""
    filename: str
    references: List[DocumentReference]
    total_score: float
    page_numbers: List[int]


class CitationDisplay:
    """引用表示コンポーネントクラス"""
    
    def __init__(self, theme: str = "default"):
        """
        初期化
        
        Args:
            theme: 表示テーマ（"default", "compact", "detailed"）
        """
        self.theme = theme
    
    def display_references(
        self, 
        references: List[DocumentReference],
        show_similarity_scores: bool = True,
        show_excerpts: bool = True,
        max_excerpt_length: int = 200
    ) -> None:
        """
        文書参照を表示
        
        Args:
            references: 文書参照リスト
            show_similarity_scores: 類似度スコア表示フラグ
            show_excerpts: 抜粋表示フラグ
            max_excerpt_length: 抜粋最大文字数
        """
        if not references:
            st.info("参照文書はありません")
            return
        
        try:
            # ファイル別にグループ化
            citation_groups = self._group_references_by_file(references)
            
            # グループ別に表示
            for group in citation_groups:
                self._display_citation_group(
                    group, 
                    show_similarity_scores, 
                    show_excerpts, 
                    max_excerpt_length
                )
                
        except Exception as e:
            logger.error(f"引用表示エラー: {str(e)}")
            st.error("引用情報の表示中にエラーが発生しました")
    
    def display_compact_references(
        self, 
        references: List[DocumentReference]
    ) -> None:
        """
        コンパクトな引用表示
        
        Args:
            references: 文書参照リスト
        """
        if not references:
            return
        
        try:
            # ファイル名とページ番号のリストを作成
            file_info = {}
            for ref in references:
                if ref.filename not in file_info:
                    file_info[ref.filename] = []
                if ref.page_number not in file_info[ref.filename]:
                    file_info[ref.filename].append(ref.page_number)
            
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
    
    def display_similarity_histogram(
        self, 
        references: List[DocumentReference]
    ) -> None:
        """
        類似度スコアのヒストグラム表示
        
        Args:
            references: 文書参照リスト
        """
        if not references:
            return
        
        try:
            scores = [ref.similarity_score for ref in references]
            
            # ヒストグラム用のデータ準備
            score_ranges = ["0.9-1.0", "0.8-0.9", "0.7-0.8", "0.6-0.7", "0.5-0.6", "0.4-0.5"]
            counts = [0] * 6
            
            for score in scores:
                if score >= 0.9:
                    counts[0] += 1
                elif score >= 0.8:
                    counts[1] += 1
                elif score >= 0.7:
                    counts[2] += 1
                elif score >= 0.6:
                    counts[3] += 1
                elif score >= 0.5:
                    counts[4] += 1
                else:
                    counts[5] += 1
            
            # Streamlitのバーチャート表示
            chart_data = {
                "類似度範囲": score_ranges,
                "文書数": counts
            }
            
            st.subheader("類似度分布")
            st.bar_chart(chart_data)
            
        except Exception as e:
            logger.error(f"ヒストグラム表示エラー: {str(e)}")
    
    def _group_references_by_file(
        self, 
        references: List[DocumentReference]
    ) -> List[CitationGroup]:
        """
        文書参照をファイル別にグループ化
        
        Args:
            references: 文書参照リスト
            
        Returns:
            List[CitationGroup]: グループ化された引用
        """
        file_groups = {}
        
        for ref in references:
            if ref.filename not in file_groups:
                file_groups[ref.filename] = []
            file_groups[ref.filename].append(ref)
        
        citation_groups = []
        for filename, refs in file_groups.items():
            # スコア順でソート
            refs.sort(key=lambda x: x.similarity_score, reverse=True)
            
            # グループ情報を計算
            total_score = sum(ref.similarity_score for ref in refs) / len(refs)
            page_numbers = sorted(list(set(ref.page_number for ref in refs)))
            
            citation_groups.append(CitationGroup(
                filename=filename,
                references=refs,
                total_score=total_score,
                page_numbers=page_numbers
            ))
        
        # 平均スコア順でソート
        citation_groups.sort(key=lambda x: x.total_score, reverse=True)
        
        return citation_groups
    
    def _display_citation_group(
        self,
        group: CitationGroup,
        show_similarity_scores: bool,
        show_excerpts: bool,
        max_excerpt_length: int
    ) -> None:
        """
        引用グループを表示
        
        Args:
            group: 引用グループ
            show_similarity_scores: 類似度スコア表示フラグ
            show_excerpts: 抜粋表示フラグ
            max_excerpt_length: 抜粋最大文字数
        """
        # ファイル名とページ番号
        page_display = self._format_page_ranges(group.page_numbers)
        
        # 類似度スコア表示
        if show_similarity_scores:
            score_color = self._get_score_color(group.total_score)
            st.markdown(
                f"📄 **{group.filename}** ({page_display}) "
                f"<span style='color:{score_color}'>類似度: {group.total_score:.2f}</span>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(f"📄 **{group.filename}** ({page_display})")
        
        # 抜粋表示
        if show_excerpts and self.theme != "compact":
            for i, ref in enumerate(group.references[:3]):  # 最大3つまで表示
                excerpt = self._truncate_text(ref.excerpt, max_excerpt_length)
                
                with st.expander(f"抜粋 {i+1} (p.{ref.page_number})", expanded=(i == 0)):
                    st.markdown(f"*{excerpt}*")
                    
                    if show_similarity_scores:
                        score_color = self._get_score_color(ref.similarity_score)
                        st.markdown(
                            f"<small style='color:{score_color}'>類似度: {ref.similarity_score:.3f}</small>",
                            unsafe_allow_html=True
                        )
        
        st.markdown("---")
    
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
    def render_citation_sidebar(references: List[DocumentReference]) -> None:
        """
        サイドバーに引用を表示
        
        Args:
            references: 文書参照リスト
        """
        if not references:
            return
        
        with st.sidebar:
            st.subheader("📚 参照文書")
            
            citation_display = CitationDisplay(theme="compact")
            citation_display.display_compact_references(references)
    
    @staticmethod
    def render_citation_expander(
        references: List[DocumentReference],
        expanded: bool = False
    ) -> None:
        """
        エクスパンダーで引用を表示
        
        Args:
            references: 文書参照リスト
            expanded: 初期展開状態
        """
        if not references:
            return
        
        with st.expander(f"📄 参照文書 ({len(references)}件)", expanded=expanded):
            citation_display = CitationDisplay(theme="detailed")
            citation_display.display_references(references)
    
    @staticmethod
    def render_inline_citations(references: List[DocumentReference]) -> None:
        """
        インライン引用を表示
        
        Args:
            references: 文書参照リスト
        """
        if not references:
            return
        
        citation_display = CitationDisplay(theme="compact")
        citation_display.display_compact_references(references)


def create_sample_references() -> List[DocumentReference]:
    """サンプル引用データを生成（テスト用）"""
    return [
        DocumentReference(
            filename="新入社員マニュアル.pdf",
            page_number=15,
            chunk_id="chunk-001",
            similarity_score=0.95,
            excerpt="新入社員の研修期間は原則として3ヶ月間です。この期間中に基本的なビジネスマナーと業務知識を習得していただきます。"
        ),
        DocumentReference(
            filename="新入社員マニュアル.pdf",
            page_number=16,
            chunk_id="chunk-002",
            similarity_score=0.87,
            excerpt="研修終了後は、各部署への正式配属となります。配属先は研修期間中の評価と本人の希望を総合的に判断して決定されます。"
        ),
        DocumentReference(
            filename="人事規程.pdf",
            page_number=8,
            chunk_id="chunk-003",
            similarity_score=0.82,
            excerpt="職員の研修に関する規定について定めます。新入職員は必修研修を受講する義務があります。"
        )
    ]
