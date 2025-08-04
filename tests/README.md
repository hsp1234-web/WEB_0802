# 測試說明文件

本目錄下的所有 `pytest` 測試（包含單元、整合與部分端對端測試）已被整合至單一的 `test.py` 檔案中。

## 主要測試檔案

-   `test.py`: 包含了專案所有的標準化測試案例。此檔案整合了來自 `unit/`, `integration/`, `e2e/` 的測試，並包含了所有共享的 fixtures (原 `conftest.py`)。

## 如何執行測試

直接在專案根目錄下運行 `pytest` 即可：

```bash
python -m pytest
```

## 特殊測試腳本

除了 `test.py` 之外，可能還存在一些獨立的、有特殊用途的測試或分析腳本：

-   `test_colab_logic.py`: 一個完整的端對端 (E2E) 測試執行器，用於模擬 Colab 環境下的完整操作流程。它會自行管理虛擬環境，應獨立執行。
-   `test_profiling.py`: 一個效能分析腳本，用於對特定的應用程式啟動腳本進行 `cProfile` 分析。

這些特殊腳本不被 `pytest` 直接調用，需要單獨運行。
