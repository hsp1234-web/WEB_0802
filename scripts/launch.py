# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║      🚀 鳳凰之心 - 核心啟動器 (Core Launcher) V1.1 (含探針)        ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - V1.1: 新增環境探針，用於在啟動時打印詳細的除錯資訊。           ║
# ║   - V1.0: 初始版本，統一環境設定與應用程式啟動。                   ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import sys
import os
import subprocess
import shutil
import asyncio
import time
import platform
from datetime import datetime

def print_header(title, char="=", length=80):
    """打印帶有標題的日誌分隔線。"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + char * length)
    print(f"🚀 {timestamp} - {title}")
    print(char * length)

def probe_environment():
    """收集並打印關鍵的環境資訊。"""
    print_header("環境探針 (Environment Probe)", char="-")

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    print(f"  - 啟動器版本: V1.1")
    print(f"  - Python 版本: {sys.version.splitlines()[0]}")
    print(f"  - Python 解釋器路徑: {sys.executable}")
    print(f"  - 作業系統: {platform.platform()}")
    print(f"  - 核心架構: {platform.machine()}")
    print(f"  - 當前工作目錄: {os.getcwd()}")
    print(f"  - 腳本絕對路徑: {os.path.abspath(__file__)}")
    print(f"  - 推斷的專案根目錄: {project_root}")

    try:
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True, check=True)
        print(f"  - uv 版本: {result.stdout.strip()}")
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        print(f"  - uv 版本: ⚠️ 未安裝或無法執行 ({e})")

    print("-" * 80)


def run_sync_command(command, cwd=".", env=None):
    """執行一個同步命令並串流其輸出。"""
    print(f"   🔹 執行命令: {' '.join(command)} (於 {cwd})")
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
        print(f"     [OUTPUT] {line.strip()}")
    return_code = process.wait()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, command)
    print(f"   ✅ 命令成功完成。")

async def run_async_server(host="0.0.0.0", port=8080):
    """以異步方式啟動 Uvicorn 伺服器。"""
    try:
        import uvicorn
        from phoenix_core.main import app

        print_header(f"步驟 5: 啟動核心應用程式於 {host}:{port}")

        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info",
            lifespan="on"
        )
        server = uvicorn.Server(config)
        await server.serve()
        print("✅ 伺服器已優雅地關閉。")
    except asyncio.CancelledError:
        print("ℹ️ 伺服器任務被取消，正在關閉。")
    except Exception as e:
        print(f"❌ 伺服器運行時發生錯誤: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    """主執行函式。"""
    start_time = time.time()

    # --- 在任何操作前，先執行環境探針 ---
    probe_environment()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(project_root, 'src'))

    VENV_DIR = os.path.join(project_root, ".venv_gold")
    VENV_PYTHON = os.path.join(VENV_DIR, "bin", "python")
    VENV_PIP = os.path.join(VENV_DIR, "bin", "pip")

    if os.environ.get("_IN_VENV") == "1":
        asyncio.run(run_async_server())
    else:
        try:
            try:
                subprocess.run(["uv", "--version"], check=True, capture_output=True, text=True)
            except (FileNotFoundError, subprocess.CalledProcessError):
                print_header("核心工具 uv 未安裝")
                run_sync_command([sys.executable, "-m", "pip", "install", "-U", "uv"])

            print_header("步驟 1: 使用 uv 建立 Python 虛擬環境")
            if os.path.isdir(VENV_DIR):
                shutil.rmtree(VENV_DIR)
            run_sync_command(["uv", "venv", "-p", sys.executable, VENV_DIR])

            print_header("步驟 2: 引導程序 (Bootstrap) - 確保 Pip 和 Wheel 存在")
            run_sync_command(["uv", "pip", "install", "--python", VENV_PYTHON, "-U", "pip", "wheel"])

            print_header("步驟 3: 將當前專案套件化安裝到 venv 中")
            run_sync_command([VENV_PIP, "install", "-e", "."], cwd=project_root)

            print_header("步驟 4: 安裝專案依賴")
            run_sync_command(["uv", "pip", "install", "--python", VENV_PYTHON, "-r", os.path.join(project_root, "requirements/base.txt")], cwd=project_root)

            print_header("步驟 4.5: 打印已安裝套件列表 (用於除錯)")
            run_sync_command(["uv", "pip", "list", "--python", VENV_PYTHON], cwd=project_root)

            print_header("重新啟動腳本以在 venv 中執行")
            env = os.environ.copy()
            env["_IN_VENV"] = "1"

            args = [VENV_PYTHON, __file__] + sys.argv[1:]
            os.execve(args[0], args, env)

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"\n❌ 環境設定失敗: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ 發生未預期的錯誤: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)

    end_time = time.time()
    print("\n" + "="*80)
    print(f"🏁 核心啟動器流程結束，總耗時: {end_time - start_time:.2f} 秒。")
    print("="*80)

if __name__ == "__main__":
    main()
