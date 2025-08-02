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

if __name__ == '__main__':
    unittest.main()
