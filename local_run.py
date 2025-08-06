# -*- coding: utf-8 -*-
# 檔案: local_run.py (V6.0 - 鳳凰守護神模式)
# 說明: 作為外部看門狗，啟動並監控 `run.sh` 監督者。
#       它不信任監督者內部的邏輯，只透過監聽檔案系統上的
#       心跳信號來判斷系統是否存活。

import sys
import subprocess
import os
import signal
from pathlib import Path
import time
import sys
import threading

# --- 設定 ---
MAX_HEARTBEAT_SILENCE = 15  # 監督者心跳最長靜默時間 (秒)
INITIAL_GRACE_PERIOD = 20 # 啟動初期給予的寬限時間 (秒)
HEARTBEAT_CHECK_INTERVAL = 2 # 檢查心跳的間隔時間 (秒)
ABSOLUTE_MAX_RUNTIME = 60 # 整個程式最長運作時間 (秒)

def absolute_timeout_handler(process_to_kill):
    """
    最終防線。當絕對超時到達時由定時器觸發。
    """
    print("="*80, file=sys.stderr)
    print(f"🚨 絕對超時！程式已運行超過 {ABSOLUTE_MAX_RUNTIME} 秒。", file=sys.stderr)
    print("   - 這可能是由於未預期的掛起或死結。", file=sys.stderr)
    print("   - 正在強制終結所有相關進程...", file=sys.stderr)
    print("="*80, file=sys.stderr)
    if process_to_kill:
        kill_process_group(process_to_kill)
    # 使用 os._exit 強制退出，因為 sys.exit() 可能會被 try/except 捕捉
    os._exit(1)

def phoenix_guardian(process_container):
    """
    鳳凰守護神的主函數。
    啟動 run.sh，然後變成一個無情的看門狗，監聽其心跳。
    """
    project_root = Path(__file__).resolve().parent
    run_script = project_root / "run.sh"
    heartbeat_file = project_root / "logs/supervisor_heartbeat.log"

    if not run_script.exists():
        print(f"❌ 致命錯誤：找不到監督者腳本: {run_script}", file=sys.stderr)
        sys.exit(1)

    # 清理舊的心跳記錄，避免使用過時的檔案
    if heartbeat_file.exists():
        heartbeat_file.unlink()

    print("="*80)
    print("🔥 鳳凰守護神已啟動 🔥")
    print(f"   - 監控對象: {run_script}")
    print(f"   - 心跳檔案: {heartbeat_file}")
    print(f"   - 最大靜默時間: {MAX_HEARTBEAT_SILENCE} 秒")
    print("="*80)

    # 使用 os.setsid (在 Unix-like 系統上) 來建立一個新的進程組。
    # 這使得我們可以殺死 run.sh 和它啟動的所有子進程，無一能逃。
    preexec_fn = os.setsid if os.name != 'nt' else None

    try:
        process = subprocess.Popen(
            [str(run_script)],
            cwd=project_root,
            preexec_fn=preexec_fn
        )
        process_container.append(process)
    except Exception as e:
        print(f"❌ 致命錯誤：無法啟動監督者 'run.sh': {e}", file=sys.stderr)
        sys.exit(1)


    print(f"⏳ 監督者已啟動 (PID: {process.pid})。進入 {INITIAL_GRACE_PERIOD} 秒寬限期...")
    time.sleep(INITIAL_GRACE_PERIOD)
    print("✅ 寬限期結束，開始監聽心跳...")

    while True:
        # 檢查監督者進程是否已經自行退出
        if process.poll() is not None:
            return_code = process.returncode
            if return_code == 0:
                print("✅ 監督者已自行正常關閉。守護神任務完成。")
            else:
                print(f"⚠️ 監督者回報錯誤並已關閉 (返回碼: {return_code})。守護神任務結束。", file=sys.stderr)
            sys.exit(return_code)

        # 檢查心跳檔案是否存在
        if not heartbeat_file.exists():
            print(f"🚨 看門狗觸發！心跳檔案遺失。假定監督者已崩潰。", file=sys.stderr)
            kill_process_group(process)
            sys.exit(1)

        # 檢查心跳是否過期
        try:
            last_modified = heartbeat_file.stat().st_mtime
            time_since_last_beat = time.time() - last_modified

            if time_since_last_beat > MAX_HEARTBEAT_SILENCE:
                print(f"🚨 看門狗觸發！監督者心跳已停止超過 {MAX_HEARTBEAT_SILENCE} 秒。", file=sys.stderr)
                print("   - 最後心跳時間: " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_modified)), file=sys.stderr)
                print("   - 當前時間:     " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())), file=sys.stderr)
                kill_process_group(process)
                sys.exit(1)
            else:
                pass

        except FileNotFoundError:
            print(f"🚨 看門狗觸發！心跳檔案在檢查期間消失。", file=sys.stderr)
            kill_process_group(process)
            sys.exit(1)

        time.sleep(HEARTBEAT_CHECK_INTERVAL)

def kill_process_group(process):
    """
    使用 os.killpg 終結整個進程組。
    """
    if os.name != 'nt' and process:
        try:
            pgid = os.getpgid(process.pid)
            print(f"   - 正在終結進程組 PGID: {pgid}", file=sys.stderr)
            os.killpg(pgid, signal.SIGKILL)
            print("   - 已發送 SIGKILL 信號。", file=sys.stderr)
        except ProcessLookupError:
            print("   - 警告：嘗試終結時，進程組已不存在。", file=sys.stderr)
        except Exception as e:
            print(f"   - 錯誤：終結進程組時發生意外：{e}", file=sys.stderr)
    elif process:
        print("   - 正在終結主進程 (Windows)", file=sys.stderr)
        process.kill()

if __name__ == "__main__":
    process_container = []

    timeout_timer = threading.Timer(ABSOLUTE_MAX_RUNTIME, lambda: absolute_timeout_handler(process_container[0] if process_container else None))
    timeout_timer.daemon = True
    timeout_timer.start()

    try:
        phoenix_guardian(process_container)

    except KeyboardInterrupt:
        print("\n🚫 收到使用者中斷 (Ctrl+C)。守護神正在關閉...")
        sys.exit(0)
    except SystemExit as e:
        sys.exit(e.code)
    except Exception as e:
        print(f"❌ 鳳凰守護神遭遇未預期的致命錯誤: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if timeout_timer.is_alive():
            timeout_timer.cancel()
