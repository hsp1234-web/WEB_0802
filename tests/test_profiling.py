# -*- coding: utf-8 -*-
"""
效能剖析測試
目標：使用 cProfile 分析 scripts/launch.py 的啟動效能，找出瓶頸。
"""
import cProfile
import pstats
import subprocess
import os
import sys
from pathlib import Path

# --- 設定路徑 ---
# 確保腳本能找到專案根目錄，以便正確引用 scripts/launch.py
# __file__ -> tests/performance/test_profiling.py
# project_root -> 專案根目錄
project_root = Path(__file__).parent.parent.parent
script_to_profile = project_root / "scripts" / "launch.py"
profile_output_file = project_root / "tests" / "performance" / "launch_profile.prof"
python_executable = sys.executable # 使用當前的 Python 解釋器

def run_profiling():
    """
    執行效能剖析並儲存/顯示結果。
    """
    if not script_to_profile.exists():
        print(f"❌ 錯誤：找不到要分析的腳本 {script_to_profile}")
        return

    print(f"🚀 開始對 {script_to_profile} 進行效能剖析...")
    print(f"   Python 解釋器: {python_executable}")

    # --- 使用 subprocess 執行腳本，以便 cProfile 能捕獲其完整的執行過程 ---
    # 我們直接在一個命令中結合 cProfile 和腳本執行
    command = [
        python_executable,
        "-m", "cProfile",
        "-o", str(profile_output_file),
        str(script_to_profile)
    ]

    try:
        # 使用 subprocess.run 來執行命令
        # 我們設定一個合理的 timeout，以防腳本掛起
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            check=True, # 如果返回非零錯誤碼，則拋出例外
            timeout=120 # 2分鐘超時
        )
        print("✅ 剖析執行完畢。")
        # print("--- STDOUT ---")
        # print(result.stdout)
        # if result.stderr:
        #     print("--- STDERR ---")
        #     print(result.stderr)

    except subprocess.CalledProcessError as e:
        print(f"❌ 剖析過程中，目標腳本執行出錯 (返回碼: {e.returncode})。")
        print("--- STDOUT ---")
        print(e.stdout)
        print("--- STDERR ---")
        print(e.stderr)
        return
    except subprocess.TimeoutExpired as e:
        print(f"❌ 剖析超時（超過 {e.timeout} 秒）。")
        print("   這可能表示目標腳本在某處掛起。")
        return

    # --- 讀取並分析剖析結果 ---
    if not profile_output_file.exists():
        print(f"❌ 錯誤：剖析輸出檔案 {profile_output_file} 未被建立。")
        return

    print("\n" + "="*50)
    print("📊 效能分析報告")
    print("="*50)

    # 使用 pstats 模組來讀取和排序結果
    stats = pstats.Stats(str(profile_output_file))

    # 脫去路徑，只留檔名，讓輸出更乾淨
    stats.strip_dirs()

    # 按照「累積耗時」排序，並顯示前 20 個結果
    print("\n--- 耗時最長的 20 個函式 (按累積時間排序) ---")
    stats.sort_stats('cumulative').print_stats(20)

    # 按照「函式自身耗時」排序，並顯示前 10 個結果
    print("\n--- 函式自身耗時最長的 10 個函式 (按內部時間排序) ---")
    stats.sort_stats('tottime').print_stats(10)

    print(f"\nℹ️ 完整的剖析數據已儲存至：{profile_output_file}")

if __name__ == "__main__":
    run_profiling()
