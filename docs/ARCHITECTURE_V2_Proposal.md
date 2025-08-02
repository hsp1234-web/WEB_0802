# 🏗️ 專案架構藍圖 (V2)

本文檔闡述了「鳳凰之心」專案在 V28 版本後採用的標準化、專業化專案架構。此架構的設計目標是實現**高度的模組化、清晰的職責分離、以及在不同環境下（本地/CI vs. Colab）的穩定、可複現執行**。

---

## 1. 高層次設計哲學

我們遵循業界公認的 Python 專案最佳實踐，其核心思想包括：

- **源碼佈局 (Source Layout)**: 所有的核心應用程式碼都應位於 `src/` 目錄下。這可以防止意外的、依賴相對路徑的導入，並確保專案被正確地安裝。
- **單一職責原則**: 每個檔案、每個模組、每個腳本都應該只有一個明確的、集中的職責。
- **環境隔離**: **絕不**在系統的全域 Python 環境中進行開發或部署。所有操作都必須在一個專案獨有的虛擬環境 (venv) 中進行。
- **依賴管理**: 所有的依賴都應在 `requirements/` 目錄中進行顯式聲明和分組，並透過 `pip-tools` 等工具進行鎖定，以保證環境的可複現性。
- **配置外部化**: 應用程式的配置（如金鑰、資源路徑等）應與程式碼分離，統一存放在 `config/` 目錄中。

---

## 2. 目錄結構詳解

以下是我們標準的目錄結構，以及每個部分的職責說明。

```
/
├── .gitignore             # Git 忽略設定，用於排除 venv、快取等檔案
├── .venv/                 # [自動生成] 本地開發用的虛擬環境 (被 gitignore 忽略)
│
├── archive/               # 【封存】存放舊的、不再使用的參考資料
│   └── ALLDATA/
│
├── config/                # 【設定】存放所有環境設定檔 (如 settings.yml)
│   └── settings.yml
│
├── docs/                  # 【文件】所有專案文件，包括本架構文件
│   ├── ARCHITECTURE_V2_Proposal.md
│   ├── Colab_Guide_V2_Proposal.md
│   └── MISSION_DEBRIEFING.md
│
├── requirements/          # 【依賴】統一管理所有 Python 依賴
│   ├── base.txt           # 核心依賴 (應用程式運行所需)
│   ├── dev.txt            # 開發依賴 (測試、格式化工具)
│   └── report.txt         # 報告生成依賴
│
├── run/                   # 【Colab 入口】為 Colab 環境保留的啟動腳本
│   ├── colab_runner.py    # Colab 儀表板前端啟動器
│   └── report.py          # Colab 報告生成觸發器
│
├── scripts/               # 【主要腳本】供開發者/CI 使用的核心自動化腳本
│   ├── run_local.py       # 本地/CI 環境的「黃金標準」總啟動器
│   ├── start_api_service.py # 專供 colab_runner.py 呼叫的穩定後端啟動器
│   └── generate_report.py # 獨立的報告生成邏輯
│
├── src/                   # 【應用程式碼】所有專案的核心原始碼
│   └── phoenix_core/      # 我們的 Python 套件
│       ├── __init__.py
│       ├── api/           # API 相關模組
│       ├── kernel/        # 核心內核模組
│       ├── utils/         # 工具函式模組
│       └── main.py        # 核心商業邏輯入口
│
├── tests/                 # 【測試碼】所有 pytest 測試
│   ├── integration/       # 整合測試
│   └── unit/              # 單元測試
│
└── pyproject.toml         # Python 專案的標準設定檔
```

---

## 3. 執行流程解析

為了適應不同的使用場景，我們設計了兩條並行但相互關聯的執行路徑：

### **路徑一：本地/CI 自動化流程**

這是最核心、最穩定的執行路徑，由我們的「黃金標準」啟動器驅動。

**[開發者/CI 系統]** `->` **`python scripts/run_local.py`**
1.  **[run_local.py]** 清理並建立 `.venv` 虛擬環境。
2.  **[run_local.py]** 安裝 `requirements/` 中的所有依賴。
3.  **[run_local.py]** 執行 `pip install -e .`，將 `src/phoenix_core` 安裝為可編輯套件。
4.  **[run_local.py]** 呼叫 `src.phoenix_core.main` 中的核心邏輯函式。
5.  **[核心邏輯]** 執行任務，並生成 `state.db`。
6.  **[run_local.py]** 呼叫 `scripts/generate_report.py`。
7.  **[generate_report.py]** 讀取資料庫，生成 Markdown 報告。
8.  **[run_local.py]** 流程結束。

### **路徑二：Colab 視覺化流程**

這條路徑為使用者提供了互動式的儀表板，其後端由一個穩定的、隔離的服務支撐。

**[Colab 使用者]** `->` **點擊執行 `run/colab_runner.py`**
1.  **[colab_runner.py]** 顯示 HTML 儀表板前端。
2.  **[colab_runner.py]** 在背景執行 `python scripts/start_api_service.py`。
3.  **[start_api_service.py]**
    *   建立一個**專用的** `.venv_colab_backend` 虛擬環境。
    *   安裝 `requirements/base.txt` 中的依賴。
    *   啟動 FastAPI 伺服器 (`src.phoenix_core.api.server`)，監聽 `localhost:8088`。
4.  **[儀表板前端]**
    *   透過 JavaScript，每秒向 `localhost:8088/api/v1/status` 發送請求。
    *   接收後端回傳的 JSON 數據，並更新儀表板上的狀態。
5.  **[Colab 使用者]** `->` **中斷 `colab_runner.py` 的執行**
6.  **[colab_runner.py]** 捕捉中斷信號，終止 `start_api_service.py` 背景進程。
7.  **[Colab 使用者]** `->` **點擊執行 `run/report.py`**
8.  **[report.py]** 呼叫 `scripts/generate_report.py`，生成最終報告。

---

此架構透過清晰的職責劃分和環境隔離，確保了專案在不同場景下的健壯性和可維護性，為未來的迭代開發奠定了堅實的基礎。
