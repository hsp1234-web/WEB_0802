# 檔案: src/phoenix_core/kernel/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator
import json
from pathlib import Path
import os

class LogSettings(BaseSettings):
    """日誌相關設定"""
    BATTLE: bool = True
    SUCCESS: bool = True
    INFO: bool = True
    CMD: bool = True
    LOG_SHELL: bool = True  # Renamed from SHELL to avoid collision with system env var
    ERROR: bool = True
    CRITICAL: bool = True
    PERF: bool = False

class Settings(BaseSettings):
    """
    應用程式的核心設定模型。
    Pydantic 會從多個來源按優先級讀取設定：
    1. 直接傳入的參數
    2. 環境變數
    3. .env 檔案
    4. JSON 設定檔
    5. 預設值
    """
    APP_NAME: str = Field("鳳凰之心", description="應用程式的名稱")
    APP_ENV: str = Field("development", description="運行環境 (development/production)")
    APP_STORAGE: str = Field("./storage", description="應用程式的本地儲存路徑")
    LOG_SETTINGS: LogSettings = Field(default_factory=LogSettings)
    TRANSCRIPTION_MODEL_SIZE: str = Field("tiny", description="用於音訊轉錄的 Whisper 模型大小")

    @model_validator(mode='before')
    @classmethod
    def load_from_json(cls, values):
        """從環境變數 PHOENIX_CONFIG_PATH 指定的 JSON 檔案載入設定"""
        config_path_str = os.environ.get("PHOENIX_CONFIG_PATH")
        if config_path_str and Path(config_path_str).exists():
            config_path = Path(config_path_str)
            print(f"--- 正在從 JSON 設定檔載入: {config_path} ---")
            with open(config_path, 'r', encoding='utf-8') as f:
                json_config = json.load(f)

            # 將 JSON 中的設定與現有值（可能來自環境變數）合併
            # 這裡簡單地讓 JSON 覆蓋現有值
            if 'log_settings' in json_config:
                # pydantic v2 中，巢狀模型需要是字典
                if 'LOG_SETTINGS' not in values:
                    values['LOG_SETTINGS'] = {}
                values['LOG_SETTINGS'].update(json_config['log_settings'])

        return values

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        env_prefix="PHOENIX_",
        case_sensitive=False,
        # 允許從巢狀字典中填充模型
        # 例如 PHOENIX_LOG_SETTINGS='{"ERROR": false}'
        env_nested_delimiter='__',
    )

# 建立一個全域可用的設定實例
settings = Settings()
