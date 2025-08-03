# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║      📦 Phoenix Local Runner V1.0                                    ║
# ║         (專為本地開發與整合測試設計)                             ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 目的: 提供一個穩定、可預測的本地後端啟動流程。                 ║
# ║   - 設計: 一個簡單的、線性的腳本，負責準備環境並在前台啟動後端。   ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝
import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime

# --- 與 colab_runner.py 共享的輔助函式 ---

def get_dependency_free_timestamp():
    """一個在安裝依賴前可安全使用的、無外部依賴的時間戳函式。"""
    return datetime.now().strftime('%H:%M:%S')

def get_local_timestamp():
    """一個使用時區設定的時間戳函式，應在依賴安裝後使用。"""
    # 為了獨立性，即使可能已安裝，也延後導入
    try:
        import pytz
        # 假設一個預設時區，因為此腳本沒有 UI 來輸入
        return datetime.now(pytz.timezone("Asia/Taipei")).strftime('%H:%M:%S')
    except ImportError:
        return get_dependency_free_timestamp()

def run_local_backend_process(repo_root: Path, config_file_path: Path):
    """
    在前台運行 backend_worker 並打印日誌。
    """
    venv_python = repo_root / ".venv" / "bin" / "python"
    backend_script_path = repo_root / "scripts" / "backend_worker.py"

    if not backend_script_path.exists():
        raise FileNotFoundError(f"找不到後端工作者腳本: {backend_script_path}")

    command = [str(venv_python), str(backend_script_path), "--config", str(config_file_path)]

    print(f"[{get_dependency_free_timestamp()}] [本地模式] 正在啟動後端工作者，日誌將直接輸出到此處...")
    print(f"[{get_dependency_free_timestamp()}] 命令: {' '.join(command)}")

    process = subprocess.Popen(
        command,
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        bufsize=1
    )
    for line in iter(process.stdout.readline, ''):
        print(line, end='')
    process.wait()
    print(f"[{get_local_timestamp()}] [本地模式] 後端工作者已結束。")

def main():
    """
    主執行函式，執行本地啟動流程。
    """
    print(f"[{get_dependency_free_timestamp()}] 🔥 Phoenix 本地執行器已啟動...")
    try:
        repo_root = Path(".").resolve()

        # 1. 設定虛擬環境
        venv_dir = repo_root / ".venv"
        print(f"[{get_dependency_free_timestamp()}] 正在設定 Python 虛擬環境於: {venv_dir}")
        if not venv_dir.is_dir():
            subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)

        # 2. 安裝依賴
        venv_python = str(venv_dir / "bin" / "python")
        requirements_file = repo_root / "requirements" / "dev.txt"
        if not requirements_file.exists():
            raise FileNotFoundError(f"找不到依賴檔案: {requirements_file}")

        print(f"[{get_dependency_free_timestamp()}] 正在從 {requirements_file} 安裝依賴...")
        subprocess.run([venv_python, "-m", "pip", "install", "-r", str(requirements_file)], check=True)

        # 3. 建立設定檔
        print(f"[{get_dependency_free_timestamp()}] 正在生成 config.json...")
        config_file_path = repo_root / "config.json"
        with open(config_file_path, "w", encoding="utf-8") as f:
            # 提供一個預設的時區設定
            json.dump({"system_settings": {"timezone": "Asia/Taipei"}}, f, indent=4)

        print(f"[{get_dependency_free_timestamp()}] ✅ 環境準備完成。")

        # 4. 啟動後端
        run_local_backend_process(repo_root, config_file_path)

    except Exception as e:
        error_message = f"❌ 發生致命錯誤: {e}"
        print(error_message, file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
