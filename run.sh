#!/bin/bash
# 檔案: run.sh
# 說明: 遵循「鳳凰之心協定」的統一服務啟動腳本。
#       使用 'uv' 工具管理虛擬環境，並作為監督者啟動和管理所有服務。

# --- 函數 ---

# 磁碟空間檢查函數
check_disk_space() {
    # --- 模擬邏輯 ---
    local required_gb=5
    local available_gb=10

    echo "[安裝保護] 正在檢查磁碟空間..."
    echo "[安裝保護] 需要空間: ${required_gb}GB，可用空間: ${available_gb}GB。"

    if [ "$available_gb" -lt "$required_gb" ]; then
        echo "❌ 錯誤：磁碟空間不足！" >&2
        echo "   - 需要至少 ${required_gb}GB 空間來安裝依賴，但只剩下 ${available_gb}GB。" >&2
        echo "   - 請清理磁碟空間後再試。" >&2
        exit 1 # 以錯誤碼退出
    fi

    echo "[安裝保護] ✅ 磁碟空間充足。"
}

# 清理函數，用於在腳本退出時終止所有背景子進程
cleanup() {
    echo -e "\n[run.sh] 收到關閉訊號，正在清理背景進程..."
    if [ ${#pids_to_kill[@]} -ne 0 ]; then
        for pid in "${pids_to_kill[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                echo "[run.sh] 正在終止進程 PID: $pid"
                kill "$pid" 2>/dev/null
            fi
        done
    fi
    echo "[run.sh] 清理完成。"
    exit 0
}

# --- 新增：心跳監控函數 ---
monitor_heartbeat() {
    echo "[看門狗] 檔案監控看門狗已啟動，正在監控: $HEARTBEAT_FILE_PATH"
    # 等待心跳檔案首次出現，最多等待30秒
    for i in {1..6}; do
        if [ -f "$HEARTBEAT_FILE_PATH" ]; then
            echo "[看門狗] ✅ 偵測到心跳檔案。"
            break
        fi
        if [ $i -eq 6 ]; then
            echo "🚨 [看門狗] 致命錯誤：在30秒內未偵測到心跳檔案！" >&2
            echo "   - Heartbeat Worker 可能啟動失敗。" >&2
            kill $$
            exit 1
        fi
        sleep 5
    done

    while true; do
        if [ ! -f "$HEARTBEAT_FILE_PATH" ]; then
            echo "🚨 [看門狗] 致命錯誤：心跳檔案消失！" >&2
            kill $$
            exit 1
        fi

        # 獲取檔案的最後修改時間 (秒) 和當前時間 (秒)
        if [[ "$(uname)" == "Darwin" ]]; then # macOS
            last_modified=$(stat -f %m "$HEARTBEAT_FILE_PATH")
        else # Linux
            last_modified=$(stat -c %Y "$HEARTBEAT_FILE_PATH")
        fi

        current_time=$(date +%s)
        age=$((current_time - last_modified))

        if [ "$age" -gt "$HEARTBEAT_TIMEOUT" ]; then
            echo "🚨 [看門狗] 致命錯誤：心跳超時！" >&2
            echo "   - 檔案 '$HEARTBEAT_FILE_PATH' 已有 ${age} 秒未更新。" >&2
            echo "   - Heartbeat Worker 可能已掛起或崩潰。" >&2
            echo "   - 正在觸發主動關閉..." >&2
            kill $$
            exit 1
        fi
        sleep "$HEARTBEAT_CHECK_INTERVAL"
    done
}


# --- 設定 ---
SOURCE_DIR=$(dirname "$(readlink -f "$0")")
VENV_PATH="./.venv"
REQUIREMENTS_PATH="requirements/base.txt"
VENV_PYTHON="$VENV_PATH/bin/python"
LOGS_DIR="./logs"
STORAGE_DIR="./storage"
HEARTBEAT_FILE_PATH="$STORAGE_DIR/heartbeat.timestamp"
HEARTBEAT_TIMEOUT=30 # 秒
HEARTBEAT_CHECK_INTERVAL=10 # 秒


# --- 主邏輯 ---

trap cleanup SIGINT SIGTERM EXIT
cd "$SOURCE_DIR" || exit 1
mkdir -p "$LOGS_DIR"
mkdir -p "$STORAGE_DIR"

# --- 步驟 1: 環境準備 ---
if [ ! -d "$VENV_PATH" ]; then
    echo "🔎 找不到虛擬環境，正在使用 'uv' 建立..."
    uv venv
    if [ $? -ne 0 ]; then exit 1; fi
    echo "✅ 虛擬環境已建立於 $VENV_PATH"
else
    echo "✅ 找到現有虛擬環境。"
fi

echo "📦 正在使用 'uv pip install' 同步依賴..."
check_disk_space
uv pip install -r "$REQUIREMENTS_PATH" > /dev/null
if [ $? -ne 0 ]; then
    echo "❌ 錯誤：使用 'uv pip install' 安裝依賴失敗。"
    exit 1
fi
echo "✅ 依賴已同步。"

# --- 步驟 2: 啟動服務 ---
echo "🚀 正在啟動所有背景服務..."
rm -f "$LOGS_DIR/api_server.log" "$LOGS_DIR/heartbeat_worker.log"
rm -f "$HEARTBEAT_FILE_PATH"

declare -A components
components=(
    ["API Server"]="$LOGS_DIR/api_server.log $VENV_PYTHON -m uvicorn src.phoenix_core.main:app --host 0.0.0.0 --port 8080"
    ["Heartbeat Worker"]="$LOGS_DIR/heartbeat_worker.log $VENV_PYTHON -u -m scripts.heartbeat_worker"
)

pids_to_kill=()
for name in "${!components[@]}"; do
    read -r log_path command <<< "${components[$name]}"
    echo "[run.sh] 正在啟動: $name..."
    $command > "$log_path" 2>&1 &
    pid=$!
    pids_to_kill+=($pid)
    echo "[run.sh] $name 已啟動，PID: $pid，日誌: $log_path"
done

# --- 步驟 3: 啟動並監控 ---
echo "🚀 正在啟動檔案心跳看門狗..."
monitor_heartbeat &
monitor_pid=$!
pids_to_kill+=($monitor_pid)
echo "[run.sh] 看門狗已啟動，PID: $monitor_pid"

echo "✅ 所有服務已在背景啟動。監督者正在監控中... (按 Ctrl+C 結束)"

wait -n "${pids_to_kill[@]}"
exit_code=$?

echo "🚨 [run.sh] 偵測到一個子進程已終止 (返回碼: $exit_code)。正在關閉所有服務..."
exit 1
