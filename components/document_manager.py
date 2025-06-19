"""
文書管理 UI コンポーネント

アップロードされた文書の管理機能を提供するStreamlitコンポーネント
"""

import streamlit as st
from typing import List, Dict, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def document_manager_component() -> None:
    """文書管理メインコンポーネント"""
    st.subheader("📚 文書管理")
    
    # タブ作成
    tab1, tab2, tab3 = st.tabs(["📄 文書一覧", "📊 統計情報", "🗑️ 削除"])
    
    with tab1:
        show_document_list()
    
    with tab2:
        show_statistics()
    
    with tab3:
        show_delete_interface()

def show_document_list() -> None:
    """文書一覧表示"""
    st.write("### 登録済み文書")
    
    # サンプルデータ（実際の実装では外部データソースから取得）
    sample_documents = [
        {
            "filename": "入社手続きガイド.pdf",
            "upload_date": "2024-01-15",
            "pages": 25,
            "size": "2.3 MB",
            "status": "処理完了"
        }
    ]
    
    if sample_documents:
        for doc in sample_documents:
            with st.expander(f"📄 {doc['filename']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**アップロード日**: {doc['upload_date']}")
                    st.write(f"**ページ数**: {doc['pages']}")
                with col2:
                    st.write(f"**ファイルサイズ**: {doc['size']}")
                    st.write(f"**状態**: {doc['status']}")
    else:
        st.info("登録された文書がありません")

def show_statistics() -> None:
    """統計情報表示"""
    st.write("### 統計情報")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("総文書数", "1", delta="0")
    with col2:
        st.metric("総ページ数", "25", delta="0")
    with col3:
        st.metric("総サイズ", "2.3 MB", delta="0")

def show_delete_interface() -> None:
    """削除インターフェース"""
    st.write("### 文書削除")
    st.warning("⚠️ 削除した文書は復元できません")
    
    # サンプル選択肢
    selected_docs = st.multiselect(
        "削除する文書を選択:",
        ["入社手続きガイド.pdf"]
    )
    
    if selected_docs:
        if st.button("選択した文書を削除", type="primary"):
            st.success(f"{len(selected_docs)}個の文書を削除しました")
            st.rerun()