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
    # V30 修復: f-string 語法衝突
    # 將所有 JavaScript 模板字串中的 { 和 } 分別用 {{ 和 }} 進行轉義
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
        table { width: 100%; border-collapse: collapse; }
        td { padding: 4px 8px; }
    </style>
    """
    html_body = """
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
    """
    javascript = f"""
    <script type="text/javascript">
        // 確保 logContainer 存在
        const logContainer = document.getElementById('log-container');
        function addLog(message, level = 'INFO') {{
            const entry = document.createElement('div');
            entry.className = `log-entry log-level-${{level}}`;
            entry.textContent = `[${{new Date().toLocaleTimeString()}}] ${{message}}`;
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

                        // 特別處理資源監控
                        if (key === 'cpu_usage' || key === 'ram_usage') {{
                            document.getElementById(key).textContent = `${{parseFloat(value).toFixed(1)}}%`;
                        }}
                    }} else if (data.type === 'log_entry') {{
                        const log = data.payload;
                        addLog(`[${{log.source}}] ${{log.message}}`, log.level);
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
    </script>
    """
    return HTML(css + html_body + javascript)


def run_backend_process(project_path: Path, config_file_path: Path, is_colab: bool):
    """
    以子程序方式啟動後端工作者 (backend_worker.py)。
    """
    # V30.2 修正：路徑邏輯。在本地模式下，腳本相對於專案根目錄，而非 project_path
    if is_colab:
        # 在 Colab 中，程式碼被 clone 到 project_path，所以 worker 在那裡面
        repo_root = project_path
    else:
        # 在本地，此腳本在 `run/`，所以根目錄是 `Path(__file__).parent.parent`
        repo_root = Path(__file__).parent.parent

    launch_script_path = repo_root / "scripts" / "backend_worker.py"
    if not launch_script_path.exists():
        raise FileNotFoundError(f"找不到後端工作者腳本: {launch_script_path}")

    venv_python = project_path / ".venv" / "bin" / "python"
    command = [str(venv_python), str(launch_script_path), "--config", str(config_file_path)]

    # 工作目錄 (cwd) 應始終是 project_path，因為那是資料 (如DB) 和 venv 的所在地
    cwd = project_path

    if is_colab:
        # Colab 模式：在背景運行，不阻塞，依賴 Comms 傳遞日誌
        print(f"[{get_dependency_free_timestamp()}] [Colab模式] 正在背景啟動後端工作者...")
        subprocess.Popen(command, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[{get_dependency_free_timestamp()}] ✅ 後端已在背景啟動。UI 將透過 Comms 接收更新。")
    else:
        # 本地模式：直接在前景運行，並將其 stdout 即時打印到當前終端
        print(f"[{get_dependency_free_timestamp()}] [本地模式] 正在啟動後端工作者，日誌將直接輸出到此處...")
        print(f"[{get_dependency_free_timestamp()}] 命令: {' '.join(command)}")
        process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', bufsize=1)
        for line in iter(process.stdout.readline, ''):
            print(line, end='')
        process.wait()
        print(f"[{get_local_timestamp()}] [本地模式] 後端工作者已結束。")

def main():
    """
    主執行函式，實現雙模態邏輯。
    """
    if IS_COLAB:
        from IPython.display import display, HTML, clear_output
        clear_output(wait=True)
        # 步驟 1 (Colab): 立即渲染 UI
        display(render_initial_html())
        print(f"[{get_dependency_free_timestamp()}] 儀表板 UI 已渲染。正在準備後端環境...")

    # --- 環境準備 (對兩種模式都通用) ---
    try:
        # V30.3 修正: 統一且清晰地處理路徑
        if IS_COLAB:
            # Colab 模式下，所有東西都在 /content/PROJECT_FOLDER_NAME 中
            project_path = Path("/content") / PROJECT_FOLDER_NAME
            repo_root = project_path
            venv_dir = project_path / ".venv"

            if FORCE_REPO_REFRESH and project_path.exists():
                print(f"[{get_dependency_free_timestamp()}] 偵測到強制刷新，正在刪除舊的專案資料夾: {project_path}...")
                shutil.rmtree(project_path)

            if not project_path.exists():
                print(f"[{get_dependency_free_timestamp()}] 正在從 {REPOSITORY_URL} (分支/標籤: {TARGET_BRANCH_OR_TAG}) 下載程式碼...")
                subprocess.run(
                    ["git", "clone", "--depth", "1", "--branch", TARGET_BRANCH_OR_TAG, REPOSITORY_URL, str(project_path)],
                    check=True, capture_output=True, text=True
                )
        else:
            # 本地模式下，repo_root 是當前目錄，venv 也在此。project_path 僅用於放置資料。
            repo_root = Path(".").resolve()
            project_path = repo_root / PROJECT_FOLDER_NAME
            venv_dir = repo_root / ".venv"
            project_path.mkdir(exist_ok=True)
            print(f"[{get_dependency_free_timestamp()}] [本地模式] 使用 {repo_root} 作為專案根目錄。")

        # --- 通用設定流程 ---
        print(f"[{get_dependency_free_timestamp()}] 正在生成 config.json...")
        config_file_path = project_path / "config.json"
        with open(config_file_path, "w", encoding="utf-8") as f:
            json.dump({"system_settings": {"timezone": TIMEZONE}}, f, indent=4)

        print(f"[{get_dependency_free_timestamp()}] 正在設定 Python 虛擬環境於: {venv_dir}")
        if not venv_dir.is_dir():
            subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)

        venv_python = venv_dir / "bin" / "python"
        requirements_file = repo_root / "requirements" / "dev.txt"
        print(f"[{get_dependency_free_timestamp()}] 正在從 {requirements_file} 安裝依賴...")
        subprocess.run([str(venv_python), "-m", "pip", "install", "-r", str(requirements_file)], check=True)

        print(f"[{get_dependency_free_timestamp()}] ✅ 環境準備完成。")

        # --- 啟動後端 (根據模式不同，行為也不同) ---
        run_backend_process(project_path, config_file_path, IS_COLAB)

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
