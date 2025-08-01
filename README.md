# 🚀 鳳凰之心 (Phoenix Heart) 專案 v27 - 資料庫驅動架構 🚀

歡迎來到鳳凰之心，一個從單體架構中浴火重生的現代化後端專案。本專案現已進化至 v27，搭載了以 **SQLite 資料庫為核心的、前後端完全解耦的**穩定架構，並特別為 Google Colab 環境的互動式操作進行了深度優化。

它不僅是一個展示模組化設計的範例，更是一個具備高度穩定性、可觀測性和擴展性的專業開發框架。

---

## 一、 核心理念與架構 (Core Philosophy & Architecture)

我們的架構基於以下四大核心理念：

- **資料庫即真相 (Database as the Single Source of Truth)**: 所有後端任務的狀態和日誌都被寫入一個獨立的 `state.db` 資料庫。這是整個系統唯一、可信的狀態來源。
- **職責分離 (Separation of Concerns)**:
    - **後端 (`scripts/launch.py`)**: 只專注於執行核心任務，並將狀態寫入資料庫。
    - **前端 (`run/colab_runner.py`)**: 只專注於從資料庫讀取狀態，並將其渲染成儀表板。
- **解耦與穩定 (Decoupling & Stability)**: 前端的任何問題（如 Colab 顯示中斷）**絕不會**影響後端任務的穩定運行。
- **依賴鎖定 (Dependency Locking)**: 透過 `pip-tools` 管理所有 Python 依賴，確保了開發與部署環境的絕對一致性。

### 核心工具鏈:

- **`scripts/launch.py`**: **後端核心服務**。此腳本是整個系統的「引擎」，負責執行所有主要任務，並將狀態和日誌記錄到 `state.db`。
- **`run/colab_runner.py`**: **Colab 前端戰情室**。在 Colab 環境中運行的主要入口，它會輪詢 `state.db` 來提供一個動態的、即時的後端狀態儀表板。
- **`scripts/report_generator.py`**: **獨立報告引擎**。由 `launch.py` 在任務結束後自動呼叫，負責從 `uvicorn.log` 等來源產生詳細的分析報告。
- **`src/phoenix_core/`**: 專案的主要 Python 套件，包含了所有 FastAPI 相關的原始碼。
- **SQLite**: 我們輕量、可靠的狀態資料庫。
- **FastAPI**: 我們所有微服務使用的現代、高效能 Web 框架。

---

## 二、 如何開始 (Getting Started)

本專案提供兩種主要的使用情境：

### 2.1. 在 Google Colab 中進行視覺化部署 (推薦)

此為體驗本專案完整功能的推薦方式。此流程需要您**打開兩個 Colab 儲存格**來模擬前後端分離的架構。

**第一步：啟動後端核心**
1.  在一個 Colab 儲存格中，貼上 `scripts/launch.py` 的內容。
2.  執行該儲存格。您會看到後端任務開始執行的日誌。讓它在背景運行。

**第二步：啟動前端戰情室**
1.  在**另一個** Colab 儲存格中，貼上 `run/colab_runner.py` 的內容。
2.  執行該儲存格。
3.  一個視覺化的 HTML 儀表板將會出現，即時顯示由第一個儲存格中的後端服務所產生的狀態和日誌。

### 2.2. 在本機環境進行開發與測試

當您需要在本機進行開發或執行測試時，請遵循以下步驟：

**1. 設定開發環境**

首先，安裝所有測試和開發所需的依賴：
```bash
# 安裝所有開發與測試所需的依賴
pip install -r requirements-dev.txt
```

**2. 執行完整測試套件**

使用 `pytest` 來驗證所有功能是否正常。我們的測試套件 (`tests/integration/test_db_driven_architecture.py`) 專為驗證此資料庫驅動架構而設計。
```bash
# 執行所有測試
python -m pytest
```

---

## 三、 檔案結構總覽

以下是專案的高層次檔案結構。更詳細的架構藍圖、設計哲學及每個模組的深入說明，請參閱 **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**。

```
.
├── README.md
├── config/
├── docs/
│   └── ARCHITECTURE.md
├── reports/
├── run/
│   ├── colab_runner.py
│   └── report.py
├── scripts/
│   ├── launch.py
│   └── report_generator.py
├── src/
│   └── phoenix_core/
└── tests/
    └── integration/
```
