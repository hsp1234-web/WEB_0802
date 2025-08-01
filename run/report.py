# 檔案: run/report.py
# 說明: 任務結束後的報告生成入口。

import subprocess
import sys
from pathlib import Path

def main():
    """
    作法：
    1. 打印一條訊息，告知使用者報告生成已開始。
    2. 使用 subprocess.run 呼叫報告生成腳本，並傳入 '--report all' 參數。
    3. 檢查子進程的返回碼，如果出錯則報告錯誤。
    4. 成功後，打印所有報告已生成完畢的訊息。
    """
    print("任務已結束，正在生成所有最終報告...")

    # 確保我們呼叫的腳本存在
    report_script_path = Path("scripts/report_generator.py")
    if not report_script_path.exists():
        print(f"錯誤：找不到報告生成腳本位於 {report_script_path}")
        sys.exit(1)

    try:
        # 使用 sys.executable 確保我們用的是同一個 python 環境
        result = subprocess.run(
            [sys.executable, str(report_script_path), "--report", "all"],
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        print("報告生成成功！")
        # 印出報告生成腳本的標準輸出，提供更多資訊
        print("--- 報告生成器日誌 ---")
        print(result.stdout)
        print("--- 日誌結束 ---")

    except FileNotFoundError:
        print("錯誤：`python` 指令未找到。請確定 Python 已安裝並在您的 PATH 中。")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print("錯誤：報告生成腳本執行失敗。")
        print(f"返回碼: {e.returncode}")
        print("--- STDOUT ---")
        print(e.stdout)
        print("--- STDERR ---")
        print(e.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"發生未預期的錯誤: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
