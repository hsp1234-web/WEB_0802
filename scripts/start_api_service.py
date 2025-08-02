# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║      🚀 start_api_service.py (V26 - 可配置版)                      ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 作者: Jules (AI Software Engineer)                               ║
# ║   - 目的: 作為 Colab 環境的穩定後端啟動器。                        ║
# ║           負責建立 venv，安裝依賴，並根據傳入的設定檔啟動服務。      ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import sys
import os
import subprocess
import shutil
import argparse
from datetime import datetime

# --- 全域設定 ---
VENV_DIR = ".venv_colab_backend"
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
        stderr=subprocess.STDOUT,
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
    parser = argparse.ArgumentParser(description="Phoenix Heart Backend Service Launcher")
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to the config.json file."
    )
    args = parser.parse_args()

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    os.chdir(project_root)
    print(f"工作目錄已變更至: {os.getcwd()}")

    try:
        # --- 步驟 1: 建立或驗證 venv ---
        print_header("步驟 1: 建立/驗證後端專用虛擬環境")
        if not os.path.isdir(VENV_DIR):
            print(f"未發現虛擬環境，正在建立於 '{VENV_DIR}'...")
            run_command([sys.executable, "-m", "venv", VENV_DIR])
            print("✅ 虛擬環境建立成功。")
        else:
            print(f"✅ 虛擬環境 '{VENV_DIR}' 已存在。")

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

        # 將設定檔路徑設定為環境變數，讓 FastAPI 應用程式可以讀取
        server_env = os.environ.copy()
        server_env["PHOENIX_CONFIG_PATH"] = os.path.abspath(args.config)
        print(f"✅ 已將設定檔路徑加入環境變數: {server_env['PHOENIX_CONFIG_PATH']}")

        # 從設定檔讀取埠號，如果存在的話
        import json
        port = "8088" # 預設埠號
        try:
            with open(args.config, "r") as f:
                config_data = json.load(f)
                if "__test_port__" in config_data:
                    port = str(config_data["__test_port__"])
                    print(f"ℹ️ 在測試模式下，使用動態埠號: {port}")
        except Exception:
            pass # 忽略錯誤，使用預設埠號

        api_server_command = [
            VENV_PYTHON,
            "-m",
            "uvicorn",
            "src.phoenix_core.main:app", # 使用我們真正的 app
            "--host", "0.0.0.0",
            "--port", port,
        ]

        print("日誌：伺服器正在啟動... (由 colab_runner.py 管理生命週期)")
        process = subprocess.Popen(api_server_command, env=server_env)
        process.wait()

    except Exception as e:
        print(f"\n❌ 發生未預期的錯誤: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
