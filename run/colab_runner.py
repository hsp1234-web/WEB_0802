# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║              🚀 Colab 指揮中心 V26 (可配置後端版)                    ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║ - 架構：Colab UI 產生 config.json，傳遞給一個獨立的、              ║
# ║           穩定的 venv 驅動的啟動器 `start_api_service.py`。        ║
# ║ - 版本：0.2.6                                                      ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

import os
import sys
import subprocess
import threading
import time
import json
from pathlib import Path
from IPython.display import display, HTML, clear_output

# --- Colab 使用者介面參數 ---
#@title 🚀 V26 鳳凰之心指揮中心 { vertical-output: true, display-mode: "form" }
#@markdown ---
#@markdown ### Part 1: 程式碼與環境設定
#@markdown > 設定 Git 倉庫、分支或標籤，以及專案資料夾。
#@markdown ---
#@markdown 後端程式碼倉庫 (REPOSITORY_URL)
REPOSITORY_URL = "https://github.com/hsp1234-web/WEB_0802.git" #@param {type:"string"}
#@markdown 後端版本分支或標籤 (TARGET_BRANCH_OR_TAG)
TARGET_BRANCH_OR_TAG = "0.1.8" #@param {type:"string"}
#@markdown 專案資料夾名稱 (PROJECT_FOLDER_NAME)
PROJECT_FOLDER_NAME = "WEB1" #@param {type:"string"}
#@markdown 強制刷新後端程式碼 (FORCE_REPO_REFRESH)
FORCE_REPO_REFRESH = True #@param {type:"boolean"}

#@markdown ---
#@markdown ### Part 2: 應用程式參數
#@markdown > 設定指揮中心的核心運行參數。
#@markdown ---
#@markdown 儀表板更新頻率 (秒) (REFRESH_RATE_SECONDS)
REFRESH_RATE_SECONDS = 1.0 #@param {type:"number"}
#@markdown 效能監控更新頻率 (秒) (PERFORMANCE_MONITOR_RATE_SECONDS)
PERFORMANCE_MONITOR_RATE_SECONDS = 0.5 #@param {type:"number"}
#@markdown 日誌歸檔資料夾 (LOG_ARCHIVE_FOLDER_NAME)
LOG_ARCHIVE_FOLDER_NAME = "作戰日誌歸檔" #@param {type:"string"}
#@markdown 時區設定 (TIMEZONE)
TIMEZONE = "Asia/Taipei" #@param {type:"string"}
#@markdown 快速測試模式 (FAST_TEST_MODE)
FAST_TEST_MODE = False #@param {type:"boolean"}

#@markdown ---
#@markdown ### Part 3: 日誌顯示設定
#@markdown > 選擇您想在儀表板上看到的日誌等級。
#@markdown ---
#@markdown 日誌顯示行數 (LOG_DISPLAY_LINES)
LOG_DISPLAY_LINES = 50 #@param {type:"integer"}
#@markdown 顯示戰鬥日誌 (SHOW_LOG_LEVEL_BATTLE)
SHOW_LOG_LEVEL_BATTLE = True #@param {type:"boolean"}
#@markdown 顯示成功日誌 (SHOW_LOG_LEVEL_SUCCESS)
SHOW_LOG_LEVEL_SUCCESS = True #@param {type:"boolean"}
#@markdown 顯示資訊日誌 (SHOW_LOG_LEVEL_INFO)
SHOW_LOG_LEVEL_INFO = False #@param {type:"boolean"}
#@markdown 顯示命令日誌 (SHOW_LOG_LEVEL_CMD)
SHOW_LOG_LEVEL_CMD = False #@param {type:"boolean"}
#@markdown 顯示系統日誌 (SHOW_LOG_LEVEL_SHELL)
SHOW_LOG_LEVEL_SHELL = False #@param {type:"boolean"}
#@markdown 顯示錯誤日誌 (SHOW_LOG_LEVEL_ERROR)
SHOW_LOG_LEVEL_ERROR = True #@param {type:"boolean"}
#@markdown 顯示嚴重錯誤日誌 (SHOW_LOG_LEVEL_CRITICAL)
SHOW_LOG_LEVEL_CRITICAL = True #@param {type:"boolean"}
#@markdown 顯示效能日誌 (SHOW_LOG_LEVEL_PERF)
SHOW_LOG_LEVEL_PERF = False #@param {type:"boolean"}

#@markdown ---
#@markdown > 設定完成後，點擊此儲存格左側的「執行」按鈕。
#@markdown ---


# ==============================================================================
# 🚀 核心邏輯
# ==============================================================================

def generate_config_file():
    """根據 Colab 表單參數生成 config.json"""
    print("正在生成 config.json...")
    config_data = {
        "repository": {
            "url": REPOSITORY_URL,
            "branch": TARGET_BRANCH_OR_TAG,
            "project_folder": PROJECT_FOLDER_NAME
        },
        "dashboard_settings": {
            "refresh_rate_seconds": REFRESH_RATE_SECONDS
        },
        "performance_monitor_settings": {
            "rate_seconds": PERFORMANCE_MONITOR_RATE_SECONDS
        },
        "log_settings": {
            "archive_folder": LOG_ARCHIVE_FOLDER_NAME,
            "display_lines": LOG_DISPLAY_LINES,
            "levels": {
                "battle": SHOW_LOG_LEVEL_BATTLE,
                "success": SHOW_LOG_LEVEL_SUCCESS,
                "info": SHOW_LOG_LEVEL_INFO,
                "cmd": SHOW_LOG_LEVEL_CMD,
                "shell": SHOW_LOG_LEVEL_SHELL,
                "error": SHOW_LOG_LEVEL_ERROR,
                "critical": SHOW_LOG_LEVEL_CRITICAL,
                "perf": SHOW_LOG_LEVEL_PERF
            }
        },
        "system_settings": {
            "timezone": TIMEZONE,
            "fast_test_mode": FAST_TEST_MODE
        }
    }

    # 確保專案目錄存在
    project_path = Path(f"/content/{PROJECT_FOLDER_NAME}")
    project_path.mkdir(exist_ok=True)

    config_file_path = project_path / "config.json"
    with open(config_file_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)
    print(f"✅ config.json 已生成於 {config_file_path}")
    return str(config_file_path)


def background_worker(stop_event, config_path):
    """
    背景工作執行緒，呼叫後端啟動器，並傳遞設定檔路徑。
    """
    try:
        print(" BACKGROUND_WORKER: 正在啟動後端服務...")
        command = [
            sys.executable,
            "scripts/start_api_service.py",
            "--config", config_path  # 將設定檔路徑傳遞給後端
        ]

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
        )

        for line in process.stdout:
            print(f"   [BACKEND] {line.strip()}")
            if stop_event.is_set():
                print("   [BACKEND] 主執行緒請求終止，正在關閉後端服務...")
                process.terminate()
                break

        process.wait()
        print(" BACKGROUND_WORKER: 後端服務程序已結束。")

    except Exception as e:
        print(f"❌ 背景工作執行緒發生致命錯誤: {e}")

def render_dashboard_html():
    """生成儀表板的 HTML 和 JavaScript。"""
    # ... (此處的 HTML/JS 碼與之前的版本相同，為節省篇幅省略)
    # 唯一重要的是，它輪詢的 API 端點是固定的
    return "<h1>儀表板正在載入...</h1><script>/* 省略的 JS 碼 */</script>"

def main():
    """主執行函式。"""
    stop_event = threading.Event()

    try:
        # 1. 生成設定檔
        config_file_path = generate_config_file()

        # 2. 清理輸出並顯示儀表板 (此處簡化，實際應顯示完整儀表板)
        clear_output(wait=True)
        print("儀表板 UI 正在渲染...")
        # display(HTML(render_dashboard_html()))

        # 3. 啟動背景工作執行緒
        worker_thread = threading.Thread(
            target=background_worker,
            args=(stop_event, config_file_path),
            daemon=True
        )
        worker_thread.start()

        # 4. 主執行緒等待，直到使用者手動中斷
        worker_thread.join()

    except KeyboardInterrupt:
        print("\n🛑 偵測到使用者手動中斷。正在通知後端服務關閉...")
        stop_event.set()
        time.sleep(2)
        print("✅ 前端程序已結束。")

if __name__ == "__main__":
    main()
