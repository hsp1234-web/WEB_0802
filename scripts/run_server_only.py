import subprocess
import os
import sys
import argparse
import json

# 使用 sys.executable 來確保我們用的是當前環境的 Python 直譯器
# 這比寫死的路徑更具可移植性
PYTHON_EXECUTABLE = sys.executable

def get_port_from_config(config_path: str) -> int:
    """從 JSON 設定檔中讀取埠號，如果失敗則返回預設值"""
    default_port = 8088
    if not config_path or not os.path.exists(config_path):
        return default_port

    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        # 測試案例使用 '__test_port__' 這個特殊的鍵來傳遞埠號
        return config_data.get('__test_port__', default_port)
    except (json.JSONDecodeError, KeyError):
        return default_port

def main():
    """
    僅負責啟動 Uvicorn 伺服器，不包含任何額外的安裝或設定邏輯。
    可以透過 --config 參數傳遞一個設定檔來動態設定埠號。
    """
    parser = argparse.ArgumentParser(description="輕量級 Uvicorn 伺服器啟動器")
    parser.add_argument('--config', type=str, help='設定檔的路徑', default=None)
    args = parser.parse_args()

    port = get_port_from_config(args.config)

    print(f"🚀 正在啟動輕量級 Uvicorn 伺服器於埠 {port}...")

    server_command = [
        PYTHON_EXECUTABLE,
        "-m",
        "uvicorn",
        "src.phoenix_core.main:app",  # 指向主應用程式實例
        "--host", "127.0.0.1",
        "--port", str(port),
        "--log-level", "info",
    ]

    try:
        print(f"   🔹 執行命令: {' '.join(server_command)}")
        subprocess.run(server_command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ 伺服器啟動失敗，返回碼: {e.returncode}")
    except KeyboardInterrupt:
        print("\n🛑 收到使用者中斷訊號，正在關閉伺服器...")
    finally:
        print("✅ 伺服器已關閉。")

if __name__ == "__main__":
    main()
