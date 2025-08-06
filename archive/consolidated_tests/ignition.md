# 抽象化摘要：點火測試 (Ignition Test)

本文檔旨在封存與總結專案中發現的兩種不同的「點火測試」實現方式。點火測試的核心目標是確保專案中所有的 Python 模組都能夠被成功導入，而不會因循環依賴、初始化錯誤等問題導致程式崩潰。

---

## 設計演進分析

在專案的不同部分發現了兩種實現此目標的方法，這反映了不同的開發階段和設計成熟度。

### 方法一：靜態手動導入 (較早期、不推薦)

這種方法在 `CL_0805/MP3_Converter_TXT/tests/ignition_test.py` 中被發現。

**設計思路**:
直接在測試檔案中 `import` 所有需要測試的模組，然後使用 `assert` 來確認這些模組對象存在。

**優點**:
*   **簡單直觀**: 程式碼極其簡單，容易理解。

**缺點**:
*   **維護成本高**: 每當專案中新增或刪除一個模組時，都必須手動更新這個測試檔案。
*   **容易遺漏**: 開發者很容易忘記更新此檔案，導致新的模組從未被納入導入測試，失去了測試的意義。

---

### 方法二：動態模組發現 (較成熟、推薦)

這種方法在 `CL_0805/0709_wolf_88/tests/ignition_test.py` 中被發現，是更為健壯和自動化的解決方案。

**設計思路**:
編寫一個腳本，在測試執行時：
1.  自動遍歷指定的源碼目錄（如 `src/`）。
2.  動態地發現所有 `.py` 檔案。
3.  將檔案系統路徑轉換為 Python 的模組導入路徑（例如 `src/foo/bar.py` -> `foo.bar`）。
4.  使用 `pytest.mark.parametrize` 為每一個發現的模組動態地創建一個測試案例。
5.  在測試案例中，使用 `importlib.import_module()` 來嘗試導入模組。

**優點**:
*   **自動化**: 無需手動維護模組列表，完全自動發現。
*   **健壯性高**: 不會因為開發者忘記更新而失效。
*   **單一職責**: 測試代碼本身保持不變，只專注於「導入」這個行為。

**結論**:
方法二是顯著更優的工程實踐。它將維護負擔從開發者轉移給了自動化腳本，確保了測試的長期有效性。因此，我們將其程式碼作為標準範例在此處封存，以供未來參考。

---

## 範例程式碼 (動態發現版本)

```python
# -*- coding: utf-8 -*-
# ==============================================================================
#  磐石協議 (The Bedrock Protocol)
#  導入測試器：ignition_test.py
#
#  功能：
#  - 輕量級地嘗試導入所有專案模組，以捕獲以下類型的錯誤：
#    1. 循環依賴 (Circular Dependencies)。
#    2. 導入時執行了錯誤的代碼 (Initialization-Time Errors)。
#    3. 某些 Python 版本或環境中才會出現的導入失敗。
#
#  執行方式：
#  - 作為 pytest 測試套件的一部分自動運行。
#
#  命名由來：
#  - "Ignition Test" (點火測試) 是一個工程術語，指在系統全面啟動前，
#    對關鍵子系統進行的初步、簡短的測試，以確保它們能被「點燃」而無爆炸。
#    這與本測試的目標——確保所有模組都能被成功導入而不崩潰——完美契合。
# ==============================================================================

import importlib
import os
from pathlib import Path

import pytest

# --- 常數定義 ---
# 定義專案的根目錄，這裡我們假設 `tests` 目錄位於專案根目錄下
PROJECT_ROOT = Path(__file__).parent.parent
# 定義要進行導入測試的源碼目錄
SOURCE_DIRECTORIES = ["src"]
# 定義需要從測試中排除的特定檔案或目錄
EXCLUDE_PATTERNS = [
    "__pycache__",  # 排除 Python 的快取目錄
    "__init__.py",  # __init__ 通常為空或只有簡單的導入，可選擇性排除
    "py.typed",  # PEP 561 標記文件，非模組
    # 如果有特定已知問題的模組，可以在此處暫時排除
    # "apps/some_problematic_module.py",
]


# --- 輔助函數 ---
def is_excluded(path: Path, root: Path) -> bool:
    """
    檢查給定的檔案路徑是否符合任何排除規則。

    Args:
        path: 要檢查的檔案的 Path 對象。
        root: 專案根目錄的 Path 對象。

    Returns:
        如果路徑應被排除，則返回 True，否則返回 False。
    """
    # 將絕對路徑轉換為相對於專案根目錄的相對路徑
    relative_path_str = str(path.relative_to(root))
    # 檢查路徑的任何部分是否匹配排除模式
    return any(pattern in relative_path_str for pattern in EXCLUDE_PATTERNS)


def discover_modules(root_dir: Path, source_dirs: list[str]) -> list[str]:
    """
    從指定的源碼目錄中發現所有可導入的 Python 模組。

    Args:
        root_dir: 專案的根目錄。
        source_dirs: 包含源碼的目錄列表 (例如 ["apps", "core"])。

    Returns:
        一個包含所有模組的 Python 導入路徑的列表 (例如 ["apps.main", "core.utils.helpers"])。
    """
    modules = []
    for source_dir in source_dirs:
        # 遍歷指定源碼目錄下的所有檔案
        for root, _, files in os.walk(root_dir / source_dir):
            for file in files:
                # 只處理 Python 檔案
                if file.endswith(".py"):
                    file_path = Path(root) / file
                    # 檢查檔案是否應被排除
                    if not is_excluded(file_path, root_dir):
                        # 將檔案系統路徑轉換為 Python 的模組導入路徑
                        # 例如：/path/to/project/src/prometheus/core/utils.py -> prometheus.core.utils
                        relative_path = file_path.relative_to(root_dir / "src")
                        # 移除 .py 副檔名
                        module_path_without_ext = relative_path.with_suffix("")
                        # 將路徑分隔符轉換為點
                        module_name = str(module_path_without_ext).replace(os.sep, ".")
                        modules.append(module_name)
    return modules


# --- 測試參數化 ---
# 在 pytest 收集測試時，動態發現所有要測試的模組
all_modules = discover_modules(PROJECT_ROOT, SOURCE_DIRECTORIES)


@pytest.mark.parametrize("module_name", all_modules)
def test_module_ignition(module_name: str):
    """
    對給定的模組名稱執行導入測試。

    Args:
        module_name: 要測試的模組的 Python 導入路徑。
    """
    try:
        # 嘗試導入模組
        importlib.import_module(module_name)
    except ImportError as e:
        # 捕捉導入失敗的錯誤，並提供清晰的錯誤訊息
        pytest.fail(
            f"🔥 點火失敗！導入模組 '{module_name}' 時發生錯誤: {e}", pytrace=False
        )
    except Exception as e:
        # 捕捉在導入過程中執行代碼時發生的任何其他異常
        pytest.fail(
            f"💥 災難性故障！模組 '{module_name}' 在導入時崩潰: {e.__class__.__name__}: {e}",
            pytrace=True,
        )
```
