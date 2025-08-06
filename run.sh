#!/bin/bash
# 檔案: run.sh
# 說明: 遵循「鳳凰之心協定」的統一服務啟動腳本。
#       使用 'uv' 工具管理虛擬環境，並作為監督者啟動和管理所有服務。

# --- 設定 ---
SOURCE_DIR=$(dirname "$(readlink -f "$0")")
VENV_PATH="./.venv"
REQUIREMENTS_PATH="requirements/base.txt"
VENV_PYTHON="$VENV_PATH/bin/python"
LOGS_DIR="./logs"

# --- 函數 ---

# 清理函數，用於在腳本退出時終止所有背景子進程
cleanup() {
    echo -e "\n[run.sh] 收到關閉訊號，正在清理背景進程..."
    # 如果 pids_to_kill 陣列存在且不為空
    if [ ${#pids_to_kill[@]} -ne 0 ]; then
        for pid in "${pids_to_kill[@]}"; do
            # 檢查進程是否存在
            if kill -0 "$pid" 2>/dev/null; then
                echo "[run.sh] 正在終止進程 PID: $pid"
                kill "$pid"
            fi
        done
    fi
    echo "[run.sh] 清理完成。"
    exit 0
}

# --- 主邏輯 ---

# 設置 trap，無論腳本如何退出 (正常退出、Ctrl+C、kill)，都執行 cleanup 函數
trap cleanup SIGINT SIGTERM EXIT

# 切換到專案根目錄
cd "$SOURCE_DIR" || exit 1

# 建立日誌目錄
mkdir -p "$LOGS_DIR"

# --- 步驟 1: 環境準備 ---
if [ ! -d "$VENV_PATH" ]; then
    echo "🔎 找不到虛擬環境，正在使用 'uv' 建立..."
    uv venv
    if [ $? -ne 0 ]; then
        echo "❌ 錯誤：使用 'uv venv' 建立虛擬環境失敗。"
        exit 1
    fi
    echo "✅ 虛擬環境已建立於 $VENV_PATH"
else
    echo "✅ 找到現有虛擬環境。"
fi

echo "📦 正在使用 'uv pip install' 同步依賴..."
uv pip install -r "$REQUIREMENTS_PATH" > /dev/null # 將輸出重導向，保持介面乾淨
if [ $? -ne 0 ]; then
    echo "❌ 錯誤：使用 'uv pip install' 安裝依賴失敗。"
    exit 1
fi
echo "✅ 依賴已同步。"

# --- 步驟 2: 啟動服務 ---
echo "🚀 正在啟動所有背景服務..."

# 清理舊的日誌檔案
rm -f "$LOGS_DIR/api_server.log" "$LOGS_DIR/heartbeat_worker.log"

# 定義要啟動的服務
# 服務名稱 => [日誌檔案, 啟動指令...]
declare -A components
components=(
    ["API Server"]="$LOGS_DIR/api_server.log $VENV_PYTHON -m uvicorn src.phoenix_core.main:app --host 0.0.0.0 --port 8080"
    ["Heartbeat Worker"]="$LOGS_DIR/heartbeat_worker.log $VENV_PYTHON -u -m scripts.heartbeat_worker"
)

pids_to_kill=()
for name in "${!components[@]}"; do
    # 從 components 陣列中分離出日誌路徑和指令
    read -r log_path command <<< "${components[$name]}"

    echo "[run.sh] 正在啟動: $name..."

    # 在背景執行指令，並將 stdout/stderr 導向到日誌檔案
    $command > "$log_path" 2>&1 &

    # 獲取剛啟動的背景進程的 PID
    pid=$!
    pids_to_kill+=($pid)
    echo "[run.sh] $name 已啟動，PID: $pid，日誌: $log_path"
done

echo "✅ 所有服務已在背景啟動。監督者正在監控中... (按 Ctrl+C 結束)"

# --- 步驟 3: 監控 ---
# wait -n 等待任何一個背景進程結束
# $! 包含了所有背景進程的 PID
wait -n "${pids_to_kill[@]}"

# 如果 wait 指令退出，說明有子進程掛了
echo "🚨 [run.sh] 偵測到一個子進程已終止。正在關閉所有服務..."

# trap 會自動觸發 cleanup 函數來終止所有其他進程
exit 1
