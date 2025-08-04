# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║    🚀 鳳凰之心 - V55 作戰指揮中心 (最終交付版)                     ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║ - V55 更新日誌:                                                      ║
# ║   - **最終交付**: 根據要求撰寫 marker.MD 技術文件。                ║
# ║   - **版本更新**: 將預設分支更新至 0.7.0。                           ║
# ║   - V54: 修正日誌等級置中對齊。                                    ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

#@title 💎 鳳凰之心 V55 作戰指揮中心 (純文字模式) { vertical-output: true, display-mode: "form" }
#@markdown ---
#@markdown ### **Part 1: 專案與環境設定**
#@markdown > **設定 Git 倉庫、分支或標籤，以及專案資料夾。**
#@markdown ---
#@markdown **後端程式碼倉庫 (REPOSITORY_URL)**
REPOSITORY_URL = "https://github.com/hsp1234-web/WEB_0802.git" #@param {type:"string"}
#@markdown **後端版本分支或標籤 (TARGET_BRANCH_OR_TAG)**
TARGET_BRANCH_OR_TAG = "0.7.0" #@param {type:"string"}
#@markdown **專案資料夾名稱 (PROJECT_FOLDER_NAME)**
PROJECT_FOLDER_NAME = "WEB1" #@param {type:"string"}
#@markdown **強制刷新後端程式碼 (FORCE_REPO_REFRESH)**
FORCE_REPO_REFRESH = True #@param {type:"boolean"}
#@markdown **後端 API 服務埠號 (API_PORT)**
API_PORT = 8088 #@param {type:"integer"}

#@markdown ---
#@markdown ### **Part 2: 儀表板與監控設定**
#@markdown > **設定儀表板的視覺與行為。**
#@markdown ---
#@markdown **儀表板更新頻率 (秒) (UI_REFRESH_SECONDS)**
UI_REFRESH_SECONDS = 0.5 #@param {type:"number"}
#@markdown **日誌顯示行數 (LOG_DISPLAY_LINES)**
LOG_DISPLAY_LINES = 30 #@param {type:"integer"}
#@markdown **時區設定 (TIMEZONE)**
TIMEZONE = "Asia/Taipei" #@param {type:"string"}

#@markdown ---
#@markdown ### **Part 3: 日誌等級可見性**
#@markdown > **勾選您想在儀表板上看到的日誌等級。**
#@markdown ---
SHOW_LOG_LEVEL_BATTLE = True #@param {type:"boolean"}
SHOW_LOG_LEVEL_SUCCESS = True #@param {type:"boolean"}
SHOW_LOG_LEVEL_INFO = True #@param {type:"boolean"}
SHOW_LOG_LEVEL_WARN = True #@param {type:"boolean"}
SHOW_LOG_LEVEL_ERROR = True #@param {type:"boolean"}
SHOW_LOG_LEVEL_CRITICAL = True #@param {type:"boolean"}
SHOW_LOG_LEVEL_DEBUG = False #@param {type:"boolean"}

#@markdown ---
#@markdown ### **Part 4: 報告與歸檔設定**
#@markdown > **設定在任務結束時如何儲存報告。**
#@markdown ---
#@markdown **日誌歸檔資料夾 (LOG_ARCHIVE_ROOT_FOLDER)**
LOG_ARCHIVE_ROOT_FOLDER = "paper" #@param {type:"string"}
#@markdown **伺服器就緒等待超時 (秒) (SERVER_READY_TIMEOUT)**
SERVER_READY_TIMEOUT = 45 #@param {type:"integer"}

#@markdown ---
#@markdown > **設定完成後，點擊此儲存格左側的「執行」按鈕。**
#@markdown ---

# ==============================================================================
# SECTION 0: 環境準備與核心依賴導入
# ==============================================================================
try:
    import psutil
except ImportError:
    print("正在安裝 psutil...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "psutil"])
    import psutil
try:
    import pytz
except ImportError:
    print("正在安裝 pytz...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "pytz"])
    import pytz

import os
import sys
import shutil
import subprocess
from pathlib import Path
import time
from datetime import datetime
import threading
from collections import deque
from IPython.display import clear_output
from google.colab import output as colab_output

# ==============================================================================
# SECTION 1: 管理器類別定義 (Managers)
# ==============================================================================

class LogManager:
    """日誌管理器：負責記錄、過濾和儲存所有日誌訊息。"""
    def __init__(self, max_lines, timezone_str, log_levels_to_show):
        self._log_deque = deque(maxlen=max_lines)
        self._lock = threading.Lock()
        self.timezone = pytz.timezone(timezone_str)
        self.log_levels_to_show = log_levels_to_show

    def log(self, level: str, message: str):
        with self._lock:
            log_entry = {"timestamp": datetime.now(self.timezone), "level": level.upper(), "message": str(message)}
            self._log_deque.append(log_entry)

    def get_display_logs(self) -> list:
        with self._lock:
            all_logs = list(self._log_deque)
            return [log for log in all_logs if self.log_levels_to_show.get(f"SHOW_LOG_LEVEL_{log['level']}", False)]

    def get_full_history(self) -> list:
        with self._lock:
            return list(self._log_deque)

class DisplayManager:
    """顯示管理器：在背景執行緒中負責繪製純文字動態儀表板。"""
    def __init__(self, log_manager, stats_dict, refresh_rate):
        self._log_manager = log_manager
        self._stats = stats_dict
        self._refresh_rate = refresh_rate
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        while not self._stop_event.is_set():
            try:
                output_buffer = []

                output_buffer.append("🚀 鳳凰之心 V55 作戰指揮中心")
                output_buffer.append("="*60)

                logs_to_display = self._log_manager.get_display_logs()
                for log in logs_to_display:
                    ts = log['timestamp'].strftime('%H:%M:%S')
                    output_buffer.append(f"[{ts}] [{log['level']:^8}] {log['message']}")

                output_buffer.append("="*60)

                if self._stats.get('proxy_url'):
                    output_buffer.append(f"✅ 代理連結已生成: {self._stats['proxy_url']}")
                    output_buffer.append("="*60)

                cpu = psutil.cpu_percent()
                ram = psutil.virtual_memory().percent
                elapsed_time = time.monotonic() - self._stats["start_time_monotonic"]
                minutes, seconds = divmod(elapsed_time, 60)

                status_line = (
                    f"⏱️ {int(minutes):02d}分{int(seconds):02d}秒 | "
                    f"💻 CPU: {cpu:5.1f}% | "
                    f"🧠 RAM: {ram:5.1f}% | "
                    f"🔥 狀態: {self._stats.get('status', '初始化...')}"
                )
                output_buffer.append(status_line)

                clear_output(wait=True)
                print("\n".join(output_buffer), flush=True)

                time.sleep(self._refresh_rate)
            except Exception as e:
                print(f"\nDisplayManager Error: {e}")
                time.sleep(5)

    def start(self): self._thread.start()
    def stop(self): self._stop_event.set(); self._thread.join(timeout=2)

class ServerManager:
    """伺服器管理器：負責啟動、停止和監控 Uvicorn 子進程。"""
    def __init__(self, log_manager, stats_dict):
        self._log_manager = log_manager
        self._stats = stats_dict
        self.server_process = None
        self.server_ready_event = threading.Event()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        try:
            env_paths = self._setup_environment()
            if not env_paths or self._stop_event.is_set():
                self._stats['status'] = "❌ 環境準備失敗"; return

            self._stats['status'] = "🚀 正在啟動伺服器..."
            self._log_manager.log("BATTLE", "=== [2/2] 正在啟動後端伺服器 ===")

            project_path, venv_python = env_paths["project_path"], env_paths["venv_python"]
            process_env = os.environ.copy()
            process_env.update({"VIRTUAL_ENV": str(venv_python.parent.parent), "PATH": f"{venv_python.parent}:{os.environ.get('PATH', '')}", "PYTHONUNBUFFERED": "1"})

            uvicorn_command = [str(venv_python), "-m", "uvicorn", "src.phoenix_core.main:app", "--host", "0.0.0.0", "--port", str(API_PORT), "--workers", "1"]
            self.server_process = subprocess.Popen(
                uvicorn_command, cwd=str(project_path), env=process_env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', preexec_fn=os.setsid
            )
            self._log_manager.log("INFO", f"Uvicorn 子進程已啟動 (PID: {self.server_process.pid})。")

            for line in iter(self.server_process.stdout.readline, ''):
                if self._stop_event.is_set(): break
                self._log_manager.log("DEBUG", line.strip())
                if "Uvicorn running on" in line:
                    self._stats['status'] = "✅ 伺服器運行中"; self._log_manager.log("SUCCESS", "伺服器已就緒！"); self.server_ready_event.set()

            self.server_process.wait()
            if not self.server_ready_event.is_set():
                self._stats['status'] = "❌ 伺服器啟動失敗"; self._log_manager.log("CRITICAL", "伺服器進程在就緒前已終止。")

        except Exception as e:
            self._stats['status'] = "❌ 發生致命錯誤"; self._log_manager.log("CRITICAL", f"ServerManager 執行緒出錯: {e}")
        finally:
             self._stats['status'] = "⏹️ 已停止"

    def _setup_environment(self):
        try:
            self._stats['status'] = "設定環境..."; self._log_manager.log("BATTLE", "=== [1/2] 準備專案環境 ===")
            base_path = Path(".").resolve()
            project_path = base_path / PROJECT_FOLDER_NAME

            if FORCE_REPO_REFRESH and project_path.exists(): shutil.rmtree(project_path); self._log_manager.log("INFO", f"舊資料夾已刪除: {project_path}")

            self._log_manager.log("INFO", f"正在從 Git 下載 (分支: {TARGET_BRANCH_OR_TAG})...")
            git_command = ["git", "clone", "--branch", TARGET_BRANCH_OR_TAG, "--depth", "1", REPOSITORY_URL, str(project_path)]
            result = subprocess.run(git_command, check=False, capture_output=True, text=True, encoding='utf-8');
            if result.returncode != 0: self._log_manager.log("CRITICAL", f"Git clone 失敗:\n{result.stderr}"); return None

            self._log_manager.log("INFO", "正在建立虛擬環境...")
            venv_path = project_path / ".venv"
            result = subprocess.run(["uv", "venv", str(venv_path)], check=False, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0: self._log_manager.log("CRITICAL", f"建立虛擬環境失敗:\n{result.stderr}"); return None

            venv_python = venv_path / "bin" / "python"
            self._log_manager.log("INFO", "引導程序：確保 pip 已安裝...")
            bootstrap_env = os.environ.copy()
            bootstrap_env["VIRTUAL_ENV"] = str(venv_path)
            bootstrap_env["PATH"] = f"{venv_path / 'bin'}:{bootstrap_env.get('PATH', '')}"
            bootstrap_command = ["uv", "pip", "install", "pip", "wheel"]
            result = subprocess.run(bootstrap_command, check=False, capture_output=True, text=True, encoding='utf-8', env=bootstrap_env)
            if result.returncode != 0: self._log_manager.log("CRITICAL", f"引導安裝 pip 失敗:\n{result.stderr}"); return None

            self._log_manager.log("INFO", "正在安裝核心依賴...")
            core_requirements_path = project_path / "requirements/requirements-core.txt"
            pip_install_command = [str(venv_python), "-m", "pip", "install", "-r", str(core_requirements_path)]
            result = subprocess.run(pip_install_command, check=False, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0: self._log_manager.log("CRITICAL", f"安裝依賴失敗:\n{result.stderr}"); return None

            self._log_manager.log("SUCCESS", "✅ 環境準備成功。")
            return {"project_path": project_path, "venv_python": venv_python}
        except Exception as e:
            self._log_manager.log("CRITICAL", f"環境準備失敗: {e}"); return None

    def start(self): self._thread.start()
    def stop(self):
        self._stop_event.set()
        if self.server_process and self.server_process.poll() is None:
            self._log_manager.log("INFO", "正在終止伺服器進程...")
            try:
                os.killpg(os.getpgid(self.server_process.pid), subprocess.signal.SIGTERM)
                self.server_process.wait(timeout=5)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try: os.killpg(os.getpgid(self.server_process.pid), subprocess.signal.SIGKILL)
                except ProcessLookupError: pass
        self._thread.join(timeout=2)

# ==============================================================================
# SECTION 2: 核心功能函式
# ==============================================================================

def archive_reports(log_manager, start_time, end_time, status):
    print("\n\n" + "="*60 + "\n--- 任務結束，開始執行自動歸檔 ---\n" + "="*60)
    try:
        root_folder = Path(LOG_ARCHIVE_ROOT_FOLDER)
        root_folder.mkdir(exist_ok=True)

        timezone = log_manager.timezone
        ts_folder_name = start_time.strftime('%Y-%m-%dT%H-%M-%S%z')
        report_dir = root_folder / ts_folder_name
        report_dir.mkdir(exist_ok=True)

        log_history = log_manager.get_full_history()

        detailed_log_content = f"# 詳細日誌\n\n```\n" + "\n".join([f"[{log['timestamp'].isoformat()}] [{log['level']}] {log['message']}" for log in log_history]) + "\n```"
        (report_dir / "詳細日誌.md").write_text(detailed_log_content, encoding='utf-8')

        duration = end_time - start_time
        perf_report_content = f"# 效能報告\n\n- **任務狀態**: {status}\n- **開始時間**: `{start_time.isoformat()}`\n- **結束時間**: `{end_time.isoformat()}`\n- **總耗時**: `{str(duration)}`\n"
        (report_dir / "效能報告.md").write_text(perf_report_content.strip(), encoding='utf-8')

        comprehensive_report = f"# 綜合報告\n\n{perf_report_content}\n{detailed_log_content}"
        (report_dir / "綜合報告.md").write_text(comprehensive_report, encoding='utf-8')

        print(f"✅ 報告已成功歸檔至: {report_dir}")
    except Exception as e:
        print(f"❌ 歸檔報告時發生錯誤: {e}")

# ==============================================================================
# SECTION 3: 主程式執行入口
# ==============================================================================

def main():
    """主執行函式，負責初始化管理器、協調流程並處理生命週期。"""
    shared_stats = {"start_time_monotonic": time.monotonic(), "status": "初始化...", "proxy_url": None}
    log_manager, display_manager, server_manager = None, None, None
    start_time = datetime.now(pytz.timezone(TIMEZONE))

    try:
        log_levels = {name: globals()[name] for name in globals() if name.startswith("SHOW_LOG_LEVEL_")}
        log_manager = LogManager(max_lines=LOG_DISPLAY_LINES, timezone_str=TIMEZONE, log_levels_to_show=log_levels)
        display_manager = DisplayManager(log_manager=log_manager, stats_dict=shared_stats, refresh_rate=UI_REFRESH_SECONDS)
        server_manager = ServerManager(log_manager=log_manager, stats_dict=shared_stats)

        display_manager.start()
        server_manager.start()

        server_ready = server_manager.server_ready_event.wait(timeout=SERVER_READY_TIMEOUT)

        if server_ready:
            url = colab_output.eval_js(f'google.colab.kernel.proxyPort({API_PORT})')
            shared_stats['proxy_url'] = url
        else:
            shared_stats['status'] = "❌ 伺服器啟動超時"
            log_manager.log("CRITICAL", f"伺服器在 {SERVER_READY_TIMEOUT} 秒內未能就緒。")

        while True:
            if not server_manager._thread.is_alive() and not shared_stats.get('proxy_url'):
                break
            time.sleep(1)

    except KeyboardInterrupt:
        if log_manager: log_manager.log("WARN", "🛑 偵測到使用者手動中斷...")
    except Exception as e:
        error_msg = f"❌ 發生未預期的致命錯誤: {e}"
        if log_manager: log_manager.log("CRITICAL", error_msg)
        else: print(error_msg)
    finally:
        if display_manager: display_manager.stop()
        if server_manager: server_manager.stop()

        end_time = datetime.now(pytz.timezone(TIMEZONE))
        if log_manager:
            archive_reports(log_manager, start_time, end_time, shared_stats.get('status', '未知'))

        print("\n--- ✅ 所有任務完成，系統已安全關閉 ---")

if __name__ == "__main__":
    main()
