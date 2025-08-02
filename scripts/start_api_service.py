# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║      🚀 start_api_service.py                                         ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 作者: Jules (AI Software Engineer)                               ║
# ║   - 目的: 作為 Colab 環境的穩定後端啟動器。                        ║
# ║           負責建立一個隔離的 venv，安裝依賴，並啟動 FastAPI 服務。 ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import sys
import os
import subprocess
import shutil
from datetime import datetime

# --- 全域設定 ---
VENV_DIR = ".venv_colab_backend" # 使用一個專用的 venv 名稱
VENV_PYTHON = os.path.join(VENV_DIR, "bin", "python")
VENV_PIP = os.path.join(VENV_DIR, "bin", "pip")

def print_header(title):
    """打印帶有標題的日誌分隔線。"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*80}\n🚀 {timestamp} - {title}\n{'='*80}")

def run_command(command, cwd=".", env=None):
    """執行命令並串流輸出。"""
    print(f"   🔹 執行命令: {' '.join(command)}")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, # 將 stderr 合併到 stdout
        text=True,
        encoding='utf-8',
        cwd=cwd,
        env=env
    )
    for line in process.stdout:
        print(f"     [LOG] {line.strip()}")

    return_code = process.wait()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, command)
    print(f"   ✅ 命令成功完成。")

def main():
    """主執行函式。"""
    # 確保我們在專案的根目錄下執行
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    os.chdir(project_root)
    print(f"工作目錄已變更至: {os.getcwd()}")

    try:
        # --- 步驟 1: 建立 venv ---
        print_header("步驟 1: 建立後端專用虛擬環境")
        if os.path.isdir(VENV_DIR):
            print(f"發現舊的虛擬環境 '{VENV_DIR}'，正在刪除...")
            shutil.rmtree(VENV_DIR)
        run_command([sys.executable, "-m", "venv", VENV_DIR])
        print("✅ 虛擬環境建立成功。")
        # 將 venv 加入 .gitignore
        with open(".gitignore", "a+") as f:
            f.seek(0)
            if VENV_DIR not in f.read():
                f.write(f"\n\n# Colab 後端專用 venv\n{VENV_DIR}/\n")
                print(f"✅ 已將 '{VENV_DIR}/' 加入 .gitignore。")


        # --- 步驟 2: 安裝依賴 ---
        print_header("步驟 2: 安裝核心依賴")
        requirements_path = os.path.join("requirements", "base.txt")
        run_command([VENV_PIP, "install", "-r", requirements_path])
        print("✅ 核心依賴安裝成功。")

        # --- 步驟 3: 將專案以可編輯模式安裝 ---
        print_header("步驟 3: 將專案以可編輯模式安裝")
        run_command([VENV_PIP, "install", "-e", "."])
        print("✅ 專案安裝成功。")

        # --- 步驟 4: 啟動 FastAPI 伺服器 ---
        print_header("步驟 4: 啟動 FastAPI API 服務")
        print("日誌：伺服器正在啟動... (可透過 Ctrl+C 終止)")
        # 我們將直接執行 uvicorn，讓它在前台運行
        # colab_runner.py 會在背景處理這個程序的生命週期
        api_server_command = [
            VENV_PYTHON,
            "-m",
            "uvicorn",
            "src.phoenix_core.api.server:app", # 假設的 API app 路徑
            "--host", "0.0.0.0",
            "--port", "8088", # Colab runner 預期的端口
        ]

        # 在啟動前，我們需要先創建 API 伺服器檔案
        # 這部分是根據我們之前討論的理想架構
        api_server_path = os.path.join("src", "phoenix_core", "api", "server.py")
        os.makedirs(os.path.dirname(api_server_path), exist_ok=True)
        with open(api_server_path, "w", encoding="utf-8") as f:
            f.write("""
from fastapi import FastAPI
app = FastAPI(title="Phoenix Core API")

@app.get("/api/v1/status", tags=["Status"])
async def get_status():
    \"\"\"回傳當前的系統狀態。 (模擬)\"\"\"
    return {
        "status": {
            "current_stage": "服務運行中",
            "cpu_usage": 12.5,
            "ram_usage": 55.8,
            "apps_status": '{"dataprovider": "running", "system_monitor": "running"}'
        },
        "logs": [
            {"timestamp": "2025-08-02T10:30:00Z", "level": "INFO", "message": "API 服務已啟動"},
            {"timestamp": "2025-08-02T10:30:05Z", "level": "SUCCESS", "message": "資料提供者模組正常運行"}
        ],
        "action_url": "http://localhost:8088/docs" # 提供 swagger UI
    }
""")
        print(f"✅ 已創建模擬的 API 伺服器檔案於: {api_server_path}")

        # 使用 Popen 以便主程序可以繼續（雖然在此腳本中是最後一步）
        # 但在真實場景中，這允許父進程（colab_runner）不被阻塞
        process = subprocess.Popen(api_server_command)
        process.wait() # 等待服務器進程結束

    except subprocess.CalledProcessError as e:
        print(f"\n❌ 一個關鍵命令執行失敗，返回碼: {e.returncode}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nℹ️ 偵測到使用者中斷，正在關閉服務...")
    except Exception as e:
        print(f"\n❌ 發生未預期的錯誤: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
