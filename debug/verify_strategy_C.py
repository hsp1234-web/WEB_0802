# -*- coding: utf-8 -*-
import sys
import subprocess
import time
import shutil
from pathlib import Path

def print_header(title):
    """打印格式化的標題。"""
    print("\n" + "=" * 60)
    print(f"🔧 {title}")
    print("=" * 60)

def main():
    """
    執行並評測策略 C：混合模式 (venv -> pip -> uv -> pip)。
    這模擬了 colab_runner.py 目前的作法。
    """
    strategy_name = "策略 C: 混合模式 (模擬當前作法)"
    print_header(f"開始測試: {strategy_name}")

    # --- 設定 ---
    project_root = Path(__file__).parent.parent.resolve()
    venv_dir = project_root / ".venv_C_temp"
    python_executable = sys.executable
    start_time = time.monotonic()
    final_result = "未知"

    try:
        # --- 清理 ---
        if venv_dir.exists():
            print(f"發現舊的虛擬環境 '{venv_dir.name}'，正在清理...")
            shutil.rmtree(venv_dir)
            print("✅ 清理完成。")

        # --- 步驟 1: 建立虛擬環境 (使用原生 venv) ---
        print(f"\n步驟 1: 使用 '{python_executable}' 建立虛擬環境...")
        subprocess.run(
            [python_executable, "-m", "venv", str(venv_dir)],
            check=True,
            capture_output=True
        )
        print(f"✅ 虛擬環境 '{venv_dir.name}' 建立成功。")

        # --- 步驟 2: 安裝 uv (使用 pip) ---
        if sys.platform == "win32":
            venv_python = venv_dir / "Scripts" / "python.exe"
        else:
            venv_python = venv_dir / "bin" / "python"

        print(f"\n步驟 2: 在虛擬環境中安裝 'uv' 工具...")
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "uv"],
            check=True,
            capture_output=True
        )
        print("✅ 工具 'uv' 安裝成功。")

        # --- 步驟 3: 安裝套件 (使用 venv 中的 uv) ---
        print(f"\n步驟 3: 使用虛擬環境中的 'uv' 安裝 'pytz'...")
        # 注意：我們透過 `python -m uv` 來呼叫 uv，以確保我們使用的是 venv 中的版本
        subprocess.run(
            [str(venv_python), "-m", "uv", "pip", "install", "pytz"],
            check=True,
            capture_output=True
        )
        print("✅ 套件 'pytz' 安裝成功。")

        # --- 步驟 4: 驗證導入 ---
        print("\n步驟 4: 驗證 'pytz' 能否被成功導入...")
        result = subprocess.run(
            [str(venv_python), "-c", "import pytz; print(f'pytz version: {pytz.__version__}')"],
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        validation_output = result.stdout.strip()
        if "pytz version" in validation_output:
            print(f"✅ 驗證成功！輸出: {validation_output}")
            final_result = "成功"
        else:
            print(f"❌ 驗證失敗！意外的輸出: {validation_output}")
            final_result = "失敗"

    except subprocess.CalledProcessError as e:
        print(f"❌ 執行期間發生錯誤！")
        stdout = e.stdout.decode(errors='ignore') if e.stdout else ""
        stderr = e.stderr.decode(errors='ignore') if e.stderr else ""
        print(f"   - 命令: {' '.join(e.cmd)}")
        print(f"   - 返回碼: {e.returncode}")
        print(f"   - STDOUT: {stdout}")
        print(f"   - STDERR: {stderr}")
        final_result = "錯誤"
    except Exception as e:
        print(f"❌ 發生未預期的錯誤: {e}")
        final_result = "錯誤"
    finally:
        # --- 最終清理 ---
        if venv_dir.exists():
            print(f"\n最終清理: 刪除虛擬環境 '{venv_dir.name}'...")
            shutil.rmtree(venv_dir)
            print("✅ 清理完成。")

    end_time = time.monotonic()
    duration = end_time - start_time

    # --- 輸出總結 ---
    print("\n" + "-" * 60)
    print("📊 測試總結")
    print(f"   - 策略: {strategy_name}")
    print(f"   - 最終結果: {final_result}")
    print(f"   - 總耗時: {duration:.4f} 秒")
    print("-" * 60)

if __name__ == "__main__":
    main()
