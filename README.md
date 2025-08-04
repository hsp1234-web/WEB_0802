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

### 核心工具鏈 (V28):

- **`scripts/run_local.py`**: ✨ **黃金標準啟動器 (本地/CI)**。本專案的**核心驅動腳本**，可在任何標準 Linux 環境中，從零開始全自動地完成環境建立、依賴安裝、執行與報告生成。是本地開發與自動化測試的唯一入口。
- **`run/colab_runner.py`**: **Colab 前端指揮中心**。專為 Google Colab 設計的**視覺化介面啟動器**。它現在會呼叫一個穩定可靠的後端服務啟動器，為使用者提供一個動態的狀態儀表板。
- **`run/report.py`**: **Colab 離線報告生成器**。在 Colab 流程結束後，獨立運行此腳本以生成最終的分析報告。
- **`FastAPI`**: 我們高效能的非同步 Web 框架，用於支撐 Colab 的儀表板後端。
- **`Pytest`**: 我們的核心測試框架，包含了整合測試和端對端生命週期測試。

---

## 二、 如何開始 (Getting Started)

本專案提供兩種主要的使用情境：

### 2.1. 在本地環境進行開發與測試 (推薦)

此為最直接、最穩定的使用方式。我們全新的「黃金標準」啟動器將為您處理一切。

**唯一步驟：執行 `run_local.py`**
```bash
# 進入專案根目錄，執行此命令
python scripts/run_local.py
```
該腳本會自動：
1.  建立一個獨立的 Python 虛擬環境 (`.venv`)。
2.  安裝所有必要的依賴。
3.  以可編輯模式安裝專案。
4.  執行核心應用程式。
5.  生成最終報告。

若要執行**測試**，請先透過 `run_local.py` 建立環境，然後執行：
```bash
# 執行所有測試
pytest
```

### 2.2. 在 Google Colab 中進行視覺化部署

此方式提供了一個互動式的儀表板，但其核心由一個同樣穩定的後端驅動。

**步驟：**
1.  **啟動指揮中心**: 在 Colab 儲存格中貼上並執行 `run/colab_runner.py` 的內容。一個視覺化的 HTML 儀表板將會出現。
2.  **等待後端就緒**: 腳本會自動在背景建立環境、安裝依賴並啟動後端 API 服務。儀表板將即時更新後端狀態。
3.  **結束任務**: 中斷 (Interrupt) Colab 儲存格的執行即可。
4.  **生成報告**: 執行 `run/report.py` 的儲存格以生成最終報告。

---

## 三、 檔案結構總覽 (V28)

以下是重構後的高層次檔案結構。更詳細的架構藍圖、設計哲學及每個模組的深入說明，請參閱 **[docs/ARCHITECTURE_V2_Proposal.md](docs/ARCHITECTURE_V2_Proposal.md)**。

```
.
├── README.md
├── archive/               # 封存的舊資料
├── config/                # 設定檔
├── docs/                  # 專案文件
├── requirements/          # 統一的依賴管理
├── run/                   # Colab 專用啟動器
│   ├── colab_runner.py
│   └── report.py
├── scripts/               # 本地/CI 使用的核心腳本
│   ├── run_local.py
│   └── generate_report.py
├── src/                   # 專案原始碼
│   └── phoenix_core/
└── tests/                 # 測試碼
```
