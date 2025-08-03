# -*- coding: utf-8 -*-
import sys
import json
from .database import db_manager

# 偵測是否在 Colab 環境中
IS_COLAB = 'google.colab' in sys.modules

class CommManager:
    """
    一個處理與 Colab 前端通訊的管理器。

    在 Colab 環境中，它使用 google.colab.kernel.comms 來發送訊息。
    在本地環境中，它會將訊息打印到主控台，以模擬通訊行為。
    """
    _instance = None

    def __new__(cls, target_name='phoenix_comms'):
        if not cls._instance:
            cls._instance = super(CommManager, cls).__new__(cls)
            cls._instance.target_name = target_name
            cls._instance.comms = None
            if IS_COLAB:
                try:
                    from google.colab import kernel
                    # 建立一個可以向前端發送訊息的通訊頻道
                    cls._instance.comms = kernel.comms.Comm(target_name=target_name)
                    print(f"[CommManager] 成功建立 Colab Comm 頻道: {target_name}")
                except Exception as e:
                    print(f"[CommManager] 建立 Colab Comm 失敗: {e}")
        return cls._instance

    def send_data(self, data_type: str, payload: dict):
        """
        向前端發送結構化數據。

        Args:
            data_type (str): 數據的類型 (例如 'log', 'status_update')。
            payload (dict): 要發送的數據內容。
        """
        message = {
            "type": data_type,
            "payload": payload
        }
        if IS_COLAB and self.comms:
            try:
                self.comms.send(json.dumps(message))
            except Exception as e:
                # 在 Colab 中，如果前端關閉，發送可能會失敗
                # print(f"[CommManager] 發送數據失敗: {e}")
                pass # 通常可以安全地忽略此錯誤
        else:
            # 在本地模式下，只打印到 console
            # print(f"[本地 Comms] 發送數據: {json.dumps(message)}")
            pass # 在本地模式下，我們直接看 backend_worker 的輸出，所以這裡不需要打印

# 我們需要修改 DatabaseManager 來整合 Comms
# 這被稱為「猴子補丁 (Monkey Patching)」，在動態語言中是一種常見的技巧，
# 用於在不修改原始碼的情況下擴充類別功能。

def db_write_log_with_comms(self, level: str, message: str, source: str = "backend"):
    """
    擴充後的日誌方法，除了寫入資料庫外，還會透過 Comms 發送日誌。
    """
    # 1. 呼叫原始的日誌方法
    self.original_write_log(level, message, source)

    # 2. 透過 Comms 發送日誌
    timestamp = self.get_status('last_log_timestamp') # 假設時間戳已寫入
    comm_manager.send_data(
        data_type='log_entry',
        payload={
            'timestamp': timestamp,
            'level': level,
            'message': message,
            'source': source
        }
    )

def db_write_status_update_with_comms(self, key: str, value: str):
    """
    擴充後的設定狀態方法，除了寫入資料庫外，還會透過 Comms 發送狀態更新。
    """
    # 1. 呼叫原始的設定狀態方法
    self.original_write_status_update(key, value)

    # 2. 透過 Comms 發送狀態更新
    comm_manager.send_data(
        data_type='status_update',
        payload={
            key: value
        }
    )

def patch_database_manager_for_comms():
    """
    將通訊功能動態地整合到現有的 DatabaseManager 中。
    """
    print("[Patcher] 正在整合 Comms 功能到 DatabaseManager...")
    # 建立一個 CommManager 實例
    global comm_manager
    comm_manager = CommManager()

    # 保存原始方法的參考
    db_manager.original_write_log = db_manager.write_log
    db_manager.original_write_status_update = db_manager.write_status_update

    # 用我們的新方法替換原始方法
    db_manager.write_log = db_write_log_with_comms.__get__(db_manager, DatabaseManager)
    db_manager.write_status_update = db_write_status_update_with_comms.__get__(db_manager, DatabaseManager)
    print("[Patcher] ✅ Comms 功能已成功整合。")

# 在模組載入時，如果環境是 Colab，就自動執行補丁
if IS_COLAB:
    patch_database_manager_for_comms()
