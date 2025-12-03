# init_ctsv_gtsi_db.py

import sqlite3
import os

# ----------------------------------------
# 設定
# ----------------------------------------
# 假設資料庫文件將在腳本執行的目錄中創建
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = "ctsv_gtsi.db"
DB_PATH = os.path.join(BASE_DIR, DB_NAME)


def init_ctsv_gtsi_db():
    """
    建立 ctsv_gtsi.db 檔案，並初始化所有必要的表格和預設數據。
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 1. 建立 ctsv_sections 表格 (頂層導航錨點)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ctsv_sections (
                section_key TEXT PRIMARY KEY,    /* 'GTSI', 'CTSV', 'MADA' */
                title TEXT NOT NULL,             /* e.g., 'GTS Interactive 區塊' */
                tag TEXT,                        /* e.g., 'Android 13+ / MADA' */
                display_order INTEGER NOT NULL DEFAULT 0
            );
            """
        )

        # 2. 建立 test_cards 表格 (每個測試步驟卡片)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS test_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_key TEXT NOT NULL,       /* FK: GTSI, CTSV, MADA */
                card_title TEXT NOT NULL,        /* e.g., 'Audio Loopback Latency Test' */
                card_subtitle TEXT,              /* Small text under title */
                content TEXT,                    /* Main content / Step list */
                image_url TEXT,                  /* Primary image URL */
                note TEXT,                       /* Content for the dedicated note box */
                display_order INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(section_key) REFERENCES ctsv_sections(section_key)
            );
            """
        )

        # 3. 檢查並插入預設區塊 (如果表格為空)
        cursor.execute("SELECT COUNT(*) FROM ctsv_sections")
        if cursor.fetchone()[0] == 0:
            default_sections = [
                ('GTSI', 'GTS Interactive 區塊', 'Android 13+ / MADA', 10),
                ('CTSV', 'CTS Verifier 區塊', 'CameraITS / Audio / Sensor', 20),
                ('MADA', 'MADA Check List 區塊', 'Auto discoverability / Doc', 30),
            ]
            cursor.executemany(
                """
                INSERT INTO ctsv_sections (section_key, title, tag, display_order)
                VALUES (?, ?, ?, ?)
                """,
                default_sections
            )
            print("    [CTSV_GTSI Sections] 插入預設頂層區塊。")

        conn.commit()
        print(f"✅ 資料庫 '{DB_NAME}' 初始化完成，表格結構已建立。")

    except sqlite3.Error as e:
        print(f"❌ 資料庫操作失敗: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()


if __name__ == "__main__":
    init_ctsv_gtsi_db()