"""
トークンカウント一貫性統合テスト

Issue #53 レビュー対応: コンポーネント間でのトークンカウント一貫性を検証
"""

import pytest
from typing import List
from unittest.mock import Mock, patch

from models.embedding import EmbeddingResult, EmbeddingBatch, EmbeddingCostCalculator
from services.embeddings import EmbeddingService
from services.text_chunker import TextChunker, ChunkMetadata, TextChunk
from services.claude_llm import ClaudeLLMService
from utils.tokenizer import TokenCounter


class TestTokenCountConsistency:
    """コンポーネント間トークンカウント一貫性テスト"""
    
    def test_token_counter_consistency_across_components(self):
        """全コンポーネントで同じテキストのトークン数が一致することを確認"""
        test_texts = [
            "短いテストテキスト",
            "中程度の長さのテキストです。このテキストは複数の文を含んでいます。",
            "長いテストテキストです。" * 50,
            "日本語と英語が混在するテキストです。This text contains both Japanese and English.",
            "特殊文字を含むテキスト: @#$%^&*()_+{}|:<>?[]\\;'\",./"
        ]
        
        # 各コンポーネントのトークンカウンター初期化
        token_counter = TokenCounter("text-embedding-3-small")
        embedding_service = EmbeddingService("test-api-key", "text-embedding-3-small")
        text_chunker = TextChunker()
        claude_service = ClaudeLLMService("test-api-key")
        cost_calculator = EmbeddingCostCalculator()
        
        for text in test_texts:
            # 各コンポーネントでトークン数をカウント
            base_count = token_counter.count_tokens(text)
            embedding_service_count = embedding_service.token_counter.count_tokens(text)
            chunker_count = text_chunker.count_tokens(text)
            
            # すべてのコンポーネントで同じ結果が得られることを確認
            assert base_count == embedding_service_count, f"EmbeddingServiceのトークン数が不一致: {base_count} != {embedding_service_count}"
            assert base_count == chunker_count, f"TextChunkerのトークン数が不一致: {base_count} != {chunker_count}"
            
            # EmbeddingResultでも同じトークン数が記録されることを確認
            embedding_result = EmbeddingResult(
                text=text,
                embedding=[0.1] * 1536,
                token_count=base_count,
                model="text-embedding-3-small"
            )
            assert embedding_result.token_count == base_count
    
    def test_embedding_service_token_count_accuracy(self):
        """EmbeddingServiceのトークンカウントが正確であることを確認"""
        service = EmbeddingService("test-api-key", "text-embedding-3-small")
        token_counter = TokenCounter("text-embedding-3-small")
        
        test_text = "これはトークンカウントのテストです。正確性を確認します。"
        
        # 単一埋め込み作成時のトークン数
        result = service.create_embedding(test_text)
        expected_count = token_counter.count_tokens(test_text)
        
        assert result.token_count == expected_count
        
        # バッチ埋め込み作成時のトークン数
        test_texts = [
            "テキスト1です。",
            "テキスト2はもう少し長くなります。",
            "テキスト3はさらに長いテキストです。これは複数の文を含んでいます。"
        ]
        
        batch_result = service.create_batch_embeddings(test_texts)
        
        for i, result in enumerate(batch_result.results):
            expected_count = token_counter.count_tokens(test_texts[i])
            assert result.token_count == expected_count, f"バッチ{i}のトークン数が不一致"
    
    def test_text_chunker_token_count_consistency(self):
        """TextChunkerのトークンカウントが一貫していることを確認"""
        chunker = TextChunker(chunk_size=100, overlap_ratio=0.1)
        token_counter = TokenCounter("text-embedding-3-small")
        
        # モックDocumentとPageを作成
        mock_document = Mock()
        mock_document.filename = "test.pdf"
        mock_document.document_id = "test-doc-id"
        mock_document.metadata = {"document_structure": Mock(sections=[])}
        
        mock_page = Mock()
        mock_page.page_number = 1
        mock_page.text_blocks = [
            Mock(content="これは最初のテキストブロックです。"),
            Mock(content="これは2番目のテキストブロックです。"),
            Mock(content="これは3番目のテキストブロックです。")
        ]
        
        mock_document.pages = [mock_page]
        
        # spaCyモックを設定
        with patch.object(chunker, 'nlp') as mock_nlp:
            mock_doc = Mock()
            mock_sentences = [
                Mock(text="これは最初のテキストブロックです。"),
                Mock(text="これは2番目のテキストブロックです。"),
                Mock(text="これは3番目のテキストブロックです。")
            ]
            mock_doc.sents = mock_sentences
            mock_nlp.return_value = mock_doc
            
            chunks = chunker.split_text_into_chunks(mock_document)
            
            # 各チャンクのトークン数が正確であることを確認
            for chunk in chunks:
                expected_count = token_counter.count_tokens(chunk.content)
                assert chunk.metadata.token_count == expected_count
    
    def test_claude_service_token_count_accuracy(self):
        """ClaudeServiceのトークンカウントが正確であることを確認"""
        service = ClaudeLLMService("test-api-key")
        token_counter = TokenCounter()
        
        query = "これはテストクエリです。"
        context_chunks = [
            "コンテキストチャンク1です。",
            "コンテキストチャンク2はもう少し長いです。"
        ]
        
        result = service.generate_response(query, context_chunks)
        
        # レスポンス生成時のトークン数が正確であることを確認
        expected_input_tokens = token_counter.count_tokens(service._build_user_prompt(query, context_chunks))
        expected_output_tokens = token_counter.count_tokens(result.content)
        
        assert result.usage["input_tokens"] == expected_input_tokens
        assert result.usage["output_tokens"] == expected_output_tokens
    
    def test_cost_calculation_consistency(self):
        """コスト計算の一貫性を確認"""
        calculator = EmbeddingCostCalculator()
        token_counter = TokenCounter("text-embedding-3-small")
        
        test_texts = [
            "短いテキスト",
            "中程度の長さのテキストです。",
            "長いテキスト。" * 100
        ]
        
        # 手動でのコスト計算
        total_manual_cost = 0.0
        for text in test_texts:
            token_count = token_counter.count_tokens(text)
            cost = calculator.calculate_cost(token_count, "text-embedding-3-small")
            total_manual_cost += cost
        
        # estimate_batch_costでの計算
        batch_cost_estimate = calculator.estimate_batch_cost(test_texts, "text-embedding-3-small")
        
        # 両方の計算結果が一致することを確認（小数点誤差を考慮）
        assert abs(total_manual_cost - batch_cost_estimate["estimated_cost_usd"]) < 0.0001
    
    def test_embedding_batch_token_consistency(self):
        """EmbeddingBatchのトークン数が一貫していることを確認"""
        token_counter = TokenCounter("text-embedding-3-small")
        
        test_texts = [
            "バッチテスト用テキスト1",
            "バッチテスト用テキスト2",
            "バッチテスト用テキスト3"
        ]
        
        # EmbeddingResultを作成
        results = []
        expected_total_tokens = 0
        
        for text in test_texts:
            token_count = token_counter.count_tokens(text)
            expected_total_tokens += token_count
            
            result = EmbeddingResult(
                text=text,
                embedding=[0.1] * 1536,
                token_count=token_count,
                model="text-embedding-3-small"
            )
            results.append(result)
        
        # EmbeddingBatch作成
        batch = EmbeddingBatch(results)
        
        # バッチの合計トークン数が正確であることを確認
        assert batch.total_tokens == expected_total_tokens
        
        # 統計情報の計算が正確であることを確認
        stats = batch.get_statistics()
        assert stats["total_tokens"] == expected_total_tokens
        assert stats["count"] == len(test_texts)
    
    def test_token_count_model_consistency(self):
        """異なるモデルでのトークンカウント一貫性を確認"""
        models = ["text-embedding-3-small", "text-embedding-3-large"]
        test_text = "モデル間でのトークンカウント一貫性テスト"
        
        # 同じエンコーディング（cl100k_base）を使用するモデルでは
        # 同じトークン数が得られることを確認
        token_counts = {}
        
        for model in models:
            counter = TokenCounter(model)
            token_counts[model] = counter.count_tokens(test_text)
        
        # text-embedding-3系は同じエンコーディングを使用するため同じ結果
        assert token_counts["text-embedding-3-small"] == token_counts["text-embedding-3-large"]
    
    def test_large_text_token_consistency(self):
        """大きなテキストでのトークンカウント一貫性テスト"""
        # Streamlit Cloud制約を考慮した大きなテキストテスト
        large_text = "大きなテキストのトークンカウントテストです。" * 1000
        
        token_counter = TokenCounter("text-embedding-3-small")
        embedding_service = EmbeddingService("test-api-key", "text-embedding-3-small")
        text_chunker = TextChunker()
        
        # 各コンポーネントで同じ結果が得られることを確認
        base_count = token_counter.count_tokens(large_text)
        service_count = embedding_service.token_counter.count_tokens(large_text)
        chunker_count = text_chunker.count_tokens(large_text)
        
        assert base_count == service_count
        assert base_count == chunker_count
        
        # メモリ効率も確認（エラーが発生しないこと）
        assert base_count > 0
        assert isinstance(base_count, int)


class TestTokenCountEdgeCases:
    """トークンカウントのエッジケーステスト"""
    
    def test_empty_text_consistency(self):
        """空のテキストでの一貫性テスト"""
        token_counter = TokenCounter()
        embedding_service = EmbeddingService("test-api-key")
        text_chunker = TextChunker()
        
        empty_texts = ["", "   ", "\n", "\t", "   \n\t   "]
        
        for empty_text in empty_texts:
            base_count = token_counter.count_tokens(empty_text)
            service_count = embedding_service.token_counter.count_tokens(empty_text)
            chunker_count = text_chunker.count_tokens(empty_text)
            
            # 空のテキストは全て0トークンとして扱われる
            assert base_count == 0
            assert service_count == 0
            assert chunker_count == 0
    
    def test_special_characters_consistency(self):
        """特殊文字でのトークンカウント一貫性テスト"""
        special_texts = [
            "🚀🎯📊💡",  # 絵文字
            "①②③④⑤",   # 丸数字
            "α β γ δ ε",  # ギリシャ文字
            "中文 русский العربية",  # 多言語
            "HTML<tag>content</tag>",  # マークアップ
            "JSON{\"key\": \"value\"}",  # 構造化データ
        ]
        
        token_counter = TokenCounter()
        embedding_service = EmbeddingService("test-api-key")
        
        for text in special_texts:
            base_count = token_counter.count_tokens(text)
            service_count = embedding_service.token_counter.count_tokens(text)
            
            assert base_count == service_count
            assert base_count > 0  # 特殊文字でも何らかのトークンが生成される


# 統合テスト用のマーカー
pytestmark = pytest.mark.integration