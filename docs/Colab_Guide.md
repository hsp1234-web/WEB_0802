# Colab 使用指南：資料庫驅動架構

## 簡介

歡迎使用「鳳凰之心」專案！本指南將引導您如何在 Google Colab 環境中，運行我們穩定、可靠的資料庫驅動架構。

此架構的核心是**前後端分離**：
*   **後端 (`scripts/launch.py`)**: 一個獨立的進程，負責執行所有核心任務，並將其狀態持續寫入 `state.db` 資料庫。
*   **前端 (`run/colab_runner.py`)**: 一個純粹的顯示器，它透過讀取 `state.db` 來即時展示後端的運行狀態。

這種設計確保了即使前端顯示被中斷，後端的核心任務也能不受影響地繼續執行。

## Colab 啟動流程

您需要**兩個 Colab 儲存格**來體驗完整的流程。

### 第一步：啟動後端核心服務

在**第一個** Colab 儲存格中，貼上 `scripts/launch.py` 的完整內容。

<details>
<summary>點此展開/收合 🚀 後端核心 (scripts/launch.py) 的程式碼</summary>

```python
# 檔案: scripts/launch.py
# 說明: 專案的核心後端服務，負責執行任務並透過資料庫更新狀態。

import sqlite3
import time
import subprocess
import sys
import os
from pathlib import Path
import logging

DB_PATH = Path("state.db")
LOG_PATH = Path("uvicorn.log")

# ... (此處應為 launch.py 的完整內容) ...
```
</details>

**執行**這個儲存格。您會看到後端開始執行的日誌。讓這個儲存格在背景持續運行。

### 第二步：啟動前端戰情室

在**第二個** Colab 儲存格中，貼上 `run/colab_runner.py` 的完整內容。

<details>
<summary>點此展開/收合 📊 前端戰情室 (run/colab_runner.py) 的程式碼</summary>

```python
# 檔案: run/colab_runner.py
# 說明: 前端戰情室，純粹作為後端服務的狀態顯示器。

import sqlite3
import time
from pathlib import Path
from IPython.display import display, HTML, clear_output

DB_PATH = Path("state.db")
LOG_PATH = Path("uvicorn.log")
# ... (此處應為 colab_runner.py 的完整內容) ...
```
</details>

**執行**這個儲存格。一個視覺化的 HTML 儀表板將會出現，並開始每隔幾秒刷新一次，即時顯示第一個儲存格中後端服務的當前狀態和日誌。

## 預期結果

*   第一個儲存格會持續打印後端任務的日誌。
*   第二個儲存格會顯示一個儀表板，上面的「後端服務狀態」會從「後端服務已啟動」逐步變為「核心任務：處理完畢」，最終變為「任務成功完成」。
*   當第一個儲存格的任務全部完成後，它會自動呼叫報告生成器，並在專案的 `reports/` 目錄下產生分析報告。

這個流程完整地展示了前後端解耦架構的穩定性和可觀測性。
