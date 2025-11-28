from flask import Flask, render_template_string, render_template, request, jsonify
import sqlite3
import os

# ----------------------------------------
# 基本設定
# ----------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "waiver.db")  # 確保 DB 路徑正確

app = Flask(__name__)

# 3PL Planning Google Sheet
gms_3pl_planning = "https://docs.google.com/spreadsheets/d/1T-m_5qRCIr2nBdPUiF-u8_Ph0bX2KACsU5_UAC1oVKk/edit?gid=0#gid=0"


# ----------------------------------------
# DB Helper (使用無 ABI 欄位的最新版本)
# ----------------------------------------
def get_db():
    """取得 SQLite 連線，記得會用 row_factory 讓 row 可以用欄位名稱取值。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化資料庫：建立 waivers 資料表 (使用無 ABI 欄位版本)。"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS waivers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            suite TEXT NOT NULL,          -- 測試套件名稱 (CTS, GTS, STS...)
            waiver_id TEXT NOT NULL,      -- Google Issue Tracker ID
            module TEXT NOT NULL,         -- 測試模組名稱
            test_case TEXT NOT NULL,      -- 測試案例名稱
            note TEXT
        );
        """
    )
    conn.commit()
    conn.close()
    print(f"✅ SQLite DB 初始化完成或已檢查：{DB_PATH}")


def create_db_if_not_exists():
    """確保 DB 存在且結構正確。"""
    init_db()


# ----------------------------------------
# 首頁 Template（恢復您的原始單頁 Tab 結構）
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


# ----------------------------------------
# Waiver API (必須在 app.py 內才能被前端呼叫)
# ----------------------------------------

@app.route("/api/waiver/list/<suite>")
def list_waivers(suite):
    """列出某個 suite 的所有 waiver"""
    conn = get_db()
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

    conn = get_db()
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

    conn = get_db()
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
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM waivers WHERE id = ?", (waiver_id,))
    conn.commit()
    affected = cur.rowcount
    conn.close()

    if affected == 0:
        return jsonify({"status": "error", "message": "waiver not found"}), 404

    return jsonify({"status": "ok"})


# ----------------------------------------
# main
# ----------------------------------------
if __name__ == "__main__":
    # 確保 DB 存在
    create_db_if_not_exists()

    # 啟動 Flask
    app.run(debug=True)