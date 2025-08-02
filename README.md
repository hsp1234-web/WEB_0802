# 🚀 鳳凰之心 (Phoenix Heart) 專案 v0.1.0 (V24) - API 驅動架構 🚀

歡迎來到鳳凰之心，一個從單體架構中浴火重生的現代化後端專案。本專案現已進化至 **V24**，搭載了以 **`Aiohttp` 非同步 API 為核心的、前後端完全解耦的**現代化架構，並特別為 Google Colab 環境的互動式操作進行了深度優化。

它不僅是一個展示模組化設計的範例，更是一個具備高度穩定性、可觀測性和擴展性的專業開發框架。

---

## 一、 核心理念與架構 (Core Philosophy & Architecture)

我們的架構基於以下四大核心理念：

- **API 驅動通訊 (API-Driven Communication)**: 前後端之間的所有通訊都透過一組定義清晰的 RESTful API 進行。這是整個系統的互動契約。
- **職責分離 (Separation of Concerns)**:
    - **後端 (`scripts/launch.py`)**: 作為一個 `Aiohttp` 服務，只專注於執行核心任務，並透過 API 端點暴露其狀態。
    - **前端 (`run/colab_runner.py`)**: 只專注於啟動後端，並透過輪詢 API 來渲染儀表板。
- **解耦與穩定 (Decoupling & Stability)**: 前端的任何問題（如 Colab 顯示中斷）**絕不會**影響後端任務的穩定運行。後端服務的狀態由其自身管理。
- **依賴鎖定 (Dependency Locking)**: 透過 `pip-tools` 管理所有 Python 依賴，確保了開發與部署環境的絕對一致性。

### 核心工具鏈:

- **`run/colab_runner.py`**: **Colab 前端指揮中心**。在 Colab 環境中運行的**唯一入口**。它會啟動後端服務，並透過輪詢 API 來提供一個動態的、即時的後端狀態儀表板。
- **`scripts/launch.py`**: **後端核心 API 服務**。此腳本是整個系統的「引擎」，負責執行所有主要任務，並透過 `/api/v1/status` 等端點提供狀態更新。
- **`run/report.py`**: **離線報告生成器**。在整個任務結束後，獨立運行此腳本，它會讀取後端服務關機時持久化的 `state.db`，生成詳細的分析報告。
- **`Aiohttp`**: 我們輕量、高效能的非同步 Web 框架。
- **`Pytest`**: 我們的核心測試框架，包含了整合測試和端對端生命週期測試。

---

## 二、 如何開始 (Getting Started)

本專案提供兩種主要的使用情境：

### 2.1. 在 Google Colab 中進行視覺化部署 (推薦)

此為體驗本專案完整功能的推薦方式。與舊版不同，**V24 架構極其簡潔，只需執行一個 Colab 儲存格**。

**唯一步驟：啟動指揮中心**
1.  在一個 Colab 儲存格中，貼上 `run/colab_runner.py` 的完整內容。
2.  根據您的需求，調整儲存格頂部的 `#@param` 表單參數（例如 `TARGET_BRANCH_OR_TAG`）。
3.  執行該儲存格。
4.  `colab_runner.py` 會自動在背景下載程式碼、安裝依賴、並啟動後端 API 服務。一個視覺化的 HTML 儀表板將會出現，即時顯示後端服務的狀態。
5.  若要結束任務，只需**中斷 (Interrupt)** Colab 儲存格的執行。腳本會自動向後端發送優雅關機信號。
6.  關機後，執行 `run/report.py` 的儲存格以生成最終報告。

### 2.2. 在本機環境進行開發與測試

當您需要在本機進行開發或執行測試時，請遵循以下步驟：

**1. 設定開發環境**

首先，建立虛擬環境並安裝所有開發依賴：
```bash
# 建立 venv
uv venv .venv
# 啟用 venv (Linux/macOS)
source .venv/bin/activate
# 安裝所有開發與測試所需的依賴
uv pip install -r requirements-dev.txt
```

**2. 執行完整測試套件**

使用 `pytest` 來驗證所有功能是否正常。我們的測試套件涵蓋了 API 整合測試和完整的端對端生命週期測試。
```bash
# 執行所有測試
pytest
```

---

## 三、 檔案結構總覽

以下是專案的高層次檔案結構。更詳細的架構藍圖、設計哲學及每個模組的深入說明，請參閱 **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**。

```
.
├── README.md
├── config/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── CHANGELOG.md
│   └── MISSION_DEBRIEFING.md
├── run/
│   ├── colab_runner.py
│   └── report.py
├── scripts/
│   ├── launch.py
│   └── report_generator.py
└── tests/
    ├── integration/
    └── e2e/
```
