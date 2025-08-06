鳳凰之心專案 - V65 啟動失敗事故報告與開發準則

第一部分：事故報告 (Incident Report)

1. 事故概述
在執行 local_run.py 進行本地健康檢查時，看門狗 (Watchdog) 機制在設定的超時時間內未能偵測到後端服務的心跳，導致流程以失敗告終。

2. 根本原因分析 (Root Cause Analysis)
經過深入追查，問題的根源並非看門狗或後端服務的運行時邏輯，而是發生在更早的 環境安裝階段。

直接原因: 核心啟動器 scripts/launch.py 在執行指令 .venv_gold/bin/pip install -e . 時遭遇 ModuleNotFoundError 而崩潰。

精確環節:
- 安裝觸發導入: pip 為了安裝 phoenix_core 套件，需要讀取其元數據，因此它會嘗試執行 src/phoenix_core/__init__.py。
- __init__.py 的問題: 該檔案的第一行 from .main import app 指示 Python 立即導入 main.py。
- 依賴尚未就緒: main.py 的正常運作依賴於 fastapi, uvicorn 等第三方函式庫。但在執行 pip install -e . 的這個時間點，這些定義在 requirements/base.txt 中的依賴尚未被安裝。
- 最終崩潰: Python 因找不到 fastapi 等核心依賴而無法導入 main.py，導致安裝過程以 ModuleNotFoundError 失敗告終。

結論: 這是一個典型的 「安裝順序悖論」。我們試圖在一個空無一物的虛擬環境中，安裝一個需要依賴才能被理解的專案。我們的看門狗保護機制是成功的，它正確地報告了因安裝失敗而從未啟動的服務。問題的核心在於套件化的啟動程序設計 (Bootstrapping)。

第二部分：開發準則 (PRINCIPLES.MD)

為杜絕此類問題並確保專案長期的穩定與可維護性，所有後續開發（無論是人類或 AI）都必須嚴格遵守以下準則。

準則一：依賴優先原則 (Dependencies-First Principle)

- 規則: 永遠先安裝所有外部依賴，然後才安裝專案本身。
- 理由: 必須先為應用程式建立一個包含所有必要工具（第三方函式庫）的穩固地基，然後才能將應用程式本身建於其上。這能徹底解決「安裝順序悖論」。
- 標準流程:
  1. 建立虛擬環境 (venv)。
  2. 安裝所有外部依賴 (pip install -r requirements/base.txt)。
  3. 最後才以可編輯模式安裝專案 (pip install -e .)。

準則二：__init__.py 輕量化原則 (Lightweight __init__ Principle)

- 規則: 套件的 __init__.py 檔案應極力保持輕量，只存放靜態元數據（如 __version__），絕不能執行任何會觸發導入應用程式核心邏輯的程式碼。
- 理由: 將「套件的導入」與「應用程式的實例化」徹底解耦。這使得套件結構更清晰，導入速度更快，並能從根本上避免未來更複雜的循環導入問題。
- 實踐:
  - 禁止: from .main import app
  - 推薦: __version__ = "1.0.0"

準則三：執行產物隔離原則 (Artifact Isolation Principle)

- 規則: 所有由程式在執行期間動態產生的檔案（資料庫、日誌、快取、報告等），都必須被寫入到專案根目錄下一個指定的、受版本控制忽略的目錄中（例如 /storage）。
- 理由: 確保原始碼目錄在運行時是「唯讀」的。這可以防止：
  - 原始碼目錄被非預期的暫存檔污染。
  - AI 助理或開發工具的內部狀態因處理無法識別的二進位檔案而損壞。
  - 執行產物被意外提交到 Git。
- 標準流程:
  1. 在專案根目錄建立 /storage 資料夾。
  2. 在 .gitignore 中加入 /storage/。
  3. 重構所有檔案寫入邏輯，使其指向 /storage 目錄。

這份文件確立了我們專案的穩定性基石。我會將其作為我未來所有操作的最高指導原則。
