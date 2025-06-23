# データベースセットアップ

## Supabaseテーブル作成手順

### 1. Supabaseダッシュボードにアクセス
1. [Supabase Dashboard](https://supabase.com/dashboard)にログイン
2. プロジェクトを選択
3. 左メニューの「SQL Editor」をクリック

### 2. テーブル作成SQLの実行
1. `create_tables.sql`ファイルの内容をコピー
2. SQL Editorに貼り付け
3. 「RUN」ボタンをクリックして実行

### 3. テーブル作成確認
以下のクエリで作成されたテーブルを確認：

```sql
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('documents', 'document_chunks');
```

### 4. pgvector拡張の確認
ベクトル検索機能が有効になっているか確認：

```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

## テーブル構造

### documents テーブル
- 文書メタデータ管理
- PDFファイル情報、処理ステータスを保存

### document_chunks テーブル  
- 文書チャンク管理
- テキスト内容、ベクトル埋め込み、位置情報を保存
- OpenAI text-embedding-3-small (1536次元) 対応

## インデックス
- ベクトル検索用: ivfflat インデックス
- 一般検索用: filename, processing_status, page_number等

## Row Level Security (RLS)
- 開発初期は全アクセス許可
- 本番環境では適切なセキュリティポリシーに更新予定