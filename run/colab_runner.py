# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║              🚀 Colab 指揮中心 V28 (穩定後端版)                      ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 架構：前端 UI + API 輪詢。後端由一個獨立的、穩定的             ║
# ║           venv 驅動的啟動器 `start_api_service.py` 全權負責。        ║
# ║   - 版本：0.2.0                                                      ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import os
import sys
import subprocess
import threading
import time
from IPython.display import display, HTML, clear_output

# --- Colab 使用者介面參數 (保持不變) ---
#@title 🚀 V28 鳳凰之心指揮中心 (穩定後端版) { vertical-output: true, display-mode: "form" }
#@markdown > **點擊左側的「執行」按鈕，即可啟動後端服務並顯示儀表板。**
#@markdown ---
#@markdown ### **監控設定**
#@markdown **儀表板更新頻率 (秒)**
REFRESH_RATE_SECONDS = 1.5 #@param {type:"number"}

# ==============================================================================
# 🚀 核心邏輯
# ==============================================================================

def background_worker(stop_event):
    """
    【已簡化】背景工作執行緒。
    唯一的職責就是呼叫穩定可靠的後端啟動器。
    """
    try:
        print(" BACKGROUND_WORKER: 正在啟動後端服務...")
        # 呼叫我們新的、穩定的後端啟動器
        # 這個腳本會處理所有複雜的工作：建立 venv, 裝依賴, 啟動伺服器
        command = [sys.executable, "scripts/start_api_service.py"]

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # 將 stderr 合併到 stdout
            text=True,
            encoding='utf-8',
        )

        # 將後端啟動器的日誌即時打印出來，方便除錯
        for line in process.stdout:
            print(f"   [BACKEND] {line.strip()}")
            if stop_event.is_set():
                print("   [BACKEND] 主執行緒請求終止，正在關閉後端服務...")
                process.terminate()
                break

        process.wait()
        print(" BACKGROUND_WORKER: 後端服務程序已結束。")

    except Exception as e:
        print(f"❌ 背景工作執行緒發生致命錯誤: {e}")

def render_dashboard_html():
    """
    【保持不變】生成儀表板的 HTML 和 JavaScript。
    前端邏輯完全不變，它仍然是輪詢 localhost:8088 的 API。
    """
    refresh_interval_ms = int(REFRESH_RATE_SECONDS * 1000)
    return f"""
    <style>
        body {{ font-family: 'Noto Sans TC', sans-serif; background-color: #1e1e1e; color: #d4d4d4; }}
        .container {{ padding: 1em; max-width: 1000px; margin: auto; }}
        .panel {{ border: 1px solid #333; margin-bottom: 1em; border-radius: 8px; overflow: hidden; }}
        .title {{ font-weight: bold; padding: 0.8em; border-bottom: 1px solid #333; background-color: #2a2a2a;}}
        .content {{ padding: 0.8em; font-size: 0.95em; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1.5fr; gap: 1em; }}
        .log-container {{ background-color: #111; padding: 0.8em; border-radius: 5px; height: 300px; overflow-y: auto; font-family: 'Fira Code', monospace; font-size: 0.85em; }}
        .log-entry {{ white-space: pre-wrap; word-break: break-all; }}
        .log-level-SUCCESS {{ color: #73c991; }}
        .log-level-ERROR, .log-level-CRITICAL {{ color: #f44747; }}
        .log-level-INFO {{ color: #569cd6; }}
        .status-grid {{ display: grid; grid-template-columns: 100px 1fr; gap: 5px; align-items: center;}}
        .status-grid strong {{ color: #9cdcfe; }}
        #entry-point-panel {{ display: none; text-align: center; padding: 1em; background-color: #2d2d2d; border: 1px solid #50fa7b; border-radius: 5px; }}
        #entry-point-button {{ display: inline-block; padding: 10px 20px; font-size: 1.2em; font-weight: bold; color: #1a1a1a; background-color: #50fa7b; border: none; border-radius: 5px; text-decoration: none; cursor: pointer; }}
    </style>
    <div class="container">
        <h1>🚀 鳳凰之心 - 狀態儀表板</h1>
        <div id="entry-point-panel">
             <a id="entry-point-button" href="#" target="_blank">進入主控台 (Swagger UI)</a>
        </div>
        <div class="grid">
            <div class="panel">
                <div class="title">📊 系統狀態</div>
                <div class="content status-grid">
                    <strong>後端階段:</strong> <span id="stage">等待中...</span>
                    <strong>CPU:</strong> <span id="cpu">-.--%</span>
                    <strong>RAM:</strong> <span id="ram">-.--%</span>
                </div>
            </div>
            <div class="panel">
                <div class="title">微服務狀態</div>
                <div class="content" id="apps-status">等待後端回報...</div>
            </div>
        </div>
        <div class="panel">
            <div class="title">📜 即時日誌</div>
            <div class="content log-container" id="log-container">等待日誌...</div>
        </div>
    </div>
    <script>
        const API_URL = 'http://localhost:8088/api/v1/status';

        function updateDashboard() {{
            fetch(API_URL)
                .then(response => {{
                    if (!response.ok) throw new Error('後端服務尚未就緒...');
                    return response.json();
                }})
                .then(data => {{
                    document.getElementById('stage').textContent = data.status.current_stage || 'N/A';
                    document.getElementById('cpu').textContent = `${{data.status.cpu_usage.toFixed(2)}}%`;
                    document.getElementById('ram').textContent = `${{data.status.ram_usage.toFixed(2)}}%`;

                    let appsHtml = '';
                    try {{
                        const apps = JSON.parse(data.status.apps_status);
                        appsHtml = Object.entries(apps).map(([name, status]) => `<div><strong>${{name}}:</strong> ${{status}}</div>`).join('');
                    }} catch (e) {{ appsHtml = '無法解析服務狀態'; }}
                    document.getElementById('apps-status').innerHTML = appsHtml;

                    const logContainer = document.getElementById('log-container');
                    let logsHtml = '';
                    if(data.logs && data.logs.length > 0) {{
                       logsHtml = data.logs.map(log => `<div class="log-entry log-level-${{log.level}}">[${{log.level}}] ${{log.message}}</div>`).join('');
                    }}
                    logContainer.innerHTML = logsHtml;
                    logContainer.scrollTop = logContainer.scrollHeight;

                    if(data.status.action_url) {{
                        document.getElementById('entry-point-panel').style.display = 'block';
                        document.getElementById('entry-point-button').href = data.status.action_url;
                    }}
                }})
                .catch(error => {{
                    document.getElementById('stage').textContent = error.message;
                }});
        }}

        setInterval(updateDashboard, {refresh_interval_ms});
        updateDashboard(); // Initial call
    </script>
    """

def main():
    """主執行函式。"""
    stop_event = threading.Event()

    try:
        # 清理輸出並顯示儀表板
        clear_output(wait=True)
        display(HTML(render_dashboard_html()))

        # 啟動背景工作執行緒
        worker_thread = threading.Thread(target=background_worker, args=(stop_event,), daemon=True)
        worker_thread.start()

        # 主執行緒等待，直到使用者手動中斷
        worker_thread.join()

    except KeyboardInterrupt:
        print("\n🛑 偵測到使用者手動中斷。正在通知後端服務關閉...")
        stop_event.set()
        # 給予一點時間讓背景程序結束
        time.sleep(2)
        print("✅ 前端程序已結束。")

if __name__ == "__main__":
    main()
