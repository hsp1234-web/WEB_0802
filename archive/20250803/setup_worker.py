# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║      🔥 Phoenix Setup Worker V1.0                                    ║
# ║         (由 run/colab_runner.py 啟動)                              ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║   - 目的: 執行所有耗時且可能失敗的環境準備工作。                   ║
# ║   - 設計: 作為一個獨立的子程序運行，所有輸出都將被父程序捕獲       ║
# ║           並轉發到前端，以解決「無聲崩潰」的問題。                 ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝
import os
import sys
import shutil
import subprocess
import json
import argparse
from pathlib import Path
from datetime import datetime

def print_log(message):
    """一個簡單的日誌函式，確保所有輸出都有時間戳。"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {message}", flush=True)

def run_command(command, check=True):
    """執行一個命令並即時串流其輸出。"""
    print_log(f"🚀 執行命令: {' '.join(command)}")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        bufsize=1
    )
    for line in iter(process.stdout.readline, ''):
        print(line.strip()) # 直接打印，讓父程序捕獲

    process.wait()
    if check and process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, command)

def main():
    # --- 環境偵測 ---
    # 這個腳本應該總是被 colab_runner 啟動，所以 IS_COLAB 的判斷應該基於父程序的環境
    # 但為了獨立性，我們再次檢查
    is_colab = 'google.colab' in sys.modules

    parser = argparse.ArgumentParser(description="Phoenix Heart Setup Worker.")
    parser.add_argument("--repo-url", required=True, help="後端程式碼倉庫 URL")
    parser.add_argument("--branch", required=True, help="後端版本分支或標籤")
    parser.add_argument("--project-folder", required=True, help="專案資料夾名稱")
    parser.add_argument("--force-refresh", action='store_true', help="強制刷新後端程式碼")
    parser.add_argument("--timezone", default="Asia/Taipei", help="時區設定")
    args = parser.parse_args()

    print_log("🔥 Phoenix 安裝工作程序已啟動！")
    print_log(f"   - Is Colab: {is_colab}")
    print_log(f"   - Project Folder: {args.project_folder}")

    try:
        # --- 路徑設定 ---
        if is_colab:
            project_path = Path("/content") / args.project_folder
            repo_root = project_path
        else:
            # 在本地模式下，此腳本不應該被直接執行，但為了完整性，我們設定路徑
            repo_root = Path(".").resolve()
            project_path = repo_root

        # --- 下載/更新程式碼 (僅 Colab) ---
        if is_colab:
            if args.force_refresh and project_path.exists():
                print_log(f"🔄 偵測到強制刷新，正在刪除舊的專案資料夾: {project_path}...")
                shutil.rmtree(project_path)

            if not project_path.exists():
                print_log(f"📥 正在從 {args.repo_url} (分支/標籤: {args.branch}) 下載程式碼...")
                run_command([
                    "git", "clone", "--depth", "1", "--branch", args.branch,
                    args.repo_url, str(project_path)
                ])

        # --- 建立設定檔 ---
        print_log("📝 正在生成 config.json...")
        config_file_path = project_path / "config.json"
        with open(config_file_path, "w", encoding="utf-8") as f:
            json.dump({"system_settings": {"timezone": args.timezone}}, f, indent=4)

        # --- 安裝依賴 ---
        # V31: 在 Colab 中，我們直接安裝到系統環境
        requirements_file = repo_root / "requirements" / "dev.txt"
        if not requirements_file.exists():
             raise FileNotFoundError(f"找不到依賴檔案: {requirements_file}")

        print_log(f"📦 正在從 {requirements_file} 安裝依賴...")
        # 在 Colab 和本地，都使用 sys.executable 來確保使用的是啟動此腳本的同一個 Python
        run_command([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)])

        print_log("✅ 環境準備完成。")

        # --- 啟動後端工作者 ---
        print_log("🚀 準備啟動後端核心工作者 (backend_worker.py)...")
        backend_script_path = repo_root / "scripts" / "backend_worker.py"
        if not backend_script_path.exists():
            raise FileNotFoundError(f"找不到後端工作者腳本: {backend_script_path}")

        command = [sys.executable, str(backend_script_path), "--config", str(config_file_path)]

        print_log(f"   執行命令: {' '.join(command)}")
        # 使用 Popen 在背景啟動，且不等待它結束
        # 父程序 (colab_runner) 已經結束其監控任務，現在讓 backend_worker 自由運行
        subprocess.Popen(command, cwd=repo_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        print_log("✅ 後端核心工作者已在背景啟動。安裝程序結束。")

    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print_log(f"❌ 發生致命錯誤: {e}")
        # 打印更詳細的錯誤
        if hasattr(e, 'stderr') and e.stderr:
            print_log(f"[錯誤詳情]: {e.stderr}")
        sys.exit(1) # 以非零狀態碼退出，讓父程序知道失敗
    except Exception as e:
        import traceback
        print_log(f"❌ 發生未預期的錯誤: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
