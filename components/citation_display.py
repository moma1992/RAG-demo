"""
引用表示 UI コンポーネント

Issue #51: 引用元表示機能実装
Streamlitを使用した詳細な引用情報表示UI
"""

import streamlit as st
from typing import List, Dict, Optional
import logging

from models.citation import Citation, CitationCollection

logger = logging.getLogger(__name__)


def display_citations(
    citations: List[Citation],
    query: str = "",
    show_context: bool = True,
    max_display: int = 5
) -> None:
    """
    引用情報を表示するメインコンポーネント
    
    Args:
        citations: 引用情報リスト
        query: 検索クエリ
        show_context: 文脈情報を表示するか
        max_display: 最大表示件数
    """
    if not citations:
        st.info("📚 関連する文書が見つかりませんでした。")
        return
    
    # CitationCollection に変換してソート
    collection = CitationCollection(citations=citations, query=query)
    sorted_collection = collection.sort_by_relevance()
    
    # 表示件数制限
    display_citations = sorted_collection.citations[:max_display]
    
    # ヘッダー表示
    st.markdown(f"### 📚 参考文書 ({len(display_citations)}件)")
    
    # 統計情報表示
    _display_statistics(sorted_collection)
    
    # 各引用を表示
    for i, citation in enumerate(display_citations, 1):
        _display_single_citation(citation, i, show_context)


def _display_statistics(collection: CitationCollection) -> None:
    """
    統計情報を表示
    
    Args:
        collection: 引用情報コレクション
    """
    stats = collection.get_statistics()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 総引用数", stats["total_citations"])
    
    with col2:
        st.metric("📄 文書数", stats["unique_documents"])
    
    with col3:
        st.metric("🎯 平均信頼度", f"{stats['avg_similarity']:.1%}")
    
    with col4:
        st.metric("⭐ 最高信頼度", f"{stats['max_similarity']:.1%}")


def _display_single_citation(
    citation: Citation, 
    index: int, 
    show_context: bool = True
) -> None:
    """
    単一の引用情報を表示
    
    Args:
        citation: 引用情報
        index: 表示順序
        show_context: 文脈情報を表示するか
    """
    # 信頼度による色分け
    confidence_color = _get_confidence_color(citation.similarity_score)
    
    # メインの引用情報表示
    with st.expander(
        f"📄 **{citation.filename}** ({citation.location_text}) "
        f"[信頼度: {citation.confidence_percentage}%]",
        expanded=(index == 1)  # 最初の項目のみ展開
    ):
        # 文書情報
        _display_document_info(citation, confidence_color)
        
        # 引用内容
        _display_citation_content(citation)
        
        # 文脈情報（オプション）
        if show_context and (citation.context_before or citation.context_after):
            _display_context_info(citation)
        
        # 詳細情報
        _display_detailed_info(citation)


def _get_confidence_color(similarity_score: float) -> str:
    """
    信頼度に基づく色を取得
    
    Args:
        similarity_score: 類似度スコア
        
    Returns:
        str: 色の名前
    """
    if similarity_score >= 0.9:
        return "green"
    elif similarity_score >= 0.8:
        return "blue"
    elif similarity_score >= 0.7:
        return "orange"
    else:
        return "red"


def _display_document_info(citation: Citation, color: str) -> None:
    """
    文書情報を表示
    
    Args:
        citation: 引用情報
        color: 表示色
    """
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # 文書の場所情報
        if citation.chapter_number and citation.section_name:
            st.markdown(f"**📍 場所:** {citation.location_text}")
        else:
            st.markdown(f"**📍 ページ:** {citation.page_number}")
    
    with col2:
        # 信頼度バッジ
        st.markdown(
            f'<div style="text-align: right;">'
            f'<span style="background-color: {color}; color: white; '
            f'padding: 4px 8px; border-radius: 12px; font-size: 12px;">'
            f'信頼度: {citation.confidence_percentage}%'
            f'</span></div>',
            unsafe_allow_html=True
        )


def _display_citation_content(citation: Citation) -> None:
    """
    引用内容を表示
    
    Args:
        citation: 引用情報
    """
    st.markdown("**📖 引用内容:**")
    
    # 引用テキストをハイライト表示
    quoted_text = citation.display_snippet
    st.markdown(
        f'<div style="background-color: #f0f2f6; padding: 12px; '
        f'border-left: 4px solid #1f77b4; margin: 8px 0; '
        f'border-radius: 4px; font-style: italic;">'
        f'"{quoted_text}"'
        f'</div>',
        unsafe_allow_html=True
    )


def _display_context_info(citation: Citation) -> None:
    """
    文脈情報を表示
    
    Args:
        citation: 引用情報
    """
    st.markdown("**🔍 前後の文脈:**")
    
    context_text = citation.get_full_context()
    
    # 文脈をハイライト表示（引用部分を強調）
    st.markdown(
        f'<div style="background-color: #fafafa; padding: 8px; '
        f'border: 1px solid #e0e0e0; border-radius: 4px; '
        f'font-size: 14px; line-height: 1.5;">'
        f'{context_text}'
        f'</div>',
        unsafe_allow_html=True
    )


def _display_detailed_info(citation: Citation) -> None:
    """
    詳細情報を表示
    
    Args:
        citation: 引用情報
    """
    with st.expander("📋 詳細情報", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**文書ID:** `{citation.document_id}`")
            st.markdown(f"**チャンクID:** `{citation.chunk_id}`")
            st.markdown(f"**類似度スコア:** {citation.similarity_score:.4f}")
        
        with col2:
            st.markdown(f"**開始位置:** x={citation.start_position.get('x', 0):.1f}, y={citation.start_position.get('y', 0):.1f}")
            st.markdown(f"**終了位置:** x={citation.end_position.get('x', 0):.1f}, y={citation.end_position.get('y', 0):.1f}")
            if citation.created_at:
                st.markdown(f"**作成日時:** {citation.created_at.strftime('%Y-%m-%d %H:%M:%S')}")


def display_citation_summary(
    collection: CitationCollection,
    show_download: bool = True
) -> None:
    """
    引用情報のサマリーを表示
    
    Args:
        collection: 引用情報コレクション
        show_download: ダウンロードボタンを表示するか
    """
    st.markdown("### 📊 引用情報サマリー")
    
    # 統計情報
    stats = collection.get_statistics()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("総引用数", stats["total_citations"])
        st.metric("文書数", stats["unique_documents"])
    
    with col2:
        st.metric("平均信頼度", f"{stats['avg_similarity']:.1%}")
        st.metric("最高信頼度", f"{stats['max_similarity']:.1%}")
    
    with col3:
        st.metric("最低信頼度", f"{stats['min_similarity']:.1%}")
        
        # ダウンロードボタン
        if show_download:
            citation_data = collection.to_dict()
            st.download_button(
                label="📥 引用情報をダウンロード",
                data=str(citation_data),
                file_name=f"citations_{collection.query.replace(' ', '_')}.json",
                mime="application/json"
            )


def display_document_groups(collection: CitationCollection) -> None:
    """
    文書別にグループ化して表示
    
    Args:
        collection: 引用情報コレクション
    """
    st.markdown("### 📁 文書別引用情報")
    
    groups = collection.group_by_document()
    
    for doc_id, citations in groups.items():
        # 文書の代表的な情報を取得
        representative = citations[0]
        total_confidence = sum(c.similarity_score for c in citations)
        avg_confidence = total_confidence / len(citations)
        
        with st.expander(
            f"📄 {representative.filename} "
            f"({len(citations)}件, 平均信頼度: {avg_confidence:.1%})",
            expanded=False
        ):
            for i, citation in enumerate(citations, 1):
                st.markdown(f"**{i}. {citation.location_text}** (信頼度: {citation.confidence_percentage}%)")
                st.markdown(f"> {citation.display_snippet}")
                st.markdown("---")


def display_interactive_citations(
    collection: CitationCollection,
    key: str = "citations"
) -> Optional[Citation]:
    """
    インタラクティブな引用表示
    
    Args:
        collection: 引用情報コレクション
        key: Streamlitのキー
        
    Returns:
        Optional[Citation]: 選択された引用情報
    """
    st.markdown("### 🔍 引用情報を選択")
    
    # 引用情報の選択肢を作成
    options = []
    for citation in collection.citations:
        option_text = (
            f"{citation.filename} ({citation.location_text}) "
            f"- 信頼度: {citation.confidence_percentage}%"
        )
        options.append(option_text)
    
    if not options:
        st.info("選択可能な引用情報がありません。")
        return None
    
    # セレクトボックス
    selected_index = st.selectbox(
        "引用情報を選択してください:",
        range(len(options)),
        format_func=lambda i: options[i],
        key=f"{key}_select"
    )
    
    if selected_index is not None:
        selected_citation = collection.citations[selected_index]
        
        # 選択された引用の詳細表示
        st.markdown("---")
        _display_single_citation(selected_citation, 1, show_context=True)
        
        return selected_citation
    
    return None


# ユーティリティ関数

def filter_citations_by_confidence(
    citations: List[Citation],
    min_confidence: float = 0.7
) -> List[Citation]:
    """
    信頼度でフィルタリング
    
    Args:
        citations: 引用情報リスト
        min_confidence: 最小信頼度
        
    Returns:
        List[Citation]: フィルタリング済み引用情報
    """
    return [c for c in citations if c.similarity_score >= min_confidence]


def get_top_citations_by_document(
    citations: List[Citation],
    top_n: int = 2
) -> List[Citation]:
    """
    文書別に上位N件の引用を取得
    
    Args:
        citations: 引用情報リスト
        top_n: 文書別の最大取得件数
        
    Returns:
        List[Citation]: 文書別上位引用情報
    """
    collection = CitationCollection(citations=citations, query="")
    groups = collection.group_by_document()
    
    result = []
    for doc_citations in groups.values():
        # 文書内で信頼度順にソート
        sorted_citations = sorted(
            doc_citations,
            key=lambda c: c.similarity_score,
            reverse=True
        )
        result.extend(sorted_citations[:top_n])
    
    # 全体で信頼度順にソート
    return sorted(result, key=lambda c: c.similarity_score, reverse=True)