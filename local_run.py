# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║      🚀 local_run.py (V29 - Programmatic Uvicorn / Asyncio)          ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 作者: Jules (AI Software Engineer)                               ║
# ║   - 目的: 在任何乾淨的 Linux 環境下，全自動地完成專案的部署、      ║
# ║           執行和報告生成。此版本使用程式化方式控制 Uvicorn。       ║
# ║   - 核心: venv, uv, Programmatic Uvicorn, Asyncio Watchdog         ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import sys
import os

# 將 'src' 目錄添加到 Python 路徑中，以解決模組導入問題
# 這確保了即使在 venv 啟用前，腳本也能找到 'phoenix_core' 模組
sys.path.insert(0, os.path.abspath('src'))

import subprocess
import shutil
import asyncio
import time
from datetime import datetime

# --- 全域設定 (Global Settings) ---
VENV_DIR = ".venv_gold"
WATCHDOG_TIMEOUT = 20  # 看門狗總體超時時間 (秒)
HEARTBEAT_CHECK_INTERVAL = 1  # 心跳檢查間隔 (秒)

VENV_PYTHON = os.path.join(VENV_DIR, "bin", "python")
VENV_UV = os.path.join(VENV_DIR, "bin", "uv")
VENV_PIP = os.path.join(VENV_DIR, "bin", "pip")

def get_timestamp():
    """獲取當前時間戳，用於日誌。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def print_header(title):
    """打印帶有標題的日誌分隔線。"""
    print("\n" + "="*80)
    print(f"🚀 {get_timestamp()} - {title}")
    print("="*80)

def run_sync_command(command, cwd=".", env=None):
    """
    【同步版本】執行一個子程序命令，並即時串流其輸出。
    用於環境設定等同步任務。
    """
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

async def watchdog_and_closer(server: "uvicorn.Server") -> bool:
    """
    【Asyncio 原生看門狗】
    監控心跳，成功後或超時後關閉伺服器。
    返回 True 表示成功，False 表示超時。
    """
    start_time = time.monotonic()
    print_header(f"看門狗已啟動 (超時設定: {WATCHDOG_TIMEOUT} 秒)")

    # db_manager 是單例，在導入時已初始化，無需手動調用 initialize。
    from phoenix_core.database import db_manager
    from phoenix_core.watchdog import HEARTBEAT_KEY

    while time.monotonic() - start_time < WATCHDOG_TIMEOUT:
        print(f"   [看門狗] 正在檢查心跳...")
        try:
            # 使用 asyncio.to_thread 在異步事件循環中安全地調用阻塞的資料庫方法
            heartbeat_value = await asyncio.to_thread(db_manager.get_status, HEARTBEAT_KEY)
            if heartbeat_value:
                print(f"   [看門狗] ✅ 成功偵測到心跳！值: {heartbeat_value}")
                print("   [看門狗] 測試通過。等待 5 秒觀察期...")
                await asyncio.sleep(5)
                server.should_exit = True
                print("   [看門狗] 已發出關閉信號。")
                return True  # 成功
            else:
                print(f"   [看門狗] ⚠️ 未找到心跳值，將在 {HEARTBEAT_CHECK_INTERVAL} 秒後重試...")

        except Exception as e:
            print(f"   [看門狗] ❌ 檢查心跳時發生錯誤: {e}", file=sys.stderr)

        await asyncio.sleep(HEARTBEAT_CHECK_INTERVAL)

    # 如果循環結束仍未返回，說明超時
    print(f"   [看門狗] ❌ 超時！在 {WATCHDOG_TIMEOUT} 秒內未偵測到有效心跳。", file=sys.stderr)
    server.should_exit = True # 無論如何都嘗試關閉伺服器
    return False # 失敗

async def main_async():
    """
    【異步主函式】
    協調 Uvicorn 伺服器和看門狗的啟動與關閉。
    """
    # 將應用程式相關的導入放在這裡，確保它們在 venv 環境設定好之後才被執行
    import uvicorn
    from phoenix_core.main import app

    print_header("步驟 4: 以程式化方式啟動核心應用程式")

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info",
        lifespan="on"  # 確保 FastAPI 的 startup/shutdown 事件被觸發
    )
    server = uvicorn.Server(config)

    # 使用 asyncio.gather 來並發運行伺服器和看門狗
    # 我們只關心看門狗的返回結果
    server_task = asyncio.create_task(server.serve())
    watchdog_task = asyncio.create_task(watchdog_and_closer(server))

    done, pending = await asyncio.wait(
        [server_task, watchdog_task],
        return_when=asyncio.FIRST_COMPLETED
    )

    # 檢查看門狗的結果
    watchdog_result = False
    if watchdog_task in done:
        watchdog_result = watchdog_task.result()

    # 取消仍在運行的任務
    for task in pending:
        task.cancel()

    # 重新 gather 以確保取消操作完成
    await asyncio.gather(*pending, return_exceptions=True)

    if not watchdog_result:
        raise RuntimeError("看門狗超時，測試失敗。")

    print("✅ 伺服器已優雅地關閉。")

def main():
    """
    主執行函式，協調所有同步和異步步驟。
    """
    start_time = time.time()
    os.environ["PYTHONUNBUFFERED"] = "1"

    try:
        # 檢查是否已在 venv 中執行
        if os.environ.get("_IN_VENV") == "1":
            # --- 我們已經在 venv 中 ---
            # 步驟 4 & 6: 執行核心異步邏輯
            asyncio.run(main_async())
            print("✅ 核心應用程式測試運行已完成。")

            # 步驟 7: 執行報告生成器
            print_header("步驟 7: 執行報告生成器")
            db_original_path = "state.db"
            db_renamed_path = "logs.sqlite"
            if os.path.exists(db_original_path):
                shutil.move(db_original_path, db_renamed_path)
                print(f"✅ 資料庫已重命名為 {db_renamed_path}")
            else:
                print(f"⚠️ 找不到資料庫檔案 {db_original_path}，無法生成報告。")
                open(db_renamed_path, 'a').close()

            report_generator_script = os.path.join("scripts", "generate_report.py")
            if os.path.exists(report_generator_script):
                requirements_report_file = "requirements/report.txt"
                if os.path.exists(requirements_report_file):
                     print("\\n--- 安裝報告依賴 ---")
                     run_sync_command([VENV_UV, "pip", "install", "--python", VENV_PYTHON, "-r", requirements_report_file], cwd=".")

                report_command = [
                    VENV_PYTHON, report_generator_script,
                    "--db-file", db_renamed_path,
                    "--report-dir", "reports",
                ]
                run_sync_command(report_command, cwd=".")
                print("✅ 報告生成完畢。")

        else:
            # --- 首次執行：設定環境並重新啟動 ---
            print_header("步驟 1: 建立 Python 虛擬環境 (venv)")
            if os.path.isdir(VENV_DIR):
                shutil.rmtree(VENV_DIR)
            run_sync_command([sys.executable, "-m", "venv", VENV_DIR])

            print_header("步驟 2: 在 venv 中安裝 uv")
            run_sync_command([VENV_PIP, "install", "-U", "uv"])

            print_header("步驟 3: 將當前專案套件化安裝到 venv 中")
            run_sync_command([VENV_PIP, "install", "-e", "."], cwd=".")

            print_header("步驟 5: 在 venv 中安裝專案依賴")
            run_sync_command([VENV_UV, "pip", "install", "--python", VENV_PYTHON, "-r", "requirements/base.txt"], cwd=".")

            print_header("重新啟動腳本以在 venv 中執行")
            env = os.environ.copy()
            env["_IN_VENV"] = "1"

            args = [VENV_PYTHON, __file__] + sys.argv[1:]
            os.execve(args[0], args, env)

    except subprocess.CalledProcessError as e:
        print(f"\n❌ 一個關鍵命令執行失敗，返回碼: {e.returncode}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 發生未預期的錯誤: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        end_time = time.time()
        print("\n" + "="*80)
        print(f"🏁 全部流程結束，總耗時: {end_time - start_time:.2f} 秒。")
        print("="*80)

if __name__ == "__main__":
    main()
