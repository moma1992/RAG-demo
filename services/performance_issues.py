"""
パフォーマンス上の致命的問題を含むサービス（テスト用）
このファイルは意図的にパフォーマンス問題を含み、AIレビューでの検出テストに使用
"""
import time
import requests


class PerformanceIssueService:
    """パフォーマンス問題があるサービスクラス（テスト用）"""
    
    def __init__(self):
        self.data = []
        
    def inefficient_search(self, documents, search_term):
        """O(n²)の非効率なアルゴリズム"""
        # 致命的エラー1: O(n²)の非効率な検索
        results = []
        for doc in documents:
            for word in doc.split():
                if search_term in word:
                    for other_doc in documents:  # 不要なネストループ
                        if other_doc != doc:
                            results.append((doc, other_doc))
        return results
        
    def blocking_api_calls(self, urls):
        """ブロッキングAPIコール"""
        # 致命的エラー2: 同期的な大量APIコール
        results = []
        for url in urls:
            response = requests.get(url, timeout=30)  # タイムアウトが長すぎ
            results.append(response.text)
            time.sleep(1)  # 不要な待機
        return results
        
    def memory_leak_function(self, iterations=10000):
        """メモリリークを引き起こす関数"""
        # 致命的エラー3: メモリリーク
        big_data = []
        for i in range(iterations):
            # 大量のデータを蓄積し続ける
            big_data.append([0] * 10000)
            self.data.append(big_data)  # グローバルリストに追加し続ける
        return len(big_data)
        
    def recursive_without_limit(self, n):
        """スタックオーバーフローを引き起こす再帰"""
        # 致命的エラー4: 制限のない再帰（スタックオーバーフロー）
        if n == 0:
            return 1
        return n * self.recursive_without_limit(n + 1)  # 無限再帰
        
    def inefficient_string_concat(self, items):
        """非効率な文字列結合"""
        # 致命的エラー5: 非効率な文字列結合（O(n²)）
        result = ""
        for item in items:
            result += str(item) + ","  # 毎回新しい文字列オブジェクト作成
        return result
        
    def database_n_plus_1(self, user_ids):
        """N+1クエリ問題"""
        # 致命的エラー6: N+1クエリ問題
        users = []
        for user_id in user_ids:
            # 各ユーザーごとに個別クエリ（非効率）
            user = self.get_user_by_id(user_id)
            profile = self.get_user_profile(user_id)  # 追加クエリ
            users.append((user, profile))
        return users
        
    def get_user_by_id(self, user_id):
        """模擬的なDBクエリ"""
        time.sleep(0.1)  # DB遅延をシミュレート
        return f"User {user_id}"
        
    def get_user_profile(self, user_id):
        """模擬的なDBクエリ"""
        time.sleep(0.1)  # DB遅延をシミュレート  
        return f"Profile for {user_id}"
        
    def inefficient_file_processing(self, file_paths):
        """非効率なファイル処理"""
        # 致命的エラー7: ファイルを何度も開き直す
        content = ""
        for path in file_paths:
            for line_num in range(1000):  # 1000回ファイルを開く
                with open(path, 'r') as f:
                    lines = f.readlines()
                    if line_num < len(lines):
                        content += lines[line_num]
        return content
        
    def cpu_intensive_loop(self, size=1000000):
        """CPU集約的な処理"""
        # 致命的エラー8: 非効率なCPU集約処理
        result = 0
        for i in range(size):
            for j in range(size):  # O(n²)の無駄な計算
                result += i * j
        return result


def global_inefficient_function():
    """グローバルスコープの非効率な関数"""
    # 致命的エラー9: グローバルな非効率処理
    data = list(range(100000))
    sorted_data = []
    
    # バブルソート（O(n²)）を実装
    for i in range(len(data)):
        for j in range(len(data) - 1):
            if data[j] > data[j + 1]:
                data[j], data[j + 1] = data[j + 1], data[j]
                
    return data