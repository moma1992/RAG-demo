"""
設定管理ユーティリティ

環境変数と設定値の管理機能
"""

import os
from typing import Optional, Dict, Any
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class APIConfig:
    """API設定"""
    openai_api_key: str
    anthropic_api_key: str
    openai_model: str = "text-embedding-3-small"
    claude_model: str = "claude-3-haiku-20240307"

@dataclass
class DatabaseConfig:
    """データベース設定"""
    supabase_url: str
    supabase_anon_key: str

@dataclass
class AppConfig:
    """アプリケーション設定"""
    max_file_size_mb: int = 50
    max_files_per_upload: int = 10
    chunk_size: int = 512
    chunk_overlap: float = 0.1
    search_top_k: int = 5
    similarity_threshold: float = 0.7

class ConfigManager:
    """設定管理クラス"""
    
    def __init__(self) -> None:
        """初期化"""
        self._api_config: Optional[APIConfig] = None
        self._db_config: Optional[DatabaseConfig] = None
        self._app_config: AppConfig = AppConfig()
        logger.info("ConfigManager初期化完了")
    
    @property
    def api_config(self) -> APIConfig:
        """API設定を取得"""
        if self._api_config is None:
            self._api_config = self._load_api_config()
        return self._api_config
    
    @property
    def db_config(self) -> DatabaseConfig:
        """データベース設定を取得"""
        if self._db_config is None:
            self._db_config = self._load_db_config()
        return self._db_config
    
    @property
    def app_config(self) -> AppConfig:
        """アプリケーション設定を取得"""
        return self._app_config
    
    def _load_api_config(self) -> APIConfig:
        """API設定をロード"""
        try:
            # Streamlit Secretsから取得を試行
            import streamlit as st
            
            openai_key = st.secrets.get("OPENAI_API_KEY")
            anthropic_key = st.secrets.get("ANTHROPIC_API_KEY")
            
            if not openai_key or not anthropic_key:
                raise KeyError("API keys not found in Streamlit secrets")
                
            return APIConfig(
                openai_api_key=openai_key,
                anthropic_api_key=anthropic_key,
                openai_model=st.secrets.get("OPENAI_MODEL", "text-embedding-3-small"),
                claude_model=st.secrets.get("CLAUDE_MODEL", "claude-3-haiku-20240307")
            )
            
        except (ImportError, KeyError):
            # 環境変数から取得
            return APIConfig(
                openai_api_key=self._get_env_var("OPENAI_API_KEY"),
                anthropic_api_key=self._get_env_var("ANTHROPIC_API_KEY"),
                openai_model=os.getenv("OPENAI_MODEL", "text-embedding-3-small"),
                claude_model=os.getenv("CLAUDE_MODEL", "claude-3-haiku-20240307")
            )
    
    def _load_db_config(self) -> DatabaseConfig:
        """データベース設定をロード"""
        try:
            # Streamlit Secretsから取得を試行
            import streamlit as st
            
            supabase_url = st.secrets.get("SUPABASE_URL")
            supabase_key = st.secrets.get("SUPABASE_ANON_KEY")
            
            if not supabase_url or not supabase_key:
                raise KeyError("Supabase keys not found in Streamlit secrets")
                
            return DatabaseConfig(
                supabase_url=supabase_url,
                supabase_anon_key=supabase_key
            )
            
        except (ImportError, KeyError):
            # 環境変数から取得
            return DatabaseConfig(
                supabase_url=self._get_env_var("SUPABASE_URL"),
                supabase_anon_key=self._get_env_var("SUPABASE_ANON_KEY")
            )
    
    def _get_env_var(self, key: str) -> str:
        """環境変数を取得"""
        value = os.getenv(key)
        if not value:
            raise ConfigError(f"環境変数 {key} が設定されていません")
        return value
    
    def validate_config(self) -> bool:
        """設定を検証"""
        try:
            # API設定の検証
            api_config = self.api_config
            if not api_config.openai_api_key.startswith(('sk-', 'sk_')):
                logger.warning("OpenAI APIキーの形式が正しくない可能性があります")
                
            # データベース設定の検証
            db_config = self.db_config
            if not db_config.supabase_url.startswith('https://'):
                logger.warning("Supabase URLの形式が正しくない可能性があります")
            
            logger.info("設定検証完了")
            return True
            
        except Exception as e:
            logger.error(f"設定検証エラー: {str(e)}")
            return False
    
    def get_streamlit_config(self) -> Dict[str, Any]:
        """Streamlit用設定を取得"""
        return {
            "page_title": "社内文書検索RAG",
            "page_icon": "📚",
            "layout": "wide",
            "initial_sidebar_state": "expanded"
        }

# グローバル設定インスタンス
config_manager = ConfigManager()

class ConfigError(Exception):
    """設定エラー"""
    pass