# -*- coding: utf-8 -*-
"""
對 `src.phoenix_core.kernel.package_utils` 的單元測試
"""
import pytest
from unittest.mock import MagicMock, patch
import httpx

from src.phoenix_core.kernel.package_utils import get_package_size, parse_package_spec

# --- parse_package_spec 的測試 ---

@pytest.mark.parametrize("spec, expected_name, expected_version", [
    ("fastapi==0.116.1", "fastapi", "0.116.1"),
    ("psutil", "psutil", None),
    ("uvicorn[standard]==0.35.0", "uvicorn", "0.35.0"),
    ("  requests  ", "requests", None),
    ("pydantic-settings==2.10.1", "pydantic-settings", "2.10.1"),
    ("invalid-spec-@", "invalid-spec-@", None), # 測試正則表達式不匹配的情況
])
def test_parse_package_spec(spec, expected_name, expected_version):
    """測試套件規格解析是否能正確處理各種格式。"""
    name, version = parse_package_spec(spec)
    assert name == expected_name
    assert version == expected_version

# --- get_package_size 的測試 ---

def create_mock_response(json_data, status_code=200):
    """建立一個模擬的 httpx.Response 物件。"""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = status_code
    mock_response.json.return_value = json_data

    def raise_for_status():
        if status_code >= 400:
            raise httpx.HTTPStatusError(
                message=f"HTTP Error {status_code}",
                request=MagicMock(),
                response=mock_response
            )
    mock_response.raise_for_status = MagicMock(side_effect=raise_for_status)
    return mock_response

@pytest.fixture
def mock_httpx_client():
    """提供一個模擬的 httpx.Client。"""
    return MagicMock(spec=httpx.Client)

def test_get_package_size_success_specific_version(mock_httpx_client):
    """測試：成功獲取指定版本套件的大小。"""
    spec = "my-package==1.2.3"
    json_payload = {
        "releases": {
            "1.2.3": [
                {"size": 100},
                {"size": 200},
            ]
        }
    }
    mock_httpx_client.get.return_value = create_mock_response(json_payload)

    size = get_package_size(spec, mock_httpx_client)

    assert size == 300
    mock_httpx_client.get.assert_called_once_with("https://pypi.org/pypi/my-package/json")

def test_get_package_size_success_latest_version(mock_httpx_client):
    """測試：成功獲取最新版本套件的大小。"""
    spec = "my-package"
    json_payload = {
        "info": {"version": "2.0.0"},
        "releases": {
            "1.0.0": [{"size": 50}],
            "2.0.0": [{"size": 500}, {"size": 500}],
        }
    }
    mock_httpx_client.get.return_value = create_mock_response(json_payload)

    size = get_package_size(spec, mock_httpx_client)

    assert size == 1000
    mock_httpx_client.get.assert_called_once_with("https://pypi.org/pypi/my-package/json")

def test_get_package_size_package_not_found(mock_httpx_client):
    """測試：當套件在 PyPI 上找不到時 (404)。"""
    spec = "non-existent-package==1.0"
    mock_httpx_client.get.return_value = create_mock_response({}, status_code=404)

    size = get_package_size(spec, mock_httpx_client)

    assert size == 0

def test_get_package_size_version_not_found(mock_httpx_client):
    """測試：當套件存在但指定版本不存在時。"""
    spec = "my-package==0.0.1"
    json_payload = {
        "releases": {"1.0.0": [{"size": 100}]}
    }
    mock_httpx_client.get.return_value = create_mock_response(json_payload)

    size = get_package_size(spec, mock_httpx_client)

    assert size == 0

def test_get_package_size_network_error(mock_httpx_client):
    """測試：當發生網路請求錯誤時。"""
    spec = "my-package==1.0"
    mock_httpx_client.get.side_effect = httpx.RequestError("Network error", request=MagicMock())

    size = get_package_size(spec, mock_httpx_client)

    assert size == 0

def test_get_package_size_no_files_for_release(mock_httpx_client):
    """測試：當版本存在但沒有任何發行檔案時。"""
    spec = "my-package==1.0.0"
    json_payload = {
        "releases": {
            "1.0.0": [] # 空的檔案列表
        }
    }
    mock_httpx_client.get.return_value = create_mock_response(json_payload)

    size = get_package_size(spec, mock_httpx_client)

    assert size == 0
