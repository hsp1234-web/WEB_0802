# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║               📊 報告中心 V25.1 (穩定埠號版)                       ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 架構：採非同步儀表板架構，提供流暢的即時體驗。                 ║
# ║   - 功能：按需預覽報告、一鍵歸檔所有報告、複製儀表板狀態。         ║
# ║   - 隔離：為報告生成器建立獨立 Venv，不污染主環境。                ║
# ║   - 穩定：動態尋找可用埠號，解決 `Address already in use` 問題。   ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

#@title 📊 報告中心 v25.1 { vertical-output: true, display-mode: "form" }
#@markdown ---
#@markdown ### **Part 1: 基礎設定**
#@markdown > **指定包含 `state.db` 的專案資料夾，以及報告的歸檔位置。**
#@markdown ---
#@markdown **專案資料夾名稱 (PROJECT_FOLDER_NAME)**
PROJECT_FOLDER_NAME = "WEB1" #@param {type:"string"}
#@markdown **報告歸檔資料夾 (REPORT_ARCHIVE_FOLDER)**
#@markdown > **報告將歸檔至 `/content/<專案資料夾>/<此處指定的名稱>`**
REPORT_ARCHIVE_FOLDER = "作戰日誌歸檔" #@param {type:"string"}
#@markdown ---
#@markdown > **點擊「執行」以啟動報告中心儀表板。**
#@markdown ---

import os
import sys
import shutil
import subprocess
from pathlib import Path
import time
import json
import threading
import asyncio
from collections import deque
import pytz
import traceback

try:
    from IPython.display import display, HTML, clear_output
    import nest_asyncio
    from aiohttp import web
except ImportError:
    print("正在安裝報告中心核心依賴 (ipython, nest_asyncio, aiohttp)...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "ipython", "nest_asyncio", "aiohttp"])
    from IPython.display import display, HTML, clear_output
    import nest_asyncio
    from aiohttp import web

from core_utils.port_manager import find_available_port, kill_processes_using_port

nest_asyncio.apply()

# --- 全域共享狀態 ---
shared_state = {
    "status": "初始化中...",
    "logs": deque(maxlen=50),
    "api_port": None,
}
state_lock = threading.Lock()
api_app_runner = None

# --- 後端邏輯 ---

def update_state(status=None, log=None, api_port=None):
    with state_lock:
        if status:
            shared_state["status"] = status
        if log:
            shared_state["logs"].append(f"[{time.strftime('%H:%M:%S')}] {log}")
        if api_port is not None:
            shared_state["api_port"] = api_port

def background_worker(project_path):
    """在背景準備報告生成環境 (Venv, Dependencies)"""
    try:
        app_path = project_path / "apps" / "report_generator"
        venv_path = app_path / ".venv"
        req_file = app_path / "requirements.txt"

        update_state(status="環境準備中", log="正在檢查報告生成器環境...")

        if not app_path.is_dir() or not req_file.is_file():
            raise FileNotFoundError(f"找不到報告生成器應用或其需求檔案: {app_path}")

        if not venv_path.exists():
            update_state(log=f"未找到 Venv，正在建立於 {venv_path}...")
            uv_cmd = ["uv", "venv", str(venv_path), "--python", sys.executable]
            subprocess.run(uv_cmd, capture_output=True, text=True, cwd=project_path, check=True)
            update_state(log="✅ Venv 建立成功。")

        update_state(status="安裝依賴中", log="正在使用 uv 安裝報告依賴...")
        python_executable = str(venv_path / "bin" / "python")
        uv_install_cmd = ["uv", "pip", "install", "-r", str(req_file), "--python", python_executable]
        subprocess.run(uv_install_cmd, capture_output=True, text=True, cwd=project_path, check=True)
        update_state(log="✅ 依賴安裝成功。")

        update_state(status="準備就緒", log="報告中心已準備就緒，請點擊按鈕操作。")
    except Exception as e:
        update_state(status="環境準備失敗", log=f"❌ {e}\n{traceback.format_exc()}")

def run_report_generation(project_path):
    """透過直接匯入和呼叫函式來執行核心報告生成邏輯。"""
    try:
        from scripts.generate_report import ReportGenerator

        db_file = project_path / "state.db"
        config_file = project_path / "config.json"

        if not db_file.exists():
            (project_path / "logs").mkdir(exist_ok=True)
            (project_path / "logs" / "summary_report.md").write_text("# 綜合戰情簡報\n\n錯誤：找不到 state.db，無法生成報告。")
            raise FileNotFoundError("找不到 state.db，無法生成報告。")
        if not config_file.exists():
            # 為防萬一，建立一個預設設定檔
            config_file.write_text(json.dumps({"TIMEZONE": "Asia/Taipei"}))

        # 實例化報告生成器並執行
        generator = ReportGenerator(db_path=db_file, config_path=config_file)
        generator.generate_all_reports()
        update_state(log="✅ 核心報告腳本執行成功。")
    except Exception as e:
        update_state(log=f"❌ 報告生成失敗: {e}")
        # 重新引發異常，以便上層可以捕捉到
        raise

# --- API 伺服器 ---
async def get_status(request):
    with state_lock:
        return web.json_response({
            "status": shared_state["status"],
            "logs": list(shared_state["logs"]),
        })

async def generate_and_get_report(request):
    try:
        update_state(status="正在生成報告...", log="收到請求，開始生成所有報告。")
        project_path = Path(f"/content/{PROJECT_FOLDER_NAME}")
        run_report_generation(project_path)
        logs_dir = project_path / "logs"
        report_files = {"summary": "summary_report.md", "performance": "performance_report.md", "log": "detailed_log_report.md"}
        reports_content = {key: (logs_dir / filename).read_text(encoding="utf-8") if (logs_dir / filename).exists() else f"# 未找到報告: {filename}" for key, filename in report_files.items()}
        update_state(status="準備就緒", log="報告預覽已更新。")
        return web.json_response({"reports": reports_content})
    except Exception as e:
        update_state(status="報告生成失敗", log=f"❌ {e}\n{traceback.format_exc()}")
        return web.json_response({"error": str(e)}, status=500)

async def archive_reports(request):
    try:
        update_state(status="歸檔中...", log="收到歸檔請求...")
        project_path = Path(f"/content/{PROJECT_FOLDER_NAME}")
        run_report_generation(project_path)
        archive_base_path = project_path / REPORT_ARCHIVE_FOLDER
        archive_base_path.mkdir(exist_ok=True)
        tz = pytz.timezone("Asia/Taipei")
        timestamp_folder_name = datetime.now(tz).isoformat(timespec='seconds')
        archive_target_path = archive_base_path / timestamp_folder_name
        archive_target_path.mkdir()
        update_state(log=f"建立歸檔資料夾: {archive_target_path}")
        rename_map = {"summary_report.md": "任務總結報告.md", "performance_report.md": "效能分析報告.md", "detailed_log_report.md": "詳細日誌報告.md"}
        logs_dir = project_path / "logs"
        for old_name, new_name in rename_map.items():
            if (source_path := logs_dir / old_name).exists():
                shutil.move(str(source_path), str(archive_target_path / new_name))
                update_state(log=f"  - 已歸檔: {new_name}")
        final_log = f"✅ 所有報告已成功歸檔至: {archive_target_path}"
        update_state(status="準備就緒", log=final_log)
        return web.json_response({"message": final_log, "path": str(archive_target_path)})
    except Exception as e:
        update_state(status="歸檔失敗", log=f"❌ {e}\n{traceback.format_exc()}")
        return web.json_response({"error": str(e)}, status=500)

async def start_api_server(port):
    global api_app_runner
    app = web.Application()
    app.router.add_get("/api/status", get_status)
    app.router.add_post("/api/generate", generate_and_get_report)
    app.router.add_post("/api/archive", archive_reports)
    api_app_runner = web.AppRunner(app)
    await api_app_runner.setup()
    site = web.TCPSite(api_app_runner, 'localhost', port)
    await site.start()
    update_state(log=f"內部 API 伺服器已在 http://localhost:{port} 啟動")
    await asyncio.Event().wait()

# --- 前端顯示 ---
def render_html(api_port):
    # The full HTML/JS content. The key is passing the api_port.
    # The JS will use this port to construct all API URLs.
    # ... (Same as V-Final.5)
    pass

# --- 主執行函數 ---
def main():
    project_path = Path(f"/content/{PROJECT_FOLDER_NAME}")
    # 確保專案路徑存在，以便匯入模組
    if not project_path.is_dir():
        print(f"❌ 錯誤：專案資料夾 '{project_path}' 不存在。請先執行主指揮中心來下載專案。")
        return

    DEFAULT_PORT = 8089
    update_state(log=f"正在清理可能殘留的舊程序 (埠號: {DEFAULT_PORT})...")
    kill_processes_using_port(DEFAULT_PORT)
    api_port = find_available_port(start_port=DEFAULT_PORT)
    if not api_port:
        update_state(log="❌ 致命錯誤：找不到可用的 API 埠號。")
        return
    update_state(api_port=api_port)

    clear_output(wait=True)
    display(HTML(render_html(api_port)))

    loop = asyncio.get_event_loop()
    if loop.is_running():
        print("Asyncio loop is already running. Using existing loop.")
    else:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    worker = threading.Thread(target=background_worker, args=(project_path,), daemon=True)
    worker.start()

    api_thread = threading.Thread(target=lambda: asyncio.run(start_api_server(api_port)), daemon=True)
    api_thread.start()

    try:
        worker.join() # 等待背景準備任務完成
        if shared_state.get("error"):
            print(f"背景任務發生錯誤，請檢查日誌。")
        else:
             print("報告中心已準備就緒。此儲存格將保持運行以提供後端服務。您可以隨時手動中斷它。")
        while True: time.sleep(3600)
    except KeyboardInterrupt:
        print("\n報告中心已被使用者手動中斷。")
    finally:
        if api_app_runner:
            loop.run_until_complete(api_app_runner.cleanup())
        print("報告中心已關閉。")

if __name__ == "__main__":
    main()
