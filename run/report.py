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
    <style>
        body {{ background-color: transparent; color: var(--colab-primary-text-color, #e0e0e0); font-family: 'Noto Sans TC', 'Fira Code', monospace; }}
        .container {{ padding: 1em; }}
        .panel {{ border: 1px solid var(--colab-border-color, #444); margin-bottom: 1em; border-radius: 8px; overflow: hidden; background-color: var(--colab-secondary-surface-color, #2d2d2d);}}
        .title {{ font-weight: bold; padding: 0.5em 1em; border-bottom: 1px solid var(--colab-border-color, #444); background-color: var(--colab-section-header-color, #2a2a2a);}}
        .content {{ padding: 1em; }}
        .button {{ background-color: #444; color: #eee; border: 1px solid #666; padding: 10px 20px; cursor: pointer; border-radius: 5px; transition: background-color 0.2s; }}
        .button:hover {{ background-color: #555; }}
        .button:disabled {{ background-color: #333; color: #888; cursor: not-allowed; }}
        .checkbox-label {{ display: flex; align-items: center; margin-bottom: 0.5em; cursor: pointer; }}
        #report-preview {{ height: 400px; overflow-y: auto; white-space: pre-wrap; word-break: break-all; background-color: var(--colab-secondary-surface-color, #1e1e1e); padding: 1em; border-radius: 5px; border: 1px solid var(--colab-border-color, #444);}}
        #toast-container {{ position: fixed; bottom: 1rem; right: 1rem; z-index: 999; }}
        .toast {{ padding: 1rem; margin-top: 0.5rem; border-radius: 5px; color: white; opacity: 0; transform: translateY(20px); transition: all 0.3s; }}
        .toast.show {{ opacity: 1; transform: translateY(0); }}
        .toast-success {{ background-color: #2E7D32; }}
        .toast-error {{ background-color: #C62828; }}
        .toast-info {{ background-color: #1565C0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1 style="text-align: center; font-size: 1.5em; margin-bottom: 1em;">📊 鳳凰之心 - 互動式報告儀表板 📊</h1>

        <div class="panel">
            <div class="title">報告選擇</div>
            <div class="content">
                <div id="report-options">
                    <label class="checkbox-label"><input type="checkbox" id="select-all" checked> <strong>全部報告</strong></label>
                    <div style="padding-left: 2em;">
                        <label class="checkbox-label"><input type="checkbox" name="report-option" value="performance_report.md" checked> 📈 效能分析報告 (performance_report.md)</label>
                        <label class="checkbox-label"><input type="checkbox" name="report-option" value="summary_report.md" checked> 📄 總結報告 (summary_report.md)</label>
                        <label class="checkbox-label"><input type="checkbox" name="report-option" value="detailed_log_report.md" checked> 📋 詳細日誌報告 (detailed_log_report.md)</label>
                    </div>
                </div>
                <div style="text-align: center; margin-top: 1em;">
                    <button id="generate-button" class="button">產生報告</button>
                </div>
            </div>
        </section>

        <div id="output-section" style="display: none;">
            <div class="panel">
                <div class="title">報告內容預覽</div>
                <div class="content">
                    <div id="report-preview"></div>
                </div>
            </div>
            <div class="panel">
                <div class="title">面板內容操作</div>
                <div class="content" style="text-align: center;">
                    <button id="copy-button" class="button">複製預覽內容</button>
                    <button id="archive-button" class="button">存檔選中報告</button>
                </div>
            </div>
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
