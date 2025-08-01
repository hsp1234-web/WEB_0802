# 測試計畫與執行指南 (v27 - 資料庫驅動架構)

**文件作者：** Jules (AI 軟體工程師)
**最後更新：** 2025年8月1日

## 一、 核心理念：專注於架構驗證

隨著專案演進至穩定的資料庫驅動架構，我們的測試理念也從測試單一、龐大的腳本，轉變為**驗證核心架構的互動與正確性**。

我們的測試框架現在專注於回答以下關鍵問題：
1.  後端核心 (`scripts/launch.py`) 能否獨立、正確地執行其任務並更新資料庫？
2.  前端顯示器 (`run/colab_runner.py`) 能否在後端运行时，正確地從資料庫讀取到一系列的狀態變化？
3.  整個前後端解耦的流程是否如預期般順暢運作？

---

## 二、 如何執行測試：`pytest` 與整合測試

所有測試都應透過 `pytest` 命令列工具來啟動。我們已經在 `pytest.ini` 中配置了高效能的預設選項 (`-n auto` 平行化執行, `--timeout=60` 全域超時)。

### **前置要求：**

- **Python 3.8+ 環境**
- **安裝開發依賴:** 在執行測試前，請確保已安裝所有必要的開發與測試依賴。
  ```bash
  pip install -r requirements-dev.txt
  ```

### **執行測試套件:**

在專案的根目錄下，執行 `pytest`：

```bash
# 執行所有測試
python -m pytest
```

或者，您可以只執行針對此架構的特定整合測試：

```bash
python -m pytest tests/integration/test_db_driven_architecture.py
```

---

## 三、 核心測試詳解：`test_db_driven_architecture.py`

這是我們目前最重要的測試檔案，它包含了兩個關鍵的測試案例：

1.  **`test_launch_script_execution()`**:
    *   **目標**: 驗證 `scripts/launch.py` 作為一個獨立單元的正確性。
    *   **作法**: 直接透過 `subprocess` 執行 `launch.py`。
    *   **斷言**: 檢查 `state.db` 是否被建立，以及任務完成後，資料庫中的最終狀態是否為「任務成功完成」。

2.  **`test_e2e_db_driven_flow()`**:
    *   **目標**: 驗證前後端之間的解耦通訊。
    *   **作法**: 使用 Python 的 `multiprocessing` 模組，在一個背景進程中啟動 `launch.py`。同時，主進程會模擬 `run/colab_runner.py` 的行為，持續輪詢 `state.db`。
    *   **斷言**: 檢查主進程是否能成功觀察到由背景進程寫入的一系列預期狀態變化。

這套測試完整地驗證了我們資料庫驅動架構的核心邏輯，確保了其穩定性和可靠性。
