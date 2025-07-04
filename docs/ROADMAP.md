# RAGアプリケーション 機能向上ロードマップ

このロードマップは、現在の実装を基盤とし、より高機能で実用的な社内文書検索システムへと発展させるための提案です。フェーズは「短期」「中期」「長期」に分かれており、それぞれが独立しつつも、積み重ねることで大きな価値を生むように設計されています。

## タイムライン概要

```mermaid
gantt
    title RAGアプリケーション 機能向上ロードマップ
    dateFormat  YYYY-MM-DD
    axisFormat %Y-%m

    section フェーズ1: 基盤強化とUX向上
    検索精度の向上 :crit, task1_1, 2025-07-01, 45d
    PDF処理の高度化 :task1_2, 2025-07-15, 45d
    UI/UXの改善   :task1_3, after task1_1, 30d

    section フェーズ2: 機能拡張と運用効率化
    対応ドキュメント拡充 :task2_1, 2025-09-15, 60d
    管理機能の強化     :task2_2, after task2_1, 45d

    section フェーズ3: 高度化と自律運用
    LLMエージェント導入   :task3_1, 2025-12-15, 90d
    パーソナライズと学習 :task3_2, after task3_1, 90d
```

## フェーズ1: 短期目標 (1〜3ヶ月) - 基盤強化とUX向上

このフェーズでは、既存機能の安定性向上と、ユーザーが日常的に利用する上での体験向上に焦点を当てます。

### 1.1. 検索精度の向上

- **ハイブリッド検索の実装**:
  - **目的**: キーワード検索とベクトル検索を組み合わせ、より網羅的な検索結果を提供する。専門用語や固有名詞など、ベクトル化で失われがちな情報も捉えられるようにする。
  - **実装案**:
    - `services/vector_store.py` に全文検索機能（例: Supabaseの `to_tsvector`）を追加。
    - 検索時にベクトル検索と全文検索を並行して実行し、結果を統合（Reciprocal Rank Fusionなど）してランキングするロジックを実装。

- **リランキング機能の導入**:
  - **目的**: 初期検索結果を、より文脈に合った順序に並べ替えることで、ユーザーが求める情報へのアクセスを高速化する。
  - **実装案**:
    - `services/claude_llm.py` に、検索結果とクエリの関連性を評価するプロンプトを追加し、リランキング用の小規模なLLMコールを実装する。
    - `streamlit_app.py` の回答生成プロセスにリランキングのステップを組み込む。

### 1.2. PDF処理の高度化

- **テーブル・画像の認識と抽出**:
  - **目的**: PDF内のテーブル（表）や画像を認識し、構造化データとして扱えるようにする。「〜の仕様を表で示して」といった質問に対応可能にする。
  - **実装案**:
    - `services/pdf_processor.py` に `PyMuPDF` のテーブル検出機能や画像抽出機能を追加。
    - 抽出したテーブルはMarkdown形式に変換し、画像は別途保存して参照できるようにする。

- **文書構造解析の活用**:
  - **目的**: `pdf_processor.py` で解析済みの文書構造（章、節）を検索や回答生成に活用する。
  - **実装案**:
    - チャンクに章や節の情報をメタデータとして付与し、`vector_store.py` に保存。
    - 回答生成時に「第3章の〜について」といった文脈を考慮できるようにする。

### 1.3. ユーザーインターフェースの改善

- **チャット履歴の永続化と検索**:
  - **目的**: 過去のQ&Aを再利用できるようにし、同じ質問を繰り返す手間を省く。
  - **実装案**:
    - Supabaseに `chat_history` テーブルを追加。
    - `components/chat_interface.py` でチャット履歴をDBに保存・読み込みする機能を実装。サイドバーに履歴一覧を表示する。

- **フィードバック機能の実装**:
  - **目的**: ユーザーからのフィードバック（回答が役に立ったか等）を収集し、システムの継続的な改善に繋げる。
  - **実装案**:
    - 回答の下に「👍」「👎」ボタンを設置。
    - フィードバック結果をSupabaseのテーブルに保存し、分析用のダッシュボードを作成する。

## フェーズ2: 中期目標 (3〜6ヶ月) - 機能拡張と運用効率化

このフェーズでは、対応できるドキュメントの種類を増やし、管理者向けの運用機能を追加します。

### 2.1. 対応ドキュメント形式の拡充

- **MS Officeファイル（Word, PowerPoint）への対応**:
  - **目的**: PDF以外の一般的な社内ドキュメント形式に対応し、利用範囲を拡大する。
  - **実装案**:
    - `python-docx`, `python-pptx` ライブラリを導入。
    - ファイル形式に応じて処理を分岐させるファクトリーパターンを `services` 層に導入する。

- **Webページ（URL）からの情報取得**:
  - **目的**: 社内Wikiやイントラネット等のWebページも情報ソースとして活用できるようにする。
  - **実装案**:
    - `BeautifulSoup` や `Scrapy` を利用したWebスクレイピング機能を `services` に追加。
    - URLを指定してコンテンツを取り込み、チャンク化・ベクトル化するUIを実装。

### 2.2. 管理機能の強化

- **管理者向けダッシュボード**:
  - **目的**: システムの利用状況、検索キーワード、ユーザーフィードバックなどを可視化し、運用改善に役立てる。
  - **実装案**:
    - Streamlitの別ページとして管理者用ダッシュボードを作成。
    - Supabaseに保存されたログやフィードバックデータを集計し、グラフ表示する。

- **定期的なドキュメント同期**:
  - **目的**: 特定のフォルダやクラウドストレージ（Google Drive, SharePoint等）を監視し、ドキュメントの追加・更新を自動でシステムに反映させる。
  - **実装案**:
    - `watchdog` ライブラリや各クラウドストレージのAPIを利用した同期スクリプトを作成。
    - これをバックグラウンドプロセスとして定期実行する仕組みを導入（例: cron, Celery）。

## フェーズ3: 長期目標 (6ヶ月〜) - 高度化と自律運用

このフェーズでは、より高度なAI技術を導入し、システムの自律的な改善とパーソナライズを目指します。

### 3.1. LLMエージェント機能の導入

- **多段階の質問応答（Multi-hop QA）**:
  - **目的**: 複雑な質問に対し、複数の情報源を組み合わせて段階的に調査し、一つの回答を生成する。
  - **実装案**:
    - LangChain AgentsやLlamaIndexのQuery Engineなどを活用。
    - 「AとBの違いを比較し、Cの観点から評価して」といった複雑なクエリに対応できるエージェントを構築する。

- **Function Callingによる外部連携****:
  - **目的**: チャットインターフェースから他の社内システム（勤怠管理、経費精算など）の情報を参照・操作できるようにする。
  - **実装案**:
    - Claude APIのFunction Calling（Tool Use）機能を活用。
    - 各社内システムのAPIを呼び出すツールを定義し、LLMが適切に利用できるようにする。

### 3.2. パーソナライズと継続的学習

- **ユーザープロファイルに基づいた回答の最適化**:
  - **目的**: ユーザーの部署や役職に応じて、参照するドキュメントの優先度を変えたり、専門用語の解説レベルを調整したりする。
  - **実装案**:
    - ユーザープロファイル（部署、専門分野など）を管理するテーブルをDBに追加。
    - 検索時や回答生成時にプロファイル情報を考慮するロジックを組み込む。

- **オンライン学習によるシステム自己改善**:
  - **目的**: ユーザーのフィードバックや利用ログを基に、検索モデルや回答生成プロンプトを自動で微調整（Fine-tuning）する。
  - **実装案**:
    - 収集したデータを学習用データセットとして整形。
    - 定期的にEmbeddingモデルや小規模なLLMのFine-tuningを行い、モデルを更新するパイプラインを構築する。