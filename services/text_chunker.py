"""
テキストチャンク分割サービス

spaCyを使用した日本語文書の意味的境界検出と512トークンチャンク分割
"""

import spacy
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import logging
import uuid
from datetime import datetime

from utils.tokenizer import TokenCounter


logger = logging.getLogger(__name__)


@dataclass
class ChunkMetadata:
    """チャンクメタデータ"""
    document_id: str
    filename: str
    page_number: int
    chapter_number: Optional[int]
    section_name: Optional[str]
    start_pos: Dict[str, float]  # PDF座標
    end_pos: Dict[str, float]    # PDF座標
    token_count: int


@dataclass
class TextChunk:
    """テキストチャンク"""
    content: str
    metadata: ChunkMetadata
    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class TextChunker:
    """テキストチャンク分割クラス"""
    
    def __init__(self, chunk_size: int = 512, overlap_ratio: float = 0.1) -> None:
        """
        初期化
        
        Args:
            chunk_size: チャンクの最大トークン数
            overlap_ratio: オーバーラップ比率
        """
        self.chunk_size = chunk_size
        self.overlap_size = int(chunk_size * overlap_ratio)
        
        # spaCy日本語モデルロード
        try:
            self.nlp = spacy.load("ja_core_news_sm")
            logger.info("spaCy日本語モデルをロードしました")
        except OSError as e:
            logger.error(f"spaCy日本語モデルのロードに失敗しました: {str(e)}")
            raise ChunkingError(f"spaCy日本語モデルをロードできませんでした: {str(e)}") from e
        
        # TokenCounterを初期化
        try:
            self.token_counter = TokenCounter("text-embedding-3-small")
            logger.info("TokenCounterを初期化しました")
        except Exception as e:
            logger.error(f"TokenCounterの初期化に失敗しました: {str(e)}")
            raise ChunkingError(f"TokenCounterを初期化できませんでした: {str(e)}") from e
        
        logger.info(f"TextChunker初期化完了 - チャンクサイズ: {chunk_size}, オーバーラップ: {overlap_ratio}")
    
    def split_text_into_chunks(self, document: 'Document') -> List[TextChunk]:
        """
        文書を意味的チャンクに分割
        
        Args:
            document: PDF処理済みDocument
            
        Returns:
            List[TextChunk]: 分割されたチャンクリスト
            
        Raises:
            ChunkingError: チャンク分割エラーの場合
        """
        logger.info(f"文書チャンク分割開始: {document.filename}")
        
        try:
            chunks = []
            for page in document.pages:
                page_chunks = self._split_page_into_chunks(page, document)
                chunks.extend(page_chunks)
            
            # オーバーラップを適用
            overlapped_chunks = self._apply_overlap(chunks)
            
            logger.info(f"チャンク分割完了: {len(overlapped_chunks)}個のチャンクを生成")
            return overlapped_chunks
            
        except Exception as e:
            logger.error(f"チャンク分割エラー: {str(e)}", exc_info=True)
            raise ChunkingError(f"テキストチャンク分割中にエラーが発生しました: {str(e)}") from e
    
    def _split_page_into_chunks(self, page: 'Page', document: 'Document') -> List[TextChunk]:
        """
        ページをチャンクに分割
        
        Args:
            page: 処理対象ページ
            document: 文書オブジェクト
            
        Returns:
            List[TextChunk]: ページ内のチャンクリスト
        """
        page_text = " ".join([block.content for block in page.text_blocks])
        
        if not page_text.strip():
            return []
        
        # spaCyで文境界を検出
        doc = self.nlp(page_text)
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        
        if not sentences:
            return []
        
        chunks = []
        current_chunk = ""
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            
            # チャンクサイズ制限チェック
            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                # 現在のチャンクを確定
                chunk = self._create_chunk(current_chunk, page, document)
                chunks.append(chunk)
                
                # 新しいチャンクを開始
                current_chunk = sentence
                current_tokens = sentence_tokens
            else:
                # チャンクに文を追加
                current_chunk += f" {sentence}" if current_chunk else sentence
                current_tokens += sentence_tokens
        
        # 最後のチャンクを追加
        if current_chunk.strip():
            chunk = self._create_chunk(current_chunk, page, document)
            chunks.append(chunk)
        
        return chunks
    
    def _create_chunk(self, content: str, page: 'Page', document: 'Document') -> TextChunk:
        """
        チャンクオブジェクトを作成
        
        Args:
            content: チャンク内容
            page: ページオブジェクト
            document: 文書オブジェクト
            
        Returns:
            TextChunk: 作成されたチャンク
        """
        # セクション情報を取得
        section_info = self._get_section_info(page, document)
        
        metadata = ChunkMetadata(
            document_id=document.document_id,
            filename=document.filename,
            page_number=page.page_number,
            chapter_number=section_info.get("chapter_number"),
            section_name=section_info.get("section_name"),
            start_pos={"x": 0, "y": 0},  # 簡易実装
            end_pos={"x": 0, "y": 0},    # 簡易実装
            token_count=self.count_tokens(content)
        )
        
        return TextChunk(
            content=content.strip(),
            metadata=metadata
        )
    
    def _get_section_info(self, page: 'Page', document: 'Document') -> Dict[str, Any]:
        """
        ページのセクション情報を取得
        
        Args:
            page: ページオブジェクト
            document: 文書オブジェクト
            
        Returns:
            Dict[str, Any]: セクション情報
        """
        # 文書構造情報からセクションを特定
        structure = document.metadata.get("document_structure")
        if not structure:
            return {}
        
        for section in structure.sections:
            if section.start_page <= page.page_number <= (section.end_page or float('inf')):
                return {
                    "chapter_number": section.level,
                    "section_name": section.title
                }
        
        return {}
    
    def _apply_overlap(self, chunks: List[TextChunk]) -> List[TextChunk]:
        """
        チャンク間にオーバーラップを適用
        
        Args:
            chunks: オーバーラップ適用前のチャンクリスト
            
        Returns:
            List[TextChunk]: オーバーラップ適用後のチャンクリスト
        """
        if len(chunks) < 2:
            return chunks
        
        overlapped_chunks = [chunks[0]]  # 最初のチャンクはそのまま
        
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i-1]
            current_chunk = chunks[i]
            
            # 前のチャンクの最後の部分を取得
            prev_content = prev_chunk.content
            prev_tokens = self.count_tokens(prev_content)
            overlap_tokens = min(self.overlap_size, prev_tokens // 2)
            
            if overlap_tokens > 0:
                # 前のチャンクからオーバーラップ部分を抽出
                overlap_text = self._extract_overlap_text(prev_content, overlap_tokens)
                
                # 現在のチャンクにオーバーラップを追加
                combined_content = f"{overlap_text} {current_chunk.content}"
                current_chunk.content = combined_content
                current_chunk.metadata.token_count = self.count_tokens(combined_content)
            
            overlapped_chunks.append(current_chunk)
        
        return overlapped_chunks
    
    def _extract_overlap_text(self, text: str, target_tokens: int) -> str:
        """
        指定トークン数のオーバーラップテキストを抽出
        
        Args:
            text: 抽出元テキスト
            target_tokens: 目標トークン数
            
        Returns:
            str: オーバーラップテキスト
        """
        # 文境界を尊重してオーバーラップ部分を抽出
        doc = self.nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        
        # 後ろから文を追加してトークン数が目標に近づくまで
        overlap_text = ""
        current_tokens = 0
        
        for sentence in reversed(sentences):
            sentence_tokens = self.count_tokens(sentence)
            if current_tokens + sentence_tokens <= target_tokens:
                overlap_text = sentence + " " + overlap_text if overlap_text else sentence
                current_tokens += sentence_tokens
            else:
                break
        
        return overlap_text.strip()
    
    def count_tokens(self, text: str) -> int:
        """
        テキストのトークン数をカウント
        
        Args:
            text: 対象テキスト
            
        Returns:
            int: トークン数
        """
        if not text.strip():
            return 0
        
        return self.token_counter.count_tokens(text)


class ChunkingError(Exception):
    """チャンク分割エラー"""
    pass