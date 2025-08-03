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
    主執行函式。
    V32 架構: 本腳本現在是輕量級的「啟動器/監視器」。
    - Colab 模式: 渲染 UI，然後啟動一個獨立的 setup_worker.py 子程序，並即時轉發其日誌。
    - 本地模式: 打印一條訊息後退出，因為本地開發應使用其他工具鏈。
    """
    if not IS_COLAB:
        print("此腳本主要設計為在 Google Colab 中運行。對於本地開發，請參閱相關文件。")
        return

    # --- Colab 執行流程 ---
    from IPython.display import display, HTML, clear_output
    from src.phoenix_core.comms import comm_manager # 延後導入

    # 1. 清理並渲染初始 UI
    clear_output(wait=True)
    display(render_initial_html())

    # 這裡的 print 會直接顯示在 Colab 輸出，作為啟動的第一個標記
    print(f"[{get_dependency_free_timestamp()}] 🚀 Phoenix 啟動器已載入。準備啟動安裝工作程序...")

    def stream_logs(process):
        """在一個執行緒中讀取和轉發日誌。"""
        for line in iter(process.stdout.readline, ''):
            # 將從子程序收到的原始日誌行，透過 comms 發送到前端
            comm_manager.send_data('runner_log', {'line': line.strip()})
        process.wait()
        # 當日誌流結束時，發送一個最終信號
        comm_manager.send_data('runner_log', {'line': '✅ 安裝工作程序已結束。'})


    try:
        # 2. 準備並啟動 setup_worker.py 子程序
        setup_script_path = Path(__file__).parent.parent / "scripts" / "setup_worker.py"
        if not setup_script_path.exists():
             # 使用 comms 發送致命錯誤
            comm_manager.send_data('runner_log', {'line': f'❌ 致命錯誤: 找不到安裝腳本 {setup_script_path}'})
            return

        command = [
            sys.executable, str(setup_script_path),
            "--repo-url", REPOSITORY_URL,
            "--branch", TARGET_BRANCH_OR_TAG,
            "--project-folder", PROJECT_FOLDER_NAME,
            "--timezone", TIMEZONE,
        ]
        if FORCE_REPO_REFRESH:
            command.append("--force-refresh")

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            bufsize=1
        )

        # 3. 在背景執行緒中開始串流日誌
        log_thread = threading.Thread(target=stream_logs, args=(process,))
        log_thread.start()

    except Exception as e:
        # 捕獲 Popen 或其他早期錯誤
        error_message = f"❌ 啟動安裝工作程序時發生致命錯誤: {e}"
        print(error_message) # 直接打印，因為 comms 可能還沒好
        # 也嘗試透過 comms 發送
        try:
            comm_manager.send_data('runner_log', {'line': error_message})
        except:
            pass
        import traceback
        traceback.print_exc()

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"[{get_dependency_free_timestamp()}] ❌ 發生致命錯誤: {e}", file=sys.stderr)
        if hasattr(e, 'stderr'):
            print(f"[{get_dependency_free_timestamp()}] [錯誤詳情]: {e.stderr}", file=sys.stderr)
    except Exception as e:
        print(f"[{get_dependency_free_timestamp()}] ❌ 發生未預期的錯誤: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
