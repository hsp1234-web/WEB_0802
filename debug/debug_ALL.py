# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║           🚀 鳳凰之心 - Pytest 整合測試啟動器 V35                    ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║ - 說明: 此腳本為專案提供一個單一、可靠的入口點，用於執行所有整合   ║
# ║         測試。它會自動處理虛擬環境的建立與依賴安裝，確保測試在     ║
# ║         一個乾淨、一致的環境中運行。                                 ║
# ║ - 核心: 利用 pytest 框架，並遵循 `tests/conftest.py` 中定義的      ║
# ║         fixture 模式。                                               ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝
import sys
import os
import subprocess
from pathlib import Path
import shutil

# --- 全域設定 ---
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
VENV_DIR = PROJECT_ROOT / ".pytest_venv"
VENV_PYTHON = VENV_DIR / "bin" / "python"
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements" / "dev.txt"

def run_command(command, check=True):
    """執行一個子程序命令並即時打印其輸出。"""
    print(f"🚀 執行命令: {' '.join(map(str, command))}")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        cwd=PROJECT_ROOT
    )
    for line in process.stdout:
        print(f"   {line.strip()}")

    process.wait()
    if check and process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, command)

def main():
    """主執行函數，包含自我引導邏輯。"""
    is_in_venv = (os.path.abspath(sys.executable) == os.path.abspath(str(VENV_PYTHON)))

    if not is_in_venv:
        # --- 外部引導程序 ---
        print("\n--- 偵測到不在虛擬環境中，開始準備測試環境 ---\n")
        if VENV_DIR.exists():
            print(f"發現舊的虛擬環境 '{VENV_DIR}'，正在刪除...")
            shutil.rmtree(VENV_DIR)

        # 1. 建立虛擬環境
        run_command([sys.executable, "-m", "venv", str(VENV_DIR)])

        # 2. 安裝依賴
        run_command([str(VENV_PYTHON), "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)])

        # 3. 安裝專案本身為可編輯模式
        run_command([str(VENV_PYTHON), "-m", "pip", "install", "-e", "."])

        # 4. 使用虛擬環境的 Python 重新執行此腳本
        print("\n--- 環境準備完畢，正在使用 venv 的 Python 重新啟動 ---\n")
        result = subprocess.run([str(VENV_PYTHON), __file__])
        sys.exit(result.returncode)
    else:
        # --- 內部執行邏輯 (已經在虛擬環境中) ---
        print("\n--- 已在虛擬環境中，開始執行 Pytest 整合測試 ---\n")
        try:
            # 執行整合測試
            run_command([str(VENV_PYTHON), "-m", "pytest", "-v", "tests/integration/"])
            print("\n🎉 所有整合測試已成功通過！")
        except subprocess.CalledProcessError:
            print("\n🔥 部分整合測試未通過！", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ 執行測試時發生未預期的錯誤: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
