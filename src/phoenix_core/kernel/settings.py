# 檔案: src/phoenix_core/kernel/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    """
    應用程式的核心設定模型。
    Pydantic 會自動從環境變數或 .env 檔案讀取這些值。
    """
    # 思路框架: 為每個設定提供預設值，並可通過環境變數覆蓋。
    #           例如，APP_NAME="MyCoolApp" 將會覆蓋預設的 "鳳凰之心"。
    APP_NAME: str = Field("鳳凰之心", description="應用程式的名稱")
    APP_ENV: str = Field("development", description="運行環境 (development/production)")

    # model_config 用於配置 Pydantic 的行為
    model_config = SettingsConfigDict(
        env_file=".env",          # 指定讀取的 .env 檔案
        env_file_encoding='utf-8',
        env_prefix="PHOENIX_",    # 所有環境變數都需以此為前綴，例如 PHOENIX_APP_ENV
        case_sensitive=False,     # 環境變數不區分大小寫
    )

# 建立一個全域可用的設定實例
settings = Settings()
