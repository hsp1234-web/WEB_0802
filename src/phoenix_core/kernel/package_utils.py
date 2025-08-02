# -*- coding: utf-8 -*-
"""
套件管理輔助工具 (Package Management Utilities)

這個模組提供了一系列與套件安裝和管理相關的輔助函式，
特別是為了在資源受限的環境中（如 Google Colab）進行安全、可靠的安裝。
"""
import httpx
import logging
import re

# 為這個模組設定一個日誌記錄器
# 外部呼叫者可以根據需要設定日誌的等級和格式
logger = logging.getLogger(__name__)

def parse_package_spec(package_spec: str) -> tuple[str, str | None]:
    """
    從套件規格字串中解析出套件名稱和版本。

    支援的格式:
    - aiohttp==3.12.15 -> ('aiohttp', '3.12.15')
    - psutil -> ('psutil', None)
    - uvicorn[standard]==0.35.0 -> ('uvicorn', '0.35.0')

    Args:
        package_spec: 套件規格字串。

    Returns:
        一個包含 (套件名稱, 版本或 None) 的元組。
    """
    # 正規表達式，用於匹配套件名稱（可能包含 extras）和可選的版本
    # ^([a-zA-Z0-9_-]+(?:\[[a-zA-Z0-9_, -]+\])?)  -> 捕獲套件名稱和 extras
    # (?:==([a-zA-Z0-9_.-]+))?                  -> 捕獲可選的 '==' 後的版本號
    match = re.match(r'^([a-zA-Z0-9_-]+(?:\[[a-zA-Z0-9_, -]+\])?)(?:==([a-zA-Z0-9_.-]+))?$', package_spec.strip())

    if not match:
        logger.warning(f"無法解析套件規格：'{package_spec}'，將其視為單純的套件名稱。")
        return package_spec.strip(), None

    name = match.group(1).split('[')[0] # 去除 extras，只取基礎名稱
    version = match.group(2) if match.group(2) else None

    return name, version


def get_package_size(package_spec: str, http_client: httpx.Client) -> int:
    """
    從 PyPI API 估算一個套件的大小（以 bytes 為單位）。

    此函式會解析套件規格（例如 'fastapi==0.116.1' 或 'psutil'），
    查詢 PyPI 的 JSON API，並加總指定版本（或最新版本）所有發行檔案的大小。
    為了效率，它接收一個 httpx.Client 實例。

    Args:
        package_spec: 套件規格字串。
        http_client: 用於發送請求的 httpx.Client 實例。

    Returns:
        預估的套件大小 (bytes)。如果找不到或發生錯誤，則返回 0。
    """
    name, version = parse_package_spec(package_spec)

    # 2. 查詢 PyPI API
    api_url = f"https://pypi.org/pypi/{name}/json"
    try:
        response = http_client.get(api_url)
        response.raise_for_status()  # 如果狀態碼不是 2xx，則引發異常
        data = response.json()
    except httpx.RequestError as e:
        logger.warning(f"查詢 PyPI API 時發生網路錯誤 ({name}): {e}")
        return 0
    except httpx.HTTPStatusError as e:
        logger.warning(f"查詢 PyPI API 時收到非預期的狀態碼 ({name}): {e.response.status_code}")
        return 0

    # 3. 確定目標版本
    if version is None:
        # 如果未指定版本，使用 'info' 中的最新版本號
        version = data.get('info', {}).get('version')
        if not version:
            logger.warning(f"無法從 PyPI API 找到套件 '{name}' 的最新版本。")
            return 0

    # 4. 尋找指定版本的發行檔案
    releases = data.get('releases', {})
    if version not in releases:
        logger.warning(f"在 PyPI 上找不到套件 '{name}' 的版本 '{version}'。")
        # 有時版本號可能帶 'v' 前綴，嘗試去掉 'v'
        if version.startswith('v') and version[1:] in releases:
            version = version[1:]
        else:
            return 0

    # 5. 加總所有檔案大小
    total_size = 0
    release_files = releases[version]
    if not release_files:
        logger.warning(f"套件 '{name}' 的版本 '{version}' 沒有發行任何檔案。")
        return 0

    for file_info in release_files:
        total_size += file_info.get('size', 0)

    if total_size == 0:
        logger.warning(f"無法計算套件 '{name}' 版本 '{version}' 的大小，可能是 API 回應中缺少大小資訊。")

    return total_size

if __name__ == '__main__':
    # 簡單的獨立測試，用於驗證此模組的功能
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

    pkgs_to_test = [
        "fastapi==0.116.1",
        "psutil",
        "non_existent_package_12345abc",
        "uvicorn[standard]==0.35.0",
        "requests==2.25.1"
    ]

    logger.info("--- 開始進行套件大小估算測試 ---")
    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        for pkg_spec in pkgs_to_test:
            logger.info(f"正在查詢 '{pkg_spec}'...")
            size_in_bytes = get_package_size(pkg_spec, client)
            if size_in_bytes > 0:
                size_in_mb = size_in_bytes / (1024 * 1024)
                logger.info(f"✅ 套件 '{pkg_spec}' 的預估大小為: {size_in_mb:.2f} MB ({size_in_bytes} bytes)")
            else:
                logger.error(f"❌ 無法獲取套件 '{pkg_spec}' 的大小。")
    logger.info("--- 測試結束 ---")
