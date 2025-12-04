import sqlite3
import os

# ----------------------------------------
# 設定 DB 路徑 - 🌟 保持 retry.db 🌟
# ----------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "retry.db")  # 🎯 正確使用 retry.db

# ----------------------------------------
# 靜態 Retry 技巧數據 (補回數據內容)
# ----------------------------------------
RETRY_DATA = [
    # --- 1. Basic ---
    {"type": "Basic", "module_case": "Radio", "condition": "實體 SIM", "trick": "使用真實SIM卡重測"},
    {"type": "Basic", "module_case": "Adoptable Host", "condition": "SD 卡", "trick": "確保SD卡格式正確"},
    {"type": "Basic", "module_case": "CarrierApiTestCases", "condition": "Test SIM", "trick": "確認 SIM 卡狀態"},
    {"type": "Basic", "module_case": "Libcore", "condition": "IPv4 測項",
     "trick": "建議連 FIH-Free / 內網等穩定 IPv4 網路"},
    {"type": "Basic", "module_case": "CtsPermission", "condition": "實體 SIM", "trick": "確認權限授予狀態"},
    {"type": "Basic", "module_case": "VCN", "condition": "實體 SIM", "trick": "檢查 VCN 服務狀態"},
    {"type": "Basic", "module_case": "MbaPrivilegedPermission", "condition": "Factory Reset",
     "trick": "重置後再跑一次測項"},
    {"type": "Basic", "module_case": "Dialeraudio", "condition": "實體 SIM", "trick": "記得開 LTE / 4G"},
    {"type": "Basic", "module_case": "SimAppDialog", "condition": "Test SIM", "trick": "確保 SIM App 正常"},

    # --- 2. GTS 測項 ---
    {"type": "GTS", "module_case": "GtsGmscoreHostTestCases", "condition": "audioservice / Camera 相關",
     "trick": "測 audioservice 時外接麥克風。若為 Camera 相關測項，記得外接 Camera。"},
    {"type": "GTS", "module_case": "GtsPermissionTestCases", "condition": "SecurityPath ＋ CtsScopedStorageHostTest",
     "trick": "兩者會互相干擾，遇到兩邊都 fail 時，建議使用：`--exclude-filter CtsScopedStorageHostTest` 重跑一次 GtsPermission。"},
    {"type": "GTS", "module_case": "GtsBackupTestCases", "condition": "Factory Reset 後，在 SetupWizard 不連網",
     "trick": "Factory Reset 後在開機設定精靈中不要連網，直接進系統，再 Retry 一次，不讓 Device 自動下載套件，通常就會 PASS。"},

    # --- 3. CTS 測項 ---
    {"type": "CTS", "module_case": "signed-CtsSecureElementAccessControlTestCases1~3 / signed-CtsOmapiTestCases",
     "condition": "Test SIM（RD 有貼 Google 標籤的那兩張）",
     "trick": "所有 Secure Element / OMAPI 系列建議統一用 Test SIM 來測。"},
    {"type": "CTS", "module_case": "CtsNetTestCases", "condition": "DNS 相關測項",
     "trick": "只要跟 DNS 相關，讓 Device 連自己手機的 Hotspot 通常就會 PASS。"},
    {"type": "CTS", "module_case": "CtsNetworkStackHostTestCases",
     "condition": "連上 FIH-Free，Network usage 設為 metered",
     "trick": "測前確認目前連線為 FIH-Free，並將該網路標記為「計量（metered）」。"},
    {"type": "CTS",
     "module_case": "CtsAutoFillServiceTestCases / testDatasetAuthResponseWhileAutofilledAppIsLifecycled",
     "condition": "Device owner 設定", "trick": "需要把裝置中的 owner 刪乾淨，只保留一個主要 owner 再跑測項。"},
    {"type": "CTS", "module_case": "arm64-v8a CtsWindowManagerDeviceTestCases PinnedStackTests (兩個測項)",
     "condition": "使用 TOT build",
     "trick": "適用於 testTranslucentActivityOnTopOfPinnedTask 和 testAutoEnterPictureInPictureOverPip 兩個測項。"},

    # --- 4. Android 10 CTS (Security / TOT 系列) ---
    {"type": "SecurityTOT",
     "module_case": "憑證系列 (CtsLibcoreOjTestCases, CtsLibcoreTestCases, CtsSecurityTestCases)",
     "condition": "憑證系列（用 TOT）",
     "trick": "憑證相關 Security 測項建議統一使用 TOT build，避免客製憑證 / Mainline 版本影響。"},
    {"type": "SecurityTOT", "module_case": "CtsOsHostTestCases", "condition": "Factory Reset 後不要連 Wi-Fi",
     "trick": "重置後直接進系統，不連 Wi-Fi，再 Retry 測項。"},

    # --- 5. 特殊情況 / 通用提醒 (Special Cases / General) ---
    {"type": "Special", "module_case": "Getac 系列", "condition": "Perform Setting",
     "trick": "需開啟 Perform Setting，否則部分 Camera 測項會無法通過。"},
    {"type": "Special", "module_case": "Getac 系列", "condition": "首次測試需插 Docker",
     "trick": "首次測試需要透過 Docker，否則可能發生 Port 掉線問題。"},
    {"type": "Special", "module_case": "PhotoPicker 測項", "condition": "登入 Google 帳號並升級 Mainline",
     "trick": "更新 Mainline 後再進行測試。"},
    {"type": "Special", "module_case": "Battery 測項 (Getac)", "condition": "拔電池並插 Docker",
     "trick": "符合 Getac 需求的測試流程。"},
    {"type": "Special", "module_case": "Getac GSI GPS 測項", "condition": "貼有 VTS 貼紙的 Device",
     "trick": "部分板子可能 GPS 不穩，可更換另一台測試以提高 PASS 率。"},
    {"type": "Special", "module_case": "DeviceInfo json 缺少欄位 (ATS)", "condition": "ATS 測試後",
     "trick": "1. 把 full test 的 zip 解壓縮。 2. 用 terminal 建立 subplan，再 retry。 3. 記得把 MCTS 關掉（Dynamic）再重跑。"},
]


def import_retry_data():
    """
    連接資料庫並批量匯入 Retry 技巧資料到 'retry_tips' 表格。
    """
    if not os.path.exists(DB_PATH):
        print(f"⚠️ 警告：找不到資料庫檔案 {DB_PATH}。請先運行 3pl.py 確保 DB 初始化。")
        return

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # 1. 確保 retry_tips 表格存在 (這是關鍵!)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS retry_tips (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,           -- 測試類型 (Basic, GTS, CTS, Special)
                    module_case TEXT NOT NULL,    -- 模組 / 測項
                    condition TEXT NOT NULL,      -- 條件 / 環境
                    trick TEXT                    -- 備註 / Retry 方法
                );
                """
            )
            conn.commit()
            print(f"✅ 資料庫 {DB_PATH} 和 'retry_tips' 表格結構已確認/建立。")

            # 2. 清空舊數據，以便重新導入
            cursor.execute("DELETE FROM retry_tips")

            # 3. 準備 SQL 語句
            sql = """
            INSERT INTO retry_tips (type, module_case, condition, trick)
            VALUES (?, ?, ?, ?)
            """

            # 4. 準備要匯入的資料 (將空字串替換為 None)
            data_to_insert = [
                (
                    d["type"],
                    d["module_case"],
                    d["condition"],
                    d["trick"] if d["trick"] else None
                )
                for d in RETRY_DATA
            ]

            # 5. 批量執行插入操作
            cursor.executemany(sql, data_to_insert)

            # 6. 提交事務
            conn.commit()

            print(f"✅ 成功匯入 {cursor.rowcount} 筆 Retry 技巧紀錄到 {DB_PATH} 的 'retry_tips' 表格中。")

    except sqlite3.Error as e:
        print(f"❌ 資料庫操作失敗: {e}")


if __name__ == "__main__":
    import_retry_data()