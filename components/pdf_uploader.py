"""
PDF アップロード UI コンポーネント

PDFファイルのアップロード機能を提供するStreamlitコンポーネント
"""

import streamlit as st
from typing import Optional, List
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def pdf_uploader_component() -> Optional[List[bytes]]:
    """
    PDFアップロードコンポーネント
    
    Returns:
        Optional[List[bytes]]: アップロードされたPDFファイルのバイトデータリスト
    """
    st.subheader("📁 PDF文書アップロード")
    
    uploaded_files = st.file_uploader(
        "PDFファイルを選択してください",
        type="pdf",
        accept_multiple_files=True,
        help="複数のPDFファイルを同時にアップロードできます"
    )
    
    if uploaded_files:
        st.success(f"{len(uploaded_files)}個のファイルがアップロードされました")
        
        # ファイル情報表示
        for file in uploaded_files:
            st.write(f"📄 {file.name} ({file.size:,} bytes)")
        
        return [file.getvalue() for file in uploaded_files]
    
    return None

def upload_progress_component(current: int, total: int, filename: str) -> None:
    """
    アップロード進捗表示コンポーネント
    
    Args:
        current: 現在の進捗
        total: 総数
        filename: 処理中のファイル名
    """
    progress = current / total if total > 0 else 0
    st.progress(progress)
    st.text(f"処理中: {filename} ({current}/{total})")