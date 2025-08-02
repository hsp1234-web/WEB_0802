# -*- coding: utf-8 -*-
"""
測試 run/colab_runner.py 中的健壯性功能，特別是依賴安裝。
"""
import unittest
from unittest.mock import patch, MagicMock, call
import sys
from pathlib import Path

# 將專案根目錄加入 sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 現在我們可以安全地 import
from run import colab_runner

class TestInstallCoreDependencies(unittest.TestCase):

    @patch('run.colab_runner.update_status')
    @patch('run.colab_runner.subprocess.Popen')
    @patch('run.colab_runner.shutil.disk_usage')
    def test_disk_space_sufficient(self, mock_disk_usage, mock_popen, mock_update_status):
        """
        測試案例：當磁碟空間充足時，安裝流程應正常繼續。
        """
        print("\n[測試] 安裝依賴 - 磁碟空間充足...")

        # --- 設定模擬 ---
        mock_project_path = MagicMock(spec=Path)
        (mock_project_path / "requirements-core.txt").exists.return_value = True
        mock_disk_usage.return_value = (0, 0, 100 * (1024**3)) # 100 GB free

        mock_process = MagicMock()
        # Simulate a process that outputs a few lines and then terminates
        mock_process.stdout.readline.side_effect = ['line 1\n', 'line 2\n', '']
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        # --- 執行 ---
        colab_runner.install_core_dependencies(mock_project_path)

        # --- 斷言 ---
        mock_disk_usage.assert_called_once_with('/')
        mock_popen.assert_called_once()
        print("[成功]")


    @patch('run.colab_runner.update_status')
    @patch('run.colab_runner.subprocess.Popen')
    @patch('run.colab_runner.shutil.disk_usage')
    def test_disk_space_insufficient(self, mock_disk_usage, mock_popen, mock_update_status):
        """
        測試案例：當磁碟空間不足時，應拋出 RuntimeError 並中止流程。
        """
        print("\n[測試] 安裝依賴 - 磁碟空間不足...")

        # --- 設定模擬 ---
        mock_project_path = MagicMock(spec=Path)
        (mock_project_path / "requirements-core.txt").exists.return_value = True
        mock_disk_usage.return_value = (0, 0, int(0.1 * (1024**3))) # 0.1 GB free

        # --- 執行並斷言 ---
        with self.assertRaises(RuntimeError) as context:
            colab_runner.install_core_dependencies(mock_project_path)

        self.assertIn("可用磁碟空間不足", str(context.exception))
        mock_popen.assert_not_called()
        print("[成功]")

    @patch('run.colab_runner.update_status')
    @patch('run.colab_runner.subprocess.Popen')
    def test_requirements_file_not_found(self, mock_popen, mock_update_status):
        """
        測試案例：當 requirements-core.txt 不存在時，應跳過安裝。
        """
        print("\n[測試] 安裝依賴 - 找不到依賴文件...")

        # --- 設定模擬 ---
        mock_project_path = MagicMock(spec=Path)
        (mock_project_path / "requirements-core.txt").exists.return_value = False

        # --- 執行 ---
        colab_runner.install_core_dependencies(mock_project_path)

        # --- 斷言 ---
        mock_popen.assert_not_called() # Popen 不應被呼叫
        # 檢查 update_status 是否被以包含「找不到」的訊息呼叫
        self.assertTrue(any("找不到" in call.kwargs.get('log', '') for call in mock_update_status.call_args_list))
        print("[成功]")


if __name__ == '__main__':
    unittest.main()
