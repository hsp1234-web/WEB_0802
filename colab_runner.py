# -*- coding: utf-8 -*-
# 檔案: colab_runner.py
# 版本: v68
# 說明: Google Colab 引導加載器。
#       此腳本提供一個使用者介面，用於從指定的 Git 儲存庫下載或更新程式碼，
#       然後啟動後端服務的中央監督者 (supervisor.py)。
#       設計上，此腳本可被輕易地複製到 Colab 儲存格中執行。

import ipywidgets as widgets
from IPython.display import display, clear_output
import subprocess
import sys
import os
from pathlib import Path
import shlex
import threading

# --- 使用者介面設定 ---

# 預設的 Git 儲存庫和分支
DEFAULT_REPO_URL = "https://github.com/user/repo.git"  # 請替換為您的儲存庫 URL
DEFAULT_BRANCH = "main"
REPO_DIR = "phoenix_project" # 本地存放庫的目錄名稱

# --- UI 元件 ---

style = {'description_width': 'initial'}
layout = widgets.Layout(width='500px')

# 標題
header = widgets.HTML("<h2>鳳凰之心 v68 - Colab 執行器</h2>")

# Git 設定
repo_url_input = widgets.Text(
    value=DEFAULT_REPO_URL,
    description='Git 儲存庫 URL:',
    style=style,
    layout=layout
)
branch_input = widgets.Text(
    value=DEFAULT_BRANCH,
    description='分支名稱:',
    style=style,
    layout=layout
)

# 執行按鈕
run_button = widgets.Button(
    description='啟動/更新服務',
    button_style='success',
    tooltip='點擊此處開始下載程式碼並啟動後端服務',
    icon='rocket'
)

# 輸出區域
output_area = widgets.Output()

# --- 核心邏輯 ---

def run_command_and_stream_output(command, output_widget):
    """執行一個命令並將其輸出即時串流到指定的 output widget。"""
    try:
        process = subprocess.Popen(
            shlex.split(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        # 讀取並顯示輸出
        while True:
            line = process.stdout.readline()
            if not line:
                break
            with output_widget:
                print(line.strip())

        process.wait()
        return process.returncode

    except Exception as e:
        with output_widget:
            print(f"執行命令時發生錯誤: {command}")
            print(f"錯誤詳情: {e}")
        return -1


def run_button_clicked(b):
    """處理按鈕點擊事件。"""
    with output_area:
        clear_output(wait=True)
        print("🚀 開始執行...")

        repo_url = repo_url_input.value
        branch = branch_input.value
        repo_path = Path(REPO_DIR)

        # 步驟 1: 下載/更新程式碼
        if not repo_path.exists():
            print(f"📂 找不到目錄 '{REPO_DIR}'，正在從 {repo_url} 進行 clone...")
            clone_command = f"git clone -b {branch} {repo_url} {REPO_DIR}"
            return_code = run_command_and_stream_output(clone_command, output_area)
            if return_code != 0:
                print(f"❌ Git clone 失敗，請檢查 URL 和分支名稱。")
                return
        else:
            print(f"🔄 目錄 '{REPO_DIR}' 已存在，正在更新...")
            # 使用 -C 選項在指定目錄下執行 git 命令
            fetch_command = f"git -C {REPO_DIR} fetch"
            checkout_command = f"git -C {REPO_DIR} checkout {branch}"
            pull_command = f"git -C {REPO_DIR} pull origin {branch}"

            for cmd in [fetch_command, checkout_command, pull_command]:
                 return_code = run_command_and_stream_output(cmd, output_area)
                 if return_code != 0:
                    print(f"❌ Git 命令 '{cmd}' 失敗。")
                    return

        print("✅ 程式碼已是最新版本。")

        # 步驟 2: 啟動監督者 (run.sh)
        supervisor_script = repo_path / "run.sh"
        if not supervisor_script.exists():
            with output_area:
                print(f"❌ 錯誤：在下載的程式碼中找不到核心啟動腳本: {supervisor_script}")
            return

        # 賦予 run.sh 執行權限，這在 git clone 後是必要的
        supervisor_script.chmod(0o755)

        with output_area:
            print("\n🔥 正在啟動後端服務...")
            print("="*50)
            print("   - 啟動腳本: run.sh")
            print("   - 模式: 背景分離模式 (日誌將寫入檔案)")

        try:
            # 我們以完全分離的方式在背景啟動 run.sh。
            # 我們不捕獲它的輸出，讓它自己處理日誌記錄 (到 logs/ 目錄)。
            # 這也避免了任何潛在的輸出管道阻塞問題。
            process = subprocess.Popen(
                [str(supervisor_script)], # 使用列表形式傳遞命令更安全
                cwd=str(repo_path),
                stdout=subprocess.DEVNULL, # 將 stdout 丟棄
                stderr=subprocess.DEVNULL, # 將 stderr 丟棄
                start_new_session=True  # 在新 session 中啟動，與 Colab 主進程徹底分離
            )
            with output_area:
                print("\n✅ 後端監督者 (run.sh) 已在背景啟動。")
                print(f"   - 監督者進程 PID: {process.pid}")
                print(f"   - 要查看詳細日誌，請檢查 '{REPO_DIR}/logs/' 目錄下的檔案。")
                print("\nℹ️ 後端服務正在初始化，請稍候片刻即可開始互動。")

        except Exception as e:
            with output_area:
                print(f"❌ 啟動 run.sh 時發生嚴重錯誤: {e}")


# --- 組合並顯示 UI ---

def display_ui():
    """組合所有元件並顯示。"""
    # 將按鈕事件與處理函數連結
    run_button.on_click(run_button_clicked)

    # 建立 UI 佈局
    ui_layout = widgets.VBox([
        header,
        widgets.HTML("<hr>"),
        repo_url_input,
        branch_input,
        run_button,
        widgets.HTML("<hr><h4>執行日誌:</h4>"),
        output_area
    ])

    display(ui_layout)

# --- 主程式入口 ---
# 在 Colab 中，只需呼叫 display_ui() 即可顯示介面
if __name__ == "__main__":
    print("這是一個 Colab 腳本。請在 Jupyter/Colab 環境中導入並呼叫 display_ui() 函數。")
    # 如果直接執行，我們也可以提供一個基本的命令行介面，但目前專注於 Colab
    pass

# 直接呼叫以在 Colab 中顯示
display_ui()
