# -*- coding: utf-8 -*-
# 這是一個本地測試腳本，用於驗證 colab_runner.py 的核心後端啟動邏輯。
# 它移除了所有 Colab UI 和顯示邏輯，專注於以下流程：
# 1. 準備環境 (git clone, uv venv, uv pip install)
# 2. 使用修正後的邏輯啟動後端伺服器 (透過 run_server_only.py)
# 3. 監控日誌以確認伺服器是否成功啟動。

import os
import sys
import shutil
import subprocess
from pathlib import Path
import time
import threading

# --- 設定 (從 colab_runner.py 複製而來) ---
REPOSITORY_URL = "https://github.com/hsp1234-web/WEB_0802.git"
TARGET_BRANCH_OR_TAG = "0.8.1"
PROJECT_FOLDER_NAME = "WEB1_local_test" # 使用不同的資料夾以避免衝突
FORCE_REPO_REFRESH = True
API_PORT = 8088
SERVER_READY_TIMEOUT = 60 # 給予更長的超時時間以應對首次安裝

class LocalServerManager:
    """
    colab_runner.py 中 ServerManager 的簡化版本，
    專為本地命令列測試而設計。
    """
    def __init__(self):
        self.server_process = None
        self.server_ready = threading.Event()
        self._stop_event = threading.Event()

    def start_and_wait(self):
        """啟動伺服器並等待其就緒或失敗。"""
        try:
            env_paths = self._setup_environment()
            if not env_paths:
                print("❌ 環境準備失敗")
                return False

            print("🚀 正在啟動伺服器...")
            project_path, venv_python = env_paths["project_path"], env_paths["venv_python"]

            process_env = os.environ.copy()
            src_path = project_path / "src"
            existing_python_path = process_env.get('PYTHONPATH', '')
            new_python_path = f"{src_path}{os.pathsep}{existing_python_path}" if existing_python_path else str(src_path)
            process_env['PYTHONPATH'] = new_python_path

            print(f"設定子進程 PYTHONPATH: {new_python_path}")

            # 這是我們在第二階段修復的核心邏輯
            # 我們需要使用主專案中的、已經被我們修改過的啟動腳本，而不是 clone 下來的新腳本
            # 因此，我們使用絕對路徑來指定它
            launcher_script_path = Path(".").resolve() / "scripts" / "run_server_only.py"
            launcher_command = [
                str(venv_python),
                str(launcher_script_path),
                "--port",
                str(API_PORT)
            ]
            print(f"正在執行啟動器: {' '.join(launcher_command)}")

            self.server_process = subprocess.Popen(
                launcher_command,
                cwd=str(project_path),
                env=process_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                bufsize=1 # 使用行緩衝
            )
            print(f"子進程已啟動 (PID: {self.server_process.pid})。等待 Uvicorn 就緒...")

            start_time = time.monotonic()
            for line in iter(self.server_process.stdout.readline, ''):
                if not line:
                    break
                print(f"   [後端日誌] {line.strip()}")
                if "Uvicorn running on" in line or "Application startup complete" in line:
                    print("\n✅ 伺服器已成功啟動！測試通過。")
                    self.server_ready.set()
                    return True
                if time.monotonic() - start_time > SERVER_READY_TIMEOUT:
                    print(f"\n❌ 測試失敗：等待伺服器就緒超時 ({SERVER_READY_TIMEOUT} 秒)。")
                    return False

            # 如果日誌流結束但伺服器仍未就緒
            print("\n❌ 測試失敗：後端進程在就緒前已終止。")
            return False

        except Exception as e:
            print(f"❌ 發生致命錯誤: {e}")
            return False
        finally:
            self.stop()

    def _setup_environment(self):
        """從 colab_runner.py 複製而來的環境準備邏輯。"""
        try:
            print("=== [1/2] 準備專案環境 ===")
            base_path = Path(".").resolve()
            project_path = base_path / PROJECT_FOLDER_NAME

            if FORCE_REPO_REFRESH and project_path.exists():
                print(f"正在刪除舊資料夾: {project_path}")
                shutil.rmtree(project_path)

            print(f"正在從 Git 下載 (分支: {TARGET_BRANCH_OR_TAG})...")
            git_command = ["git", "clone", "--branch", TARGET_BRANCH_OR_TAG, "--depth", "1", REPOSITORY_URL, str(project_path)]
            result = subprocess.run(git_command, check=False, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0:
                print(f"❌ Git clone 失敗:\n{result.stderr}")
                return None

            print("正在建立虛擬環境...")
            venv_path = project_path / ".venv"
            result = subprocess.run(["uv", "venv", str(venv_path)], check=False, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0:
                print(f"❌ 建立虛擬環境失敗:\n{result.stderr}")
                return None

            venv_python = venv_path / "bin" / "python"

            print("正在安裝相依性套件 (dev.txt)...")
            requirements_path = project_path / "requirements/dev.txt"
            install_command = ["uv", "pip", "install", "--python", str(venv_python), "-r", str(requirements_path)]
            result = subprocess.run(install_command, check=False, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0:
                print(f"❌ 安裝 dev.txt 失敗:\n{result.stderr}")
                return None

            print("✅ 環境準備完成。")
            return {"project_path": project_path, "venv_python": venv_python}
        except Exception as e:
            print(f"❌ 環境準備過程中發生錯誤: {e}")
            return None

    def stop(self):
        """停止伺服器子進程。"""
        if self.server_process and self.server_process.poll() is None:
            print("正在終止伺服器進程...")
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                self.server_process.kill()
            print("伺服器進程已停止。")

if __name__ == "__main__":
    print("--- 啟動 Colab Runner 本地邏輯測試器 ---")
    manager = LocalServerManager()
    success = manager.start_and_wait()

    # 清理測試用的專案資料夾
    test_project_path = Path(".").resolve() / PROJECT_FOLDER_NAME
    if test_project_path.exists():
        print(f"正在清理測試專案資料夾: {test_project_path}")
        shutil.rmtree(test_project_path)

    if success:
        print("\n🎉🎉🎉 驗證成功！核心啟動邏輯運作正常。 🎉🎉🎉")
        sys.exit(0)
    else:
        print("\n🔥🔥🔥 驗證失敗。 🔥🔥🔥")
        sys.exit(1)
