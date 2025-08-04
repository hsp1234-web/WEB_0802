#@title 📊 鳳凰之心 - 互動式報告儀表板
# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║              📊 鳳凰之心 - 互動式報告儀表板 V35 (HTML)               ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║ - 說明: 在 Colab 中渲染一個純 HTML/JS 的互動儀表板，風格與主監控   ║
# ║         面板統一。透過 google.colab.kernel 與 Python 後端通訊。      ║
# ║ - 版本: 2.0.0 (純 HTML 介面與 Kernel Callbacks)                    ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

# --- 導入必要的函式庫 ---
from IPython.display import display, HTML, Javascript
from google.colab import output
from pathlib import Path
import sys
import os
import json

# --- 路徑修正 ---
project_root = os.getcwd()
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- 導入後端邏輯 ---
try:
    from src.phoenix_core.report_generator import read_selected_reports, archive_selected_reports
except ImportError as e:
    # 提供一個 fallback，以防在非標準環境中執行
    print(f"⚠️ 警告: 無法導入 report_generator ({e})。將使用模擬函式。")
    def read_selected_reports(directory, selection):
        mock_reports = {
            'performance_report.md': '### 📈 效能分析報告\n- 模擬數據: 核心初始化耗時: 2.34s',
            'summary_report.md': '### 📄 總結報告\n- 模擬數據: 本次任務成功執行 128 個操作。',
            'detailed_log_report.md': '### 📋 詳細日誌報告\n- [20:25:38] [SUCCESS] ✅ 市場分析報告已生成。'
        }
        return "\n\n---\n\n".join([mock_reports.get(s, f"找不到報告: {s}") for s in selection])

    def archive_selected_reports(reports_dir, archive_root, selection):
        archive_path = Path(archive_root) / "archive" / "mock_archive_123"
        archive_path.mkdir(parents=True, exist_ok=True)
        return str(archive_path)


# --- 全域變數與設定 ---
REPORTS_DIR = Path("./reports")
ARCHIVE_ROOT_DIR = Path("./")

# --- Python 後端回呼函式 ---
def get_report_data(selection):
    """供 JavaScript 呼叫以獲取報告內容。"""
    try:
        content = read_selected_reports(REPORTS_DIR, selection)
        return json.dumps({'status': 'success', 'content': content})
    except Exception as e:
        return json.dumps({'status': 'error', 'message': str(e)})

def archive_reports(selection):
    """供 JavaScript 呼叫以存檔報告。"""
    try:
        archive_path = archive_selected_reports(REPORTS_DIR, ARCHIVE_ROOT_DIR, selection)
        return json.dumps({'status': 'success', 'path': str(archive_path)})
    except Exception as e:
        return json.dumps({'status': 'error', 'message': str(e)})

# 註冊回呼函式，使其可從 JS 訪問
output.register_callback('notebook.get_report_data', get_report_data)
output.register_callback('notebook.archive_reports', archive_reports)


# --- 前端 HTML/CSS/JS ---
DASHBOARD_UI_HTML = """
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>鳳凰之心 - 互動式報告儀表板</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&family=Noto+Sans+TC:wght@400;500;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', 'Noto Sans TC', sans-serif;
            background-color: transparent; /* 適應 Colab 主題 */
            color: var(--colab-primary-text-color, #333);
        }
        .font-code { font-family: 'Fira Code', monospace; }
        .dashboard-panel {
            background-color: var(--colab-secondary-surface-color, #f7f7f7);
            border: 1px solid var(--colab-border-color, #e0e0e0);
            border-radius: 0.75rem;
            margin-bottom: 1.5rem;
        }
        .panel-title {
            padding: 0.75rem 1.25rem;
            border-bottom: 1px solid var(--colab-border-color, #e0e0e0);
            color: var(--colab-secondary-text-color, #555);
            font-weight: 500;
        }
        .custom-checkbox {
            appearance: none;
            background-color: var(--colab-secondary-surface-color, #eee);
            border: 1px solid var(--colab-border-color, #ccc);
            border-radius: 0.25rem; width: 1.25rem; height: 1.25rem;
            cursor: pointer; position: relative; transition: all 0.2s;
        }
        .custom-checkbox:checked {
            background-color: #3b82f6; /* blue-500 */
            border-color: #3b82f6;
        }
        .custom-checkbox:checked::after {
            content: '✓'; color: white; position: absolute;
            left: 50%; top: 50%; transform: translate(-50%, -50%);
            font-size: 0.875rem;
        }
        #report-preview {
            background-color: var(--colab-secondary-surface-color, #fdfdfd);
            border: 1px solid var(--colab-border-color, #e0e0e0);
            border-radius: 0.5rem;
            color: var(--colab-primary-text-color, #333);
        }
    </style>
</head>
<body class="p-4 sm:p-6 md:p-8">
    <div class="max-w-4xl mx-auto">
        <header class="text-center mb-8">
            <h1 class="text-2xl sm:text-3xl font-bold" style="color: #1E88E5;">
                📊 鳳凰之心 - 互動式報告儀表板 📊
            </h1>
        </header>

        <section class="dashboard-panel">
            <div class="panel-title">請選擇您需要產生的報告類型</div>
            <div class="p-6 space-y-4">
                <label class="flex items-center space-x-3 cursor-pointer">
                    <input type="checkbox" id="select-all" class="custom-checkbox" checked>
                    <span>全部報告</span>
                </label>
                <div id="report-options" class="pl-8 space-y-3">
                    <label class="flex items-center space-x-3 cursor-pointer">
                        <input type="checkbox" name="report-option" value="performance_report.md" class="custom-checkbox" checked>
                        <span>📈 效能分析報告 (performance_report.md)</span>
                    </label>
                    <label class="flex items-center space-x-3 cursor-pointer">
                        <input type="checkbox" name="report-option" value="summary_report.md" class="custom-checkbox" checked>
                        <span>📄 總結報告 (summary_report.md)</span>
                    </label>
                    <label class="flex items-center space-x-3 cursor-pointer">
                        <input type="checkbox" name="report-option" value="detailed_log_report.md" class="custom-checkbox" checked>
                        <span>📋 詳細日誌報告 (detailed_log_report.md)</span>
                    </label>
                </div>
                <div class="pt-4 flex justify-center">
                    <button id="generate-button" class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-6 rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105">
                        產生報告
                    </button>
                </div>
            </div>
        </section>

        <div id="output-section" class="hidden">
            <section class="dashboard-panel">
                <div class="panel-title">報告內容預覽</div>
                <div id="report-preview" class="p-6 font-code text-sm leading-relaxed h-80 overflow-y-auto whitespace-pre-wrap"></div>
            </section>

            <section class="dashboard-panel">
                <div class="panel-title">📋 面板內容操作</div>
                <div class="p-4 flex flex-wrap justify-center gap-4">
                    <button id="copy-button" class="bg-violet-600 hover:bg-violet-700 text-white font-bold py-2 px-4 rounded-lg">複製預覽內容</button>
                    <button id="archive-button" class="bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded-lg">存檔選中報告</button>
                </div>
            </section>
        </div>
    </div>

    <div id="toast-container" class="fixed bottom-4 right-4 space-y-2"></div>

<script>
    const selectAllCheckbox = document.getElementById('select-all');
    const reportOptions = document.querySelectorAll('input[name="report-option"]');
    const generateButton = document.getElementById('generate-button');
    const outputSection = document.getElementById('output-section');
    const reportPreview = document.getElementById('report-preview');
    const copyButton = document.getElementById('copy-button');
    const archiveButton = document.getElementById('archive-button');

    // --- Toast 訊息功能 ---
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        const colors = {
            success: 'bg-green-600', error: 'bg-red-600', info: 'bg-blue-600'
        };
        toast.className = `p-4 rounded-lg text-white font-bold shadow-lg transition-all duration-300 transform translate-x-full ${colors[type]}`;
        toast.textContent = message;
        document.getElementById('toast-container').appendChild(toast);

        requestAnimationFrame(() => {
            toast.style.transform = 'translateX(0)';
        });

        setTimeout(() => {
            toast.style.transform = 'translateX(120%)';
            toast.addEventListener('transitionend', () => toast.remove());
        }, 3000);
    }

    // --- 事件監聽 ---
    selectAllCheckbox.addEventListener('change', (e) => {
        reportOptions.forEach(chk => chk.checked = e.target.checked);
    });

    reportOptions.forEach(chk => {
        chk.addEventListener('change', () => {
            selectAllCheckbox.checked = [...reportOptions].every(c => c.checked);
        });
    });

    generateButton.addEventListener('click', async () => {
        const selection = [...reportOptions].filter(c => c.checked).map(c => c.value);
        if (selection.length === 0) {
            showToast('請至少選擇一份報告', 'info');
            return;
        }

        generateButton.disabled = true;
        generateButton.textContent = '正在產生...';

        try {
            const resultStr = await google.colab.kernel.invokeFunction('notebook.get_report_data', [selection], {});
            const result = JSON.parse(resultStr);

            if (result.status === 'success') {
                reportPreview.textContent = result.content;
                outputSection.classList.remove('hidden');
                showToast('報告已成功產生', 'success');
            } else {
                reportPreview.textContent = '產生報告時發生錯誤：\\n' + result.message;
                showToast('產生報告失敗', 'error');
            }
        } catch (e) {
            reportPreview.textContent = '與 Python 後端通訊失敗：\\n' + e;
            showToast('通訊失敗', 'error');
        } finally {
            generateButton.disabled = false;
            generateButton.textContent = '產生報告';
        }
    });

    copyButton.addEventListener('click', () => {
        navigator.clipboard.writeText(reportPreview.textContent).then(() => {
            showToast('已複製到剪貼簿', 'success');
        }, () => {
            showToast('複製失敗', 'error');
        });
    });

    archiveButton.addEventListener('click', async () => {
        const selection = [...reportOptions].filter(c => c.checked).map(c => c.value);
        if (selection.length === 0) {
            showToast('請選擇要存檔的報告', 'info');
            return;
        }

        archiveButton.disabled = true;
        archiveButton.textContent = '正在存檔...';

        try {
            const resultStr = await google.colab.kernel.invokeFunction('notebook.archive_reports', [selection], {});
            const result = JSON.parse(resultStr);
            if(result.status === 'success') {
                showToast(`成功存檔至 ${result.path}`, 'success');
            } else {
                showToast(`存檔失敗: ${result.message}`, 'error');
            }
        } catch (e) {
            showToast('與 Python 後端通訊失敗', 'error');
        } finally {
            archiveButton.disabled = false;
            archiveButton.textContent = '存檔選中報告';
        }
    });
</script>
</body>
</html>
"""

def display_dashboard():
    """渲染儀表板 UI。"""
    display(HTML(DASHBOARD_UI_HTML))

# --- 主程式入口 ---
if __name__ == "__main__":
    if not REPORTS_DIR.exists():
        REPORTS_DIR.mkdir()
        print(f"‼️ 警告：報告目錄 '{REPORTS_DIR}' 不存在，已自動建立。")
        print("   請確保後端已生成報告檔案至此目錄。")

    # 檢查是否在 Colab 環境中
    try:
        import google.colab
        display_dashboard()
    except ImportError:
        print("❌ 錯誤：此腳本設計為在 Google Colab 中執行。")
        print("   它需要 `google.colab` 函式庫來進行前後端通訊。")
