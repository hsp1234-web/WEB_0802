import subprocess
import sys
import shutil
from pathlib import Path

# 這些資訊來自 run/colab_runner.py，確保我們的測試與之對齊
REPOSITORY_URL = "https://github.com/hsp1234-web/WEB_0802.git"
TARGET_BRANCH_OR_TAG = "0.7.0"
# 為避免與其他測試或真實執行衝突，使用一個獨立的目錄名稱
PROJECT_FOLDER_NAME = "debug_project_v2"

def main():
    """
    此腳本旨在透過 clone 真實的 Git 專案來重現 'No module named pip' 錯誤。
    這是第二版的測試，比第一版更貼近真實場景。
    """
    print("--- 測試開始 (V2)：使用真實 Git Repo 重現錯誤 ---")

    # 1. 設定測試路徑
    base_path = Path(".").resolve()
    project_path = base_path / PROJECT_FOLDER_NAME
    venv_path = project_path / ".venv"

    print(f"測試專案將建立於: {project_path}")

    # 2. 清理上一次執行的殘留物，確保測試環境乾淨
    if project_path.exists():
        print(f"發現舊的測試目錄，正在刪除: {project_path}")
        shutil.rmtree(project_path)

    # 3. 步驟一：從 Git clone 完整專案
    print(f"\n[步驟 1/3] 正在從 Git clone 專案 (分支: {TARGET_BRANCH_OR_TAG})...")
    git_command = ["git", "clone", "--branch", TARGET_BRANCH_OR_TAG, "--depth", "1", REPOSITORY_URL, str(project_path)]
    result = subprocess.run(git_command, capture_output=True, text=True, encoding='utf-8')

    if result.returncode != 0:
        print(f"❌ Git clone 失敗!")
        print(f"STDERR:\n{result.stderr.strip()}")
        sys.exit(1)
    else:
        print("✅ Git clone 成功。")

    # 4. 步驟二：在 clone 下來的專案中建立虛擬環境
    print(f"\n[步驟 2/3] 使用 'uv venv' 建立虛擬環境...")
    venv_cmd = ["uv", "venv", str(venv_path), "--seed"]
    result = subprocess.run(venv_cmd, capture_output=True, text=True, encoding='utf-8')

    if result.returncode != 0:
        print(f"❌ 建立虛擬環境失敗!")
        print(f"STDERR:\n{result.stderr.strip()}")
        sys.exit(1)
    else:
        print("✅ 虛擬環境建立成功。")

    venv_python = venv_path / "bin" / "python"
    print(f"虛擬環境 Python 解譯器路徑: {venv_python}")

    # 5. 步驟三：嘗試安裝真實的依賴文件
    print(f"\n[步驟 3/3] 嘗試用新環境的 Python 安裝真實的依賴文件...")
    requirements_file = project_path / "requirements/requirements-core.txt"
    pip_cmd = [str(venv_python), "-m", "pip", "install", "-r", str(requirements_file)]
    result = subprocess.run(pip_cmd, capture_output=True, text=True, encoding='utf-8')

    # 6. 判斷 V2 測試的結果
    if result.returncode != 0 and "No module named pip" in result.stderr:
        print("\n🎉 [預期中的成功] 依賴安裝失敗，並捕獲到 'No module named pip' 錯誤。")
        print("這強烈暗示問題的觸發與 clone 下來的專案內容/結構有關。")
        print(f"返回碼: {result.returncode}")
        print(f"錯誤訊息 (STDERR):\n{result.stderr.strip()}")
        print("\n--- ✅ 測試結束：成功重現錯誤 ---")
        sys.exit(0)
    elif result.returncode != 0:
        print("\n🤔 [預期外的失敗] 依賴安裝失敗，但原因不是缺少 pip。")
        print(f"返回碼: {result.returncode}")
        print(f"STDOUT:\n{result.stdout.strip()}")
        print(f"STDERR:\n{result.stderr.strip()}")
        print("\n--- ❌ 測試結束：未能按預期重現錯誤 ---")
        sys.exit(1)
    else:
        print("\n🤔 [預期外的成功] 依賴安裝成功了。")
        print("這強烈暗示問題與專案內容無關，根源極有可能在於執行路徑或其他環境因素。")
        print(f"STDOUT:\n{result.stdout.strip()}")
        print("\n--- ❌ 測試結束：未能重現錯誤 ---")
        sys.exit(1)

if __name__ == "__main__":
    main()
