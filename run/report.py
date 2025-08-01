# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║               📊 報告中心 V27 (資料庫直讀版)                       ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 核心職責：讀取 state.db，或直接呼叫報告生成腳本。                ║
# ║   - 獨立執行：可在主指揮中心任務結束後獨立運行，用於歸檔或分析。     ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

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

    report_script_path = Path("scripts/report_generator.py")
    if not report_script_path.exists():
        print(f"❌ 錯誤：找不到報告生成腳本位於 {report_script_path}")
        sys.exit(1)

    # 確保 uvicorn.log 存在，因為報告生成器依賴它
    log_path = Path("uvicorn.log")
    if not log_path.exists():
        print(f"⚠️ 警告：找不到日誌檔案 {log_path}。日誌相關報告可能為空。")
        # 建立一個空檔案以防腳本出錯
        log_path.touch()

    try:
        result = subprocess.run(
            [sys.executable, str(report_script_path), "--report", "all"],
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        print("✅ 報告生成成功！")
        print("\n--- 報告生成器日誌 ---")
        print(result.stdout)
        print("--- 日誌結束 ---\n")

    except subprocess.CalledProcessError as e:
        print("❌ 錯誤：報告生成腳本執行失敗。")
        print(f"返回碼: {e.returncode}")
        print("--- STDOUT ---")
        print(e.stdout)
        print("--- STDERR ---")
        print(e.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ 發生未預期的錯誤: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
