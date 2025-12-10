from flask import Flask, render_template_string, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import sqlite3
import os

# ----------------------------------------
# 基本設定
# ----------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)

# 3PL Planning Google Sheet
gms_3pl_planning = "https://docs.google.com/spreadsheets/d/1T-m_5qRCIr2nBdPUiF-u8_Ph0bX2KACsU5_UAC1oVKk/edit?gid=0#gid=0"

# 檔案上傳設定
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'zip', 'docx', 'xlsx', 'mp4'}

app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ----------------------------------------
# DB Helper
# ----------------------------------------
def get_db_conn(db_name="waiver"):
    if db_name == "retry":
        db_path = os.path.join(BASE_DIR, "retry.db")
    elif db_name == "ctsv_gtsi":
        db_path = os.path.join(BASE_DIR, "ctsv_gtsi.db")
    else:
        db_path = os.path.join(BASE_DIR, "waiver.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化所有資料庫"""
    # 1. waivers.db
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

    # 2. retry.db
    conn_retry = get_db_conn("retry")
    cursor_retry = conn_retry.cursor()
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
    cursor_retry.execute(
        """
        CREATE TABLE IF NOT EXISTS suites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            suite_key TEXT UNIQUE NOT NULL,    
            suite_title TEXT NOT NULL,         
            suite_tag TEXT,                    
            display_order INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    # 預設區塊
    cursor_retry.execute("SELECT COUNT(*) FROM suites")
    if cursor_retry.fetchone()[0] == 0:
        default_suites = [
            ('BASIC', 'Basic 測項', 'SIM / Host / Permission 類', 10),
            ('GTS', 'GTS 測項', 'GTS', 20),
            ('CTS', 'CTS 測項', 'CTS', 30),
            ('SECURITYTOT', 'Security / TOT 測項', 'Security / TOT', 40),
            ('SPECIAL', '特殊情況 ', 'Special Cases / General', 50),
        ]
        cursor_retry.executemany(
            "INSERT INTO suites (suite_key, suite_title, suite_tag, display_order) VALUES (?, ?, ?, ?)",
            default_suites
        )
    conn_retry.commit()
    conn_retry.close()

    # 3. ctsv_gtsi.db
    conn_ctsv = get_db_conn("ctsv_gtsi")
    cursor_ctsv = conn_ctsv.cursor()
    cursor_ctsv.execute(
        """
        CREATE TABLE IF NOT EXISTS ctsv_sections (
            section_key TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            tag TEXT,
            display_order INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    cursor_ctsv.execute(
        """
        CREATE TABLE IF NOT EXISTS test_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_key TEXT NOT NULL,
            card_title TEXT NOT NULL,
            card_subtitle TEXT,
            content TEXT,
            image_url TEXT,
            note TEXT,
            display_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(section_key) REFERENCES ctsv_sections(section_key) ON DELETE CASCADE
        );
        """
    )
    cursor_ctsv.execute(
        """
        CREATE TABLE IF NOT EXISTS card_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            display_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(card_id) REFERENCES test_cards(id) ON DELETE CASCADE
        );
        """
    )
    # 預設區塊
    cursor_ctsv.execute("SELECT COUNT(*) FROM ctsv_sections")
    if cursor_ctsv.fetchone()[0] == 0:
        default_sections = [
            ('GTSI', 'GTS Interactive 區塊', 'Android 13+ / MADA', 10),
            ('CTSV', 'CTS Verifier 區塊', 'CameraITS / Audio / Sensor', 20),
            ('MADA', 'MADA Check List 區塊', 'Auto discoverability / Doc', 30),
        ]
        cursor_ctsv.executemany(
            "INSERT INTO ctsv_sections (section_key, title, tag, display_order) VALUES (?, ?, ?, ?)",
            default_sections
        )
    conn_ctsv.commit()
    conn_ctsv.close()
    print("✅ 資料庫初始化完成。")


def create_db_if_not_exists():
    init_db()


# ----------------------------------------
# 首頁 Template (字體顏色已修正為亮白)
# ----------------------------------------
TEMPLATE = r"""
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <title>3PL Google XTS 測試流程</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link
      href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
      rel="stylesheet"
    >
    <style>
        /* --- 強制深色主題設定 --- */
        body {
            background: radial-gradient(circle at top left, #172554, #0f172a, #020617) !important;
            background-attachment: fixed !important;
            color: #f1f5f9 !important; /* 強制全域文字亮白 */
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            min-height: 100vh;
        }

        .container-main {
            max-width: 1200px;
            margin-top: 60px;
            margin-bottom: 60px;
        }

        /* --- 卡片修正 --- */
        .card {
            background: rgba(30, 41, 59, 0.7) !important;
            backdrop-filter: blur(20px); 
            -webkit-backdrop-filter: blur(20px);
            border-radius: 24px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.6);
            color: #f1f5f9 !important;
        }

        /* --- 標題 --- */
        h1.h3 {
            font-weight: 800;
            background: linear-gradient(to right, #60a5fa, #22d3ee);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }

        .sub-link a {
            color: #38bdf8 !important;
            text-decoration: none;
            border-bottom: 1px dashed rgba(56, 189, 248, 0.5);
            transition: all 0.3s;
        }
        .sub-link a:hover {
            color: #bae6fd !important;
            border-bottom-color: #bae6fd;
        }

        /* --- 頂部標籤 --- */
        .badge-tag {
            background: rgba(56, 189, 248, 0.15); 
            color: #7dd3fc !important;
            border: 1px solid rgba(56, 189, 248, 0.2);
            padding: 6px 14px;
            border-radius: 100px;
            font-size: 0.8rem;
            font-weight: 500;
            margin-left: 8px;
        }

        /* --- 導航頁籤 --- */
        .nav-pills {
            background: rgba(0, 0, 0, 0.3);
            padding: 6px;
            border-radius: 16px;
            display: inline-flex;
            margin-bottom: 30px;
            border: 1px solid rgba(255,255,255,0.05);
        }
        .nav-pills .nav-link {
            border-radius: 12px;
            color: #94a3b8 !important;
            font-weight: 500;
            padding: 10px 24px;
            transition: all 0.2s ease;
        }
        .nav-pills .nav-link:hover {
            color: #fff !important;
            background: rgba(255, 255, 255, 0.08);
        }
        .nav-pills .nav-link.active {
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
            color: #ffffff !important;
            font-weight: 700;
            box-shadow: 0 4px 15px rgba(37, 99, 235, 0.5);
        }

        /* --- Tab 內容 --- */
        .tab-title {
            font-size: 1.6rem;
            font-weight: 700;
            color: #fff !important;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
        }
        .tab-title::before {
            content: '';
            display: inline-block;
            width: 6px;
            height: 28px;
            background: #38bdf8;
            border-radius: 4px;
            margin-right: 14px;
            box-shadow: 0 0 15px rgba(56, 189, 248, 0.6);
        }
        .tab-subtitle {
            font-size: 1.05rem;
            color: #cbd5e1 !important;
            margin-bottom: 30px;
            line-height: 1.6;
            padding-left: 20px;
        }

        /* --- 連結與按鈕 --- */
        .beauty-btn {
            position: relative;
            background: rgba(56, 189, 248, 0.1);
            color: #38bdf8 !important;
            padding: 12px 28px;
            border-radius: 12px;
            font-weight: 600;
            font-size: 0.95rem;
            border: 1px solid rgba(56, 189, 248, 0.3);
            overflow: hidden;
            transition: all 0.3s;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
        }
        .beauty-btn:hover {
            background: rgba(56, 189, 248, 0.2);
            transform: translateY(-2px);
            box-shadow: 0 0 20px rgba(56, 189, 248, 0.2);
            color: #fff !important;
            border-color: #7dd3fc;
        }

        img {
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.15);
            max-width: 100%;
            margin-top: 10px;
        }

        a.doc-link {
            display: flex;
            align-items: center;
            margin-bottom: 12px;
            color: #bae6fd !important;
            text-decoration: none;
            font-weight: 500;
            padding: 12px 16px;
            background: rgba(15, 23, 42, 0.6);
            border-radius: 12px;
            transition: all 0.2s;
            border: 1px solid rgba(56, 189, 248, 0.1);
        }
        a.doc-link:hover {
            background: rgba(56, 189, 248, 0.15);
            color: #fff !important;
            border-color: rgba(56, 189, 248, 0.4);
            transform: translateX(4px);
        }

        /* --- 表格樣式 (修復字體顏色) --- */
        .table-container {
            border-radius: 16px;
            overflow: hidden;
            background: transparent;
            margin: 20px 0;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        .flash-flow-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-size: 1rem;
            color: #f1f5f9 !important;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            overflow: hidden;
        }

        .flash-flow-table th {
            background: rgba(15, 23, 42, 0.95) !important;
            color: #38bdf8 !important;
            font-weight: 700;
            padding: 20px 24px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 2px solid rgba(56, 189, 248, 0.3);
        }

        .flash-flow-table td {
            background: rgba(30, 41, 59, 0.4);
            padding: 20px 24px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            vertical-align: top;
            color: #e2e8f0 !important;
            line-height: 1.6;
        }

        /* 強調文字 */
        .flash-flow-table strong {
            color: #fff !important;
            font-weight: 700;
            font-size: 1.05rem;
            display: block;
            margin-bottom: 6px;
        }

        .flash-flow-table tbody tr:hover td {
            background: rgba(56, 189, 248, 0.05) !important;
        }

        /* --- Badges --- */
        .flash-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 0.75rem;
            font-weight: 800;
            margin: 4px 6px 4px 0;
            letter-spacing: 0.5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            color: #0f172a !important; /* 文字統一深色 */
            text-transform: uppercase;
        }

        .flash-badge-cts { background: #fbbf24 !important; }
        .flash-badge-gts { background: #2dd4bf !important; }
        .flash-badge-sts { background: #fb923c !important; }
        .flash-badge-vts { background: #60a5fa !important; }

        .flash-flow-table td:last-child {
            color: #cbd5e1 !important;
            font-size: 0.95rem;
        }

        /* --- 文件卡片 --- */
        .doc-card {
            background: rgba(15, 23, 42, 0.6);
            padding: 24px;
            border-radius: 16px;
            border: 1px solid rgba(255,255,255,0.08);
            margin-bottom: 20px;
        }
        .doc-list li { 
            margin-bottom: 12px; 
            color: #e2e8f0 !important; 
        }
        .doc-list strong { 
            color: #7dd3fc !important; 
            margin-right: 8px;
        }

    </style>
</head>
<body>
<div class="container container-main">
    <div class="card p-4 p-md-5">
        <div class="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-5">
            <div>
                <h1 class="h3">3PL Google XTS 測試流程</h1>
                <div class="sub-link">
                    進度追蹤表: 
                    <a href="{{ planning_url }}" target="_blank" rel="noopener noreferrer">3PL Planning Sheet ↗</a>
                </div>
            </div>
            <div class="mt-3 mt-md-0 d-flex align-items-center">
                <span class="badge-tag">Flash</span>
                <span class="badge-tag">SOP</span>
                <span class="badge-tag">CTS / GTS</span>
                <span class="badge-tag">Retry</span>
                <span class="badge-tag">Waiver</span>
            </div>
        </div>

        <ul class="nav nav-pills" id="main-tabs" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="flash-tab" data-bs-toggle="pill" data-bs-target="#flash" type="button" role="tab">Flash</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="sop-tab" data-bs-toggle="pill" data-bs-target="#sop" type="button" role="tab">SOP</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="ctsv-tab" data-bs-toggle="pill" data-bs-target="#ctsv" type="button" role="tab">CTSV / GTSI</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="retry-tab" data-bs-toggle="pill" data-bs-target="#retry" type="button" role="tab">Retry 方法</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="waiver-tab" data-bs-toggle="pill" data-bs-target="#waiver" type="button" role="tab">Waiver</button>
            </li>
        </ul>

        <div class="tab-content" id="main-tabs-content">
            <div class="tab-pane fade show active" id="flash" role="tabpanel">
                <div class="tab-title">Flash 流程</div>
                <div class="tab-subtitle">
                    解釋各式測項需測試的 Test Coverage、Android 版本不同的燒錄版本，及 Driver 驅動的安裝。
                </div>

                <div class="table-container">
                  <table class="flash-flow-table">
                    <thead>
                      <tr>
                        <th width="20%"> SW </th>
                        <th width="30%"> 燒錄組合 </th>
                        <th width="25%"> 對應測試項目 </th>
                        <th> 備註 </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td rowspan="3"><strong>User Build SW</strong></td>
                        <td>User Build SW </td>
                        <td>
                          <span class="flash-badge flash-badge-cts">CTS</span>
                          <span class="flash-badge flash-badge-cts">CTS VERIFIER</span>
                        </td>
                        <td>-</td>
                      </tr>
                      <tr>
                        <td>User Build SW </td>
                        <td>
                          <span class="flash-badge flash-badge-gts">GTS</span>
                        </td>
                        <td>-</td>
                      </tr>
                      <tr>
                        <td>User Build SW + Vendor-Boot Debug</td>
                        <td>
                          <span class="flash-badge flash-badge-gts">GTS INTERACTIVE</span><br>
                          <br>
                          <span class="flash-badge flash-badge-gts">GTS-ROOT</span> <span style="font-size:0.85em; color:#94a3b8;">(A15↑)</span>
                        </td>
                        <td>需額外燒錄 Vendor-Boot Debug；A15 以上才需要 GTS-Root。</td>
                      </tr>

                      <tr>
                        <td rowspan="2"><strong>User Build SW + Google GSI</strong></td>
                        <td>User Build SW + Google GSI</td>
                        <td>
                          <span class="flash-badge flash-badge-cts">CTS-ON-GSI</span>
                        </td>
                        <td>需依流程下載 GSI 並修改 fastboot bat 檔（見下方 CTS-on-GSI 章節）。</td>
                      </tr>
                      <tr>
                        <td>User Build SW + Google GSI + Vendor-Boot Debug</td>
                        <td>
                          <span class="flash-badge flash-badge-vts">VTS</span>
                        </td>
                        <td>在 CTS-on-GSI 上再加 Vendor-Boot Debug 以進行 VTS 測試。</td>
                      </tr>

                      <tr>
                        <td><strong>Userdebug SW</strong></td>
                        <td>Userdebug SW </td>
                        <td>
                          <span class="flash-badge flash-badge-sts">STS</span>
                        </td>
                        <td>僅 STS 測試使用 Userdebug，不與其他 XTS 項目共用。</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div style="text-align: right;">
                    <button class="beauty-btn" onclick="window.location.href='/flash_image'">
                        Flash Image 介紹
                    </button>
                </div>
            </div>

            <div class="tab-pane fade" id="sop" role="tabpanel">
                <div class="tab-title">SOP（標準作業流程）</div>
                <div class="tab-subtitle">從拿到樣機到提交報告的完整步驟。</div>

                <div class="doc-card">
                    <ul class="doc-list" style="list-style: none; padding: 0; font-size: 1.05rem;">
                        <li><strong>Step 1.</strong> Pretest & FIH_CheckList</li>
                        <li><strong>Step 2.</strong> Flash Image 燒錄</li>
                        <li><strong>Step 3.</strong> ATS / Terminal 環境架設</li>
                        <li><strong>Step 4.</strong> Run XTS</li>
                        <li><strong>Step 5.</strong> Fail 測項 Retry & Waiver ID 提交</li>
                        <li><strong>Step 6.</strong> Report Check Tool 確認報告</li>
                        <li><strong>Step 7.</strong> FIH報告提交</li>
                    </ul>
                </div>

                <div style="text-align: right;">
                    <button class="beauty-btn" onclick="window.location.href='/sop'">
                        測試 SOP
                    </button>
                </div>
            </div>

            <div class="tab-pane fade" id="ctsv" role="tabpanel">
                <div class="tab-title">CTSV</div>
                <div class="tab-subtitle">
                    CTSV 備份工具 2.1.bat <br>
                    <br>
                    * Tool 位置在 : \\10.57.41.153\User$\QA\XTS\CTSV <br>
                    <img src="{{ url_for('static', filename='CTSVTool.jpg') }}" alt="CTSVTool" style="margin-bottom:15px;">
                    <div style="color:#cbd5e1; background:rgba(0,0,0,0.2); padding:10px; border-radius:8px; display:inline-block;">
                    -- 按下 1 [Backup] 根據DUT上測項內容生成db檔，db檔會在該路徑自動建立databases的資料夾中<br>
                    -- 按下 2 [Restore] 會把databases內的db吃掉，並備份到你想要Restore的樣機上<br>
                    </div>
                    <br><br>
                    <strong>CTSV 測試參考文件(載完App要一定要記得開權限)：</strong>
                </div>

                <div style="display:flex; flex-direction:column; gap:12px; margin-bottom:40px;">
                    <a href="{{ url_for('static', filename='CTSV/CTSV 指令.docx') }}" target="_blank" class="doc-link">
                        📄 CTSV App 權限指令.docx
                    </a>
                    <a href="{{ url_for('static', filename='CTSV/104115__Android 14 CTS Verifier测试指导手册V1.0 1.pdf') }}" target="_blank" class="doc-link">
                        📘 A14 CTSV.pdf
                    </a>
                    <a href="{{ url_for('static', filename='CTSV/CTS_15.0 Verifier 操作手冊_V1.2_Summer.xlsx') }}" target="_blank" class="doc-link">
                        📗 A15 CTSV.xlsx
                    </a>
                </div>

                <div class="tab-title">GTSI</div>
                <div class="tab-subtitle">
                    GTS Interactive 測試環境架設:<br><br>
                    <div style="color:#cbd5e1; background:rgba(0,0,0,0.2); padding:10px; border-radius:8px; display:inline-block;">
                            Step 1 . 在 /home/fih/XTS 位置下載指定版本的 GTS 包並複製到本機位置進行測試<br>
                            Step 2 . 在 terminal 執行 gts-tradefed ，按下 Enter，建立 Google tradefed 的環境<br>
                            Step 3 . 輸入 run gts-interactive。<br><br>
                    </div>
                    <br><br><strong>GTSI 測試參考文件：</strong>
                </div>

                <div style="display:flex; flex-direction:column; gap:12px;">
                    <a href="{{ url_for('static', filename='GTSI/GTS_Interactive_Setupwizard_PART1_oldversion.pdf') }}" target="_blank" class="doc-link">
                        📄 GtsInteractiveMadaChecklistSetupWizardTestCases.pdf
                    </a>
                    <a href="{{ url_for('static', filename='GTSI/GtsInteractiveMadachecklistTestCases_20250508.pdf') }}" target="_blank" class="doc-link">
                        📄 GtsInteractiveMadachecklistTestCases.pdf
                    </a>
                </div>

                <div style="text-align: right; margin-top: 30px;">
                    <button class="beauty-btn" onclick="window.location.href='/ctsv_gtsi'">
                         手動測試 管理頁面
                    </button>
                </div>
            </div>

            <div class="tab-pane fade" id="retry" role="tabpanel">
                <div class="tab-title">Retry 方法</div>
                <div class="tab-subtitle">整理各式 Retry 的方法，遇到測試無法通過時，可以過來找找。</div>
                <div style="padding: 30px; text-align:center; color:#94a3b8; border: 1px dashed rgba(255,255,255,0.1); border-radius:16px; background: rgba(0,0,0,0.2);">
                    <p>有遇到特別手法、特殊樣機、環境等等都歡迎紀錄。</p>
                </div>
                <div style="text-align: right;">        
                    <button class="beauty-btn" onclick="window.location.href='/retry'">
                         Retry 方法
                    </button>
                </div>
            </div>

            <div class="tab-pane fade" id="waiver" role="tabpanel">
                <div class="tab-title">Waiver ID</div>
                <div class="tab-subtitle">
                    會有一些測項無法通過，是因為被 Google 發現有問題或被關掉之後，Google 會額外提供 Waiver ID。<br>
                    要如何確定會有 Waiver：
                </div>

                <div style="background: rgba(56, 189, 248, 0.05); border-left: 4px solid #38bdf8; padding: 20px; border-radius: 0 8px 8px 0; color:#cbd5e1;">
                    <ol style="margin: 0; padding-left: 20px;">
                        <li>TOT 跑完測項顯示 0 次執行，結果也為 0。</li>
                        <li>在 Google IssueTracker 上輸入TestCase名稱查詢的到該 Waiver ID。</li>
                    </ol>
                </div>
                <div style="font-size:0.95rem; color:#94a3b8; margin-top: 16px;">
                    如果後續有遇到其他的 Waiver 可以繼續新增，另外有些 TestCase 只有 Warning，無 bug id。
                </div>

                <div style="text-align: right;">
                    <button class="beauty-btn" onclick="window.location.href='/waiver'">
                         Waiver 管理頁面
                    </button>
                </div>
            </div>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""


# ----------------------------------------
# APIs (包含重要的圖片路徑修復補丁)
# ----------------------------------------

@app.route("/")
def index():
    return render_template_string(TEMPLATE, planning_url=gms_3pl_planning)


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


# --- 圖片路徑修復補丁 (Magic Route) ---
@app.route('/ctsv_gtsi/<path:filename>')
def serve_ctsv_image_fallback(filename):
    """
    這是一個 'Magic Route'。
    因為 ctvs_gtsi.html 前端可能用相對路徑 (src="image.jpg") 呼叫圖片，
    瀏覽器會去 /ctsv_gtsi/image.jpg 找，但圖片實際在 uploads 資料夾。
    這個函數會自動把請求轉接到 static/uploads/ 去。
    """
    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    return "File not found", 404


# --- Waiver API ---
@app.route("/api/waiver/list/<suite>")
def list_waivers(suite):
    conn = get_db_conn("waiver")
    cur = conn.cursor()
    cur.execute("SELECT id, suite, waiver_id, module, test_case, note FROM waivers WHERE suite = ? ORDER BY id",
                (suite.upper(),))
    rows = cur.fetchall()
    conn.close()
    data = [{"id": r["id"], "suite": r["suite"], "waiver_id": r["waiver_id"], "module": r["module"],
             "test_case": r["test_case"], "note": r["note"]} for r in rows]
    return jsonify(data)


@app.route("/api/waiver/add", methods=["POST"])
def add_waiver():
    data = request.json or {}
    conn = get_db_conn("waiver")
    cur = conn.cursor()
    cur.execute("INSERT INTO waivers (suite, waiver_id, module, test_case, note) VALUES (?, ?, ?, ?, ?)",
                (data.get("suite").upper(), data.get("waiver_id"), data.get("module"), data.get("test_case"),
                 data.get("note")))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"status": "ok", "id": new_id})


@app.route("/api/waiver/update/<int:waiver_id>", methods=["PUT", "POST"])
def update_waiver(waiver_id):
    data = request.json or {}
    conn = get_db_conn("waiver")
    cur = conn.cursor()
    cur.execute("UPDATE waivers SET suite = ?, waiver_id = ?, module = ?, test_case = ?, note = ? WHERE id = ?",
                (data.get("suite").upper(), data.get("waiver_id"), data.get("module"), data.get("test_case"),
                 data.get("note"), waiver_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/waiver/delete/<int:waiver_id>", methods=["DELETE", "POST"])
def delete_waiver(waiver_id):
    conn = get_db_conn("waiver")
    cur = conn.cursor()
    cur.execute("DELETE FROM waivers WHERE id = ?", (waiver_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


# --- Retry API ---
@app.route("/api/retry/list")
def list_retry_tips():
    conn = get_db_conn("retry")
    cur = conn.cursor()
    cur.execute("SELECT id, type, module_case, condition, trick FROM retry_tips ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    data = [{k: r[k] for k in r.keys()} for r in rows]
    return jsonify(data)


@app.route("/api/retry/add", methods=["POST"])
def add_retry_tip():
    data = request.json or {}
    conn = get_db_conn("retry")
    cur = conn.cursor()
    cur.execute("INSERT INTO retry_tips (type, module_case, condition, trick) VALUES (?, ?, ?, ?)",
                (data.get("type"), data.get("module_case"), data.get("condition"), data.get("trick")))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"status": "ok", "id": new_id})


@app.route("/api/retry/update/<int:tip_id>", methods=["PUT", "POST"])
def update_retry_tip(tip_id):
    data = request.json or {}
    conn = get_db_conn("retry")
    cur = conn.cursor()
    cur.execute("UPDATE retry_tips SET type = ?, module_case = ?, condition = ?, trick = ? WHERE id = ?",
                (data.get("type"), data.get("module_case"), data.get("condition"), data.get("trick"), tip_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/retry/delete/<int:tip_id>", methods=["DELETE", "POST"])
def delete_retry_tip(tip_id):
    conn = get_db_conn("retry")
    cur = conn.cursor()
    cur.execute("DELETE FROM retry_tips WHERE id = ?", (tip_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


# --- Suites API ---
@app.route("/api/suites/list")
def list_suites():
    conn = get_db_conn("retry")
    cur = conn.cursor()
    cur.execute("SELECT suite_key, suite_title, suite_tag, display_order FROM suites ORDER BY display_order")
    rows = cur.fetchall()
    conn.close()
    data = [{k: r[k] for k in r.keys()} for r in rows]
    return jsonify(data)


@app.route("/api/suites/add", methods=["POST"])
def add_suite():
    data = request.json or {}
    suite_title = data.get('suite_title', '').strip()
    if not suite_title: return jsonify({"status": "error"}), 400
    suite_tag = data.get('suite_tag', '').strip()
    import re
    suite_key = re.sub(r'[^A-Z0-9]', '_', (suite_tag if suite_tag else suite_title).upper())

    conn = get_db_conn("retry")
    cur = conn.cursor()
    cur.execute("INSERT INTO suites (suite_key, suite_title, suite_tag, display_order) VALUES (?, ?, ?, 999)",
                (suite_key, suite_title, suite_tag))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"status": "ok", "id": new_id, "suite_key": suite_key})


@app.route("/api/suites/delete/<suite_key>", methods=["DELETE"])
def delete_suite(suite_key):
    conn = get_db_conn("retry")
    cur = conn.cursor()
    cur.execute("DELETE FROM suites WHERE suite_key = ?", (suite_key.upper(),))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/suites/reorder", methods=["PUT"])
def reorder_suites():
    data = request.json or []
    conn = get_db_conn("retry")
    cur = conn.cursor()
    for idx, key in enumerate(data):
        cur.execute("UPDATE suites SET display_order = ? WHERE suite_key = ?", ((idx + 1) * 10, key.upper()))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


# --- CTSV/GTSI API ---
@app.route("/api/ctsv_gtsi/sections/list")
def list_ctsv_sections():
    conn = get_db_conn("ctsv_gtsi")
    cur = conn.cursor()
    cur.execute("SELECT section_key, title, tag FROM ctsv_sections ORDER BY display_order")
    rows = cur.fetchall()
    conn.close()
    data = [{k: r[k] for k in r.keys()} for r in rows]
    return jsonify(data)


@app.route("/api/ctsv_gtsi/cards/list")
def list_ctsv_cards():
    conn = get_db_conn("ctsv_gtsi")
    cur = conn.cursor()
    cur.execute(
        "SELECT id, section_key, card_title, card_subtitle, content, note, display_order FROM test_cards ORDER BY section_key, display_order")
    cards = [dict(r) for r in cur.fetchall()]

    # 獲取圖片
    card_ids = [c['id'] for c in cards]
    imgs_by_card = {}
    if card_ids:
        placeholders = ','.join('?' for _ in card_ids)
        cur.execute(
            f"SELECT card_id, filename FROM card_images WHERE card_id IN ({placeholders}) ORDER BY card_id, display_order",
            card_ids)
        for r in cur.fetchall():
            imgs_by_card.setdefault(r["card_id"], []).append(r["filename"])

    for c in cards:
        c["image_urls"] = imgs_by_card.get(c["id"], [])

    conn.close()
    return jsonify(cards)


@app.route("/api/ctsv_gtsi/cards/add", methods=["POST"])
def add_ctsv_card():
    data = request.json or {}
    conn = get_db_conn("ctsv_gtsi")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO test_cards (section_key, card_title, card_subtitle, content, note, display_order) VALUES (?, ?, ?, ?, ?, 999)",
        (data['section_key'], data['card_title'], data.get('card_subtitle'), data['content'], data.get('note')))
    new_id = cur.lastrowid

    # 處理圖片
    image_urls = data.get("image_urls") or []
    for idx, url in enumerate(image_urls):
        cur.execute("INSERT INTO card_images (card_id, filename, display_order) VALUES (?, ?, ?)",
                    (new_id, url, (idx + 1) * 10))

    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "id": new_id})


@app.route("/api/ctsv_gtsi/cards/update/<int:card_id>", methods=["PUT"])
def update_ctsv_card(card_id):
    data = request.json or {}
    conn = get_db_conn("ctsv_gtsi")
    cur = conn.cursor()
    cur.execute("UPDATE test_cards SET section_key=?, card_title=?, card_subtitle=?, content=?, note=? WHERE id=?",
                (data['section_key'], data['card_title'], data.get('card_subtitle'), data['content'], data.get('note'),
                 card_id))

    # 更新圖片 (先刪後加)
    cur.execute("DELETE FROM card_images WHERE card_id = ?", (card_id,))
    image_urls = data.get("image_urls") or []
    for idx, url in enumerate(image_urls):
        cur.execute("INSERT INTO card_images (card_id, filename, display_order) VALUES (?, ?, ?)",
                    (card_id, url, (idx + 1) * 10))

    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/ctsv_gtsi/cards/delete/<int:card_id>", methods=["DELETE"])
def delete_ctsv_card(card_id):
    conn = get_db_conn("ctsv_gtsi")
    cur = conn.cursor()
    cur.execute("DELETE FROM test_cards WHERE id = ?", (card_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route("/api/ctsv_gtsi/upload_file", methods=["POST"])
def upload_file():
    if 'file' not in request.files: return jsonify({"status": "error"}), 400
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify({"status": "ok", "file_path": filename})
    return jsonify({"status": "error"}), 400


@app.route("/ping")
def ping(): return "pong", 200


if __name__ == "__main__":
    create_db_if_not_exists()
    app.run(host="0.0.0.0", port=5000, debug=False)