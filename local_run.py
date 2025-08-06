# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║      🎯 local_run.py (V2.0 - Launcher & Watchdog)                    ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 目的: 作為一個自動化測試腳本，呼叫核心啟動器 `scripts/launch.py` ║
# ║           並使用看門狗驗證其是否成功啟動，然後自動關閉。             ║
# ║   - 核心: Subprocess, Watchdog, Report Generation                  ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import sys
import os
import subprocess
import time
import shutil
from datetime import datetime

# --- 全域設定 ---
LAUNCHER_SCRIPT = os.path.join("scripts", "launch.py")
WATCHDOG_TIMEOUT = 30  # 總超時時間 (秒)
HEARTBEAT_CHECK_INTERVAL = 1  # 心跳檢查間隔 (秒)
VENV_DIR = ".venv_gold"
VENV_PYTHON = os.path.join(VENV_DIR, "bin", "python")
VENV_UV = os.path.join(VENV_DIR, "bin", "uv")

def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def print_header(title):
    print("\n" + "="*80)
    print(f"🎯 {get_timestamp()} - {title}")
    print("="*80)

def run_sync_command(command, cwd=".", env=None):
    """執行一個同步命令並串流其輸出。"""
    print(f"   🔹 執行命令: {' '.join(command)} (於 {cwd})")
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding='utf-8', cwd=cwd, env=env
    )
    for line in process.stdout:
        print(f"     [OUTPUT] {line.strip()}")
    return_code = process.wait()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, command)
    print(f"   ✅ 命令成功完成。")

def main():
    start_time = time.time()
    server_process = None

    try:
        # --- 步驟 1: 呼叫核心啟動器 ---
        print_header(f"呼叫核心啟動器: {LAUNCHER_SCRIPT}")
        # 我們期望 launch.py 會自行處理 venv 的建立和重新啟動
        # 因此我們直接用系統的 python 執行它
        server_process = subprocess.Popen(
            [sys.executable, LAUNCHER_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8'
        )

        # --- 步驟 2: 看門狗監控 ---
        print_header("啟動看門狗以監控伺服器心跳")
        start_wait = time.monotonic()
        heartbeat_detected = False

        # 在等待心跳時，同時打印來自伺服器的日誌
        # 我們不能用 server_process.wait() 因為它會阻塞
        while time.monotonic() - start_wait < WATCHDOG_TIMEOUT:
            # 檢查心跳 (這裡我們簡化為檢查 state.db 的存在與更新)
            # 注意：一個更健壯的實作會實際查詢資料庫
            db_path = "storage/state.db"
            if os.path.exists(db_path):
                 # 這裡可以加入更複雜的檢查，例如讀取 status_updates 表
                print("   [看門狗] ✅ 偵測到心跳信號 (資料庫存在)!")
                heartbeat_detected = True
                break

            # 打印一行輸出 (如果有的話)
            try:
                line = server_process.stdout.readline()
                if line:
                    print(f"     [SERVER] {line.strip()}")
            except (IOError, ValueError):
                # 當子進程關閉時，readline 可能會出錯
                pass

            print(f"   [看門狗] ⚠️ 未找到心跳，將在 {HEARTBEAT_CHECK_INTERVAL} 秒後重試...")
            time.sleep(HEARTBEAT_CHECK_INTERVAL)

        if not heartbeat_detected:
            raise RuntimeError(f"看門狗超時！在 {WATCHDOG_TIMEOUT} 秒內未偵測到心跳。")

        # --- 步驟 3: 成功後，優雅地關閉伺服器 ---
        print_header("測試成功，正在終止伺服器")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
            print("✅ 伺服器已成功終止。")
        except subprocess.TimeoutExpired:
            print("⚠️ 伺服器終止超時，強制中斷。")
            server_process.kill()

        # --- 步驟 4: 執行報告生成器 ---
        print_header("執行報告生成器")
        # (這部分可以保持不變，或者也移到 launch.py 中作為一個可選步驟)
        db_original_path = "storage/state.db"
        db_renamed_path = "logs.sqlite"
        if os.path.exists(db_original_path):
            shutil.move(db_original_path, db_renamed_path)
            print(f"✅ 資料庫已重命名為 {db_renamed_path}")
        else:
            print(f"⚠️ 找不到資料庫檔案 {db_original_path}，無法生成報告。")
            open(db_renamed_path, 'a').close()

        # TODO: 這裡我們需要一個真正的報告生成腳本
        # report_generator_script = os.path.join("run", "report_cli.py")
        # ...

    except Exception as e:
        print(f"\n❌ local_run 執行期間發生錯誤: {e}", file=sys.stderr)
        if server_process and server_process.poll() is None:
            server_process.kill()
        sys.exit(1)
    finally:
        end_time = time.time()
        print("\n" + "="*80)
        print(f"🏁 local_run 流程結束，總耗時: {end_time - start_time:.2f} 秒。")
        print("="*80)

if __name__ == "__main__":
    main()
