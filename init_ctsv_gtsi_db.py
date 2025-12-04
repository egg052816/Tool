# migrate_ctsv_gtsi_to_multiimage.py
# 將舊版 ctsv_gtsi.db (含 test_cards.image_url) 遷移成支援多圖的 schema (card_images)
# 執行前請先關閉你的 Flask server
import sqlite3
import os
import shutil
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = "ctsv_gtsi.db"
DB_PATH = os.path.join(BASE_DIR, DB_NAME)

BACKUP_NAME = f"ctsv_gtsi_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.db"
BACKUP_PATH = os.path.join(BASE_DIR, BACKUP_NAME)

def backup_db():
    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, BACKUP_PATH)
        print(f"已備份原資料庫到: {BACKUP_PATH}")
    else:
        print(f"資料庫 {DB_PATH} 不存在，將建立新的資料庫。")

def table_exists(cur, table_name):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table_name,))
    return cur.fetchone() is not None

def migrate():
    print("開始遷移 ctsv_gtsi.db ...")
    backup_db()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 確保 foreign_keys 啟用
    cur.execute("PRAGMA foreign_keys = ON;")

    # 1) 如果 ctsv_sections 不存在，建立預設
    if not table_exists(cur, "ctsv_sections"):
        print("ctsv_sections 不存在，建立預設 sections ...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ctsv_sections (
                section_key TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                tag TEXT,
                display_order INTEGER NOT NULL DEFAULT 0
            );
        """)
        default_sections = [
            ('GTSI', 'GTS Interactive 區塊', 'Android 13+ / MADA', 10),
            ('CTSV', 'CTS Verifier 區塊', 'CameraITS / Audio / Sensor', 20),
            ('MADA', 'MADA Check List 區塊', 'Auto discoverability / Doc', 30),
        ]
        cur.executemany("INSERT OR IGNORE INTO ctsv_sections (section_key, title, tag, display_order) VALUES (?,?,?,?)", default_sections)
        conn.commit()
        print("已建立並插入預設 ctsv_sections。")

    # 2) 如果 test_cards 不存在，建立新版結構（不含 image_url）
    if not table_exists(cur, "test_cards"):
        print("test_cards 不存在，建立新版 test_cards ...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS test_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_key TEXT NOT NULL,
                card_title TEXT NOT NULL,
                card_subtitle TEXT,
                content TEXT,
                note TEXT,
                display_order INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(section_key) REFERENCES ctsv_sections(section_key)
            );
        """)
        conn.commit()
        print("已建立 test_cards（新版）。")

    # 3) 若 card_images 不存在，建立
    if not table_exists(cur, "card_images"):
        print("建立 card_images 表 ...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS card_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                display_order INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(card_id) REFERENCES test_cards(id) ON DELETE CASCADE
            );
        """)
        conn.commit()
        print("已建立 card_images 。")

    # 4) 檢查舊版 test_cards 是否有 image_url 欄位（如果存在且有值，需要遷移）
    # 透過 PRAGMA table_info 取得欄位
    cur.execute("PRAGMA table_info(test_cards);")
    cols = [r["name"] for r in cur.fetchall()]
    if "image_url" in cols:
        print("發現舊版 test_cards.image_url 欄位，開始遷移 image_url 到 card_images ...")
        # 取得現有所有卡片（含 image_url）
        cur.execute("SELECT id, image_url FROM test_cards WHERE image_url IS NOT NULL AND TRIM(image_url) <> ''")
        rows = cur.fetchall()
        moved = 0
        for r in rows:
            card_id = r["id"]
            image_url = r["image_url"].strip()
            # 若 image_url 可能包含多個以逗號分隔（保險），先拆解
            candidates = [p.strip() for p in image_url.split(',') if p.strip()]
            for idx, p in enumerate(candidates):
                cur.execute("INSERT INTO card_images (card_id, filename, display_order) VALUES (?,?,?)",
                            (card_id, p, (idx+1)*10))
                moved += 1
        conn.commit()
        print(f"已將 {moved} 筆 image_url 資料搬移到 card_images。")

        # 5) 為了完全移除 image_url 欄位，對 test_cards 做 table 重建 (SQLite 不支援直接 DROP COLUMN)
        print("準備重建 test_cards（去除 image_url 欄位）...")
        # 讀出現有資料（完整）
        cur.execute("SELECT id, section_key, card_title, card_subtitle, content, note, display_order FROM test_cards")
        all_cards = cur.fetchall()

        # 建立臨時表 new_test_cards
        cur.execute("""
            CREATE TABLE IF NOT EXISTS new_test_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_key TEXT NOT NULL,
                card_title TEXT NOT NULL,
                card_subtitle TEXT,
                content TEXT,
                note TEXT,
                display_order INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(section_key) REFERENCES ctsv_sections(section_key)
            );
        """)
        conn.commit()

        # 將資料寫入 new_test_cards（保留原 id）
        for r in all_cards:
            cur.execute("""
                INSERT INTO new_test_cards (id, section_key, card_title, card_subtitle, content, note, display_order)
                VALUES (?,?,?,?,?,?,?)
            """, (r["id"], r["section_key"], r["card_title"], r["card_subtitle"], r["content"], r["note"], r["display_order"]))
        conn.commit()

        # 刪除舊表，rename new -> test_cards
        cur.execute("DROP TABLE test_cards;")
        cur.execute("ALTER TABLE new_test_cards RENAME TO test_cards;")
        conn.commit()
        print("重建完成，test_cards 已不包含 image_url 欄位。")
    else:
        print("test_cards 無 image_url 欄位，無需遷移該欄位。")

    # 6) 最後檢查 card_images 是否成功
    cur.execute("SELECT COUNT(*) AS cnt FROM card_images")
    cnt = cur.fetchone()["cnt"]
    print(f"card_images 總筆數: {cnt}")

    conn.close()
    print("遷移完成，請重新啟動 Flask 並在前端測試新增/上傳圖片功能。")
    print(f"如有問題可以回復我，我會幫你檢查 API 呼叫及日誌 (Flask console log)。")

if __name__ == "__main__":
    migrate()
