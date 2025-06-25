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
    
    try:
        # VectorStoreからドキュメント一覧を取得
        if "vector_store" in st.session_state:
            vector_store = st.session_state.vector_store
            documents = vector_store.get_documents()
            
            if documents:
                for doc in documents:
                    # ファイルサイズを MB 単位に変換
                    size_mb = doc.file_size / 1024 / 1024 if doc.file_size else 0
                    size_str = f"{size_mb:.1f} MB" if size_mb > 0 else "不明"
                    
                    # アップロード日の表示形式調整
                    upload_date = doc.upload_date.split('T')[0] if 'T' in doc.upload_date else doc.upload_date
                    
                    with st.expander(f"📄 {doc.original_filename}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**アップロード日**: {upload_date}")
                            st.write(f"**ページ数**: {doc.total_pages or '不明'}")
                        with col2:
                            st.write(f"**ファイルサイズ**: {size_str}")
                            st.write(f"**状態**: {doc.processing_status}")
                        
                        # 関連チャンク数を表示
                        try:
                            chunk_count = vector_store.client.table('document_chunks').select('id', count='exact').eq('document_id', doc.id).execute()
                            st.write(f"**チャンク数**: {chunk_count.count}件")
                        except Exception as e:
                            logger.warning(f"チャンク数取得エラー: {str(e)}")
                            st.write(f"**チャンク数**: 不明")
            else:
                st.info("登録された文書がありません")
        else:
            st.error("ベクターストアが初期化されていません")
            # フォールバック: サンプルデータ表示
            _show_sample_document_list()
            
    except Exception as e:
        logger.error(f"文書一覧取得エラー: {str(e)}")
        st.error(f"文書一覧の取得に失敗しました: {str(e)}")
        # フォールバック: サンプルデータ表示
        _show_sample_document_list()

def _show_sample_document_list() -> None:
    """サンプル文書一覧表示（フォールバック用）"""
    sample_documents = [
        {
            "filename": "入社手続きガイド.pdf",
            "upload_date": "2024-01-15",
            "pages": 25,
            "size": "2.3 MB",
            "status": "処理完了",
            "chunks": 5
        }
    ]
    
    for doc in sample_documents:
        with st.expander(f"📄 {doc['filename']}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**アップロード日**: {doc['upload_date']}")
                st.write(f"**ページ数**: {doc['pages']}")
            with col2:
                st.write(f"**ファイルサイズ**: {doc['size']}")
                st.write(f"**状態**: {doc['status']}")
            st.write(f"**チャンク数**: {doc['chunks']}件")

def show_statistics() -> None:
    """統計情報表示"""
    st.write("### 統計情報")
    
    try:
        if "vector_store" in st.session_state:
            vector_store = st.session_state.vector_store
            
            # 文書統計を取得
            documents = vector_store.get_documents()
            total_docs = len(documents)
            total_pages = sum(doc.total_pages or 0 for doc in documents)
            total_size_mb = sum(doc.file_size or 0 for doc in documents) / 1024 / 1024
            
            # チャンク統計を取得
            try:
                chunk_result = vector_store.client.table('document_chunks').select('id', count='exact').execute()
                total_chunks = chunk_result.count
            except Exception:
                total_chunks = 0
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("総文書数", f"{total_docs}")
            with col2:
                st.metric("総ページ数", f"{total_pages}")
            with col3:
                st.metric("総サイズ", f"{total_size_mb:.1f} MB")
            with col4:
                st.metric("総チャンク数", f"{total_chunks}")
                
        else:
            st.error("ベクターストアが初期化されていません")
            # フォールバック表示
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("総文書数", "1")
            with col2:
                st.metric("総ページ数", "25")
            with col3:
                st.metric("総サイズ", "2.3 MB")
            
    except Exception as e:
        logger.error(f"統計情報取得エラー: {str(e)}")
        st.error(f"統計情報の取得に失敗しました: {str(e)}")
        # フォールバック表示
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("総文書数", "不明")
        with col2:
            st.metric("総ページ数", "不明")
        with col3:
            st.metric("総サイズ", "不明")

def show_delete_interface() -> None:
    """削除インターフェース"""
    st.write("### 文書削除")
    st.warning("⚠️ 削除した文書は復元できません。関連するすべてのチャンクも削除されます。")
    
    try:
        if "vector_store" in st.session_state:
            vector_store = st.session_state.vector_store
            documents = vector_store.get_documents()
            
            if documents:
                # 文書選択肢
                doc_options = {doc.original_filename: doc.id for doc in documents}
                selected_docs = st.multiselect(
                    "削除する文書を選択:",
                    options=list(doc_options.keys())
                )
                
                if selected_docs:
                    st.write(f"選択した文書: {len(selected_docs)}件")
                    for doc_name in selected_docs:
                        st.write(f"- {doc_name}")
                    
                    if st.button("選択した文書を削除", type="primary"):
                        try:
                            # 削除処理
                            for doc_name in selected_docs:
                                doc_id = doc_options[doc_name]
                                vector_store.delete_document(doc_id)
                            
                            st.success(f"{len(selected_docs)}個の文書を削除しました")
                            st.rerun()
                            
                        except Exception as e:
                            logger.error(f"文書削除エラー: {str(e)}")
                            st.error(f"文書削除中にエラーが発生しました: {str(e)}")
            else:
                st.info("削除可能な文書がありません")
        else:
            st.error("ベクターストアが初期化されていません")
            
    except Exception as e:
        logger.error(f"削除インターフェースエラー: {str(e)}")
        st.error(f"削除機能でエラーが発生しました: {str(e)}")
        # フォールバック: サンプル選択肢
        selected_docs = st.multiselect(
            "削除する文書を選択:",
            ["入社手続きガイド.pdf"]
        )
        
        if selected_docs:
            if st.button("選択した文書を削除", type="primary"):
                st.info("デモモードでは削除機能は利用できません")