"""
システムリソース監視機能

Issue #39: Error Handling and Logging Implementation
TDD Green フェーズ: システム監視機能の実装

システムリソース（CPU、メモリ、ディスク、ネットワークI/O）の監視、
異常検知、アラート機能を提供します。
"""

import time
import logging
import psutil
import statistics
from collections import deque
from typing import Dict, Any, List, Optional, Deque
from dataclasses import dataclass, field
from enum import Enum
import threading
from datetime import datetime

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """アラートレベル"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ResourceUsage:
    """リソース使用量データクラス"""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_io: Dict[str, float]
    timestamp: float
    
    def __post_init__(self):
        """初期化後の検証"""
        if not (0 <= self.cpu_percent <= 100):
            raise ValueError(f"cpu_percent は0-100の範囲である必要があります: {self.cpu_percent}")
        if not (0 <= self.memory_percent <= 100):
            raise ValueError(f"memory_percent は0-100の範囲である必要があります: {self.memory_percent}")
        if not (0 <= self.disk_percent <= 100):
            raise ValueError(f"disk_percent は0-100の範囲である必要があります: {self.disk_percent}")
        if not isinstance(self.network_io, dict):
            raise ValueError("network_io は辞書である必要があります")


@dataclass
class SystemAlert:
    """システムアラートデータクラス"""
    level: AlertLevel
    message: str
    resource_type: str
    current_value: float
    threshold: float
    timestamp: float
    context: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初期化後の検証"""
        if not isinstance(self.level, AlertLevel):
            raise ValueError("level は AlertLevel enum である必要があります")
        if not self.message.strip():
            raise ValueError("message は空でない文字列である必要があります")


@dataclass
class PerformanceMetrics:
    """パフォーマンスメトリクスデータクラス"""
    operation_name: str
    response_time_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    timestamp: float
    success: bool
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """初期化後の検証"""
        if not self.operation_name.strip():
            raise ValueError("operation_name は空でない文字列である必要があります")
        if self.response_time_ms < 0:
            raise ValueError("response_time_ms は非負数である必要があります")
        if not (0 <= self.cpu_usage_percent <= 100):
            raise ValueError("cpu_usage_percent は0-100の範囲である必要があります")


@dataclass
class MonitoringConfig:
    """監視設定データクラス"""
    cpu_threshold: float = 80.0
    memory_threshold: float = 85.0
    disk_threshold: float = 90.0
    response_time_threshold_ms: float = 500.0
    check_interval_seconds: float = 30.0
    enable_alerts: bool = True
    alert_cooldown_seconds: float = 300.0
    
    def __post_init__(self):
        """初期化後の検証"""
        if not (0 <= self.cpu_threshold <= 100):
            raise ValueError("cpu_threshold は0-100の範囲である必要があります")
        if not (0 <= self.memory_threshold <= 100):
            raise ValueError("memory_threshold は0-100の範囲である必要があります")
        if not (0 <= self.disk_threshold <= 100):
            raise ValueError("disk_threshold は0-100の範囲である必要があります")
        if self.check_interval_seconds <= 0:
            raise ValueError("check_interval_seconds は正の数である必要があります")


class SystemMonitor:
    """システムリソース監視クラス"""
    
    def __init__(self, config: MonitoringConfig):
        """
        初期化
        
        Args:
            config: 監視設定
        """
        self.config = config
        self.last_alert_times: Dict[str, float] = {}
        self.performance_metrics: List[PerformanceMetrics] = []
        self._lock = threading.Lock()
        
        logger.info(f"SystemMonitor初期化完了: thresholds CPU={config.cpu_threshold}%, "
                   f"Memory={config.memory_threshold}%, Disk={config.disk_threshold}%")
    
    def get_current_resource_usage(self) -> ResourceUsage:
        """
        現在のリソース使用量を取得
        
        Returns:
            ResourceUsage: リソース使用量データ
        """
        try:
            # CPU使用率取得
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # メモリ使用率取得
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # ディスク使用率取得（ルートパーティション）
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # ネットワークI/O取得
            net_io = psutil.net_io_counters()
            network_io = {
                "bytes_sent": float(net_io.bytes_sent),
                "bytes_recv": float(net_io.bytes_recv),
                "packets_sent": float(net_io.packets_sent),
                "packets_recv": float(net_io.packets_recv)
            } if net_io else {
                "bytes_sent": 0.0,
                "bytes_recv": 0.0,
                "packets_sent": 0.0,
                "packets_recv": 0.0
            }
            
            return ResourceUsage(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_percent=disk_percent,
                network_io=network_io,
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"リソース使用量取得エラー: {str(e)}", exc_info=True)
            # エラー時は安全な値を返す
            return ResourceUsage(
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_percent=0.0,
                network_io={"bytes_sent": 0.0, "bytes_recv": 0.0, "packets_sent": 0.0, "packets_recv": 0.0},
                timestamp=time.time()
            )
    
    def check_thresholds(self) -> List[SystemAlert]:
        """
        閾値チェックとアラート生成
        
        Returns:
            List[SystemAlert]: 生成されたアラートリスト
        """
        if not self.config.enable_alerts:
            return []
        
        alerts = []
        current_time = time.time()
        
        try:
            usage = self.get_current_resource_usage()
            
            # CPU使用率チェック
            if usage.cpu_percent > self.config.cpu_threshold:
                if self._should_send_alert("cpu", current_time):
                    alert = SystemAlert(
                        level=self._get_alert_level("cpu", usage.cpu_percent, self.config.cpu_threshold),
                        message=f"CPU使用率が閾値を超過しました: {usage.cpu_percent:.1f}% (閾値: {self.config.cpu_threshold}%)",
                        resource_type="cpu",
                        current_value=usage.cpu_percent,
                        threshold=self.config.cpu_threshold,
                        timestamp=current_time,
                        context={
                            "cpu_count": psutil.cpu_count(),
                            "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
                        }
                    )
                    alerts.append(alert)
                    self.last_alert_times["cpu"] = current_time
            
            # メモリ使用率チェック
            if usage.memory_percent > self.config.memory_threshold:
                if self._should_send_alert("memory", current_time):
                    alert = SystemAlert(
                        level=self._get_alert_level("memory", usage.memory_percent, self.config.memory_threshold),
                        message=f"メモリ使用率が閾値を超過しました: {usage.memory_percent:.1f}% (閾値: {self.config.memory_threshold}%)",
                        resource_type="memory",
                        current_value=usage.memory_percent,
                        threshold=self.config.memory_threshold,
                        timestamp=current_time,
                        context={
                            "total_memory_gb": psutil.virtual_memory().total / (1024**3),
                            "available_memory_gb": psutil.virtual_memory().available / (1024**3)
                        }
                    )
                    alerts.append(alert)
                    self.last_alert_times["memory"] = current_time
            
            # ディスク使用率チェック
            if usage.disk_percent > self.config.disk_threshold:
                if self._should_send_alert("disk", current_time):
                    alert = SystemAlert(
                        level=self._get_alert_level("disk", usage.disk_percent, self.config.disk_threshold),
                        message=f"ディスク使用率が閾値を超過しました: {usage.disk_percent:.1f}% (閾値: {self.config.disk_threshold}%)",
                        resource_type="disk",
                        current_value=usage.disk_percent,
                        threshold=self.config.disk_threshold,
                        timestamp=current_time,
                        context={
                            "total_disk_gb": psutil.disk_usage('/').total / (1024**3),
                            "free_disk_gb": psutil.disk_usage('/').free / (1024**3)
                        }
                    )
                    alerts.append(alert)
                    self.last_alert_times["disk"] = current_time
            
        except Exception as e:
            logger.error(f"閾値チェックエラー: {str(e)}", exc_info=True)
            # エラー時はエラーアラートを生成
            error_alert = SystemAlert(
                level=AlertLevel.ERROR,
                message=f"システム監視エラーが発生しました: {str(e)}",
                resource_type="system",
                current_value=0.0,
                threshold=0.0,
                timestamp=current_time,
                context={"error": str(e)}
            )
            alerts.append(error_alert)
        
        return alerts
    
    def _should_send_alert(self, resource_type: str, current_time: float) -> bool:
        """
        アラート送信可否判定（クールダウン考慮）
        
        Args:
            resource_type: リソースタイプ
            current_time: 現在時刻
            
        Returns:
            bool: アラート送信可否
        """
        last_alert_time = self.last_alert_times.get(resource_type, 0)
        return (current_time - last_alert_time) >= self.config.alert_cooldown_seconds
    
    def _get_alert_level(self, resource_type: str, current_value: float, threshold: float) -> AlertLevel:
        """
        アラートレベル決定
        
        Args:
            resource_type: リソースタイプ
            current_value: 現在値
            threshold: 閾値
            
        Returns:
            AlertLevel: アラートレベル
        """
        # 閾値からの超過率でレベル決定
        excess_ratio = (current_value - threshold) / threshold
        
        if excess_ratio >= 0.5:  # 50%以上超過
            return AlertLevel.CRITICAL
        elif excess_ratio >= 0.2:  # 20%以上超過
            return AlertLevel.ERROR
        else:
            return AlertLevel.WARNING
    
    def record_performance_metrics(self, metrics: PerformanceMetrics) -> None:
        """
        パフォーマンスメトリクス記録
        
        Args:
            metrics: パフォーマンスメトリクス
        """
        with self._lock:
            self.performance_metrics.append(metrics)
            
            # 古いメトリクスを削除（最新1000件まで保持）
            if len(self.performance_metrics) > 1000:
                self.performance_metrics = self.performance_metrics[-1000:]
        
        # パフォーマンス警告チェック
        if metrics.response_time_ms > self.config.response_time_threshold_ms:
            logger.warning(
                f"パフォーマンス警告: {metrics.operation_name}が{metrics.response_time_ms:.2f}ms "
                f"(閾値: {self.config.response_time_threshold_ms}ms)",
                extra={
                    "operation": metrics.operation_name,
                    "response_time_ms": metrics.response_time_ms,
                    "threshold_ms": self.config.response_time_threshold_ms,
                    "success": metrics.success
                }
            )
    
    def get_performance_summary(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """
        パフォーマンス統計取得
        
        Args:
            operation_name: 操作名（指定時はフィルタリング）
            
        Returns:
            Dict[str, Any]: パフォーマンス統計
        """
        with self._lock:
            metrics = self.performance_metrics.copy()
        
        if operation_name:
            metrics = [m for m in metrics if m.operation_name == operation_name]
        
        if not metrics:
            return {"total_operations": 0}
        
        response_times = [m.response_time_ms for m in metrics]
        success_count = sum(1 for m in metrics if m.success)
        
        return {
            "total_operations": len(metrics),
            "success_rate": success_count / len(metrics),
            "avg_response_time_ms": statistics.mean(response_times),
            "min_response_time_ms": min(response_times),
            "max_response_time_ms": max(response_times),
            "median_response_time_ms": statistics.median(response_times),
            "p95_response_time_ms": statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times)
        }


class AnomalyDetector:
    """異常検知クラス"""
    
    def __init__(self, window_size: int = 10):
        """
        初期化
        
        Args:
            window_size: 移動平均ウィンドウサイズ
        """
        self.window_size = window_size
        self.data_windows: Dict[str, Deque[float]] = {}
        self._lock = threading.Lock()
        
        logger.info(f"AnomalyDetector初期化完了: window_size={window_size}")
    
    def add_data_point(self, metric_name: str, value: float) -> None:
        """
        データポイント追加
        
        Args:
            metric_name: メトリクス名
            value: データ値
        """
        with self._lock:
            if metric_name not in self.data_windows:
                self.data_windows[metric_name] = deque(maxlen=self.window_size)
            
            self.data_windows[metric_name].append(value)
    
    def detect_anomaly(self, metric_name: str, value: float, threshold_multiplier: float = 2.0) -> bool:
        """
        異常値検知（統計的手法）
        
        Args:
            metric_name: メトリクス名
            value: 検査対象値
            threshold_multiplier: 閾値乗数（標準偏差の何倍を異常とするか）
            
        Returns:
            bool: 異常値かどうか
        """
        with self._lock:
            if metric_name not in self.data_windows:
                return False
            
            window = list(self.data_windows[metric_name])
        
        if len(window) < 5:  # 最低データ数
            return False
        
        try:
            mean_value = statistics.mean(window)
            stdev_value = statistics.stdev(window)
            
            # Z-scoreによる異常検知
            if stdev_value == 0:
                return False
            
            z_score = abs(value - mean_value) / stdev_value
            return z_score > threshold_multiplier
            
        except Exception as e:
            logger.error(f"異常検知エラー: {str(e)}", exc_info=True)
            return False
    
    def detect_trend_anomaly(self, metric_name: str, trend_threshold: float = 0.1) -> bool:
        """
        トレンド異常検知（継続的な増加・減少）
        
        Args:
            metric_name: メトリクス名
            trend_threshold: トレンド閾値（継続的変化率）
            
        Returns:
            bool: トレンド異常かどうか
        """
        with self._lock:
            if metric_name not in self.data_windows:
                return False
            
            window = list(self.data_windows[metric_name])
        
        if len(window) < 6:  # トレンド検知には最低6データポイント必要
            return False
        
        try:
            # 連続する差分を計算
            diffs = [window[i+1] - window[i] for i in range(len(window)-1)]
            
            # 同じ方向の変化が継続しているかチェック
            positive_count = sum(1 for d in diffs if d > trend_threshold)
            negative_count = sum(1 for d in diffs if d < -trend_threshold)
            
            # 80%以上が同じ方向の変化の場合、トレンド異常とみなす
            total_diffs = len(diffs)
            return (positive_count / total_diffs >= 0.8) or (negative_count / total_diffs >= 0.8)
            
        except Exception as e:
            logger.error(f"トレンド異常検知エラー: {str(e)}", exc_info=True)
            return False
    
    def get_statistics(self, metric_name: str) -> Dict[str, Any]:
        """
        メトリクス統計取得
        
        Args:
            metric_name: メトリクス名
            
        Returns:
            Dict[str, Any]: 統計データ
        """
        with self._lock:
            if metric_name not in self.data_windows:
                return {}
            
            window = list(self.data_windows[metric_name])
        
        if len(window) < 2:
            return {"data_points": len(window)}
        
        try:
            return {
                "data_points": len(window),
                "mean": statistics.mean(window),
                "median": statistics.median(window),
                "stdev": statistics.stdev(window) if len(window) >= 2 else 0,
                "min": min(window),
                "max": max(window),
                "latest": window[-1] if window else 0
            }
        except Exception as e:
            logger.error(f"統計計算エラー: {str(e)}", exc_info=True)
            return {"error": str(e)}


class LogRotationManager:
    """ログローテーション管理クラス（実装予定）"""
    
    def __init__(self, log_directory: str, max_size_mb: int = 100, max_files: int = 10):
        """
        初期化
        
        Args:
            log_directory: ログディレクトリ
            max_size_mb: 最大ログファイルサイズ（MB）
            max_files: 最大ログファイル数
        """
        self.log_directory = log_directory
        self.max_size_mb = max_size_mb
        self.max_files = max_files
        
        logger.info(f"LogRotationManager初期化完了: {log_directory}")
    
    def rotate_if_needed(self) -> bool:
        """
        必要に応じてログローテーション実行
        
        Returns:
            bool: ローテーション実行したかどうか
        """
        # 実装予定
        logger.info("ログローテーションチェック（実装予定）")
        return False


class SentryIntegration:
    """Sentry統合クラス（実装予定）"""
    
    def __init__(self, dsn: Optional[str] = None):
        """
        初期化
        
        Args:
            dsn: Sentry DSN
        """
        self.dsn = dsn
        self.enabled = dsn is not None
        
        if self.enabled:
            logger.info("Sentry統合有効化（実装予定）")
        else:
            logger.info("Sentry統合無効")
    
    def capture_exception(self, exception: Exception) -> None:
        """
        例外をSentryに送信
        
        Args:
            exception: 送信する例外
        """
        if self.enabled:
            logger.info(f"Sentryに例外送信（実装予定）: {str(exception)}")
        else:
            logger.debug(f"Sentry無効のため例外ログ出力: {str(exception)}")