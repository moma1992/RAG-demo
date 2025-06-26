"""
PDF アップロード UI コンポーネント - Issue #66

PDFファイルのアップロード機能を提供するStreamlitコンポーネント
ベクターストアへの保存とチャンク処理を統合
"""

import streamlit as st
from typing import Optional, List
import logging
from pathlib import Path
import tempfile
import uuid

logger = logging.getLogger(__name__)

def pdf_uploader_component() -> None:
    """
    PDFアップロードコンポーネント（統合版）
    """
    st.subheader("📁 PDF文書アップロード")
    
    # サービス状態確認
    required_services = ["vector_store", "embedding_service"]
    missing_services = []
    
    for service in required_services:
        if service not in st.session_state:
            missing_services.append(service)
    
    if missing_services:
        st.error(f"PDF処理には以下のサービスが必要です: {', '.join(missing_services)}")
        st.info("設定ページでAPIキーを確認してください。")
        return
    
    # ファイルアップロード
    uploaded_files = st.file_uploader(
        "PDFファイルを選択してください",
        type="pdf",
        accept_multiple_files=True,
        help="複数のPDFファイルを同時にアップロードできます（最大10GB）"
    )
    
    if uploaded_files:
        st.success(f"{len(uploaded_files)}個のファイルがアップロードされました")
        
        # ファイル情報表示
        total_size = 0
        for file in uploaded_files:
            size_mb = file.size / 1024 / 1024
            total_size += size_mb
            st.write(f"📄 {file.name} ({size_mb:.1f} MB)")
        
        st.write(f"**総サイズ**: {total_size:.1f} MB")
        
        # 処理オプション
        with st.expander("⚙️ 処理オプション"):
            chunk_size = st.slider("チャンクサイズ（トークン数）", 256, 1024, 512)
            overlap_ratio = st.slider("オーバーラップ率", 0.0, 0.3, 0.1)
            
        # 処理開始ボタン
        if st.button("PDF処理を開始", type="primary"):
            process_uploaded_pdfs(uploaded_files, chunk_size, overlap_ratio)

def process_uploaded_pdfs(uploaded_files: List, chunk_size: int, overlap_ratio: float) -> None:
    """
    アップロードされたPDFファイルを処理
    
    Args:
        uploaded_files: アップロードされたファイルリスト
        chunk_size: チャンクサイズ
        overlap_ratio: オーバーラップ率
    """
    try:
        # サービス取得
        vector_store = st.session_state.vector_store
        embedding_service = st.session_state.embedding_service
        
        # 必要なサービスをインポート
        from services.pdf_processor import PDFProcessor
        from services.text_chunker import TextChunker
        
        # プログレスバー
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_files = len(uploaded_files)
        
        for i, uploaded_file in enumerate(uploaded_files):
            file_progress = i / total_files
            progress_bar.progress(file_progress)
            status_text.text(f"処理中: {uploaded_file.name} ({i+1}/{total_files})")
            
            try:
                # 一時ファイルに保存
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                # PDFを処理
                pdf_processor = PDFProcessor()
                extracted_data = pdf_processor.extract_text_from_pdf(Path(tmp_path))
                
                # 文書をデータベースに保存
                document_id = str(uuid.uuid4())
                vector_store.add_document(
                    id=document_id,
                    filename=uploaded_file.name,
                    original_filename=uploaded_file.name,
                    file_size=uploaded_file.size,
                    total_pages=len(extracted_data.pages),
                    processing_status="processing"
                )
                
                # テキストをチャンクに分割
                text_chunker = TextChunker(
                    chunk_size=chunk_size,
                    overlap_ratio=overlap_ratio
                )
                
                chunks = []
                for page_num, page_data in enumerate(extracted_data.pages, 1):
                    # TextBlocksからページ全体のテキストを結合
                    page_text = "\n".join([block.content for block in page_data.text_blocks])
                    
                    page_chunks = text_chunker.chunk_text(
                        page_text,
                        metadata={
                            "page_number": page_num,
                            "filename": uploaded_file.name
                        }
                    )
                    chunks.extend(page_chunks)
                
                # チャンクごとに埋め込み生成と保存
                chunk_progress = st.progress(0)
                chunk_status = st.empty()
                
                for j, chunk in enumerate(chunks):
                    chunk_progress.progress(j / len(chunks))
                    chunk_status.text(f"埋め込み生成中: チャンク {j+1}/{len(chunks)}")
                    
                    # 埋め込み生成
                    embedding_result = embedding_service.generate_embedding(chunk.content)
                    
                    # ベクターストアに保存
                    vector_store.add_chunk(
                        document_id=document_id,
                        content=chunk.content,
                        filename=uploaded_file.name,
                        page_number=chunk.metadata.get("page_number", 1),
                        embedding=embedding_result.embedding,
                        token_count=chunk.token_count
                    )
                
                # 処理完了をマーク
                vector_store.update_document_status(document_id, "completed")
                
                # 一時ファイル削除
                Path(tmp_path).unlink()
                
                # チャンクプログレスバーをクリア
                chunk_progress.empty()
                chunk_status.empty()
                
            except Exception as e:
                logger.error(f"ファイル {uploaded_file.name} の処理エラー: {str(e)}")
                st.error(f"ファイル {uploaded_file.name} の処理中にエラーが発生しました: {str(e)}")
                continue
        
        # 処理完了
        progress_bar.progress(1.0)
        status_text.text("処理完了！")
        st.success(f"{total_files}個のPDFファイルの処理が完了しました")
        
        # 自動でチャットページに移動を提案
        if st.button("チャットページに移動", type="secondary"):
            st.switch_page("チャット")
            
    except Exception as e:
        logger.error(f"PDF処理エラー: {str(e)}")
        st.error(f"PDF処理中にエラーが発生しました: {str(e)}")

def simple_pdf_uploader_component() -> Optional[List[bytes]]:
    """
    シンプルなPDFアップロードコンポーネント（後方互換性用）
    
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