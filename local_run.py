# -*- coding: utf-8 -*-
# 檔案: local_run.py (V5.0 - 最終看門狗模式)
# 說明: 本地開發與測試的統一啟動入口。
#       其職責是呼叫中央監督者腳本 (supervisor.py)，
#       並作為最後一道防線，對其執行時間進行監控。

import sys
import subprocess
import os
import signal
from pathlib import Path
import time

# --- 設定 ---
# 終極看門狗超時：如果 run.sh 在此時間內沒有自行退出，
# local_run.py 將強制終止它和它的所有子進程。
# 60 秒對於後續執行來說是個合理的超時時間。
FINAL_WATCHDOG_TIMEOUT_SECONDS = 60
# 終極看門狗觸發時的退出碼
WATCHDOG_EXIT_CODE = 99

def main():
    """
    啟動並監控由 run.sh 管理的後端服務，為其提供最終的超時保護。
    """
    project_root = Path(__file__).resolve().parent
    run_script = project_root / "run.sh"

    if not run_script.exists():
        print(f"❌ 錯誤：找不到核心啟動腳本: {run_script}", file=sys.stderr)
        sys.exit(1)

    print("="*80)
    print("🎯 正在透過 'run.sh' 啟動後端服務 (最終看門狗模式)...")
    print(f"   - 呼叫腳本: {run_script}")
    print(f"   - 終極看門狗超時: {FINAL_WATCHDOG_TIMEOUT_SECONDS} 秒")
    print("="*80)

    # 現在我們只執行 run.sh，它負責處理所有環境設定和啟動邏輯
    command = [str(run_script)]

    # 跨平台處理進程組
    # 在 Unix-like 系統上，我們創建一個新的進程組，以便可以一次性殺死 supervisor 和它所有的子進程。
    preexec_fn = None
    if os.name != 'nt':
        preexec_fn = os.setsid

    process = None
    exit_code = 0
    try:
        process = subprocess.Popen(
            command,
            cwd=project_root,
            preexec_fn=preexec_fn
        )

        # 等待 supervisor 進程結束，並設置超時
        process.wait(timeout=FINAL_WATCHDOG_TIMEOUT_SECONDS)
        exit_code = process.returncode

        print("="*80)
        if exit_code == 0:
            print("✅ 監督者已在預期內正常關閉。")
        else:
            print(f"⚠️ 監督者已在預期內關閉，但回報了錯誤，返回碼: {exit_code}", file=sys.stderr)

    except subprocess.TimeoutExpired:
        print("="*80, file=sys.stderr)
        print(f"🚨🚨🚨 終極看門狗觸發！🚨🚨🚨", file=sys.stderr)
        print(f"監督者腳本 (supervisor.py) 在 {FINAL_WATCHDOG_TIMEOUT_SECONDS} 秒內未能完成任務。", file=sys.stderr)
        print("這可能表示監督者本身或其子進程發生了嚴重掛起。", file=sys.stderr)
        print("正在強制終止所有相關進程...", file=sys.stderr)

        # 強制終止進程
        if process:
            if os.name != 'nt':
                # 殺死整個進程組
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass # 進程可能剛好結束
            else:
                # 在 Windows 上，終止主進程
                process.kill()

        print("強制終止完成。", file=sys.stderr)
        exit_code = WATCHDOG_EXIT_CODE

    except KeyboardInterrupt:
        print("\n🏁 收到中斷訊號，正在要求監督者優雅關閉...")
        # supervisor.py 的 finally 區塊會處理清理工作
        if process:
            # 等待 supervisor 自行處理
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                print("監督者未能及時關閉，強制終止...", file=sys.stderr)
                process.kill()
        print("本地運行流程已終止。")
        exit_code = 1

    except Exception as e:
        print(f"❌ 執行 local_run.py 時發生未預期的錯誤: {e}", file=sys.stderr)
        exit_code = 1

    finally:
        # 確保進程在任何情況下都被處理
        if process and process.poll() is None:
            print("[local_run] 警告：在退出時，監督者進程仍在運行。強制終止。")
            process.kill()

    print("="*80)
    print("🏁 本地運行流程結束。")
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
