# -*- coding: utf-8 -*-
# 檔案: scripts/supervisor.py
# 說明: 中央監督者腳本，負責啟動、監控和管理所有後端微核心元件。

import sys
import subprocess
import time
from pathlib import Path
import os

# 確保我們在專案根目錄下執行，以便路徑解析正確
project_root = Path(__file__).resolve().parents[1]
logs_dir = project_root / "logs"

# 建立日誌目錄 (如果不存在)
os.makedirs(logs_dir, exist_ok=True)

# 為每個子進程開啟使用 UTF-8 編碼的日誌檔案
log_files = {
    "API Server": open(logs_dir / "api_server.log", "w", encoding="utf-8"),
    "Heartbeat Worker": open(logs_dir / "heartbeat_worker.log", "w", encoding="utf-8")
}


def launch_process(command, name, log_file):
    """
    啟動一個子進程並返回其處理程序物件。
    將子進程的 stdout 和 stderr 導向到指定的日誌檔案。
    """
    print(f"[Supervisor] 正在啟動 {name} (日誌位於: {log_file.name})...")
    # 使用 Popen 進行非阻塞啟動
    process = subprocess.Popen(
        command,
        stdout=log_file,
        stderr=log_file,
        cwd=project_root  # 確保子進程在正確的工作目錄下執行
    )
    print(f"[Supervisor] {name} 已啟動，PID: {process.pid}")
    return process

def main():
    """
    主函數，啟動並監控所有子進程。
    """
    print("[Supervisor] 中央監督者已啟動。")

    processes = {}

    # 定義要啟動的元件
    # 使用 sys.executable 確保我們用的是同一個 Python 直譯器
    # 使用 'python' 而不是 sys.executable，以依賴 PATH 環境變數，
    # 這在虛擬環境中通常更可靠。
    python_executable = "python"

    components = {
        "API Server": [
            python_executable,
            "-m", "uvicorn",
            "src.phoenix_core.main:app",
            "--host", "0.0.0.0",
            "--port", "8080"
        ],
        "Heartbeat Worker": [
            python_executable,
            str(project_root / "scripts" / "heartbeat_worker.py")
        ]
    }

    try:
        # 啟動所有元件
        for name, command in components.items():
            log_file = log_files[name]
            processes[name] = launch_process(command, name, log_file)
            time.sleep(1) # 短暫延遲，避免啟動時資源競爭

        # 監控迴圈
        while True:
            for name, process in processes.items():
                return_code = process.poll()
                if return_code is not None:
                    print(f"[Supervisor] 偵測到元件 '{name}' 已終止，返回碼: {return_code}。正在關閉所有服務...", file=sys.stderr)
                    # 如果任何一個元件掛了，就終止所有元件
                    raise KeyboardInterrupt # 觸發 finally 區塊來進行清理

            time.sleep(5) # 每 5 秒檢查一次狀態

    except KeyboardInterrupt:
        print("\n[Supervisor] 收到關閉訊號 (KeyboardInterrupt)。正在優雅地關閉所有子進程...")
    except Exception as e:
        print(f"\n[Supervisor] 發生未預期的錯誤: {e}。正在關閉所有子進程...", file=sys.stderr)
    finally:
        # 1. 關閉子進程
        for name, process in reversed(list(processes.items())):
            if process.poll() is None: # 如果進程還在運行
                print(f"[Supervisor] 正在終止 {name} (PID: {process.pid})...")
                process.terminate() # 發送 SIGTERM

        # 2. 等待所有進程終止
        for name, process in processes.items():
            try:
                process.wait(timeout=5)
                print(f"[Supervisor] {name} 已成功終止。")
            except subprocess.TimeoutExpired:
                print(f"[Supervisor] {name} 在 5 秒內未終止，強制終止 (kill)...", file=sys.stderr)
                process.kill() # 發送 SIGKILL

        # 3. 關閉所有日誌檔案
        for name, f in log_files.items():
            try:
                f.close()
                print(f"[Supervisor] 日誌檔案 for {name} 已關閉。")
            except Exception as e:
                print(f"[Supervisor] 關閉日誌檔案 for {name} 時發生錯誤: {e}", file=sys.stderr)


        print("[Supervisor] 所有服務已關閉。再見。")

if __name__ == "__main__":
    main()
