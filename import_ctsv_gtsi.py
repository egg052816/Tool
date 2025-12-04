# import_ctsv_gtsi.py
# -*- coding: utf-8 -*-
"""
將固定內容（對應你提供的 ctsv_gtsi HTML）匯入 ctsv_gtsi.db。
- 建立或確認表格: ctsv_sections, test_cards, card_images
- 清空 test_cards & card_images，然後匯入 HTML 裡的卡片與多張圖片
"""
import sqlite3
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "ctsv_gtsi.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def ensure_tables(conn):
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ctsv_sections (
        section_key TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        tag TEXT,
        display_order INTEGER NOT NULL DEFAULT 0
    );
    """)
    # test_cards (no image_url column; images in card_images)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS test_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        section_key TEXT NOT NULL,
        card_title TEXT NOT NULL,
        card_subtitle TEXT,
        content TEXT,
        note TEXT,
        display_order INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY(section_key) REFERENCES ctsv_sections(section_key) ON DELETE CASCADE
    );
    """)
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

def upsert_sections(conn):
    cur = conn.cursor()
    default_sections = [
        ('GTSI', 'GTS-I 手動測試 ', 'GTS-I', 10),
        ('CTSV', 'CTS Verifier 手動測試', 'CTS Verifier', 20),
        ('MADA', 'MADA Check List', 'MADA', 30),
    ]
    for key, title, tag, order in default_sections:
        cur.execute("SELECT 1 FROM ctsv_sections WHERE section_key = ?", (key,))
        if cur.fetchone():
            cur.execute("UPDATE ctsv_sections SET title=?, tag=?, display_order=? WHERE section_key=?",
                        (title, tag, order, key))
        else:
            cur.execute("INSERT INTO ctsv_sections (section_key, title, tag, display_order) VALUES (?, ?, ?, ?)",
                        (key, title, tag, order))
    conn.commit()

def clear_cards(conn):
    cur = conn.cursor()
    cur.execute("DELETE FROM card_images")
    cur.execute("DELETE FROM test_cards")
    conn.commit()

def insert_card(conn, card):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO test_cards (section_key, card_title, card_subtitle, content, note, display_order)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (card['section_key'], card['card_title'], card.get('card_subtitle'),
          card.get('content'), card.get('note'), card.get('display_order')))
    card_id = cur.lastrowid
    for idx, fname in enumerate(card.get('image_urls', [])):
        if not fname:
            continue
        cur.execute("INSERT INTO card_images (card_id, filename, display_order) VALUES (?, ?, ?)",
                    (card_id, fname, (idx + 1) * 10))
    conn.commit()
    return card_id

def main():
    print("使用資料庫：", DB_PATH)
    conn = get_conn()
    try:
        ensure_tables(conn)
        upsert_sections(conn)
        print("ctsv_sections 建立/更新完成。")

        print("清空現有 test_cards 與 card_images（避免重複匯入）...")
        clear_cards(conn)

        cards = []
        order = 10

        # （以下完全照你給的 HTML 內容填入）
        cards.append({
            "section_key": "GTSI",
            "card_title": "GtsInteractiveOverUsbTestCases",
            "card_subtitle": None,
            "content": "Step 1 . 在 /home/fih/XTS 位置下載指定版本的 GTS 包並複製到本機位置進行測試\nStep 2 . 在 terminal 執行 gts-tradefed ，按下 Enter，建立 Google tradefed 的環境\nStep 3 . 輸入 run gts-interactive。",
            "note": None,
            "image_urls": [],
            "display_order": order
        }); order += 10

        cards.append({
            "section_key": "GTSI",
            "card_title": "GtsInteractiveOverUsbTestCases - Usb Over Wifi (iPhone Hotspot)",
            "card_subtitle": None,
            "content": "Step 1 . 測試Usb Over Wifi 時，需使用iPhone Hotspot與DUT建立 Wi-Fi 連線。\nStep 2 . DUT 按下Setting -> Debugging  -> Wireless -> 顯示ip。\nStep 3 . 在Terminal 輸入 adb connect xxx.xxx.xxx.xxx:xxxx (ip位置)。\nStep 4 . 關閉電腦乙太網路。\nStep 5 . 拔掉 DUT 連接電腦的 cable ，並在 tradefed 輸入 ld 確認 iphone 提供的 ip 位置是online的\nStep 6 . 利用WiFi連線的adb進行後續步驟依照提示詞依序進行",
            "note": None,
            "image_urls": [],
            "display_order": order
        }); order += 10

        cards.append({
            "section_key": "GTSI",
            "card_title": "AndroidAutoOverUsbInteractiveHostTest",
            "card_subtitle": "Test item：只要測項名稱有顯示 OverUsb 就都要連上iphone hotspot，利用WiFi連線的adb進行測試",
            "content": "測試 Android Auto 時，待DUT前置WiFi步驟連線完成後，需接上車機進行測試。\n車機有額外提供獨立電源，請確認接線是否正確，另外背板有一Type-C孔，可跟DUT做連接。",
            "note": "建議紀錄：請注意DUT與車機是否有正常連線，畫面是否可正常投影至車機。",
            "image_urls": [],
            "display_order": order
        }); order += 10

        cards.append({
            "section_key": "GTSI",
            "card_title": "Madachecklist SetupWizard - QRCode / NFC Tag",
            "card_subtitle": None,
            "content": "Madachecklist SetupWizard 第 2 與第 3 張截圖需要使用下列工具：\n2. SetupWizard Qrcode：額外附在 \\\\10.57.41.153\\user$\\QA\\XTS\\GTSI\\QR Code\n3. Nfc Tag : 請確認為此張 Tag，避免測試錯誤。\n以上兩種方式皆用於 work provisioning 測試。",
            "note": "請確認 NFC Tag 與 QR Code 檔案位置正確。",
            "image_urls": ["GTSI/QR Code/QRCode_SetupWizard.png", "NFC_Tag.jpg"],
            "display_order": order
        }); order += 10

        cards.append({
            "section_key": "GTSI",
            "card_title": "GtsInteractiveMadachecklistTest (截圖參照 PDF)",
            "card_subtitle": None,
            "content": "Case9_2 測試條件要求 SetupWizard 介面「完全不連網路」直接進入主頁。\n該截圖請改成對應的圖片（請參照專案 static 檔案）。",
            "note": "測試時需確認：裝置從開機到 SetupWizard 全程未連上任何網路，且畫面內容需與截圖一致。",
            "image_urls": ["Case9_2.jpg", "GTSI/GTS_Interactive_Setupwizard_PART1_oldversion.pdf"],
            "display_order": order
        }); order += 10

        cards.append({
            "section_key": "GTSI",
            "card_title": "✯ TOT版本(Preview)",
            "card_subtitle": None,
            "content": "GTSI 也有提供TOT的版本，只是名稱不相同叫做「Preview」。\nPreview 版的GTS測試包也會附在 /home/fih/XTS/GTS 的資料夾內，資料夾名稱會特別標示。\n若已完全根據提示詞測試確認無法通過，則可使用Preview版本，進行驗證確認該項測試在DUT上為Fail。\n若依舊為Fail，則須將其測試過程及結果截圖，並回報給RD分析。",
            "note": None,
            "image_urls": [],
            "display_order": order
        }); order += 10

        # CTSV cards
        cards.append({
            "section_key": "CTSV",
            "card_title": "Audio Loopback Latency Test",
            "card_subtitle": None,
            "content": "第 2 個子項的 Analog 測試需要使用 3.5mm loopback dongle。\n需將已封起來的回收用 loopback dongle 接在耳機孔 做 loopback 測試。",
            "note": "測試時確認：請依圖片上的loopback dongle做測試，以免影響 Latency 結果。",
            "image_urls": ["LoopBack.jpg"],
            "display_order": order
        }); order += 10

        cards.append({
            "section_key": "CTSV",
            "card_title": "Voicemail Broadcast Test",
            "card_subtitle": None,
            "content": "台灣地區未支援 Voicemail 服務。\n需搭配 NowSMS Server 進行模擬測試。",
            "note": "由於先前同仁架設之伺服器已消失，需重新架設(須研究)。",
            "image_urls": ["CTSV/NowSMS.zip"],
            "display_order": order
        }); order += 10

        cards.append({
            "section_key": "CTSV",
            "card_title": "Java MIDI Test / Native MIDI Test",
            "card_subtitle": None,
            "content": "MIDI_BLE.apk 會在每一台實驗室電腦的 /home/fih/XTS/CTS/MIDI_BLE 中\n只需安裝並使用 1.11 版本即可，不需另外到 Google Play 下載最新版。",
            "note": "測試前確認：裝置已安裝 MIDI_BLE.apk。",
            "image_urls": [],
            "display_order": order
        }); order += 10

        cards.append({
            "section_key": "CTSV",
            "card_title": "Camera ITS 測項 (RFoV box / Reference tablet)",
            "card_subtitle": None,
            "content": "Step 1 . 開啟 Terminal 根據你的 Android 版本並 initialize 測試環境，輸入 source ITS.sh 版本 (例如: source ITS.sh 15)。\nStep 2 . 將測試環境拉到自己資料夾位置，用來 SetUp 及修改內部 Config。\nStep 3 . 輸入 source build/envsetup.sh。\nStep 4 . 輸入 adb -s <Serial ID> shell am compat enable ALLOW_TEST_API_ACCESS com.android.cts.verifier。\nStep 5 . 更改內部 Config (依實驗室設備、DUT Serial、Arduino、Light 等進行修改)。\nStep 6 . 執行 Python 檔案: python tools/run_all_tests.py camera=0 scenes=1 。",
            "note": "自動化測試，待全部測試完才會出結果；log 會存在 tmp 下（如有 fail，需提供 log 給 RD）。",
            "image_urls": ["Step1.jpg","CameraITS.jpg","CameraITS_Config.jpg","Step5.jpg","Step6.jpg"],
            "display_order": order
        }); order += 10

        cards.append({
            "section_key": "CTSV",
            "card_title": "ITS Test - Sensor Fusion（Test Pattern）",
            "card_subtitle": None,
            "content": "Sensor Fusion 需要使用上方有滾輪的箱子做測試，並需要額外準備 Test Pattern 紙張。\n若 Test Pattern 測試無法通過，請至 Google CTS Verifier 查詢官方範例圖片與說明。",
            "note": "如有 fail，需提供 log 給 RD。參考: https://source.android.com/docs/compatibility/cts/sensor-fusion-box-assembly",
            "image_urls": ["ITS_Fusionjpg"],
            "display_order": order
        }); order += 10

        cards.append({
            "section_key": "CTSV",
            "card_title": "ITS Test - CameraWebcamTest",
            "card_subtitle": None,
            "content": "Step 1 . initialize 測試環境，輸入 source ITS.sh 15 W。\nStep 2 . cd 到 CameraWebcamTest 目錄並修改 config。\nStep 3 . 執行測試: python run_webcam_test.py -c config.yml。",
            "note": None,
            "image_urls": ["Step 1.jpg","CameraWebcam.jpg","CameraWebcam_Config.jpg","Step 4.jpg"],
            "display_order": order
        }); order += 10

        cards.append({
            "section_key": "CTSV",
            "card_title": "MultiDeviceTest",
            "card_subtitle": None,
            "content": "Step 1 . 準備 PN532 NFC reader，並將 PN532 接上電腦 (檢查 /dev/ttyUSB* path)。\nStep 2 . DUT 需安裝 NfcEmulatorTestApp.apk (adb install -r -g NfcEmulatorTestApp.apk)。\nStep 3 . 打開 source ITS.sh 15，cd 到 MultiDevice 目錄，修改 config 中 DUT ID 及 pn532_serial_path。\nStep 4 . 執行測試: python3 tools/run_all_tests.py。",
            "note": "若本項單條測項錯誤，請使用 TOT 版本再跑一次；log 會存在 tmp 下。",
            "image_urls": ["PN532.jng","MultiDevice.jpg","MultiDeviceTest_Config.jpg"],
            "display_order": order
        }); order += 10

        # MADA
        cards.append({
            "section_key": "MADA",
            "card_title": "MADA - 文件與工具位置",
            "card_subtitle": None,
            "content": "最新版本的 MADA 都會放在: /home/fih/CHECKLIST_LATEST/GMS_Mada Compliance Form - (External sharing).docx。\n內部會需要用到的測試 apk 也都放在相同位置。",
            "note": "完成每個測項並附上照片後，請在最右側輸入 pass；若該 DUT 無該功能或不符版本，則註明原因並填上 N/A。",
            "image_urls": ["MADA附件.jpg","DUT_Detail.jpg","Step3.jpg"],
            "display_order": order
        }); order += 10

        cards.append({
            "section_key": "MADA",
            "card_title": "M63 - Android Auto discoverability",
            "card_subtitle": None,
            "content": "車機測項需由手機樣機進行測試，並錄影提供影片給 Google 查驗。\nGoogle 範例影片請參考: https://www.youtube.com/watch?v=FzBJqehq3As",
            "note": "於 MADA 上註明影片名稱及附上影片位置，並提供給 PM。",
            "image_urls": [],
            "display_order": order
        }); order += 10

        print("開始匯入卡片...")
        for c in cards:
            cid = insert_card(conn, c)
            print(f"Inserted card id={cid} title='{c['card_title']}' section={c['section_key']} images={len(c.get('image_urls',[]))}")

        print("匯入完成。請把靜態檔放到 static/ 對應路徑，以便前端顯示。")
        # 列印使用到的檔案
        used_files = []
        for c in cards:
            for f in c.get('image_urls', []):
                if f and f not in used_files:
                    used_files.append(f)
        if used_files:
            print("使用到的檔案（請確認 static/ 下有這些檔案）:")
            for f in used_files:
                print("  -", f)
        else:
            print("沒有外部檔案清單。")
    except Exception as e:
        print("匯入發生錯誤:", e)
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
