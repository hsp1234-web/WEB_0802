# 檔案: run/colab_runner.py
# 說明: 指揮中心核心啟動器。

import threading
import subprocess
import time
import os
from IPython.display import display, HTML, clear_output

# --- 概念區塊：背景核心任務 ---

def main_task():
    """
    作法：
    1. 此函式將在一個獨立的背景執行緒中運行。
    2. 使用 subprocess.Popen 啟動 uvicorn 伺服器。
    3. 將 uvicorn 的 stdout 和 stderr 重新導向到 'uvicorn.log' 檔案。
    4. 持續監控該進程。
    """
    print("背景任務：正在啟動核心引擎...")
    with open("uvicorn.log", "w") as log_file:
        # 使用 sys.executable 確保我們用的是同一個 python 環境
        process = subprocess.Popen(
            ["uvicorn", "src.phoenix_core.main:app", "--host", "0.0.0.0", "--port", "8000"],
            stdout=log_file,
            stderr=subprocess.STDOUT
        )
    print("背景任務：核心引擎已啟動。")
    process.wait()
    print("背景任務：核心引擎已停止。")
    # 將進程物件儲存到全域變數以便主執行緒可以存取
    global uvicorn_process
    uvicorn_process = process


# --- 概念區塊：主執行緒與儀表板渲染 ---

def tail_log(log_file_path, last_pos):
    """
    讀取檔案從上次讀取位置之後的新增內容。
    """
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            f.seek(last_pos)
            new_content = f.read()
            current_pos = f.tell()
            return new_content, current_pos
    except FileNotFoundError:
        return "", last_pos


def main():
    # 清理舊的日誌檔案
    if os.path.exists("uvicorn.log"):
        os.remove("uvicorn.log")

    # 讀取 HTML 模板
    try:
        with open("wolf.html", "r", encoding="utf-8") as f:
            html_template = f.read()
    except FileNotFoundError:
        print("錯誤: wolf.html 模板檔案不存在。")
        return

    # 啟動背景任務
    global uvicorn_process
    uvicorn_process = None

    worker_thread = threading.Thread(target=main_task, daemon=True)
    worker_thread.start()

    print("主執行緒：儀表板渲染已啟動。")

    last_log_position = 0

    try:
        while worker_thread.is_alive():
            # 讀取增量日誌
            new_logs, last_log_position = tail_log("uvicorn.log", last_log_position)

            # 準備要插入到 HTML 的日誌內容
            # 為了顯示效果，我們將換行符替換為 <br>
            log_html = new_logs.replace('\n', '<br>')

            # 動態更新 HTML
            # 這裡我們用一個簡單的替換來注入日誌
            # 在真實場景中，可能會用更複雜的模板引擎或 DOM 操作
            display_html = html_template.replace(
                '<p><span class="text-green-400">[INFO]</span> [2025-07-18 13:30:00] System initialized.</p>',
                f'<p>{log_html}</p>'
            )

            clear_output(wait=True)
            display(HTML(display_html))

            time.sleep(2) # 每 2 秒更新一次

    except KeyboardInterrupt:
        print("\n🛑 操作已被使用者手動中斷。")
    finally:
        # 確保 uvicorn 進程被終止
        if uvicorn_process and uvicorn_process.poll() is None:
            print("正在終止背景 uvicorn 進程...")
            uvicorn_process.terminate()
            try:
                uvicorn_process.wait(timeout=5)
                print("Uvicorn 進程已成功終止。")
            except subprocess.TimeoutExpired:
                print("Uvicorn 進程終止超時，強制終止。")
                uvicorn_process.kill()

        # 尋找並終止任何殘留的 uvicorn 進程
        try:
            # 這是一個比較強硬的清理方式，確保不會有殘留進程
            subprocess.run(["pkill", "-f", "uvicorn"], check=False)
            print("已執行殘留進程清理。")
        except FileNotFoundError:
            # 如果 pkill 不存在 (例如在 Windows 上)
            pass

        print("指揮中心已關閉。")


if __name__ == "__main__":
    main()
