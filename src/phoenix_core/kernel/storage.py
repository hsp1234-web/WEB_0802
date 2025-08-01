import json
from pathlib import Path
from typing import Any, Optional

# 思路框架: 定義一個指向 ALLDATA 目錄的絕對路徑，確保路徑的穩定性。
#           Path(__file__).resolve() 獲取當前檔案的絕對路徑。
#           Path(__file__).resolve() 獲取當前檔案的絕對路徑。
#           .parent.parent.parent 會向上三級，從 .../kernel/storage.py 到 .../phoenix_core/
#           再到 .../src/，最後到專案根目錄 /app。
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ALLDATA_PATH = BASE_DIR / "ALLDATA"

# 確保目錄存在
ALLDATA_PATH.mkdir(exist_ok=True)

def save_json(file_name: str, data: Any):
    """將數據以 JSON 格式保存到 ALLDATA 目錄。"""
    file_path = ALLDATA_PATH / f"{file_name}.json"
    print(f"正在將數據保存到: {file_path}")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_json(file_name: str) -> Optional[Any]:
    """從 ALLDATA 目錄讀取 JSON 檔案。如果檔案不存在，返回 None。"""
    file_path = ALLDATA_PATH / f"{file_name}.json"
    if not file_path.exists():
        return None

    print(f"正在從以下路徑讀取數據: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)
