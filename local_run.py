# -*- coding: utf-8 -*-
# 檔案: local_run.py (V4.0 - Supervisor 模式)
# 說明: 本地開發與測試的統一啟動入口。
#       其唯一職責是呼叫中央監督者腳本 (supervisor.py)。

import sys
import subprocess
import os
from pathlib import Path

def main():
    """
    啟動中央監督者 (supervisor) 來運行整個後端應用程式。
    """
    project_root = Path(__file__).resolve().parent
    supervisor_script = project_root / "scripts" / "supervisor.py"

    if not supervisor_script.exists():
        print(f"錯誤：找不到監督者腳本: {supervisor_script}", file=sys.stderr)
        sys.exit(1)

    print("="*80)
    print("🎯 正在啟動後端服務 (Supervisor 模式)...")
    print(f"   - 呼叫監督者: {supervisor_script}")
    print("="*80)

    # 使用 subprocess.run 來執行監督者腳本。
    # 這是一個阻塞操作，此腳本將會等待監督者結束 (例如，被使用者 Ctrl+C 中斷)。
    # 我們將控制權完全交給 supervisor.py。
    try:
        # 使用 sys.executable 確保使用與當前環境相同的 Python 解譯器。
        command = [sys.executable, str(supervisor_script)]

        # 將工作目錄設定為專案根目錄，以確保所有相對路徑都能正常解析。
        process = subprocess.run(
            command,
            check=False,  # 我們自己處理返回碼
            cwd=project_root
        )

        print("="*80)
        if process.returncode == 0:
            print("✅ 監督者已正常關閉。")
        else:
            # supervisor.py 中的 finally 區塊應該會處理優雅關閉，
            # 但如果 supervisor 本身崩潰，這裡會捕獲到非零返回碼。
            print(f"⚠️ 監督者意外終止，返回碼: {process.returncode}", file=sys.stderr)
        print("🏁 本地運行流程結束。")

    except KeyboardInterrupt:
        # 當使用者在 local_run.py 層級按下 Ctrl+C 時，
        # subprocess.run 會將訊號傳遞給子進程 (supervisor.py)。
        # supervisor.py 內部的 finally 區塊會負責清理工作。
        print("\n🏁 收到中斷訊號，本地運行流程已終止。")

    except Exception as e:
        print(f"❌ 執行 local_run.py 時發生未預期的錯誤: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
