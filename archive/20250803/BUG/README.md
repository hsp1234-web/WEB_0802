# 偵錯腳本黃金標準 (Golden Standard Debugging Scripts)

本目錄 (`BUG/`) 存放的是一系列經過驗證、可獨立運行的「黃金標準」偵錯腳本。這些腳本的設計目標是在一個可控的本地環境中，精準地重現和測試核心應用程式的特定流程。

## 核心原則

- **獨立性**: 每個腳本都應盡可能獨立，自行處理環境設定（如建立虛擬環境），以確保測試的可重現性。
- **清晰性**: 腳本應包含詳細的日誌輸出，清楚地標示出其執行的每一個階段。
- **確定性**: 在相同的程式碼版本下，腳本的執行結果應該是穩定且可預測的。

## 腳本說明

### `colab_runner_debug.py`

- **核心功能**: 模擬 `run/colab_runner.py` 的核心後端啟動流程。
- **執行內容**:
    1.  建立一個獨立的虛擬環境 (`.venv_debug`)。
    2.  安裝 `requirements/dev.txt` 中的所有依賴。
    3.  啟動後端服務 (`scripts/start_api_service.py`)。
    4.  **實現了一個看門狗 (Watchdog) 機制**: 監控後端服務的日誌輸出，如果在指定時間內沒有任何活動，則會判定服務已卡死並將其終止。
- **使用方法**:
  ```bash
  # 從專案根目錄執行
  python BUG/colab_runner_debug.py
  ```

### `report_debug.py`

- **核心功能**: 獨立測試報告生成流程。
- **執行內容**:
    1.  使用由 `colab_runner_debug.py` 建立的 `.venv_debug` 虛擬環境。
    2.  安裝報告專用的額外依賴 (`requirements/report.txt`)。
    3.  如果找不到 `logs.sqlite` 資料庫，會自動建立一個包含假數據的資料庫以供測試。
    4.  執行報告生成腳本 (`scripts/generate_report.py`)。
- **使用方法**:
  ```bash
  # 應在 colab_runner_debug.py 執行完畢後運行
  python BUG/report_debug.py
  ```
