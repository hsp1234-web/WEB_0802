# tools/local_launch_tester.py
import subprocess
import os
import sys
import time
import threading

# --- 設定 ---
API_PORT = 8088
SERVER_READY_TIMEOUT = 20  # 秒
LOG_PREFIX = "[啟動測試器]"
SUCCESS_MESSAGE = "Uvicorn running on"

def main():
    """
    一個獨立的、安全的腳本，用於測試核心伺服器啟動邏輯。
    它假設所有依賴都已安裝，且程式碼位於正確的位置。
    """
    print(f"{LOG_PREFIX} 開始本地啟動測試...")
    server_process = None

    # 取得專案根目錄 (此腳本位於 project_root/tools/，所以根目錄是上一層)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(f"{LOG_PREFIX} 專案根目錄: {project_root}")

    # 設定子進程的環境變數
    process_env = os.environ.copy()
    src_path = os.path.join(project_root, "src")

    # 將 PYTHONUNBUFFERED 設為 "1" 以禁用輸出緩衝
    # 將 PYTHONPATH 設為 src 目錄以解決模組導入問題
    process_env.update({
        "PYTHONUNBUFFERED": "1",
        "PYTHONPATH": str(src_path)
    })

    print(f"{LOG_PREFIX} 設定子進程 PYTHONPATH: {src_path}")

    # 建立啟動指令
    # 使用 sys.executable 確保我們用的是執行此腳本的同一個 Python 直譯器
    launcher_script = os.path.join(project_root, "scripts", "run_server_only.py")
    command = [
        sys.executable,
        launcher_script,
        "--port",
        str(API_PORT)
    ]

    print(f"{LOG_PREFIX} 準備執行命令: {' '.join(command)}")

    server_ready_event = threading.Event()

    try:
        print(f"\n{LOG_PREFIX} 正在啟動子進程...")
        server_process = subprocess.Popen(
            command,
            cwd=project_root,
            env=process_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
        )

        print(f"{LOG_PREFIX} 子進程已啟動 (PID: {server_process.pid})。等待伺服器就緒...")

        # 使用一個內部函數來讀取流，以便我們可以設定超時
        def read_output():
            for line in iter(server_process.stdout.readline, ''):
                if not line:
                    break
                print(f"[伺服器日誌] {line.strip()}")
                if SUCCESS_MESSAGE in line:
                    server_ready_event.set()
                    break # 成功後即可退出監控迴圈

        reader_thread = threading.Thread(target=read_output)
        reader_thread.daemon = True
        reader_thread.start()

        # 等待成功事件，或直到超時
        if server_ready_event.wait(timeout=SERVER_READY_TIMEOUT):
            print(f"\n{LOG_PREFIX} ✅ 偵測到成功訊息！伺服器已就緒。")
            print(f"\n{LOG_PREFIX} 測試成功！伺服器能夠在無環境設定的情況下啟動。")
        else:
            print(f"\n{LOG_PREFIX} ❌ 錯誤：伺服器在 {SERVER_READY_TIMEOUT} 秒內未能就緒。")
            # 超時後，主執行緒繼續，最終會進入 finally 區塊來清理
            sys.exit(1)

    except FileNotFoundError:
        print(f"{LOG_PREFIX} ❌ 錯誤：找不到命令或腳本: {' '.join(command)}")
        sys.exit(1)
    except Exception as e:
        print(f"{LOG_PREFIX} ❌ 發生未預期的錯誤: {e}")
        sys.exit(1)
    finally:
        if server_process and server_process.poll() is None:
            print(f"\n{LOG_PREFIX} 正在清理，終止子進程 (PID: {server_process.pid})...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"{LOG_PREFIX} 終止失敗，強制終止...")
                server_process.kill()
            print(f"{LOG_PREFIX} 子進程已停止。")

if __name__ == "__main__":
    main()
