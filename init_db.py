import sqlite3

conn = sqlite3.connect("waiver.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS waivers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    suite TEXT NOT NULL,
    waiver_id TEXT,
    module TEXT,
    test_case TEXT,
    note TEXT
)
""")

conn.commit()
conn.close()

print("資料庫建立成功")