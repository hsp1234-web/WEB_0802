import subprocess
import sys
import shutil
from pathlib import Path

def main():
    """
    此腳本旨在重現 'No module named pip' 的錯誤。
    它模仿 run/colab_runner.py 中有問題的環境設定邏輯。
    """
    print("--- 測試開始：重現 'No module named pip' 錯誤 ---")

    # 1. 設定測試路徑
    base_path = Path(".").resolve()
    project_path = base_path / "debug_project_fail"
    venv_path = project_path / ".venv"
    requirements_dir = project_path / "requirements"
    requirements_file = requirements_dir / "requirements-core.txt"

    print(f"將在以下路徑建立臨時專案: {project_path}")

    # 2. 為確保測試可重複執行，先清理舊的測試目錄
    if project_path.exists():
        print(f"發現舊的測試目錄，正在刪除: {project_path}")
        shutil.rmtree(project_path)

    # 3. 建立一個假的專案結構和依賴文件
    print("正在建立測試用的專案結構和 requirements.txt...")
    requirements_dir.mkdir(parents=True, exist_ok=True)
    # 使用一個常見且輕量的套件進行測試
    requirements_file.write_text("pytz\n", encoding='utf-8')
    print(f"已建立假的依賴文件: {requirements_file}")

    # 4. 步驟一：使用 'uv venv' 建立虛擬環境
    # 根據 uv 文件，--seed 參數 (預設啟用) 應該要安裝 pip。
    # 我們的目的是驗證在當前這個沙箱環境下，它是否真的這樣做了。
    print("\n[步驟 1/2] 使用 'uv venv' 建立虛擬環境...")
    venv_cmd = ["uv", "venv", str(venv_path), "--seed"]
    result = subprocess.run(venv_cmd, capture_output=True, text=True, encoding='utf-8')

    if result.returncode != 0:
        print("❌ 建立虛擬環境失敗!")
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
        sys.exit(1)
    else:
        print("✅ 虛擬環境建立成功。")

    venv_python = venv_path / "bin" / "python"
    print(f"虛擬環境 Python 解譯器路徑: {venv_python}")

    # 5. 步驟二：直接使用該環境的 Python 執行 pip 安裝 (預期會失敗的地方)
    print("\n[步驟 2/2] 嘗試用新環境的 Python 執行 'pip install'...")
    pip_cmd = [str(venv_python), "-m", "pip", "install", "-r", str(requirements_file)]
    result = subprocess.run(pip_cmd, capture_output=True, text=True, encoding='utf-8')

    # 6. 判斷測試結果
    # 在這個測試中，「失敗」才是我們預期的「成功」。
    if result.returncode != 0 and "No module named pip" in result.stderr:
        print("\n🎉 [預期中的成功] 依賴安裝失敗，並捕獲到 'No module named pip' 錯誤。")
        print("這證明了 'uv venv' 在此環境中沒有預設安裝 pip。")
        print(f"返回碼: {result.returncode}")
        print(f"錯誤訊息 (STDERR):\n{result.stderr.strip()}")
        print("\n--- ✅ 測試結束：成功重現錯誤 ---")
        sys.exit(0) # 退出碼 0 代表此測試成功
    elif result.returncode != 0:
        print("\n🤔 [預期外的失敗] 依賴安裝失敗，但原因不是缺少 pip。")
        print(f"返回碼: {result.returncode}")
        print(f"STDOUT:\n{result.stdout.strip()}")
        print(f"STDERR:\n{result.stderr.strip()}")
        print("\n--- ❌ 測試結束：未能按預期重現錯誤 ---")
        sys.exit(1)
    else:
        print("\n🤔 [預期外的成功] 依賴安裝成功了。")
        print("這意味著 'uv venv' 在此環境中確實安裝了 pip，問題可能更複雜。")
        print(f"STDOUT:\n{result.stdout.strip()}")
        print("\n--- ❌ 測試結束：未能重現錯誤 ---")
        sys.exit(1)

if __name__ == "__main__":
    main()
