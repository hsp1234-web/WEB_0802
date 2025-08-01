# 檔案: run/colab_runner.py
# 說明: 前端戰情室，純粹作為後端服務的狀態顯示器。

import sqlite3
import time
import os
from pathlib import Path
from IPython.display import display, HTML, clear_output

DB_PATH = Path("state.db")
LOG_PATH = Path("uvicorn.log")
# 注意：此腳本不應包含任何啟動後端的邏輯。
# 它假設 `scripts/launch.py` 正在另一個進程中獨立運行。

def read_status_from_db(db_path):
    """以唯讀模式從資料庫安全地讀取狀態。"""
    if not db_path.exists():
        return "等待後端服務建立資料庫..."

    try:
        # 使用 URI 進行唯讀連接，增加穩定性
        db_uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(db_uri, uri=True)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM status WHERE key = 'current_status'")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else "狀態尚未寫入..."
    except sqlite3.OperationalError as e:
        # 處理資料庫被鎖定等並發問題
        return f"讀取資料庫時發生錯誤: {e}"
    except Exception as e:
        return f"發生未預期的錯誤: {e}"

def tail_log(log_path, lines=20):
    """讀取日誌檔案的最後 N 行。"""
    if not log_path.exists():
        return "等待日誌檔案建立..."

    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            # 這是一個簡單的 tail 實現，對於大檔案可能效率不高
            # 但對於 Colab 顯示已經足夠
            content = f.readlines()
            return "".join(content[-lines:])
    except Exception as e:
        return f"讀取日誌時發生錯誤: {e}"

def render_html_dashboard(current_status, latest_logs):
    """根據傳入的數據渲染 HTML 儀表板。"""
    # 將日誌中的換行符和 HTML 特殊字元轉換
    logs_html = latest_logs.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')

    html = f"""
    <div style="font-family: 'Fira Code', monospace; background-color: #282a36; color: #f8f8f2; padding: 20px; border-radius: 8px; border: 1px solid #44475a;">
        <h2 style="color: #50fa7b; border-bottom: 1px solid #44475a; padding-bottom: 10px;">🚀 鳳凰之心 - 前端戰情室</h2>
        <p style="margin-top: 20px;">
            <strong>後端服務狀態:</strong>
            <span style="background-color: #44475a; color: #8be9fd; padding: 5px 10px; border-radius: 5px;">{current_status}</span>
        </p>
        <h4 style="margin-top: 20px; color: #ff79c6;">即時日誌 (最後 20 行):</h4>
        <div style="height: 400px; overflow-y: auto; background-color: #21222c; padding: 15px; border-radius: 5px; white-space: pre-wrap; word-wrap: break-word;">
            {logs_html}
        </div>
        <p style="font-size: 0.8em; color: #6272a4; margin-top: 15px;">儀表板每 2 秒自動刷新。按 Ctrl+C 或儲存格停止按鈕來關閉。</p>
    </div>
    """
    return html

def main():
    """主執行函數，持續輪詢並刷新儀表板。"""
    try:
        print("正在啟動前端戰情室...")
        print(f"將會監控資料庫 '{DB_PATH}' 和日誌 '{LOG_PATH}'。")
        print("請確保 `scripts/launch.py` 已在另一個終端或進程中啟動。")
        time.sleep(2)

        while True:
            clear_output(wait=True)
            current_status = read_status_from_db(DB_PATH)
            latest_logs = tail_log(LOG_PATH)

            dashboard = render_html_dashboard(current_status, latest_logs)
            display(HTML(dashboard))

            time.sleep(2)

    except KeyboardInterrupt:
        print("\n🛑 戰情室已被使用者手動關閉。")

if __name__ == "__main__":
    main()
