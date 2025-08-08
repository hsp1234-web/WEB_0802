import os
import sys
import subprocess
import tarfile
import ast
from pathlib import Path
import shutil

# --- 設定 ---
# 取得專案根目錄 (此腳本的父目錄的父目錄)
ROOT_DIR = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT_DIR / "tools"
BAKED_ENVS_DIR = ROOT_DIR / "storage" / "baked_envs"
LOG_PREFIX = "[Baker]"

# --- 日誌記錄 ---
def log(message):
    """標準化的日誌輸出。"""
    timestamp = Path(sys.argv[0]).name
    print(f"{LOG_PREFIX}[{timestamp}] {message}")

# --- 核心功能 ---
def get_tool_dependencies(tool_path: Path) -> dict:
    """
    安全地從 Python 原始碼檔案中解析 'DEPENDENCIES' 字典。
    使用 AST (抽象語法樹) 來避免直接執行檔案。
    """
    log(f"正在解析 '{tool_path.name}' 的依賴...")
    try:
        with open(tool_path, 'r', encoding='utf-8') as f:
            source_code = f.read()

        tree = ast.parse(source_code)

        for node in ast.walk(tree):
            # 我們尋找一個名為 'DEPENDENCIES' 的賦值語句
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == 'DEPENDENCIES':
                        # ast.literal_eval 可以安全地求值 Python 的字面量 (如字典、列表、字串等)
                        dependencies = ast.literal_eval(node.value)
                        if isinstance(dependencies, dict) and dependencies:
                            log(f"✅ 在 '{tool_path.name}' 中找到依賴: {list(dependencies.values())}")
                            return dependencies

        log(f"⚠️ 在 '{tool_path.name}' 中未找到有效的 'DEPENDENCIES' 字典。")
        return {}
    except (FileNotFoundError, SyntaxError, ValueError) as e:
        log(f"❌ 解析 '{tool_path.name}' 時發生錯誤: {e}")
        return {}

def bake_environment(tool_path: Path):
    """為單一工具執行完整的烘烤流程。"""
    tool_name = tool_path.stem
    venv_dir = TOOLS_DIR / f".venv_{tool_name}"
    archive_path = BAKED_ENVS_DIR / f"{venv_dir.name}.tar.xz"

    log(f"--- 開始為 '{tool_name}' 烘烤環境 ---")

    if archive_path.exists():
        log(f"✅ '{tool_name}' 的環境存檔已存在，跳過。")
        return True

    # 1. 取得依賴列表
    dependencies = get_tool_dependencies(tool_path)
    if not dependencies:
        log(f"'{tool_name}' 沒有定義任何依賴，無需烘烤。")
        return True

    # 在 finally 區塊中確保無論成功或失敗都會清理
    try:
        # 如果舊的 venv 存在，先移除
        if venv_dir.exists():
            log(f"🧹 正在清理舊的虛擬環境: {venv_dir}")
            shutil.rmtree(venv_dir)

        # 2. 使用 uv 建立虛擬環境
        log(f"⚙️  正在建立虛擬環境: {venv_dir}")
        uv_command = ["uv", "venv", str(venv_dir), "--python", sys.executable]
        result = subprocess.run(uv_command, capture_output=True, text=True, encoding='utf-8')
        if result.returncode != 0:
            log(f"❌ 建立虛擬環境失敗。返回碼: {result.returncode}")
            log(f"錯誤輸出:\n{result.stderr}")
            return False

        # 3. 安裝依賴
        python_executable = venv_dir / "bin" / "python"
        deps_to_install = list(dependencies.values())
        log(f"📦 正在安裝 {len(deps_to_install)} 個依賴: {', '.join(deps_to_install)}")
        # 使用 uv 指令並透過 -p 指定目標 Python 解譯器來安裝依賴，這是與 uv 互動的正確方式
        install_command = ["uv", "pip", "install", *deps_to_install, "-p", str(python_executable)]
        result = subprocess.run(install_command, capture_output=True, text=True, encoding='utf-8')
        if result.returncode != 0:
            log(f"❌ 安裝依賴失敗。返回碼: {result.returncode}")
            log(f"錯誤輸出:\n{result.stderr}")
            return False

        # 4. 壓縮虛擬環境
        log(f"📦 正在將 '{venv_dir.name}' 壓縮至 '{archive_path}' (使用 xz)...")
        with tarfile.open(archive_path, "w:xz") as tar:
            # arcname=venv_dir.name 確保在解壓縮時不會產生多餘的上層目錄
            tar.add(str(venv_dir), arcname=venv_dir.name)

        log(f"🎉 成功為 '{tool_name}' 烘烤環境！")
        return True

    except Exception as e:
        log(f"❌ 在為 '{tool_name}' 烘烤時發生未預期的錯誤: {e}")
        return False
    finally:
        # 5. 清理臨時的虛擬環境目錄
        if venv_dir.exists():
            log(f"🧹 正在清理臨時的虛擬環境: {venv_dir}")
            shutil.rmtree(venv_dir)

def main():
    """主函數，執行所有工具的環境烘烤。"""
    log("=== 鳳凰之心 :: 環境烘烤腳本 ===")

    # 確保目標目錄存在
    BAKED_ENVS_DIR.mkdir(parents=True, exist_ok=True)
    log(f"存檔將儲存至: {BAKED_ENVS_DIR}")

    # 尋找所有需要被處理的工具
    tool_files = [
        p for p in TOOLS_DIR.glob("*.py")
        if p.is_file() and not p.name.startswith(('manager', 'heartbeat', 'test_'))
    ]

    if not tool_files:
        log("在 'tools/' 目錄下未找到任何需要烘烤的工具腳本。")
        return

    log(f"找到 {len(tool_files)} 個工具需要處理: {[t.name for t in tool_files]}")

    # 使用 ProcessPoolExecutor 來平行執行烘烤任務
    # 這在多核心 CPU 上能顯著提升速度
    from concurrent.futures import ProcessPoolExecutor

    log(f"🔥 即將以平行模式開始烘烤 {len(tool_files)} 個工具...")

    with ProcessPoolExecutor() as executor:
        # map 會將 tool_files 中的每個元素作為參數傳遞給 bake_environment
        # 並以平行方式執行
        results = executor.map(bake_environment, tool_files)

    # 收集結果
    success_count = sum(1 for r in results if r)
    failure_count = len(tool_files) - success_count

    log("--- 烘烤流程總結 ---")
    log(f"✅ 成功: {success_count} 個")
    log(f"❌ 失敗: {failure_count} 個")
    log("========================")
    log("Final baked environment archives:")
    try:
        total_size = 0
        files = list(BAKED_ENVS_DIR.glob('*.tar.xz'))
        if not files:
             log("No archives found.")

        for f in sorted(files):
            size_bytes = f.stat().st_size
            total_size += size_bytes
            if size_bytes > 1024 * 1024:
                size_str = f"{size_bytes / (1024*1024):.2f} MB"
            else:
                size_str = f"{size_bytes / 1024:.2f} KB"
            log(f"- {f.name:<40} {size_str}")

        total_size_mb = total_size / (1024 * 1024)
        log(f"Total size: {total_size_mb:.2f} MB")
    except Exception as e:
        log(f"Error listing baked archives: {e}")


    if failure_count > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
