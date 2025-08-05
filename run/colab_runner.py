# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║    🐦‍🔥 鳳凰之心 - V63 作戰指揮中心 (加速安裝版)                  🐦‍🔥 ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║ - V63 更新日誌:                                                      ║
# ║   - **安裝器修正**: 移除 `uv` 不支援的 `--ignore-installed` 參數。    ║
# ║   - **版本號統一**: 將顯示版本全面更新至 V63。                         ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

#@title 🐦‍🔥 鳳凰之心 V63 作戰指揮中心 { vertical-output: true, display-mode: "form" }
#@markdown ---
#@markdown ### **Part 1: 專案與環境設定**
#@markdown > **設定 Git 倉庫、分支或標籤，以及專案資料夾。**
#@markdown ---
#@markdown **後端程式碼倉庫 (REPOSITORY_URL)**
REPOSITORY_URL = "https://github.com/hsp1234-web/WEB_0802.git" #@param {type:"string"}
#@markdown **後端版本分支或標籤 (TARGET_BRANCH_OR_TAG)**
TARGET_BRANCH_OR_TAG = "0.8.1" #@param {type:"string"}
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

# V65: Simplified color scheme
ANSI_COLORS = {
    "SUCCESS": "\033[32m",  # Green
    "WARN": "\033[33m",     # Yellow
    "ERROR": "\033[31m",    # Red
    "CRITICAL": "\033[31m", # Red
    "RESET": "\033[0m"      # Reset color
}

def colorize(text, level):
    """Wraps text in ANSI color codes based on the log level."""
    color_code = ANSI_COLORS.get(level, "")
    reset_code = ANSI_COLORS["RESET"]
    return f"{color_code}{text}{reset_code}"

class DisplayManager:
    """顯示管理器：在背景執行緒中負責繪製純文字動態儀表板。"""
    def __init__(self, log_manager, stats_dict, refresh_rate):
        self._log_manager = log_manager
        self._stats = stats_dict
        self._refresh_rate = refresh_rate
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _build_output_buffer(self) -> list[str]:
        """建立儀表板的輸出內容緩衝區。"""
        output_buffer = []

        # V63: 加速安裝版
        output_buffer.append("🐦‍🔥 鳳凰之心 - V63 作戰指揮中心 (加速安裝版) 🐦‍🔥")
        # V65: Add a blank line for spacing after title
        output_buffer.append("")

        logs_to_display = self._log_manager.get_display_logs()
        for log in logs_to_display:
            ts = log['timestamp'].strftime('%H:%M:%S')
            level = log['level']
            padded_level = f"[{level:^8}]"
            colored_level = colorize(padded_level, level)
            output_buffer.append(f"[{ts}] {colored_level} {log['message']}")

        if self._stats.get('proxy_url'):
            # Add a blank line for spacing if there are logs
            if logs_to_display:
                output_buffer.append("")
            output_buffer.append(f"✅ 代理連結已生成: {self._stats['proxy_url']}")

        try:
            import psutil
            cpu_percent = psutil.cpu_percent()
            ram_percent = psutil.virtual_memory().percent
            cpu_text = f"{cpu_percent:5.1f}%"
            ram_text = f"{ram_percent:5.1f}%"
        except ImportError:
            cpu_text = "  N/A "
            ram_text = "  N/A "

        elapsed_time = time.monotonic() - self._stats.get("start_time_monotonic", time.monotonic())
        minutes, seconds = divmod(elapsed_time, 60)

        output_buffer.append("")
        status_line = (
            f"⏱️ {int(minutes):02d}分{int(seconds):02d}秒 | "
            f"💻 CPU: {cpu_text} | "
            f"🧠 RAM: {ram_text} | "
            f"🔥 狀態: {self._stats.get('status', '初始化...')}"
        )
        output_buffer.append(status_line)
        return output_buffer

    def _run(self):
        """顯示執行緒的主迴圈，負責定時重繪儀表板。"""
        while not self._stop_event.is_set():
            try:
                output_buffer = self._build_output_buffer()
                clear_output(wait=True)
                print("\n".join(output_buffer), flush=True)
                time.sleep(self._refresh_rate)
            except Exception as e:
                print(f"\nDisplayManager 執行緒發生錯誤: {e}")
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

            # V67 (Jules): 修正 PYTHONPATH，將 src 目錄加入，解決絕對路徑導入問題
            src_path = project_path / "src"
            existing_python_path = os.environ.get('PYTHONPATH', '')
            new_python_path = f"{src_path}{os.pathsep}{existing_python_path}" if existing_python_path else str(src_path)

            process_env.update({
                "VIRTUAL_ENV": str(venv_python.parent.parent),
                "PATH": f"{venv_python.parent}:{os.environ.get('PATH', '')}",
                "PYTHONUNBUFFERED": "1",
                "PYTHONPATH": new_python_path
            })
            self._log_manager.log("DEBUG", f"設定子進程 PYTHONPATH: {new_python_path}")

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

            # V55.1 修正：重新加入防禦性的 pip 引導程序，以應對 uv venv 在某些環境下可能不會安裝 pip 的偶發性問題。
            # 這是根據 marker.MD 的歷史經驗和使用者回報的錯誤日誌所做的決定。
            self._log_manager.log("INFO", "引導程序：確保 pip 已安裝...")
            bootstrap_command = ["uv", "pip", "install", "--python", str(venv_python), "pip", "wheel"]
            result = subprocess.run(bootstrap_command, check=False, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0:
                self._log_manager.log("CRITICAL", f"引導程序安裝 pip 失敗:\n{result.stderr}")
                return None

            # V66 (Jules): 修正為安裝所有必要的相依性檔案，而不僅僅是核心檔案
            # 這樣可以確保 Colab 環境與開發環境一致，解決缺少 'python-multipart' 的問題
            requirements_files = [
                "requirements/requirements-core.txt",
                "requirements/dev.txt"
            ]

            for req_file_name in requirements_files:
                self._log_manager.log("INFO", f"正在安裝相依性檔案: {req_file_name}...")
                requirements_path = project_path / req_file_name
                if not requirements_path.is_file():
                    self._log_manager.log("CRITICAL", f"找不到依賴檔案: {requirements_path}")
                    return None

                # 使用 uv 直接從檔案安裝，更有效率
                install_command = ["uv", "pip", "install", "--python", str(venv_python), "-r", str(requirements_path)]
                self._stats['status'] = f"⚙️ 正在安裝 {req_file_name}..."
                result = subprocess.run(install_command, check=False, capture_output=True, text=True, encoding='utf-8')

                if result.returncode != 0:
                    self._log_manager.log("CRITICAL", f"安裝 {req_file_name} 失敗:\n{result.stderr}")
                    # 顯示詳細的 uv 輸出以幫助除錯
                    self._log_manager.log("DEBUG", f"uv stdout:\n{result.stdout}")
                    return None
                self._log_manager.log("SUCCESS", f"✅ {req_file_name} 安裝成功。")

            self._log_manager.log("SUCCESS", "✅ 所有相依性套件已成功安裝。")
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
            max_retries = 10
            retry_delay = 3
            url_obtained = False
            for attempt in range(max_retries):
                try:
                    log_manager.log("INFO", f"正在嘗試取得代理連結... (第 {attempt + 1}/{max_retries} 次)")
                    url = colab_output.eval_js(f'google.colab.kernel.proxyPort({API_PORT})')
                    if url and url.strip():
                        shared_stats['proxy_url'] = url
                        log_manager.log("SUCCESS", "✅ 成功取得代理連結！")
                        url_obtained = True
                        break
                    else:
                        log_manager.log("WARN", f"取得的代理連結為空，將於 {retry_delay} 秒後重試...")
                except Exception as e:
                    log_manager.log("WARN", f"取得代理連結時發生錯誤: {e}，將於 {retry_delay} 秒後重試...")
                time.sleep(retry_delay)

            if not url_obtained:
                shared_stats['status'] = "❌ 取得代理連結失敗"
                log_manager.log("CRITICAL", f"在 {max_retries} 次嘗試後，仍無法取得有效的代理連結。")
        else:
            shared_stats['status'] = "❌ 伺服器啟動超時"
            log_manager.log("CRITICAL", f"伺服器在 {SERVER_READY_TIMEOUT} 秒內未能就緒。")

        # Keep the main thread alive to allow background threads to run
        while server_manager._thread.is_alive():
            time.sleep(1)

    except KeyboardInterrupt:
        if log_manager: log_manager.log("WARN", "🛑 偵測到使用者手動中斷...")
    except Exception as e:
        error_msg = f"❌ 發生未預期的致命錯誤: {e}"
        if log_manager: log_manager.log("CRITICAL", error_msg)
        else: print(error_msg)
    finally:
        # Stop the threads first
        if display_manager and display_manager._thread.is_alive():
            display_manager.stop()
        if server_manager:
            server_manager.stop()

        # --- V65: Final Render and Post-execution controls ---
        end_time = datetime.now(pytz.timezone(TIMEZONE))
        if log_manager and display_manager:
            # Do one last render to ensure the final state is on screen
            clear_output()
            final_output_buffer = display_manager._build_output_buffer()
            final_screen_text = "\n".join(final_output_buffer)
            print(final_screen_text)

            print("\n--- ✅ 所有任務完成，系統已安全關閉 ---")

            # Prepare data for copy buttons
            from IPython.display import display, HTML
            import json
            full_log_history = log_manager.get_full_history()

            # Escape strings for JavaScript
            js_escaped_screen_text = json.dumps(final_screen_text)
            js_escaped_full_logs = json.dumps(
                "\\n".join([f"[{log['timestamp'].isoformat()}] [{log['level']}] {log['message']}" for log in full_log_history])
            )

            # Display HTML buttons with embedded JavaScript for copying
            display(HTML(f"""
                <script>
                    function copyToClipboard(text) {{
                        navigator.clipboard.writeText(text).then(function() {{
                            console.log('Copying to clipboard was successful!');
                        }}, function(err) {{
                            console.error('Could not copy text: ', err);
                        }});
                    }}
                </script>
                <button onclick='copyToClipboard({js_escaped_screen_text})'>📋 複製上方儲存格輸出</button>
                <button onclick='copyToClipboard({js_escaped_full_logs})'>📄 複製完整詳細日誌</button>
            """))

            archive_reports(log_manager, start_time, end_time, shared_stats.get('status', '未知'))

if __name__ == "__main__":
    main()
