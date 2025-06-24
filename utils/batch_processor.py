"""
Batch Embedding Processor
Issue #55: 大量テキストチャンクの効率的バッチ埋め込み処理実装

OpenAI APIレート制限を考慮した非同期バッチ処理システム

TDD Green Phase: 最小実装
"""

import asyncio
import time
import logging
from dataclasses import dataclass
from typing import List, Any, Optional, Callable
import psutil
import os
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from services.embeddings import EmbeddingService, EmbeddingError

logger = logging.getLogger(__name__)

# Type Aliases
ProgressCallback = Callable[["ProgressInfo"], None]


@dataclass
class RateLimitConfig:
    """レート制限設定"""

    requests_per_minute: int
    tokens_per_minute: int
    max_concurrent_requests: int
    retry_delays: List[float]


@dataclass
class ProgressInfo:
    """進捗情報"""

    processed_count: int
    total_count: int
    success_count: int
    failure_count: int
    elapsed_time: float
    estimated_remaining_time: Optional[float] = None


@dataclass
class FailedItem:
    """失敗アイテム情報"""

    text: str
    error_message: str
    retry_count: int


@dataclass
class BatchProcessingResult:
    """バッチ処理結果"""

    total_processed: int
    success_count: int
    failure_count: int
    results: List[Any]
    failed_items: List[FailedItem]
    processing_time: float

    @property
    def success_rate(self) -> float:
        """成功率計算"""
        if self.total_processed == 0:
            return 0.0
        return self.success_count / self.total_processed


class BatchProcessingError(Exception):
    """バッチ処理エラー"""

    pass


class BatchEmbeddingProcessor:
    """バッチ埋め込み処理クラス"""

    def __init__(self, api_key: str, rate_limit_config: RateLimitConfig):
        """
        初期化

        Args:
            api_key: OpenAI APIキー
            rate_limit_config: レート制限設定

        Raises:
            ValueError: 無効な設定の場合
        """
        if not api_key:
            raise ValueError("APIキーが必要です")

        if (
            rate_limit_config.requests_per_minute <= 0
            or rate_limit_config.tokens_per_minute <= 0
            or rate_limit_config.max_concurrent_requests <= 0
            or not rate_limit_config.retry_delays
        ):
            raise ValueError("無効なレート制限設定")

        self.api_key = api_key
        self.rate_limit_config = rate_limit_config
        self.max_concurrent_requests = rate_limit_config.max_concurrent_requests

        # EmbeddingServiceの初期化
        self.embedding_service = EmbeddingService(api_key=api_key, async_mode=True)

        # 同時実行制御用セマフォ
        self.semaphore = asyncio.Semaphore(rate_limit_config.max_concurrent_requests)

        logger.info(
            f"BatchEmbeddingProcessor初期化完了: max_concurrent={self.max_concurrent_requests}"
        )

    async def process_batch(
        self, texts: List[str], progress_callback: Optional[ProgressCallback] = None
    ) -> BatchProcessingResult:
        """
        バッチ埋め込み処理

        Args:
            texts: 処理対象テキストリスト
            progress_callback: 進捗コールバック

        Returns:
            BatchProcessingResult: 処理結果

        Raises:
            ValueError: 無効な入力の場合
            BatchProcessingError: 処理エラーの場合
        """
        if not texts:
            raise ValueError("テキストリストが空です")

        if len(texts) > 1000:
            raise ValueError("バッチサイズが制限を超えています（最大1000件）")

        start_time = time.time()

        # 進捗情報初期化
        progress = ProgressInfo(
            processed_count=0,
            total_count=len(texts),
            success_count=0,
            failure_count=0,
            elapsed_time=0.0,
        )

        if progress_callback:
            progress_callback(progress)

        # 実際のバッチ処理実装
        results = []
        failed_items = []

        try:
            # バッチを小さな単位に分割して並列処理
            batch_size = min(20, len(texts))  # 20件ずつ処理
            batches = [
                texts[i : i + batch_size] for i in range(0, len(texts), batch_size)
            ]

            # 並列処理でバッチを実行
            for batch_index, batch in enumerate(batches):
                batch_results, batch_failures = await self._process_batch_with_retry(
                    batch
                )
                results.extend(batch_results)
                failed_items.extend(batch_failures)

                # 進捗更新
                progress.processed_count = min(
                    (batch_index + 1) * batch_size, len(texts)
                )
                progress.success_count = len(results)
                progress.failure_count = len(failed_items)
                progress.elapsed_time = time.time() - start_time
                progress.estimated_remaining_time = self._estimate_remaining_time(
                    progress.processed_count, len(texts), progress.elapsed_time
                )

                if progress_callback:
                    progress_callback(progress)

                # メモリ使用量チェック
                if self._check_memory_usage():
                    logger.warning("メモリ使用量が500MBに近づいています")

        except Exception as e:
            logger.error(f"バッチ処理エラー: {str(e)}")
            raise BatchProcessingError(
                f"バッチ処理中にエラーが発生しました: {str(e)}"
            ) from e

        processing_time = time.time() - start_time

        return BatchProcessingResult(
            total_processed=len(texts),
            success_count=len(results),
            failure_count=len(failed_items),
            results=results,
            failed_items=failed_items,
            processing_time=processing_time,
        )

    def estimate_processing_time(self, texts: List[str]) -> float:
        """
        処理時間推定

        Args:
            texts: 処理対象テキストリスト

        Returns:
            float: 推定処理時間（秒）

        Raises:
            ValueError: 空リストの場合
        """
        if not texts:
            raise ValueError("テキストリストが空です")

        # 簡単な推定ロジック
        avg_processing_time_per_item = 0.5  # 500ms per item
        concurrent_factor = min(len(texts), self.max_concurrent_requests)

        estimated_time = (len(texts) / concurrent_factor) * avg_processing_time_per_item

        # レート制限による遅延を考慮
        requests_per_second = self.rate_limit_config.requests_per_minute / 60
        if len(texts) > requests_per_second:
            rate_limit_delay = (len(texts) - requests_per_second) / requests_per_second
            estimated_time += rate_limit_delay

        return estimated_time

    async def _process_batch_with_retry(
        self, texts: List[str]
    ) -> tuple[List[Any], List[FailedItem]]:
        """
        リトライ機能付きバッチ処理

        Args:
            texts: 処理対象テキスト

        Returns:
            tuple[List[Any], List[FailedItem]]: 成功結果と失敗アイテム
        """
        results = []
        failed_items = []

        # 並列処理でテキストを処理
        tasks = [self._process_single_text_with_retry(text) for text in texts]

        # 同時実行数を制限して実行
        for i in range(0, len(tasks), self.max_concurrent_requests):
            batch_tasks = tasks[i : i + self.max_concurrent_requests]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            for j, result in enumerate(batch_results):
                text_index = i + j
                if isinstance(result, Exception):
                    failed_items.append(
                        FailedItem(
                            text=texts[text_index],
                            error_message=str(result),
                            retry_count=self.rate_limit_config.retry_delays.__len__(),
                        )
                    )
                else:
                    results.append(result)

            # レート制限を考慮した遅延
            if i + self.max_concurrent_requests < len(tasks):
                await asyncio.sleep(60 / self.rate_limit_config.requests_per_minute)

        return results, failed_items

    def _calculate_retry_delay(self, retry_count: int) -> float:
        """
        リトライ遅延計算

        Args:
            retry_count: リトライ回数

        Returns:
            float: 遅延時間（秒）
        """
        if retry_count < len(self.rate_limit_config.retry_delays):
            return self.rate_limit_config.retry_delays[retry_count]
        else:
            # 最大遅延時間を返す
            return self.rate_limit_config.retry_delays[-1]

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=16),
        retry=retry_if_exception_type((EmbeddingError, Exception)),
    )
    async def _process_single_text_with_retry(self, text: str) -> Any:
        """
        単一テキストのリトライ付き処理

        Args:
            text: 処理対象テキスト

        Returns:
            Any: 埋め込み結果

        Raises:
            Exception: 最大リトライ回数に達した場合
        """
        async with self.semaphore:
            try:
                result = await self.embedding_service.generate_embedding_async(text)
                return result
            except EmbeddingError as e:
                logger.warning(f"埋め込み生成エラー (リトライ対象): {str(e)}")
                raise
            except Exception as e:
                logger.warning(f"予期しないエラー (リトライ対象): {str(e)}")
                raise

    def _estimate_remaining_time(
        self, processed: int, total: int, elapsed_time: float
    ) -> Optional[float]:
        """
        残り時間推定

        Args:
            processed: 処理済み件数
            total: 総件数
            elapsed_time: 経過時間

        Returns:
            Optional[float]: 推定残り時間（秒）
        """
        if processed == 0:
            return None

        avg_time_per_item = elapsed_time / processed
        remaining_items = total - processed

        return remaining_items * avg_time_per_item

    def _check_memory_usage(self) -> bool:
        """
        メモリ使用量チェック

        Returns:
            bool: メモリ使用量が400MB以上の場合True
        """
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024

        return memory_mb > 400  # 400MB以上で警告
