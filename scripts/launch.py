# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║         🚀 鳳凰之心 - 核心啟動器 (Core Launcher) V1.0              ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 目的: 作為一個單一、可靠的進入點，負責專案的環境設定、         ║
# ║           依賴安裝和應用程式啟動。                                 ║
# ║   - 設計: 此腳本被設計為可被其他腳本 (如 local_run.py 或          ║
# ║           colab_runner.py) 呼叫，以確保環境一致性。                ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import sys
import os
import subprocess
import shutil
import asyncio
import time
from datetime import datetime

def print_header(title):
    """打印帶有標題的日誌分隔線。"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "="*80)
    print(f"🚀 {timestamp} - {title}")
    print("="*80)

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
        # 將導入放在這裡，確保我們在 venv 環境中
        import uvicorn
        from phoenix_core.main import app

        print_header(f"步驟 4: 啟動核心應用程式於 {host}:{port}")

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
    # 將 src 目錄加入 sys.path
    sys.path.insert(0, os.path.abspath('src'))

    # --- 全域設定 ---
    VENV_DIR = ".venv_gold"
    VENV_PYTHON = os.path.join(VENV_DIR, "bin", "python")
    VENV_UV = os.path.join(VENV_DIR, "bin", "uv")
    VENV_PIP = os.path.join(VENV_DIR, "bin", "pip")

    # --- 檢查是否已在 venv 中 ---
    if os.environ.get("_IN_VENV") == "1":
        # --- 在 venv 中：直接啟動伺服器 ---
        # TODO: 從 argparse 解析 host 和 port
        asyncio.run(run_async_server())
    else:
        # --- 不在 venv 中：設定環境並重新啟動 ---
        try:
            print_header("步驟 1: 建立 Python 虛擬環境 (venv)")
            if os.path.isdir(VENV_DIR):
                shutil.rmtree(VENV_DIR)
            run_sync_command([sys.executable, "-m", "venv", VENV_DIR])

            print_header("步驟 2: 在 venv 中安裝 uv")
            run_sync_command([VENV_PIP, "install", "-U", "uv"])

            print_header("步驟 3: 將當前專案套件化安裝到 venv 中")
            run_sync_command([VENV_PIP, "install", "-e", "."], cwd=".")

            print_header("步驟 3.5: 安裝專案依賴")
            # 注意：這裡我們將使用 base.txt 作為統一的依賴來源
            run_sync_command([VENV_UV, "pip", "install", "--python", VENV_PYTHON, "-r", "requirements/base.txt"], cwd=".")

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
