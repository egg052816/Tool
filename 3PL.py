# 3pl.py (最終版 - 簡化 Suite Key 邏輯)

from flask import Flask, render_template_string, render_template, request, jsonify
import sqlite3
import os

# ----------------------------------------
# 基本設定
# ----------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)

# 3PL Planning Google Sheet
gms_3pl_planning = "https://docs.google.com/sheets/d/1T-m_5qRCIr2nBdPUiF-u8_Ph0bX2KACsU5_UAC1oVKk/edit?gid=0#gid=0"


# ----------------------------------------
# DB Helper (保持不變)
# ----------------------------------------
def get_db_conn(db_name="waiver"):
    """
    取得 SQLite 連線，根據名稱返回不同的 DB 檔案連線。
    db_name 參數可以是 'waiver' 或 'retry'。
    """
    if db_name == "retry":
        db_path = os.path.join(BASE_DIR, "retry.db")
    else:
        # 默認為 waiver.db
        db_path = os.path.join(BASE_DIR, "waiver.db")

    conn = sqlite3.connect(db_path)
    # 設定 row_factory 以便通過欄位名稱存取數據 (例如 row['id'])
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化資料庫：建立 waivers.db 和 retry.db 中的所有表格。"""

    # 1. 初始化 waivers.db
    conn_waiver = get_db_conn("waiver")
    cursor_waiver = conn_waiver.cursor()
    cursor_waiver.execute(
        """
        CREATE TABLE IF NOT EXISTS waivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            suite TEXT NOT NULL, waiver_id TEXT NOT NULL, module TEXT NOT NULL, 
            test_case TEXT NOT NULL, note TEXT
        );
        """
    )
    conn_waiver.commit()
    conn_waiver.close()
    print("✅ waiver.db 初始化完成。")

    # 2. 初始化 retry.db (包含 retry_tips 和新的 suites 表格)
    conn_retry = get_db_conn("retry")
    cursor_retry = conn_retry.cursor()

    # 建立 retry_tips 表格 (儲存單行測項資料)
    cursor_retry.execute(
        """
        CREATE TABLE IF NOT EXISTS retry_tips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL, 
            module_case TEXT NOT NULL, 
            condition TEXT NOT NULL, 
            trick TEXT
        );
        """
    )

    # 建立 suites 表格 (儲存區塊標題資料，對應前端的大區塊)
    cursor_retry.execute(
        """
        CREATE TABLE IF NOT EXISTS suites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            suite_key TEXT UNIQUE NOT NULL,    /* 區塊的唯一標識，例如 'BASIC', 'GTS' */
            suite_title TEXT NOT NULL,         /* 區塊的顯示標題，例如 'Basic 測項' */
            suite_tag TEXT,                    /* 區塊的標籤，例如 'SIM / Host / Permission 類' */
            display_order INTEGER NOT NULL DEFAULT 0
        );
        """
    )

    # 檢查並插入預設的區塊（如果表格為空）
    cursor_retry.execute("SELECT COUNT(*) FROM suites")
    if cursor_retry.fetchone()[0] == 0:
        # 注意: suite_key 必須是英文/數字，所以這裡使用大寫英文
        default_suites = [
            ('BASIC', 'Basic 測項', 'SIM / Host / Permission 類', 10),
            ('GTS', 'GTS 測項', 'GTS', 20),
            ('CTS', 'CTS 測項', 'CTS', 30),
            ('SECURITYTOT', 'Security / TOT 測項', 'Security / TOT', 40),
            ('SPECIAL', '特殊情況 ', 'Special Cases / General', 50),
        ]
        cursor_retry.executemany(
            """
            INSERT INTO suites (suite_key, suite_title, suite_tag, display_order)
            VALUES (?, ?, ?, ?)
            """,
            default_suites
        )
        print("    [Suites] 插入預設區塊。")

    conn_retry.commit()
    conn_retry.close()
    print("✅ retry.db (包含 retry_tips & suites) 初始化完成。")


def create_db_if_not_exists():
    """確保兩個 DB 都存在且結構正確。"""
    init_db()


# ----------------------------------------
# 首頁 Template (保持不變)
# ----------------------------------------
TEMPLATE = r"""
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <title>測試流程工具頁</title>
    <link
      href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
      rel="stylesheet"
      integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH"
      crossorigin="anonymous"
    >
    <style>
        body {
            background-color: #0f172a; /* 深色底 */
            color: #e5e7eb;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }
        .container-main {
            max-width: 1100px;
            margin-top: 40px;
            margin-bottom: 40px;
        }
        .card {
            background: #020617;
            border-radius: 18px;
            border: 1px solid #1f2937;
            box-shadow: 0 22px 45px rgba(15,23,42,.8);
        }
        .nav-pills .nav-link {
            border-radius: 999px;
            color: #9ca3af;
        }
        .nav-pills .nav-link.active {
            background: linear-gradient(135deg, #22c55e, #0ea5e9);
            color: #0b1120;
            font-weight: 600;
        }
        .tab-pane {
            padding-top: 20px;
        }
        .tab-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: #9ca3af;
            margin-bottom: 10px;
        }
        .tab-subtitle {
            font-size: 0.95rem;
            color: #9ca3af;
            margin-bottom: 18px;
        }
        .code-block {
            background: #020617;
            border-radius: 12px;
            padding: 14px 16px;
            font-family: "JetBrains Mono", "Fira Code", monospace;
            font-size: 0.85rem;
            border: 1px solid #1f2937;
            color: #e5e7eb;
            white-space: pre-wrap;
        }
        a, a:hover {
            color: #22c55e;
        }
        .badge-tag {
            background-color: #1d283a;
            color: #9ca3af;
            border-radius: 999px;
            padding: 4px 10px;
            font-size: 0.75rem;
            margin-right: 4px;
        }

        .beauty-btn {
            padding: 6px 16px;
            background: transparent;
            color: #e5e7eb;
            border: 1px solid #22c1c3;
            border-radius: 999px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            margin-top: 16px;
            transition: background 0.18s ease,
                        color 0.18s ease,
                        box-shadow 0.18s ease,
                        transform 0.18s ease;
        }

        .beauty-btn:hover {
            background: rgba(34, 193, 195, 0.15);
            box-shadow: 0 0 0 1px rgba(34,193,195,0.4);
            transform: translateY(-1px);
        }

        .beauty-btn:active {
            transform: translateY(0);
            background: rgba(34, 193, 195, 0.25);
        }
    </style>
</head>
<body>
<div class="container container-main">
    <div class="card p-4 p-md-5">
        <div class="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-4">
            <div>
                <h1 class="h3 mb-1" style="color:#e5e7eb;">3PL Google XTS 測試流程</h1>
                <div style="color:#9ca3af; font-size:1.2rem;">
                    注意事項<br>
                    <a href="{{ planning_url }}" target="_blank" rel="noopener noreferrer">3PL Planning</a>
                </div>
            </div>
            <div class="mt-3 mt-md-0">
                <span class="badge-tag">Flash</span>
                <span class="badge-tag">CTS / GTS</span>
                <span class="badge-tag">Retry</span>
                <span class="badge-tag">Waiver</span>
            </div>
        </div>

        <ul class="nav nav-pills mb-3" id="main-tabs" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active"
                        id="flash-tab"
                        data-bs-toggle="pill"
                        data-bs-target="#flash"
                        type="button"
                        role="tab"
                        aria-controls="flash"
                        aria-selected="true">
                    Flash
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link"
                        id="sop-tab"
                        data-bs-toggle="pill"
                        data-bs-target="#sop"
                        type="button"
                        role="tab"
                        aria-controls="sop"
                        aria-selected="false">
                    SOP
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link"
                        id="ctsv-tab"
                        data-bs-toggle="pill"
                        data-bs-target="#ctsv"
                        type="button"
                        role="tab"
                        aria-controls="ctsv"
                        aria-selected="false">
                    CTSV / GTSI
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link"
                        id="retry-tab"
                        data-bs-toggle="pill"
                        data-bs-target="#retry"
                        type="button"
                        role="tab"
                        aria-controls="retry"
                        aria-selected="false">
                    Retry 方法
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link"
                        id="waiver-tab"
                        data-bs-toggle="pill"
                        data-bs-target="#waiver"
                        type="button"
                        role="tab"
                        aria-controls="waiver"
                        aria-selected="false">
                    Waiver
                </button>
            </li>
        </ul>

        <div class="tab-content" id="main-tabs-content">
            <div class="tab-pane fade show active" id="flash" role="tabpanel" aria-labelledby="flash-tab">
                <div class="tab-title">Flash 流程</div>
                <div class="tab-subtitle">
                    這裡之後可以整理你真正的 flash 指令、log 存放路徑、常見錯誤處理。現在先放一個簡單骨架。
                </div>
                <div class="code-block">
                    @echo off
                    REM 這裡可以放你現在習慣用的 flash batch / shell

                    fastboot devices
                    fastboot flashing unlock

                    REM TODO：之後你可以把實際專案用到的指令貼進來
                </div>

                <button class="beauty-btn" onclick="window.location.href='/flash_image'">
                    Flash Image 介紹
                </button>
            </div>

            <div class="tab-pane fade" id="sop" role="tabpanel" aria-labelledby="sop-tab">
                <div class="tab-title">SOP（標準作業流程）</div>
                <div class="tab-subtitle">
                    這一頁可以當作「人看得懂」的版本：步驟拆開、注意事項寫清楚，真正用來丟給新同事或 RD/PM 的。
                </div>
                <ul>
                    <li>Step 1：確認機種、Android 版本、build type（user / userdebug）。</li>
                    <li>Step 2：確認測試項目（CTS / GTS / STS / AACT / MADA...）。</li>
                    <li>Step 3：準備測試環境（網路、SIM、log 工具、CAN / DLT 等）。</li>
                    <li>Step 4：執行測試並紀錄 log 位置。</li>
                    <li>Step 5：整理結果、retry、判斷是否要提 waiver。</li>
                </ul>
                <div style="font-size:0.85rem; color:#9ca3af;">
                    之後你可以把這些條列換成你實際的 SOP，一條一條貼上去就好。
                </div>

                <button class="beauty-btn" onclick="window.location.href='/sop'">
                    測試 SOP
                </button>
            </div>

            <div class="tab-pane fade" id="ctsv" role="tabpanel" aria-labelledby="ctsv-tab">
                <div class="tab-title">CTSV / GTSI 區塊</div>
                <div class="tab-subtitle">
                    這裡可以放：subplan 命名規則、run / retry 指令、常用 exclude、log 存放位置說明。
                </div>
                <div class="code-block">
                    # CTS 例：跑特定 subplan
                    cts-tradefed run cts \
                      --subplan My_SubPlan \
                      --max-testcase-run-count 1

                    # GTSI / CTSV 例：retry
                    cts-tradefed run cts \
                      --retry 3 \
                      --subplan My_SubPlan

                    # TODO：你之後可以把你真正在用的 command 貼上來
                </div>

                <button class="beauty-btn" onclick="window.location.href='/ctsv_gtsi'">
                    手動測試
                </button>
            </div>

            <div class="tab-pane fade" id="retry" role="tabpanel" aria-labelledby="retry-tab">
                <div class="tab-title">Retry 方法</div>
                <div class="tab-subtitle">
                    這一頁可以整理：什麼情境用 retry，怎麼決定 retry 次數、怎麼記錄每次 retry 的差異。
                </div>
                <ul>
                    <li>Retry 條件：暫時性環境問題（network、server、lab 狀態不穩）。</li>
                    <li>不建議 retry 的情況：穩定重現的功能 bug、明顯的 device 行為異常。</li>
                    <li>建議紀錄：第幾次 run、環境差異、是否更換 device / port / cable。</li>
                </ul>
                <div class="code-block">
                    # 範例：只 retry previously failed tests
                    cts-tradefed run cts --retry 2

                    # 範例：針對指定模組 retry
                    cts-tradefed run cts --module CtsNetTestCases --retry 2
                </div>

                <button class="beauty-btn" onclick="window.location.href='/retry'">
                     Retry 方法
                </button>
            </div>

            <div class="tab-pane fade" id="waiver" role="tabpanel" aria-labelledby="waiver-tab">
                <div class="tab-title">Waiver 區塊</div>
                <div class="tab-subtitle">
                    會有一些測項無法通過，是因為被 Google 發現有問題或被關掉之後，Google 會額外提供 Waiver ID。<br>
                    要如何確定會有 Waiver：
                </div>
                <ol style="color:#9ca3af;">
                    <li>TOT 跑完測項顯示 0 次執行，結果也為 0。</li>
                    <li>在 Google IssueTracker 上查詢該 TestCase ID。</li>
                </ol>
                <div style="font-size:0.85rem; color:#9ca3af;">
                    如果後續有遇到其他的 Waiver 可以繼續新增，另外有些 TestCase 只有 Warning，無 bug id。
                </div>

                <button class="beauty-btn" onclick="window.location.href='/waiver'">
                     Waiver 管理頁面
                </button>
                <button class="beauty-btn" onclick="window.location.href='/save'">
                     save
                </button>
            </div>
        </div>
    </div>
</div>

<script
  src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"
  integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz"
  crossorigin="anonymous"
></script>
</body>
</html>
"""


# ----------------------------------------
# 一般頁面 Route
# ----------------------------------------
@app.route("/")
def index():
    # 這裡使用 render_template_string 返回單頁 Tab 結構
    return render_template_string(TEMPLATE, planning_url=gms_3pl_planning)


# 這裡的路由負責返回獨立的 HTML 檔案
@app.route("/flash_image")
def flash_image():
    return render_template("flash_image.html")


@app.route("/sop")
def sop():
    return render_template("sop.html")


@app.route("/retry")
def retry():
    return render_template("retry.html")


@app.route("/waiver")
def waiver():
    return render_template("waiver.html")


@app.route("/ctsv_gtsi")
def ctsv_gtsi():
    return render_template("ctsv_gtsi.html")


@app.route("/save")
def save():
    return render_template("save.html")


# ----------------------------------------
# Waiver API (連接 waiver.db)
# ----------------------------------------

@app.route("/api/waiver/list/<suite>")
def list_waivers(suite):
    """列出某個 suite 的所有 waiver"""
    conn = get_db_conn("waiver")
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, suite, waiver_id, module, test_case, note
        FROM waivers
        WHERE suite = ?
        ORDER BY id
        """,
        (suite.upper(),),
    )
    rows = cur.fetchall()
    conn.close()

    data = [
        {
            "id": r["id"],
            "suite": r["suite"],
            "waiver_id": r["waiver_id"],
            "module": r["module"],
            "test_case": r["test_case"],
            "note": r["note"],
        }
        for r in rows
    ]
    return jsonify(data)


@app.route("/api/waiver/add", methods=["POST"])
def add_waiver():
    """新增一筆 waiver"""
    data = request.json or {}
    required_fields = ["suite", "waiver_id", "module", "test_case"]
    if not all(data.get(k) is not None for k in required_fields):
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    conn = get_db_conn("waiver")
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO waivers (suite, waiver_id, module, test_case, note)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            data.get("suite").upper(),
            data.get("waiver_id"),
            data.get("module"),
            data.get("test_case"),
            data.get("note"),
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()

    return jsonify({"status": "ok", "id": new_id})


@app.route("/api/waiver/update/<int:waiver_id>", methods=["PUT", "POST"])
def update_waiver(waiver_id):
    """更新一筆 waiver"""
    data = request.json or {}
    required_fields = ["suite", "waiver_id", "module", "test_case"]
    if not all(data.get(k) is not None for k in required_fields):
        return jsonify({"status": "error", "message": "Missing required fields for update"}), 400

    conn = get_db_conn("waiver")
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE waivers
        SET suite = ?, waiver_id = ?, module = ?, test_case = ?, note = ?
        WHERE id = ?
        """,
        (
            data.get("suite").upper(),
            data.get("waiver_id"),
            data.get("module"),
            data.get("test_case"),
            data.get("note"),
            waiver_id,
        ),
    )
    conn.commit()
    affected = cur.rowcount
    conn.close()

    if affected == 0:
        return jsonify({"status": "error", "message": "waiver not found"}), 404

    return jsonify({"status": "ok"})


@app.route("/api/waiver/delete/<int:waiver_id>", methods=["DELETE", "POST"])
def delete_waiver(waiver_id):
    """刪除一筆 waiver"""
    conn = get_db_conn("waiver")
    cur = conn.cursor()
    cur.execute("DELETE FROM waivers WHERE id = ?", (waiver_id,))
    conn.commit()
    affected = cur.rowcount
    conn.close()

    if affected == 0:
        return jsonify({"status": "error", "message": "waiver not found"}), 404

    return jsonify({"status": "ok"})


# ----------------------------------------
# Retry API (連接 retry.db)
# ----------------------------------------

@app.route("/api/retry/list")
def list_retry_tips():
    """列出所有 retry tips"""
    conn = get_db_conn("retry")
    cur = conn.cursor()
    cur.execute("SELECT id, type, module_case, condition, trick FROM retry_tips ORDER BY id")
    rows = cur.fetchall()
    conn.close()

    # 將 sqlite3.Row 物件轉換為字典列表
    data = [{k: r[k] for k in r.keys()} for r in rows]
    return jsonify(data)


@app.route("/api/retry/add", methods=["POST"])
def add_retry_tip():
    """新增一筆 retry tip"""
    data = request.json or {}
    required_fields = ["type", "module_case", "condition"]
    if not all(data.get(k) is not None for k in required_fields):
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    conn = get_db_conn("retry")
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO retry_tips (type, module_case, condition, trick)
        VALUES (?, ?, ?, ?)
        """,
        (
            data.get("type"),
            data.get("module_case"),
            data.get("condition"),
            data.get("trick"),
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()

    return jsonify({"status": "ok", "id": new_id})


@app.route("/api/retry/update/<int:tip_id>", methods=["PUT", "POST"])
def update_retry_tip(tip_id):
    """更新一筆 retry tip"""
    data = request.json or {}
    required_fields = ["type", "module_case", "condition"]
    if not all(data.get(k) is not None for k in required_fields):
        return jsonify({"status": "error", "message": "Missing required fields for update"}), 400

    conn = get_db_conn("retry")
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE retry_tips
        SET type = ?, module_case = ?, condition = ?, trick = ?
        WHERE id = ?
        """,
        (
            data.get("type"),
            data.get("module_case"),
            data.get("condition"),
            data.get("trick"),
            tip_id,
        ),
    )
    conn.commit()
    affected = cur.rowcount
    conn.close()

    if affected == 0:
        return jsonify({"status": "error", "message": "Tip not found"}), 404

    return jsonify({"status": "ok"})


@app.route("/api/retry/delete/<int:tip_id>", methods=["DELETE", "POST"])
def delete_retry_tip(tip_id):
    """刪除一筆 retry tip"""
    conn = get_db_conn("retry")
    cur = conn.cursor()
    cur.execute("DELETE FROM retry_tips WHERE id = ?", (tip_id,))
    conn.commit()
    affected = cur.rowcount
    conn.close()

    if affected == 0:
        return jsonify({"status": "error", "message": "Tip not found"}), 404

    return jsonify({"status": "ok"})


# ----------------------------------------
# Suite API (新增 - 取得和新增/刪除區塊功能)
# ----------------------------------------

@app.route("/api/suites/list")
def list_suites():
    """列出所有區塊標題 (例如 Basic, GTS, CTS)"""
    conn = get_db_conn("retry")
    cur = conn.cursor()
    cur.execute("SELECT suite_key, suite_title, suite_tag, display_order FROM suites ORDER BY display_order")
    rows = cur.fetchall()
    conn.close()

    data = [{k: r[k] for k in r.keys()} for r in rows]
    return jsonify(data)


@app.route("/api/suites/add", methods=["POST"])
def add_suite():
    """新增一個區塊標題 (對應「新增區塊」按鈕)"""
    data = request.json or {}

    # 🌟 修正點 1: 僅檢查 suite_title 是否必填 🌟
    required_fields = ["suite_title"]
    if not all(data.get(k) for k in required_fields):
        return jsonify({"status": "error", "message": "Missing required field: suite_title"}), 400

    suite_title = data['suite_title'].strip()
    suite_tag = data.get('suite_tag', '').strip()

    # 🌟 修正點 2: 自動生成 suite_key 的邏輯 🌟
    # 規則: 若 suite_tag 有值，用 suite_tag，否則用 suite_title。
    # 為了確保 suite_key 是唯一且適合資料庫使用，我們移除特殊符號並轉大寫。

    source_key = suite_tag if suite_tag else suite_title

    # 簡單的清理函數: 移除空格和特殊符號
    def sanitize_key(text):
        if not text:
            return ""
        # 只保留字母、數字、底線，並將空格替換為底線
        key = ''.join(c if c.isalnum() else '_' for c in text)
        # 移除重複的底線，並轉大寫
        return '_'.join(filter(None, key.split('_'))).upper()

    suite_key = sanitize_key(source_key)

    if not suite_key:
        # 如果標題和標籤都是空字符串，則無法生成 Key
        return jsonify({"status": "error", "message": "Cannot generate a unique key from title or tag."}), 400

    conn = get_db_conn("retry")
    cur = conn.cursor()

    # 檢查是否已存在
    cur.execute("SELECT 1 FROM suites WHERE suite_key = ?", (suite_key,))
    if cur.fetchone():
        conn.close()
        # 409 Conflict: Key 衝突，可能是用戶輸入相同標籤或標題
        return jsonify({"status": "error",
                        "message": f"Suite key '{suite_key}' already exists. Please use a unique title or tag."}), 409

    # 計算最大的 display_order，並加 10
    cur.execute("SELECT MAX(display_order) FROM suites")
    max_order = cur.fetchone()[0] or 0
    new_order = max_order + 10

    cur.execute(
        """
        INSERT INTO suites (suite_key, suite_title, suite_tag, display_order)
        VALUES (?, ?, ?, ?)
        """,
        (
            suite_key,
            suite_title,
            suite_tag,
            new_order
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()

    return jsonify({"status": "ok", "id": new_id, "suite_key": suite_key})


@app.route("/api/suites/delete/<suite_key>", methods=["DELETE"])
def delete_suite(suite_key):
    """刪除一個區塊標題及其所有相關的 retry tips"""
    suite_key = suite_key.upper()

    conn = get_db_conn("retry")
    cur = conn.cursor()

    try:
        # 1. 刪除該區塊下的所有測項 (從 retry_tips 表格)
        cur.execute("DELETE FROM retry_tips WHERE type = ?", (suite_key,))
        tips_affected = cur.rowcount

        # 2. 刪除區塊標題本身 (從 suites 表格)
        cur.execute("DELETE FROM suites WHERE suite_key = ?", (suite_key,))
        suites_affected = cur.rowcount

        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500

    conn.close()

    if suites_affected == 0:
        return jsonify({"status": "error", "message": f"Suite key '{suite_key}' not found."}), 404

    return jsonify({
        "status": "ok",
        "message": f"Suite '{suite_key}' and {tips_affected} related tips deleted successfully."
    })


# ----------------------------------------
# Suite API (新增排序功能)
# ----------------------------------------

# ... (list_suites, add_suite, delete_suite 等函數保持不變) ...

@app.route("/api/suites/reorder", methods=["PUT"])
def reorder_suites():
    """接收前端傳來的排序列表，更新 suites 表格的 display_order"""
    data = request.json or []
    if not isinstance(data, list) or not data:
        return jsonify({"status": "error", "message": "Invalid or empty reorder list"}), 400

    conn = get_db_conn("retry")
    cur = conn.cursor()

    try:
        # 遍歷接收到的列表，列表中的順序就是新的 display_order
        for index, suite_key in enumerate(data):
            # 新的 order 值可以基於 index，確保間距以防未來需要插入
            new_order = (index + 1) * 10

            cur.execute(
                """
                UPDATE suites
                SET display_order = ?
                WHERE suite_key = ?
                """,
                (new_order, suite_key.upper()),
            )

        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"status": "error", "message": f"Database error during reorder: {str(e)}"}), 500

    conn.close()
    return jsonify({"status": "ok", "message": "Suites reordered successfully"}), 200


# ---------- quick debug routes (保持不變) ----------
@app.route("/ping")
def ping():
    return "pong", 200


# ----------------------------------------
# main
# ----------------------------------------
if __name__ == "__main__":
    # 確保 DB 存在
    create_db_if_not_exists()

    # 啟動 Flask
    app.run(debug=True)