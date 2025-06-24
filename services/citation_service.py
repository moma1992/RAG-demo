"""
引用情報処理サービス

Issue #51: 引用元表示機能実装
ベクトル検索結果から引用情報を生成・処理するサービス
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
from dataclasses import dataclass

from models.citation import Citation, CitationCollection, create_citation_from_search_result
from services.vector_store import VectorStore
from services.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class CitationService:
    """引用情報処理サービスクラス"""
    
    def __init__(
        self,
        vector_store: VectorStore,
        database_manager: DatabaseManager,
        default_context_length: int = 100
    ) -> None:
        """
        初期化
        
        Args:
            vector_store: ベクトルストアサービス
            database_manager: データベース管理サービス
            default_context_length: デフォルト文脈長
        """
        self.vector_store = vector_store
        self.database_manager = database_manager
        self.default_context_length = default_context_length
        
        logger.info("CitationService初期化完了")
    
    def create_citations_from_search_results(
        self,
        search_results: List[Dict[str, Any]],
        query: str,
        similarity_scores: List[float],
        include_context: bool = True
    ) -> CitationCollection:
        """
        ベクトル検索結果から引用情報コレクションを作成
        
        Args:
            search_results: ベクトル検索結果
            query: 検索クエリ
            similarity_scores: 類似度スコアリスト
            include_context: 文脈情報を含むか
            
        Returns:
            CitationCollection: 引用情報コレクション
            
        Raises:
            CitationError: 引用情報作成エラーの場合
        """
        logger.info(f"引用情報作成開始: {len(search_results)}件の検索結果")
        
        try:
            citations = []
            
            for result, score in zip(search_results, similarity_scores):
                # 基本引用情報作成
                citation = create_citation_from_search_result(result, query, score)
                
                # 文脈情報を追加
                if include_context:
                    citation = self._enrich_with_context(citation, result)
                
                # 文書メタデータを追加
                citation = self._enrich_with_document_metadata(citation)
                
                citations.append(citation)
            
            collection = CitationCollection(citations=citations, query=query)
            
            logger.info(f"引用情報作成完了: {len(citations)}件")
            return collection
            
        except Exception as e:
            logger.error(f"引用情報作成エラー: {str(e)}", exc_info=True)
            raise CitationError(f"引用情報の作成中にエラーが発生しました: {str(e)}") from e
    
    def _enrich_with_context(
        self, 
        citation: Citation, 
        search_result: Dict[str, Any]
    ) -> Citation:
        """
        文脈情報で引用を拡張
        
        Args:
            citation: 基本引用情報
            search_result: 検索結果
            
        Returns:
            Citation: 文脈情報付き引用情報
        """
        try:
            # 前後の文脈を取得
            context_before, context_after = self._get_surrounding_context(
                citation.document_id,
                citation.page_number,
                citation.content_snippet
            )
            
            # 引用情報を更新
            citation.context_before = context_before
            citation.context_after = context_after
            
            return citation
            
        except Exception as e:
            logger.warning(f"文脈情報取得エラー（継続実行）: {str(e)}")
            return citation
    
    def _enrich_with_document_metadata(self, citation: Citation) -> Citation:
        """
        文書メタデータで引用を拡張
        
        Args:
            citation: 基本引用情報
            
        Returns:
            Citation: メタデータ付き引用情報
        """
        try:
            # データベースから文書メタデータを取得
            metadata = self.database_manager.get_document_metadata(citation.document_id)
            
            if metadata:
                # ファイル名の更新（より詳細な情報があれば）
                if metadata.get("original_filename"):
                    citation.filename = metadata["original_filename"]
                
                # 章・セクション情報の更新
                if metadata.get("chapter_info"):
                    chapter_info = metadata["chapter_info"]
                    if citation.page_number in chapter_info:
                        page_info = chapter_info[citation.page_number]
                        citation.chapter_number = page_info.get("chapter_number")
                        citation.section_name = page_info.get("section_name")
            
            return citation
            
        except Exception as e:
            logger.warning(f"メタデータ取得エラー（継続実行）: {str(e)}")
            return citation
    
    def _get_surrounding_context(
        self,
        document_id: str,
        page_number: int,
        content_snippet: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        前後の文脈を取得
        
        Args:
            document_id: 文書ID
            page_number: ページ番号
            content_snippet: 引用内容
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (前の文脈, 後の文脈)
        """
        try:
            # 同じページの他のチャンクを取得
            page_chunks = self.database_manager.get_page_chunks(
                document_id, 
                page_number
            )
            
            # 現在のチャンクの位置を特定
            current_index = None
            for i, chunk in enumerate(page_chunks):
                if content_snippet in chunk.get("content", ""):
                    current_index = i
                    break
            
            if current_index is None:
                return None, None
            
            # 前の文脈
            context_before = None
            if current_index > 0:
                prev_chunk = page_chunks[current_index - 1]
                context_before = prev_chunk.get("content", "")[-self.default_context_length:]
            
            # 後の文脈
            context_after = None
            if current_index < len(page_chunks) - 1:
                next_chunk = page_chunks[current_index + 1]
                context_after = next_chunk.get("content", "")[:self.default_context_length]
            
            return context_before, context_after
            
        except Exception as e:
            logger.warning(f"文脈取得エラー: {str(e)}")
            return None, None
    
    def filter_citations_by_relevance(
        self,
        collection: CitationCollection,
        min_similarity: float = 0.7,
        max_results: int = 10
    ) -> CitationCollection:
        """
        関連度によるフィルタリング
        
        Args:
            collection: 引用情報コレクション
            min_similarity: 最小類似度
            max_results: 最大結果件数
            
        Returns:
            CitationCollection: フィルタリング済みコレクション
        """
        logger.info(f"引用フィルタリング開始: 最小類似度={min_similarity}, 最大件数={max_results}")
        
        # 類似度でフィルタリング
        filtered_collection = collection.filter_by_threshold(min_similarity)
        
        # 結果件数制限
        if len(filtered_collection.citations) > max_results:
            top_citations = filtered_collection.get_top_citations(max_results)
            filtered_collection = CitationCollection(
                citations=top_citations,
                query=collection.query
            )
        
        logger.info(f"フィルタリング完了: {len(filtered_collection.citations)}件")
        return filtered_collection
    
    def deduplicate_citations(self, collection: CitationCollection) -> CitationCollection:
        """
        重複する引用を除去
        
        Args:
            collection: 引用情報コレクション
            
        Returns:
            CitationCollection: 重複除去済みコレクション
        """
        logger.info(f"重複除去開始: {len(collection.citations)}件")
        
        seen_combinations = set()
        unique_citations = []
        
        for citation in collection.citations:
            # 文書ID + ページ番号 + 内容の組み合わせで重複判定
            combination = (
                citation.document_id,
                citation.page_number,
                citation.content_snippet[:100]  # 最初の100文字で判定
            )
            
            if combination not in seen_combinations:
                seen_combinations.add(combination)
                unique_citations.append(citation)
            else:
                logger.debug(f"重複引用をスキップ: {citation.filename} p.{citation.page_number}")
        
        deduplicated_collection = CitationCollection(
            citations=unique_citations,
            query=collection.query
        )
        
        logger.info(f"重複除去完了: {len(unique_citations)}件（{len(collection.citations) - len(unique_citations)}件削除）")
        return deduplicated_collection
    
    def enhance_citations_with_highlights(
        self,
        collection: CitationCollection,
        query_terms: List[str]
    ) -> CitationCollection:
        """
        検索語句のハイライト情報を追加
        
        Args:
            collection: 引用情報コレクション
            query_terms: 検索語句リスト
            
        Returns:
            CitationCollection: ハイライト情報付きコレクション
        """
        logger.info(f"ハイライト情報追加開始: {len(query_terms)}語句")
        
        enhanced_citations = []
        
        for citation in collection.citations:
            enhanced_citation = self._add_highlights_to_citation(citation, query_terms)
            enhanced_citations.append(enhanced_citation)
        
        enhanced_collection = CitationCollection(
            citations=enhanced_citations,
            query=collection.query
        )
        
        logger.info("ハイライト情報追加完了")
        return enhanced_collection
    
    def _add_highlights_to_citation(
        self,
        citation: Citation,
        query_terms: List[str]
    ) -> Citation:
        """
        単一引用にハイライト情報を追加
        
        Args:
            citation: 引用情報
            query_terms: 検索語句リスト
            
        Returns:
            Citation: ハイライト情報付き引用情報
        """
        content = citation.content_snippet
        
        # 各検索語句をハイライト
        for term in query_terms:
            if term.lower() in content.lower():
                # 大文字小文字を無視して置換
                import re
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                content = pattern.sub(f"**{term}**", content)
        
        # ハイライト済みの内容で新しい引用を作成
        citation.content_snippet = content
        return citation
    
    def get_citation_statistics(
        self,
        collection: CitationCollection
    ) -> Dict[str, Any]:
        """
        引用統計情報を取得
        
        Args:
            collection: 引用情報コレクション
            
        Returns:
            Dict[str, Any]: 詳細統計情報
        """
        base_stats = collection.get_statistics()
        
        # 追加統計情報
        document_groups = collection.group_by_document()
        
        # 文書別統計
        doc_stats = []
        for doc_id, citations in document_groups.items():
            if citations:
                doc_stat = {
                    "document_id": doc_id,
                    "filename": citations[0].filename,
                    "citation_count": len(citations),
                    "avg_similarity": sum(c.similarity_score for c in citations) / len(citations),
                    "page_range": {
                        "min": min(c.page_number for c in citations),
                        "max": max(c.page_number for c in citations)
                    }
                }
                doc_stats.append(doc_stat)
        
        # 拡張統計情報
        enhanced_stats = {
            **base_stats,
            "document_statistics": doc_stats,
            "similarity_distribution": {
                "excellent": len([c for c in collection.citations if c.similarity_score >= 0.9]),
                "good": len([c for c in collection.citations if 0.8 <= c.similarity_score < 0.9]),
                "fair": len([c for c in collection.citations if 0.7 <= c.similarity_score < 0.8]),
                "poor": len([c for c in collection.citations if c.similarity_score < 0.7])
            }
        }
        
        return enhanced_stats
    
    def create_citation_report(
        self,
        collection: CitationCollection,
        include_full_text: bool = False
    ) -> str:
        """
        引用レポートを生成
        
        Args:
            collection: 引用情報コレクション
            include_full_text: 全文を含むか
            
        Returns:
            str: 引用レポート（Markdown形式）
        """
        stats = self.get_citation_statistics(collection)
        
        report_lines = [
            f"# 引用レポート: {collection.query}",
            "",
            "## 概要",
            f"- 検索クエリ: {collection.query}",
            f"- 総引用数: {stats['total_citations']}件",
            f"- 文書数: {stats['unique_documents']}件",
            f"- 平均信頼度: {stats['avg_similarity']:.1%}",
            "",
            "## 信頼度分布",
            f"- 優秀 (90%以上): {stats['similarity_distribution']['excellent']}件",
            f"- 良好 (80-89%): {stats['similarity_distribution']['good']}件",
            f"- 普通 (70-79%): {stats['similarity_distribution']['fair']}件",
            f"- 要注意 (70%未満): {stats['similarity_distribution']['poor']}件",
            "",
            "## 引用詳細"
        ]
        
        # 引用詳細
        for i, citation in enumerate(collection.citations, 1):
            report_lines.extend([
                f"### {i}. {citation.filename} ({citation.location_text})",
                f"**信頼度:** {citation.confidence_percentage}%",
                f"**引用内容:**",
                f"> {citation.display_snippet}",
                ""
            ])
            
            if include_full_text and citation.get_full_context():
                report_lines.extend([
                    "**完全な文脈:**",
                    citation.get_full_context(),
                    ""
                ])
        
        return "\n".join(report_lines)


class CitationError(Exception):
    """引用処理エラー"""
    pass