# -*- coding: utf-8 -*-
import subprocess
import threading
import time
import os

def worker():
    """
    此工作函式嘗試呼叫 subprocess.Popen。
    根據 docs/BUG.md，在此環境中呼叫一個包含 Popen 的函式，
    預期會導致無聲的掛起。
    """
    print("工作執行緒已啟動。正在嘗試呼叫 Popen...")

    # 這是可能產生問題的呼叫。我們預期腳本會在此處掛起，
    # 甚至在呼叫 worker() 本身時就掛起。
    try:
        process = subprocess.Popen(
            ["tools/.venv_test/bin/python", "tools/dummy_script.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )

        print("工作執行緒：Popen 呼叫已完成。正在等待進程結束...") # 此行預期不會被執行。
        stdout, stderr = process.communicate(timeout=10)
        print("工作執行緒：進程已結束。") # 此行預期不會被執行。
        print("工作執行緒 stdout:", stdout)
        print("工作執行緒 stderr:", stderr)
    except Exception as e:
        print(f"工作執行緒發生未預期的錯誤: {e}") # 此行可能不會被執行，因為預期是死鎖而不是異常。


def main():
    """
    主函式，用於啟動測試。
    """
    print("主程式：開始測試 subprocess.Popen 掛起問題。")

    # 建立並啟動將要呼叫 Popen 的執行緒。
    t = threading.Thread(target=worker)
    t.daemon = True # 將執行緒設為守護執行緒，這樣主程式退出時它也會退出。
    t.start()

    print("主程式：工作執行緒已啟動。等待其完成...")

    # 我們將等待一個較短的超時時間。如果它掛起了，join 會超時。
    t.join(timeout=15)

    if t.is_alive():
        print("\n======================================================================")
        print("✅ 測試成功復現問題：工作執行緒在 15 秒後依然存活。")
        print("這證實了在執行緒中呼叫 subprocess.Popen 會導致無聲掛起的假設。")
        print("======================================================================")
        # 為了讓 CI/CD 或自動化腳本能夠捕獲，我們以非 0 的狀態碼退出
        # sys.exit(1) # 在 Colab 中，這可能會中斷整個執行，所以我們僅打印資訊
    else:
        print("\n======================================================================")
        print("❌ 測試未復現問題：工作執行緒已在預期時間內結束。")
        print("這表示問題可能比預想的更複雜，或者此最小化測試案例不足以觸發它。")
        print("======================================================================")

if __name__ == "__main__":
    main()
