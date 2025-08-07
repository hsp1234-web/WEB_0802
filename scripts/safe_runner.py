# -*- coding: utf-8 -*-
# 檔案: scripts/safe_runner.py
# 說明: 一個帶有日誌監控看門狗的安全進程啟動器。

import subprocess
import threading
import sys
import os
import queue
import time

# --- 看門狗設定 ---
# 如果子進程在此秒數內沒有任何日誌輸出，將被視為掛起並被終止。
WATCHDOG_TIMEOUT_SECONDS = 15.0

# --- 全域狀態 ---
# 將子進程和計時器設為全域變數，以便在超時處理函式中存取。
g_process = None
g_watchdog_timer = None

def handle_timeout():
    """
    看門狗超時處理函式。
    此函式在一個獨立的計時器執行緒中被呼叫。
    """
    global g_process
    if g_process and g_process.poll() is None:
        # 使用 print 將錯誤訊息導向 stderr
        print("\n" + "="*80, file=sys.stderr)
        print(f"❌ 看門狗超時 ({WATCHDOG_TIMEOUT_SECONDS}s)! 目標進程未產生輸出。", file=sys.stderr)
        print(f"   正在終止掛起的進程 (PID: {g_process.pid})...", file=sys.stderr)
        print("="*80, file=sys.stderr)

        # 強制終止子進程
        g_process.kill()

        # 立即以錯誤碼退出看門狗腳本本身，這是一個關鍵的失敗信號。
        # 使用 os._exit 而不是 sys.exit，因為這是在一個非主執行緒中。
        os._exit(1)

def reset_watchdog():
    """
    取消當前的看門狗計時器並啟動一個新的。
    """
    global g_watchdog_timer
    if g_watchdog_timer:
        g_watchdog_timer.cancel()
    g_watchdog_timer = threading.Timer(WATCHDOG_TIMEOUT_SECONDS, handle_timeout)
    g_watchdog_timer.start()

def enqueue_output(stream, q):
    """
    在背景執行緒中讀取流 (stdout/stderr) 並將每一行放入佇列。
    """
    for line in iter(stream.readline, ''):
        q.put(line)
    stream.close()

def main():
    """
    主函數：啟動並監控一個子進程。
    """
    global g_process
    global g_watchdog_timer

    # 從命令列參數獲取要執行的指令
    command_to_run = sys.argv[1:]
    if not command_to_run:
        print("Usage: python safe_runner.py <command_to_run...>", file=sys.stderr)
        print("Example: python safe_runner.py .venv/bin/python -u -m scripts.heartbeat_worker", file=sys.stderr)
        sys.exit(1)

    print("="*80)
    print(f"👁️‍🗨️  安全啟動器已啟動，正在監控指令:")
    print(f"   {' '.join(command_to_run)}")
    print(f"⏱️  看門狗超時設定為: {WATCHDOG_TIMEOUT_SECONDS} 秒")
    print("="*80)

    exit_code = 0
    try:
        # 啟動子進程。
        # text=True (或 universal_newlines=True) 很重要，它讓輸出以文字形式處理。
        # bufsize=1 確保行緩衝。
        g_process = subprocess.Popen(
            command_to_run,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # 將 stderr 合併到 stdout
            text=True,
            bufsize=1
        )

        # 建立並啟動讀取器執行緒，從子進程的 stdout 讀取輸出
        output_queue = queue.Queue()
        reader_thread = threading.Thread(target=enqueue_output, args=(g_process.stdout, output_queue))
        reader_thread.daemon = True  # 確保主程式退出時執行緒也會退出
        reader_thread.start()

        # 啟動第一個看門狗計時器
        reset_watchdog()

        # 主迴圈：監控進程狀態並處理日誌輸出
        while g_process.poll() is None:
            try:
                # 以非阻塞方式從佇列中獲取日誌行
                line = output_queue.get(timeout=0.5)
            except queue.Empty:
                # 佇列為空是正常情況，表示子進程暫時沒有輸出。
                # 我們的看門狗仍在背景倒數，所以一切盡在掌握。
                continue
            else:
                # 成功獲取到一行輸出！
                # 打印它，並重置看門狗計時器。
                print(line, end='', flush=True)
                reset_watchdog()

        # 如果迴圈結束，代表子進程已自行終止
        exit_code = g_process.returncode
        print("\n" + "-"*80)
        print(f"✅ 目標進程已自行結束，返回碼: {exit_code}")

    except KeyboardInterrupt:
        print("\n" + "-"*80)
        print(" manualmente 中斷 (Ctrl+C)。正在終止子進程...")
        exit_code = 1
    except Exception as e:
        print(f"\n❌ 安全啟動器發生未預期的錯誤: {e}", file=sys.stderr)
        exit_code = 1
    finally:
        # 最後的清理工作
        if g_watchdog_timer:
            g_watchdog_timer.cancel()
        if g_process and g_process.poll() is None:
            g_process.kill()
        print("="*80)
        print("🏁 安全啟動器已關閉。")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
