# 📖 E2E 測試框架設計指南 (tests/e2e/test_colab_logic.py)

**文件作者：** Jules (AI 軟體工程師)
**建立日期：** 2025年8月2日

## 一、 設計哲學：在 CI/CD 中精準模擬 Colab 核心邏輯

本專案的核心挑戰之一，是在標準化、自動化的持續整合/持續部署 (CI/CD) 環境中，如何有效地測試一個為 Google Colab 這種特殊、互動式環境設計的腳本 (`run/colab_runner.py`)。

直接在 CI/CD 中執行 `colab_runner.py` 是不可行且不穩定的。因此，我們設計了 `tests/e2e/test_colab_logic.py`，其核心設計哲學是：

> **不直接執行 `colab_runner.py`，而是透過模擬其核心行為，來端對端地驗證後端服務的反應是否符合預期。**

這個 E2E 測試框架是目前專案中**最權威、最全面的測試**，它覆蓋了從環境設定、後端啟動、API 驗證到報告生成的完整生命週期。

---

## 二、 穩定性基石：自我引導的測試環境

此測試腳本最關鍵的設計之一，是它的**自我引導 (Bootstrapping)** 能力。這確保了無論它在何種乾淨的環境中執行（開發者本機、新的 CI 執行器），都能保證測試在一個完全一致、可預期的環境中運行。

其運作流程如下：
1.  **啟動**: 當使用者執行 `python tests/e2e/test_colab_logic.py` 時，腳本首先使用當前的 Python 直譯器啟動。
2.  **環境檢查與準備 (`setup_virtualenv`)**: 腳本會**立即**檢查 `.venv` 虛擬環境是否存在。
    *   如果不存在，則建立它。
    *   接著，它會使用 `.venv/bin/pip` **無條件地**安裝 `requirements/` 目錄中定義的所有依賴 (`base`, `dev`, `report`)。這一步確保了所有需要的套件都是最新且完整的。
3.  **重新啟動 (`os.execv`)**: 在確保 venv 和依賴都就緒後，腳本會檢查當前的 Python 直譯器路徑。如果不是 `.venv/bin/python`，它就會使用 `os.execv` 命令，用 venv 中的 Python 直譯器**重新啟動自己**。
4.  **執行測試**: 當腳本第二次啟動時，它檢測到自己已在正確的 venv 中，便開始執行真正的測試邏輯。

這個設計從根本上解決了「`ModuleNotFoundError`」等因環境不一致引發的各種問題，是整個測試框架穩定性的基石。

---

## 三、 測試流程詳解

在自我引導完成後，測試腳本會依序執行以下一系列的驗證：

### 1. **下載功能隔離測試 (`run_download_test`)**
*   **目的**: 獨立驗證 `colab_runner.py` 中定義的 `git clone` 功能。
*   **作法**:
    1.  建立一個臨時目錄 `temp_download_test`。
    2.  執行 `git clone` 將遠端倉庫下載到此目錄。
    3.  驗證關鍵檔案 (`pyproject.toml`) 是否存在。
    4.  在 `finally` 區塊中，**保證**會刪除 `temp_download_test` 目錄，不留下任何殘跡。

### 2. **完整伺服器生命週期測試 (`run_all_tests`)**
這部分是測試的主體，它涵蓋了從伺服器啟動到關閉的完整流程。

*   **伺服器啟動 (`start_server`)**:
    *   **模擬 `config.json`**: 根據測試案例，動態生成一個 `config.json` 檔案，模擬 `@markdown` 參數的設定。
    *   **啟動子進程**: 使用 `subprocess.Popen` 啟動後端服務 `scripts/start_api_service.py`。
    *   **看門狗機制**: 啟動一個 10 秒的定時器。在監聽後端日誌的過程中，每收到一行新日誌，就重置定時器。如果 10 秒內沒有任何動靜，測試會自動失敗，防止 CI/CD 卡死。

*   **API 驗證 (`run_api_tests`)**:
    *   驗證 `/` 端點（網頁可訪問性）。
    *   驗證 `/api/v1/status/dashboard` 端點回傳的日誌，是否符合 `config.json` 中設定的過濾規則。

*   **刷新率驗證 (`run_refresh_rate_test`)**:
    *   驗證 `/api/v1/status/performance` 端點回傳的是即時的、非寫死的系統數據。

*   **報告生成驗證 (`run_report_generation_test`)**:
    *   **偽造資料庫**: 由於後端 API 目前是 Mock 狀態，此步驟會先**動態建立一個假的 `state.db`**，並填入模擬的日誌和狀態資料。
    *   **執行與驗證**: 接著執行 `scripts/generate_report.py`，並斷言所有預期的 Markdown 報告是否都已生成。

*   **全面清理 (`cleanup`)**:
    *   在每個測試案例結束時，保證會終止伺服器進程，並刪除所有臨時產生的檔案（`config.json`, `state.db`, `wolf.html`）和目錄（報告目錄）。

---

## 四、 結論

`tests/e2e/test_colab_logic.py` 不僅僅是一個測試腳本，它是一個**穩定、可靠、且自我修復的自動化框架**。它透過精巧的設計，成功地在一個標準化的環境中，驗證了一個為非標準化環境所開發的應用程式的核心功能，為專案的品質提供了堅實的保障。
