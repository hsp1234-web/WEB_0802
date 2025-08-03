# -- coding: utf-8 --
""" 核心工具：資源監控器 (Resource Monitor) """
import shutil
from typing import Dict, Any
import psutil
import yaml
from .logger import logger
from src.phoenix_core.database import db_manager

def get_system_resources() -> Dict[str, Any]:
    """ 獲取當前系統的記憶體和磁碟使用情況。

    Returns:
        一個包含記憶體和磁碟資訊的字典。
    """
    memory = psutil.virtual_memory()
    disk_usage = shutil.disk_usage("/")
    cpu_usage = psutil.cpu_percent(interval=None) # interval=None 表示與上次呼叫的間隔

    return {
        "cpu": {
            "used_percent": cpu_usage,
        },
        "memory": {
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "used_percent": memory.percent,
        },
        "disk": {
            "total_gb": round(disk_usage.total / (1024**3), 2),
            "used_gb": round(disk_usage.used / (1024**3), 2),
            "free_gb": round(disk_usage.free / (1024**3), 2),
            "used_percent": round((disk_usage.used / disk_usage.total) * 100, 2),
        }
    }

def log_system_resources():
    """
    獲取當前系統資源並將其寫入資料庫。
    這是此模組對外提供的主要功能，用於替代直接的 print 或手動寫入。
    """
    resources = get_system_resources()

    # 呼叫 db_manager 的方法，將數據寫入 hardware_stats 表
    db_manager.write_hardware_stat(
        cpu_usage=resources["cpu"]["used_percent"],
        memory_usage=resources["memory"]["used_percent"],
        disk_usage=resources["disk"]["used_percent"],
        gpu_temperature=None  # 目前無法輕易獲取 GPU 溫度
    )

def load_resource_settings(config_path: str = "config/resource_settings.yml") -> Dict[str, Any]:
    """ 從指定的 YAML 檔案載入資源監控的設定。

    Args:
        config_path: 設定檔的路徑。

    Returns:
        一個包含設定參數的字典。
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.log("WARNING", f"找不到設定檔 {config_path}，將使用預設值。", source="resource_monitor")
        return {
            "resource_monitoring": {
                "memory_usage_threshold_percent": 75.0,
                "min_disk_space_mb": 512,
            }
        }

def is_resource_sufficient(settings: Dict[str, Any]) -> tuple[bool, str]:
    """ 根據提供的設定，檢查系統資源是否充足。

    Args:
        settings: 從設定檔載入的參數字典。

    Returns:
        一個元組 (is_sufficient, message)，
        如果資源充足，is_sufficient 為 True，否則為 False，
        message 包含檢查的詳細資訊。
    """
    # 為了獲取 CPU 使用率，我們需要在第一次呼叫時有個基準
    psutil.cpu_percent(interval=None)

    resources = get_system_resources()
    thresholds = settings.get("resource_monitoring", {})

    mem_threshold = thresholds.get("memory_usage_threshold_percent", 75.0)
    disk_threshold_mb = thresholds.get("min_disk_space_mb", 512)

    mem_ok = resources["memory"]["used_percent"] < mem_threshold

    # shutil.disk_usage takes path as argument
    disk_info = shutil.disk_usage("/")
    disk_free_mb = disk_info.free / (1024**2)
    disk_ok = disk_free_mb > disk_threshold_mb

    # 產生詳細的訊息
    mem_percent = resources["memory"]["used_percent"]

    message = (
        f"Memory: {mem_percent:.1f}% < {mem_threshold:.1f}% -> {'OK' if mem_ok else 'FAIL'}. "
        f"Disk: {disk_free_mb:.0f}MB > {disk_threshold_mb}MB -> {'OK' if disk_ok else 'FAIL'}."
    )

    return mem_ok and disk_ok, message
