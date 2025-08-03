# -*- coding: utf-8 -*-
# 版本：V26 - 已為本地除錯修補 (並已整合為正式版本)
# 目的：作為一個精簡的後端啟動器，假設環境已由外部腳本設定完成。
import sys
import os
import subprocess
import argparse
import json
from datetime import datetime

def print_header(title):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*80}\n🚀 {timestamp} - {title}\n{'='*80}")

def main():
    parser = argparse.ArgumentParser(description="Phoenix Heart Backend Service Launcher (Patched)")
    parser.add_argument("--config", type=str, required=True, help="Path to the config.json file.")
    args = parser.parse_args()

    try:
        # 這個腳本現在假設它總是被正確的 Python 解譯器 (在 venv 中) 呼叫。
        print("✅ 後端啟動器：偵測到精簡模式，跳過 venv 建立與依賴安裝。")
        print_header("步驟 4: 啟動 FastAPI API 服務")

        server_env = os.environ.copy()
        # 我們需要傳入絕對路徑，因為 uvicorn 的工作目錄可能不同
        config_path = os.path.abspath(args.config)
        server_env["PHOENIX_CONFIG_PATH"] = config_path
        print(f"✅ 已將設定檔路徑加入環境變數: {server_env['PHOENIX_CONFIG_PATH']}")

        # 從設定檔讀取埠號
        port = "8088" # 保留一個預設值以防萬一
        print(f"正在從 {config_path} 讀取設定...")
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)

        port = str(config_data.get("system_settings", {}).get("api_port", port))
        print(f"✅ 取得 API 埠號: {port}")

        api_server_command = [
            sys.executable, # 直接使用當前的 Python 解譯器 (應為 .venv/bin/python)
            "-m", "uvicorn", "src.phoenix_core.main:app",
            "--host", "0.0.0.0", "--port", port,
        ]

        print(f"日誌：伺服器正在啟動... 指令: {' '.join(api_server_command)}")
        # 使用 execvpe 來用 uvicorn 程序取代當前的 python 程序
        # 這更乾淨，因為此腳本的任務到此已完成。
        os.execvpe(api_server_command[0], api_server_command, server_env)

    except Exception as e:
        print(f"\n❌ 發生未預期的錯誤: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
