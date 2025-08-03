# -*- coding: utf-8 -*-
# 檔案: tests/test_fixtures.py
# 說明: 用於驗證 conftest.py 中定義的 pytest fixtures 是否正常運作。

import pytest

def test_mock_report_files_creation(mock_report_files):
    """
    測試 mock_report_files fixture 是否成功建立了指定的報告檔案。
    """
    # mock_report_files fixture 返回的是 tmp_path
    reports_path = mock_report_files / "reports"

    # 斷言目錄和檔案都存在
    assert reports_path.exists()
    assert (reports_path / "summary_report.md").exists()
    assert (reports_path / "detailed_log_report.md").exists()
    assert (reports_path / "performance_report.md").exists()

    # 也可以斷言檔案內容
    summary_content = (reports_path / "summary_report.md").read_text()
    assert summary_content == "這是總結報告。"
