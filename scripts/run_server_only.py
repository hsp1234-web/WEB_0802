import subprocess
import os

# 根據「環境隔離原則」，使用絕對路徑指向虛擬環境中的 Python 解譯器
VENV_PYTHON = ".venv/bin/python"

def main():
    """
    僅負責啟動 Uvicorn 伺服器，不包含任何額外的安裝或設定邏輯。
    """
    print("🚀 正在啟動輕量級 Uvicorn 伺服器...")

    # 根據任務 3.2 的要求，伺服器需在 8088 埠上運行
    server_command = [
        VENV_PYTHON,
        "-m",
        "uvicorn",
        "src.phoenix_core.main:app",  # 指向主應用程式實例
        "--host", "127.0.0.1",
        "--port", "8088",
        "--log-level", "info",
    ]

    try:
        print(f"   🔹 執行命令: {' '.join(server_command)}")
        # 使用 subprocess.run 來執行，它會等待命令完成
        # 這使得此腳本的行為很單純：執行它，伺服器就運行；終止它，伺服器就停止。
        subprocess.run(server_command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ 伺服器啟動失敗，返回碼: {e.returncode}")
    except KeyboardInterrupt:
        print("\n🛑 收到使用者中斷訊號，正在關閉伺服器...")
    finally:
        print("✅ 伺服器已關閉。")

if __name__ == "__main__":
    main()
