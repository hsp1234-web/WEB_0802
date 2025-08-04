import subprocess
import time
import sys
import os
from pathlib import Path

# --- 配置 ---
PROBE_VENV_DIR = ".venv_legacy_probe"
REQUIREMENTS_FILE = "requirements/base.txt"
LOG_PREFIX = "[傳統方法探測器]"

def run_command(command: list[str], description: str) -> None:
    """執行一個命令並打印其輸出"""
    print(f"{LOG_PREFIX} 執行中: {description}...")
    print(f"{LOG_PREFIX} 命令: {' '.join(command)}")

    # 使用 PYTHONUNBUFFERED=1 確保子進程輸出是即時的
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    process = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding='utf-8',
        env=env
    )

    if process.returncode != 0:
        print(f"❌ {LOG_PREFIX} 錯誤: {description} 失敗。返回碼: {process.returncode}")
        print("--- STDOUT ---")
        print(process.stdout)
        print("--- STDERR ---")
        print(process.stderr)
        print("----------------")
        sys.exit(1)
    else:
        print(f"✅ {LOG_PREFIX} 成功: {description} 完成。")
        # 為了簡潔，只在需要時打印詳細輸出
        # print(process.stdout)
    return

def main():
    """主執行函數"""
    start_time = time.time()

    # 確保我們在專案根目錄
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    print(f"{LOG_PREFIX} 當前工作目錄: {os.getcwd()}")

    # 1. 建立虛擬環境
    print("\n" + "="*50)
    print("步驟 1: 建立虛擬環境 (使用 python -m venv)")
    print("="*50)
    venv_path = project_root / PROBE_VENV_DIR
    if venv_path.exists():
        print(f"{LOG_PREFIX} 虛擬環境 '{PROBE_VENV_DIR}' 已存在，將先刪除...")
        run_command(["rm", "-rf", str(venv_path)], "清理舊的虛擬環境")

    venv_setup_start = time.time()
    # 獲取當前運行的 python 解譯器路徑
    python_executable = sys.executable
    run_command([python_executable, "-m", "venv", str(venv_path)], "使用 python -m venv 建立虛擬環境")
    venv_setup_time = time.time() - venv_setup_start
    print(f"{LOG_PREFIX} 虛擬環境建立耗時: {venv_setup_time:.2f} 秒")

    # 2. 安裝依賴
    print("\n" + "="*50)
    print("步驟 2: 安裝依賴 (使用 pip)")
    print("="*50)
    pip_executable = str(venv_path / "bin" / "python")

    install_deps_start = time.time()
    run_command([
        pip_executable, "-m", "pip", "install",
        "-r", REQUIREMENTS_FILE,
        "--ignore-installed" # 增加此選項以模擬更真實的隔離環境行為
    ], f"使用 pip 安裝依賴到 '{PROBE_VENV_DIR}'")
    install_deps_time = time.time() - install_deps_start
    print(f"{LOG_PREFIX} 依賴安裝耗時: {install_deps_time:.2f} 秒")

    # 3. 總結報告
    total_time = time.time() - start_time
    print("\n" + "="*50)
    print("📊 探測任務完成: 性能報告 (傳統方法)")
    print("="*50)
    print(f"虛擬環境建立 ({'python -m venv'}): {venv_setup_time:.2f} 秒")
    print(f"依賴安裝 ({'pip install'}): {install_deps_time:.2f} 秒")
    print("-" * 50)
    print(f"總環境準備耗時: {total_time:.2f} 秒")
    print("\n✅ {LOG_PREFIX} 探測成功！數據已收集，可用於與新方法進行比較。")

if __name__ == "__main__":
    main()
