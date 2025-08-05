# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║      🚀 local_run.py (V30 - Orchestrator/Executor Split)             ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 作者: Jules (AI Software Engineer)                               ║
# ║   - 目的: 作為總協調器，建立環境後，呼叫 venv 中的執行器腳本。     ║
# ║   - 核心: venv, uv                                                 ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import sys
import os
import subprocess
import shutil
import time
from datetime import datetime

# --- 全域設定 (Global Settings) ---
VENV_DIR = ".venv_gold"
VENV_PYTHON = os.path.join(VENV_DIR, "bin", "python")
VENV_UV = os.path.join(VENV_DIR, "bin", "uv")
VENV_PIP = os.path.join(VENV_DIR, "bin", "pip")
CORE_RUNNER_SCRIPT = "core_runner.py"

def get_timestamp():
    """獲取當前時間戳，用於日誌。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def print_header(title):
    """打印帶有標題的日誌分隔線。"""
    print("\n" + "="*80)
    print(f"🚀 {get_timestamp()} - {title}")
    print("="*80)

def run_sync_command(command, cwd=".", env=None):
    """
    【同步版本】執行一個子程序命令，並即時串流其輸出。
    用於環境設定等同步任務。
    """
    print(f"   🔹 執行命令: {' '.join(command)} (於 {cwd})")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        cwd=cwd,
        env=env
    )
    output_lines = []
    for line in process.stdout:
        print(f"     [OUTPUT] {line.strip()}")
        output_lines.append(line)

    return_code = process.wait()
    if return_code != 0:
        print(f"❌ 命令執行失敗，返回碼: {return_code}", file=sys.stderr)
        # 如果有需要，可以在此處打印完整的錯誤日誌
        # print("".join(output_lines), file=sys.stderr)
        raise subprocess.CalledProcessError(return_code, command)
    print(f"   ✅ 命令成功完成。")

def main():
    """
    主執行函式，協調所有同步和異步步驟。
    """
    start_time = time.time()
    os.environ["PYTHONUNBUFFERED"] = "1"

    try:
        # --- 步驟 1-3 & 5: 同步的環境設定 ---
        print_header("步驟 1: 建立 Python 虛擬環境 (venv)")
        if os.path.isdir(VENV_DIR):
            print(f"   ℹ️ 正在移除已存在的虛擬環境: {VENV_DIR}")
            shutil.rmtree(VENV_DIR)
        run_sync_command([sys.executable, "-m", "venv", VENV_DIR])

        print_header("步驟 2: 在 venv 中安裝 uv")
        run_sync_command([VENV_PIP, "install", "-U", "uv"])

        print_header("步驟 2b: 在 venv 中安裝 pip-tools")
        run_sync_command([VENV_PIP, "install", "pip-tools"])

        print_header("步驟 2c: 重新編譯依賴文件")
        pip_compile_command = [
            os.path.join(VENV_DIR, "bin", "pip-compile"),
            "requirements/dev.in",
            "-o", "requirements/dev.txt"
        ]
        run_sync_command(pip_compile_command)

        print_header("步驟 3: 將當前專案套件化安裝到 venv 中")
        run_sync_command([VENV_PIP, "install", "-e", "."], cwd=".")

        print_header("步驟 5: 在 venv 中安裝專案依賴")
        run_sync_command([VENV_UV, "pip", "install", "--python", VENV_PYTHON, "-r", "requirements/base.txt"], cwd=".")

        # --- 步驟 4 & 6: 在 venv 中執行核心應用程式 ---
        print_header("步驟 4 & 6: 執行核心應用程式 (在 venv 中)")
        run_sync_command([VENV_PYTHON, CORE_RUNNER_SCRIPT], cwd=".")

        # --- 步驟 7: 執行報告生成器 (同步) ---
        print_header("步驟 7: 執行報告生成器")
        db_original_path = "state.db"
        db_renamed_path = "logs.sqlite"
        if os.path.exists(db_original_path):
            shutil.move(db_original_path, db_renamed_path)
            print(f"✅ 資料庫已重命名為 {db_renamed_path}")
        else:
            print(f"⚠️ 找不到資料庫檔案 {db_original_path}，無法生成報告。")
            # 創建一個空文件以避免後續流程出錯
            open(db_renamed_path, 'a').close()

        report_generator_script = os.path.join("scripts", "generate_report.py")
        if os.path.exists(report_generator_script):
            requirements_report_file = "requirements/report.txt"
            if os.path.exists(requirements_report_file):
                 print("\n--- 安裝報告依賴 ---")
                 run_sync_command([VENV_UV, "pip", "install", "--python", VENV_PYTHON, "-r", requirements_report_file], cwd=".")

            report_command = [
                VENV_PYTHON, report_generator_script,
                "--db-file", db_renamed_path,
                "--report-dir", "reports",
            ]
            run_sync_command(report_command, cwd=".")
            print("✅ 報告生成完畢。")

    except subprocess.CalledProcessError as e:
        print(f"\n❌ 一個關鍵命令執行失敗，返回碼: {e.returncode}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 發生未預期的錯誤: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        end_time = time.time()
        print("\n" + "="*80)
        print(f"🏁 全部流程結束，總耗時: {end_time - start_time:.2f} 秒。")
        print("="*80)

if __name__ == "__main__":
    # 將 'src' 目錄添加到 Python 路徑中，以解決模組導入問題
    # 這確保了即使在 venv 啟用前，腳本也能找到 'phoenix_core' 模組
    sys.path.insert(0, os.path.abspath('src'))
    main()
