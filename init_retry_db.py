import sqlite3

# 連接到資料庫
conn = sqlite3.connect("retry.db")
cursor = conn.cursor()

# 根據您提供的 CREATE TABLE 語句進行修正
# 1. 保留表格名稱：retry
# 2. 保留 ID 欄位與 AUTOINCREMENT 語法 (修正為大寫: AUTOINCREMENT)
# 3. 移除不屬於 Retry 數據的欄位 (waiver_id, test_case, module, note)
# 4. 替換為 Retry 數據應有的欄位 (module_case, condition, trick)
cursor.execute("""
CREATE TABLE IF NOT EXISTS retry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,         -- 對應 Basic, GTS, CTS 等分類
    module_case TEXT NOT NULL,  -- 模組 / 測項 
    condition TEXT NOT NULL,    -- 關鍵條件 / 環境
    trick TEXT                  -- 備註 / Retry 技巧
)
""")

# 提交變更並關閉連接
conn.commit()
conn.close()

print("✅ 'retry' 資料庫建立成功。")