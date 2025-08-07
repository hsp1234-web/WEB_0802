import subprocess
import sys
import time
from pathlib import Path
from IPython.display import clear_output, display, HTML
import os

# --- 組態設定 ---
MANAGER_SCRIPT_PATH = Path("tools/manager_service.py")
LOG_FILE_PATH = Path("storage/dashboard.log")

def main():
    """
    Colab 儀表板運行的主進入點。
    """
    manager_process = None
    try:
        # 步驟 1: 在背景啟動管理器服務
        print("🚀 正在啟動後端服務管理器...")
        manager_process = subprocess.Popen(
            [sys.executable, str(MANAGER_SCRIPT_PATH)],
            stdout=sys.stdout, # 讓管理器在需要時可以打印自己的除錯輸出
            stderr=sys.stderr
        )
        print(f"✅ 服務管理器已在背景啟動 (PID: {manager_process.pid}).")
        time.sleep(2) # 給管理器一點時間啟動並建立日誌檔案

        # 步驟 2: 進入「朗讀者」循環
        while True:
            clear_output(wait=True)

            # 顯示標題
            display(HTML("<h1>鳳凰之心系統儀表板</h1>"))

            # 顯示 API 資訊
            api_url = "http://127.0.0.1:8000"
            display(HTML(f"""
                <div style="border: 1px solid #ccc; padding: 10px; border-radius: 5px; margin-bottom: 10px; background-color: #eef;">
                    <p><b>管理器 API 已上線</b></p>
                    <p>請使用以下端點上傳檔案以開始轉錄任務 (可使用 Postman 或 curl 等工具):</p>
                    <ul>
                        <li><b>上傳端點 (POST):</b> <code>{api_url}/api/v1/transcribe</code></li>
                        <li><b>互動式 API 文件 (Swagger UI):</b> <a href="{api_url}/docs" target="_blank">{api_url}/docs</a></li>
                    </ul>
                </div>
            """))

            log_content = ""
            if LOG_FILE_PATH.exists():
                with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
                    log_content = f.read()
            else:
                log_content = "⏳ 正在等待日誌檔案建立..."

            # 將日誌內容顯示在預格式化的區塊中，以獲得更好的可讀性
            # <pre> 標籤會保留空白和換行符
            display(HTML(f"<pre style='white-space: pre-wrap; word-wrap: break-word; background-color: #f4f4f4; border: 1px solid #ddd; padding: 10px; border-radius: 5px;'>{log_content}</pre>"))

            # 檢查管理器程序是否仍在運行。如果沒有，則跳出循環。
            if manager_process.poll() is not None:
                print("\n---")
                print("ℹ️ 後端服務管理器已停止運作。儀表板更新已停止。")
                break

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n\n🛑 收到使用者中斷指令，正在關閉系統...")
    except Exception as e:
        print(f"\n\n❌ 儀表板發生未預期的錯誤: {e}")
    finally:
        if manager_process and manager_process.poll() is None:
            print("🔪 正在終止後端服務管理器...")
            manager_process.terminate()
            try:
                manager_process.wait(timeout=5)
                print("✅ 服務管理器已成功終止。")
            except subprocess.TimeoutExpired:
                print("⚠️ 管理器在 5 秒內未回應終止信號，將強制終止。")
                manager_process.kill()
                print("✅ 服務管理器已被強制終止。")
        else:
            print("🏁 系統已關閉。")

if __name__ == "__main__":
    main()
