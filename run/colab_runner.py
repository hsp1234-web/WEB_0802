# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║          🚀 Colab 雙模態啟動器 V30 (Comms + DB 架構)               ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║ - 架構: 根據環境智慧切換模式。                                     ║
# ║   - Colab 模式: 立即渲染 UI，透過原生 Comms 通訊接收後端數據。     ║
# ║   - 本地模式: 作為標準 CLI 工具，直接打印後端日誌。                ║
# ║ - 版本：0.3.0 (雙模態架構)                                         ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝
import os
import sys
import shutil
import subprocess
import threading
import time
import json
from pathlib import Path
from datetime import datetime

# --- 環境偵測 ---
IS_COLAB = 'google.colab' in sys.modules

if IS_COLAB:
    from IPython.display import display, HTML, clear_output

# --- Colab 使用者介面參數 (保持不變) ---
#@title 🚀 V30 鳳凰之心 (雙模態 Comms 架構) { vertical-output: true, display-mode: "form" }
#@markdown ---
#@markdown ### Part 1: 程式碼與環境設定
#@markdown > 設定 Git 倉庫、分支或標籤，以及專案資料夾。
#@markdown ---
#@markdown 後端程式碼倉庫 (REPOSITORY_URL)
REPOSITORY_URL = "https://github.com/hsp1234-web/WEB_0802.git" #@param {type:"string"}
#@markdown 後端版本分支或標籤 (TARGET_BRANCH_OR_TAG)
TARGET_BRANCH_OR_TAG = "0.3.4" #@param {type:"string"}
#@markdown 專案資料夾名稱 (PROJECT_FOLDER_NAME)
PROJECT_FOLDER_NAME = "WEB1" #@param {type:"string"}
#@markdown 強制刷新後端程式碼 (FORCE_REPO_REFRESH)
FORCE_REPO_REFRESH = True #@param {type:"boolean"}
#@markdown 時區設定 (TIMEZONE)
TIMEZONE = "Asia/Taipei" #@param {type:"string"}

# ==============================================================================
# 🚀 核心邏輯
# ==============================================================================

def get_dependency_free_timestamp():
    """一個在安裝依賴前可安全使用的、無外部依賴的時間戳函式。"""
    return datetime.now().strftime('%H:%M:%S')

def get_local_timestamp():
    """一個使用時區設定的時間戳函式，應在依賴安裝後使用。"""
    import pytz
    return datetime.now(pytz.timezone(TIMEZONE)).strftime('%H:%M:%S')

def render_initial_html():
    """
    渲染儀表板的靜態 HTML 骨架和負責接收 Comms 數據的 JavaScript。
    """
    # V32: 為 runner_log 新增 CSS
    css = """
    <style>
        body { font-family: 'Noto Sans TC', 'Fira Code', monospace; background-color: #1a1a1a; color: #e0e0e0; }
        .container { padding: 1em; }
        .panel { border: 1px solid #444; margin-bottom: 1em; border-radius: 8px; overflow: hidden; }
        .title { font-weight: bold; padding: 0.5em; border-bottom: 1px solid #444; background-color: #2a2a2a;}
        .content { padding: 0.8em; }
        .grid { display: grid; grid-template-columns: 1fr 2fr; gap: 1em; }
        .log-container { height: 400px; overflow-y: auto; background-color: #222; padding: 0.5em; border-radius: 5px; font-size: 0.9em; }
        .log-entry { white-space: pre-wrap; word-break: break-all; margin-bottom: 5px; }
        .log-level-SUCCESS { color: #c3e88d; }
        .log-level-ERROR, .log-level-CRITICAL { color: #ff5370; font-weight: bold; }
        .log-level-INFO { color: #89ddff; }
        .log-level-PERF { color: #f7b89c; }
        .log-level-RUNNER { color: #e5c07b; } /* Runner log 的新顏色 */
        table { width: 100%; border-collapse: collapse; }
        td { padding: 4px 8px; }
        #copy-btn-container { text-align: center; padding-top: 10px; }
        #copy-output-btn {
            background-color: #0d47a1; color: white; border: none;
            padding: 10px 20px; border-radius: 5px; cursor: pointer;
            transition: background-color 0.3s;
        }
        #copy-output-btn:hover { background-color: #1565c0; }
        #copy-output-btn.copied { background-color: #4caf50; }
    </style>
    """
    html_body = """
    <div id="phoenix-main-output">
        <div class="container">
            <div class="grid">
                <div>
                    <div class="panel">
                        <div class="title">後端狀態</div>
                        <div class="content"><table id="status-table"><tbody><tr><td>等待後端回報...</td></tr></tbody></table></div>
                    </div>
                    <div class="panel">
                        <div class="title">系統資源</div>
                        <div class="content">
                            <table>
                                <tr><td>CPU</td><td id="cpu_usage">等待中...</td></tr>
                                <tr><td>RAM</td><td id="ram_usage">等待中...</td></tr>
                            </table>
                        </div>
                    </div>
                </div>
                <div class="panel">
                    <div class="title">前端日誌 (Comms)</div>
                    <div class="content log-container" id="log-container">等待 Comms 連接...</div>
                </div>
            </div>
        </div>
    </div>
    <div id="copy-btn-container">
        <button id="copy-output-btn">📋 複製上方所有儲存格輸出</button>
    </div>
    """
    javascript = f"""
    <script type="text/javascript">
        const logContainer = document.getElementById('log-container');
        function addLog(message, level = 'INFO') {{
            const entry = document.createElement('div');
            entry.className = `log-entry log-level-${{level}}`;
            // V32: 對 Runner log 不加時間戳，因為它自帶時間戳
            if (level === 'RUNNER') {{
                entry.textContent = message;
            }} else {{
                entry.textContent = `[${{new Date().toLocaleTimeString()}}] ${{message}}`;
            }}
            logContainer.appendChild(entry);
            logContainer.scrollTop = logContainer.scrollHeight;
        }}

        addLog('前端 JavaScript 已載入，正在註冊 Comms 目標...');

        google.colab.kernel.comms.registerTarget('phoenix_comms', (comm, message) => {{
            addLog('✅ Comms 頻道已連接！');
            comm.onMsg = (msg) => {{
                try {{
                    const data = JSON.parse(msg);
                    if (data.type === 'status_update') {{
                        const key = Object.keys(data.payload)[0];
                        const value = data.payload[key];
                        let table = document.getElementById('status-table').querySelector('tbody');
                        let row = document.getElementById(`status-row-${{key}}`);
                        if (!row) {{
                            row = table.insertRow();
                            row.id = `status-row-${{key}}`;
                            row.innerHTML = `<td>${{key}}</td><td id="status-val-${{key}}"></td>`;
                        }}
                        document.getElementById(`status-val-${{key}}`).textContent = value;

                        if (key === 'cpu_usage' || key === 'ram_usage') {{
                            document.getElementById(key).textContent = `${{parseFloat(value).toFixed(1)}}%`;
                        }}
                    }} else if (data.type === 'log_entry') {{
                        const log = data.payload;
                        addLog(`[${{log.source}}] ${{log.message}}`, log.level);
                    // V32: 新增對 runner_log 的處理
                    }} else if (data.type === 'runner_log') {{
                        addLog(data.payload.line, 'RUNNER');
                    }}
                }} catch (e) {{
                    addLog(`處理 Comms 訊息時發生錯誤: ${{e}}`, 'ERROR');
                }}
            }};
            comm.onClose = () => {{
                addLog('Comms 頻道已關閉。', 'ERROR');
            }};
        }});
        addLog('Comms 目標 "phoenix_comms" 已註冊。等待後端連接...');

        // --- 新增的複製按鈕邏輯 ---
        const copyBtn = document.getElementById('copy-output-btn');
        copyBtn.addEventListener('click', () => {{
            const outputContainer = document.getElementById('phoenix-main-output');
            if (navigator.clipboard) {{
                navigator.clipboard.writeText(outputContainer.innerText).then(() => {{
                    const originalText = copyBtn.textContent;
                    copyBtn.textContent = '✅ 已複製！';
                    copyBtn.classList.add('copied');
                    setTimeout(() => {{
                        copyBtn.textContent = originalText;
                        copyBtn.classList.remove('copied');
                    }}, 2000);
                }}).catch(err => {{
                    addLog('複製失敗: ' + err, 'ERROR');
                }});
            }} else {{
                addLog('瀏覽器不支援 Clipboard API', 'ERROR');
            }}
        }});
    </script>
    """
    return HTML(css + html_body + javascript)


def main():
    """
    主執行函式 (V34 - Colab 專用)。
    本腳本現在只為 Colab 環境服務，採用「啟動器-工作者」架構。
    """
    if not IS_COLAB:
        print("此腳本專為 Google Colab 設計。對於本地開發，請使用 `run/local_runner.py`。")
        return

    # --- Colab 執行流程 ---
    try:
        # V34: 解決 ModuleNotFoundError 的關鍵步驟
        # 在導入任何專案模組之前，先將未來的專案路徑加入 sys.path
        project_path = Path("/content") / PROJECT_FOLDER_NAME
        sys.path.insert(0, str(project_path))

        from IPython.display import display, HTML, clear_output
        from src.phoenix_core.comms import comm_manager

        clear_output(wait=True)
        display(render_initial_html())
        print(f"[{get_dependency_free_timestamp()}] 🚀 Phoenix 啟動器已載入。準備啟動安裝工作程序...")

        def stream_logs(process):
            """在一個執行緒中讀取和轉發日誌。"""
            for line in iter(process.stdout.readline, ''):
                comm_manager.send_data('runner_log', {'line': line.strip()})
            process.wait()
            comm_manager.send_data('runner_log', {'line': '✅ 安裝工作程序已結束。'})

        setup_script_path = project_path / "scripts" / "setup_worker.py"

        # 這裡我們不預先檢查 setup_script_path 是否存在，
        # 因為它是由子程序自己下載的。如果子程序失敗，日誌會回報。

        command = [
            sys.executable, str(setup_script_path),
            "--repo-url", REPOSITORY_URL, "--branch", TARGET_BRANCH_OR_TAG,
            "--project-folder", PROJECT_FOLDER_NAME, "--timezone", TIMEZONE,
        ]
        if FORCE_REPO_REFRESH:
            command.append("--force-refresh")

        # 在啟動子程序前，先確保 /content/WEB1 的父目錄存在
        project_path.parent.mkdir(parents=True, exist_ok=True)

        # 工作目錄 cwd 應該是 /content，因為 setup_worker.py 預期在那裡創建 WEB1
        process = subprocess.Popen(
            command,
            cwd=project_path.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            bufsize=1
        )

        log_thread = threading.Thread(target=stream_logs, args=(process,))
        log_thread.start()

    except Exception as e:
        # 通用的頂層錯誤捕獲
        error_message = f"❌ 啟動器發生致命錯誤: {e}"
        print(error_message, file=sys.stderr)
        try:
            # 再次嘗試導入 comms 以回報錯誤
            from src.phoenix_core.comms import comm_manager
            comm_manager.send_data('runner_log', {'line': error_message})
        except:
            pass # 如果連 comms 都導入不了，也沒辦法了
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
