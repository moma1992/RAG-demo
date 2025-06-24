"""
引用情報データモデル

Issue #51: 引用元表示機能実装
RAG回答の信頼性向上のための詳細な引用情報管理
"""

from dataclasses import dataclass
from typing import Optional, Dict, List
import uuid
from datetime import datetime


@dataclass
class Citation:
    """
    引用情報データクラス
    
    RAG回答において参照された文書の詳細情報を管理
    """
    document_id: str
    filename: str
    page_number: int
    chapter_number: Optional[int]
    section_name: Optional[str]
    content_snippet: str
    similarity_score: float
    start_position: Dict[str, float]  # {x, y} 座標
    end_position: Dict[str, float]    # {x, y} 座標
    context_before: Optional[str] = None
    context_after: Optional[str] = None
    chunk_id: Optional[str] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        """初期化後処理"""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.chunk_id is None:
            self.chunk_id = str(uuid.uuid4())

    @property
    def confidence_percentage(self) -> float:
        """
        信頼度をパーセンテージで返す
        
        Returns:
            float: 信頼度（0-100%）
        """
        return round(self.similarity_score * 100, 1)

    @property
    def location_text(self) -> str:
        """
        場所情報を文字列で返す
        
        Returns:
            str: 場所情報（例：「第2章 > 2.3 勤務時間について (p.15)」）
        """
        location_parts = []
        
        if self.chapter_number:
            location_parts.append(f"第{self.chapter_number}章")
        
        if self.section_name:
            location_parts.append(self.section_name)
        
        location_parts.append(f"p.{self.page_number}")
        
        return " > ".join(location_parts) if len(location_parts) > 1 else location_parts[0]

    @property
    def display_snippet(self) -> str:
        """
        表示用文書スニペット（長すぎる場合は省略）
        
        Returns:
            str: 表示用スニペット
        """
        max_length = 200
        if len(self.content_snippet) <= max_length:
            return self.content_snippet
        
        return self.content_snippet[:max_length] + "..."

    def get_full_context(self) -> str:
        """
        完全な文脈情報を取得
        
        Returns:
            str: 前後の文脈を含む完全なテキスト
        """
        parts = []
        
        if self.context_before:
            parts.append(f"...{self.context_before}")
        
        parts.append(f"**{self.content_snippet}**")  # 引用部分を強調
        
        if self.context_after:
            parts.append(f"{self.context_after}...")
        
        return " ".join(parts)

    def to_dict(self) -> Dict:
        """
        辞書形式に変換
        
        Returns:
            Dict: 辞書形式の引用情報
        """
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "page_number": self.page_number,
            "chapter_number": self.chapter_number,
            "section_name": self.section_name,
            "content_snippet": self.content_snippet,
            "similarity_score": self.similarity_score,
            "confidence_percentage": self.confidence_percentage,
            "location_text": self.location_text,
            "start_position": self.start_position,
            "end_position": self.end_position,
            "context_before": self.context_before,
            "context_after": self.context_after,
            "chunk_id": self.chunk_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Citation":
        """
        辞書から Citation オブジェクトを作成
        
        Args:
            data: 引用情報辞書
            
        Returns:
            Citation: Citation オブジェクト
        """
        # created_at の処理
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        
        return cls(
            document_id=data["document_id"],
            filename=data["filename"],
            page_number=data["page_number"],
            chapter_number=data.get("chapter_number"),
            section_name=data.get("section_name"),
            content_snippet=data["content_snippet"],
            similarity_score=data["similarity_score"],
            start_position=data["start_position"],
            end_position=data["end_position"],
            context_before=data.get("context_before"),
            context_after=data.get("context_after"),
            chunk_id=data.get("chunk_id"),
            created_at=created_at
        )


@dataclass
class CitationCollection:
    """
    引用情報コレクション
    
    複数の引用情報を管理し、表示用にソート・フィルタリング機能を提供
    """
    citations: List[Citation]
    query: str
    total_documents: int = 0

    def __post_init__(self):
        """初期化後処理"""
        if self.total_documents == 0:
            self.total_documents = len(set(c.document_id for c in self.citations))

    def sort_by_relevance(self) -> "CitationCollection":
        """
        関連度（類似度スコア）でソート
        
        Returns:
            CitationCollection: ソート済みコレクション
        """
        sorted_citations = sorted(
            self.citations, 
            key=lambda c: c.similarity_score, 
            reverse=True
        )
        return CitationCollection(
            citations=sorted_citations,
            query=self.query,
            total_documents=self.total_documents
        )

    def filter_by_threshold(self, threshold: float = 0.7) -> "CitationCollection":
        """
        類似度閾値でフィルタリング
        
        Args:
            threshold: 類似度閾値
            
        Returns:
            CitationCollection: フィルタリング済みコレクション
        """
        filtered_citations = [
            c for c in self.citations 
            if c.similarity_score >= threshold
        ]
        return CitationCollection(
            citations=filtered_citations,
            query=self.query,
            total_documents=len(set(c.document_id for c in filtered_citations))
        )

    def group_by_document(self) -> Dict[str, List[Citation]]:
        """
        文書別にグループ化
        
        Returns:
            Dict[str, List[Citation]]: 文書ID別の引用情報
        """
        groups = {}
        for citation in self.citations:
            if citation.document_id not in groups:
                groups[citation.document_id] = []
            groups[citation.document_id].append(citation)
        
        return groups

    def get_top_citations(self, n: int = 5) -> List[Citation]:
        """
        上位N件の引用情報を取得
        
        Args:
            n: 取得件数
            
        Returns:
            List[Citation]: 上位N件の引用情報
        """
        sorted_collection = self.sort_by_relevance()
        return sorted_collection.citations[:n]

    def get_unique_documents(self) -> List[str]:
        """
        一意の文書IDリストを取得
        
        Returns:
            List[str]: 一意の文書IDリスト
        """
        return list(set(c.document_id for c in self.citations))

    def get_statistics(self) -> Dict[str, Any]:
        """
        統計情報を取得
        
        Returns:
            Dict[str, Any]: 統計情報
        """
        if not self.citations:
            return {
                "total_citations": 0,
                "unique_documents": 0,
                "avg_similarity": 0.0,
                "max_similarity": 0.0,
                "min_similarity": 0.0
            }
        
        similarities = [c.similarity_score for c in self.citations]
        
        return {
            "total_citations": len(self.citations),
            "unique_documents": self.total_documents,
            "avg_similarity": round(sum(similarities) / len(similarities), 3),
            "max_similarity": round(max(similarities), 3),
            "min_similarity": round(min(similarities), 3)
        }

    def to_dict(self) -> Dict:
        """
        辞書形式に変換
        
        Returns:
            Dict: 辞書形式のコレクション情報
        """
        return {
            "citations": [c.to_dict() for c in self.citations],
            "query": self.query,
            "total_documents": self.total_documents,
            "statistics": self.get_statistics()
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "CitationCollection":
        """
        辞書から CitationCollection オブジェクトを作成
        
        Args:
            data: コレクション情報辞書
            
        Returns:
            CitationCollection: CitationCollection オブジェクト
        """
        citations = [Citation.from_dict(c) for c in data["citations"]]
        
        return cls(
            citations=citations,
            query=data["query"],
            total_documents=data.get("total_documents", 0)
        )


# ユーティリティ関数

def create_citation_from_search_result(
    search_result: Dict,
    query: str,
    similarity_score: float
) -> Citation:
    """
    検索結果から Citation オブジェクトを作成
    
    Args:
        search_result: ベクトル検索結果
        query: 検索クエリ
        similarity_score: 類似度スコア
        
    Returns:
        Citation: Citation オブジェクト
    """
    return Citation(
        document_id=search_result.get("document_id", ""),
        filename=search_result.get("filename", ""),
        page_number=search_result.get("page_number", 1),
        chapter_number=search_result.get("chapter_number"),
        section_name=search_result.get("section_name"),
        content_snippet=search_result.get("content", ""),
        similarity_score=similarity_score,
        start_position=search_result.get("start_pos", {}),
        end_position=search_result.get("end_pos", {}),
        context_before=search_result.get("context_before"),
        context_after=search_result.get("context_after"),
        chunk_id=search_result.get("id")
    )


def merge_citation_collections(*collections: CitationCollection) -> CitationCollection:
    """
    複数の CitationCollection をマージ
    
    Args:
        *collections: マージ対象のコレクション
        
    Returns:
        CitationCollection: マージされたコレクション
    """
    if not collections:
        return CitationCollection(citations=[], query="")
    
    all_citations = []
    queries = []
    
    for collection in collections:
        all_citations.extend(collection.citations)
        if collection.query and collection.query not in queries:
            queries.append(collection.query)
    
    merged_query = " | ".join(queries)
    
    return CitationCollection(
        citations=all_citations,
        query=merged_query
    )