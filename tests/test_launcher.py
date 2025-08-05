# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║     ✅ 測試: 核心啟動器整合測試 (`test_launcher.py`)             ✅ ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 目的: 模擬 Colab 環境的行為，對 `scripts/launch.py` 進行一個   ║
# ║           完整的端對端整合測試。                                   ║
# ║   - 核心: 在一個乾淨的臨時目錄中，從頭開始執行 `git clone` 和      ║
# ║           啟動器腳本，以驗證環境設定的每一個步驟。                 ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import sys
import os
import subprocess
import shutil
import tempfile
import time
from pathlib import Path

def print_header(title):
    """打印漂亮的標題。"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "="*80)
    print(f"🧪 {timestamp} - {title}")
    print("="*80)

def run_test():
    """執行主測試邏輯。"""
    # --- 測試設定 ---
    # 使用與 colab_runner.py 相同的設定
    REPO_URL = "https://github.com/hsp1234-web/WEB_0802.git"
    TARGET_BRANCH = "1.1.6"
    PROJECT_FOLDER_NAME = "WEB1_TEST" # 使用不同的名稱以避免衝突
    LAUNCH_TIMEOUT = 120 # 給予啟動器足夠的執行時間 (秒)

    # --- 測試環境準備 ---
    # 建立一個臨時目錄來模擬一個乾淨的 Colab 環境
    test_dir = Path(tempfile.mkdtemp())
    print(f"建立臨時測試目錄: {test_dir}")

    launcher_process = None
    try:
        # --- 步驟 1: 複製當前工作區到臨時目錄 ---
        print_header("步驟 1: 複製當前工作區以進行隔離測試")

        # 獲取當前工作區的根目錄 (此測試腳本位於 tests/，所以是上兩層)
        workspace_root = Path(__file__).resolve().parent.parent
        project_path = test_dir / workspace_root.name

        # 複製整個目錄樹
        shutil.copytree(workspace_root, project_path, dirs_exist_ok=True)
        print(f"✅ 工作區已成功複製到: {project_path}")

        # --- 步驟 2: 執行核心啟動器 ---
        launcher_script_path = project_path / "scripts" / "launch.py"
        if not launcher_script_path.is_file():
            raise FileNotFoundError(f"啟動器腳本未在預期路徑找到: {launcher_script_path}")

        print_header(f"步驟 2: 在 '{project_path}' 中執行核心啟動器")

        # 使用系統的 python 執行，因為啟動器會自己處理 venv
        launch_command = [sys.executable, str(launcher_script_path)]

        launcher_process = subprocess.Popen(
            launch_command,
            cwd=str(project_path), # 關鍵：在專案目錄下執行
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8'
        )

        # --- 步驟 3: 監控啟動器輸出 ---
        print_header("步驟 3: 監控啟動器日誌輸出 (超時: 120 秒)")
        start_time = time.monotonic()
        server_ready = False

        for line in iter(launcher_process.stdout.readline, ''):
            if time.monotonic() - start_time > LAUNCH_TIMEOUT:
                raise TimeoutError("啟動器執行超時。")

            print(f"   [LAUNCHER] {line.strip()}")

            # 檢查是否有任何失敗的關鍵字
            if "❌" in line or "失敗" in line or "Error" in line.upper():
                # 打印剩餘的日誌以幫助除錯
                print("--- 偵測到錯誤，打印剩餘日誌 ---")
                for remaining_line in launcher_process.stdout:
                    print(f"   [LAUNCHER] {remaining_line.strip()}")
                raise RuntimeError(f"啟動器日誌中偵測到錯誤: {line.strip()}")

            # 檢查成功的關鍵字
            if "Uvicorn running on" in line or "Application startup complete" in line:
                print("\n✅ 伺服器已成功啟動！測試通過。")
                server_ready = True
                break

        if not server_ready:
            raise RuntimeError("啟動器日誌流結束，但未偵測到伺服器就緒信號。")

    except Exception as e:
        print(f"\n❌ 測試執行失敗: {e}")
        # 如果有 launcher 進程，確保它被終止
        if launcher_process:
            launcher_process.kill()
        sys.exit(1)
    finally:
        # --- 清理 ---
        print_header("清理測試環境")
        if launcher_process:
            print("正在終止啟動器進程...")
            launcher_process.terminate()
            try:
                launcher_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                launcher_process.kill()

        print(f"正在刪除臨時目錄: {test_dir}")
        shutil.rmtree(test_dir)
        print("✅ 清理完成。")

if __name__ == "__main__":
    run_test()
