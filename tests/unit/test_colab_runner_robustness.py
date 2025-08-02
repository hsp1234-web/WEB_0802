# -*- coding: utf-8 -*-
"""
對 run/colab_runner.py 中新的安全安裝邏輯進行單元測試。
"""
import unittest
from unittest.mock import patch, MagicMock, mock_open, call
from pathlib import Path
import sys

# 確保可以從測試目錄中找到 run 模組
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from run import colab_runner

class TestSafeInstallCoreDependencies(unittest.TestCase):
    """
    專門測試重構後的 install_core_dependencies 函式。
    """

    @patch('run.colab_runner.update_status')
    @patch('run.colab_runner.subprocess.run')
    @patch('run.colab_runner.shutil.disk_usage')
    @patch('run.colab_runner.get_package_size') # 正確的 patch 目標
    @patch('builtins.open', new_callable=mock_open, read_data="pkg-A==1.0\n#這是一個註解\npkg-B==1.0")
    def test_install_success_happy_path(
        self, mock_open, mock_get_package_size, mock_disk_usage, mock_subprocess_run, mock_update_status
    ):
        """
        測試成功路徑：當磁碟空間充足時，所有套件都應被安裝。
        """
        print("\n[測試] 安全安裝 - 空間充足，成功路徑...")
        # --- 設定模擬 ---
        mock_project_path = MagicMock(spec=Path)
        mock_get_package_size.return_value = 10 * 1024**2  # 每個套件 10MB
        mock_disk_usage.return_value = (0, 0, 200 * 1024**2) # 200MB 可用空間
        # 模擬 subprocess.run 成功
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        # --- 執行 ---
        colab_runner.install_core_dependencies(mock_project_path)

        # --- 斷言 ---
        # 應為兩個套件呼叫安裝命令（註解會被忽略）
        self.assertEqual(mock_subprocess_run.call_count, 2)
        # 檢查最後的日誌訊息是否為成功訊息
        final_log_call = mock_update_status.call_args_list[-1]
        self.assertIn("✅ 所有核心依賴均已成功安裝", final_log_call.kwargs.get('log', ''))
        print("[成功]")


    @patch('run.colab_runner.update_status')
    @patch('run.colab_runner.subprocess.run')
    @patch('run.colab_runner.shutil.disk_usage')
    @patch('run.colab_runner.get_package_size') # 正確的 patch 目標
    @patch('builtins.open', new_callable=mock_open, read_data="pkg-small==1.0\npkg-large==1.0")
    def test_install_insufficient_space_for_second_package(
        self, mock_open, mock_get_package_size, mock_disk_usage, mock_subprocess_run, mock_update_status
    ):
        """
        壓力測試：模擬磁碟空間只夠安裝第一個，但在安裝第二個時失敗。
        """
        print("\n[壓力測試] 安全安裝 - 空間不足以安裝第二個套件...")

        # --- 設定模擬 ---
        mock_project_path = MagicMock(spec=Path)

        # 模擬 get_package_size 的行為
        def size_selector(package_spec, client):
            if "pkg-small" in package_spec:
                return 10 * 1024**2  # 10 MB
            if "pkg-large" in package_spec:
                return 100 * 1024**2 # 100 MB
            return 0
        mock_get_package_size.side_effect = size_selector

        # 模擬磁碟空間 (80MB)，足夠安裝 pkg-small (需求 10*1.2=12MB)
        # 但不足以安裝 pkg-large (需求 100*1.2=120MB)
        mock_disk_usage.return_value = (0, 0, 80 * 1024**2)

        # --- 執行並斷言 ---
        with self.assertRaises(RuntimeError) as context:
            colab_runner.install_core_dependencies(mock_project_path)

        # 驗證錯誤訊息
        self.assertIn("可用磁碟空間不足以安裝 'pkg-large==1.0'", str(context.exception))
        # 驗證 get_package_size 被呼叫了兩次
        self.assertEqual(mock_get_package_size.call_count, 2)
        # 驗證 subprocess.run 只被呼叫了一次 (僅針對 pkg-small)
        mock_subprocess_run.assert_called_once()
        self.assertIn("pkg-small==1.0", mock_subprocess_run.call_args[0][0])

        print("[成功]")

if __name__ == '__main__':
    unittest.main()
