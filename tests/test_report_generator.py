# -*- coding: utf-8 -*-
# 檔案: tests/test_report_generator.py
# 說明: 對 src/phoenix_core/report_generator.py 中的函式進行單元測試。

import pytest
from src.phoenix_core.report_generator import read_selected_reports

def test_read_selected_reports(mock_report_files):
    """
    測試 read_selected_reports 函式是否能正確讀取並合併所選的報告。
    """
    # mock_report_files 返回的是 tmp_path，報告實際在 'reports' 子目錄中
    reports_dir = mock_report_files / "reports"
    selection = ['summary_report.md', 'performance_report.md']

    # 呼叫我們要測試的函式
    result = read_selected_reports(reports_dir, selection)

    # 斷言返回的內容是正確的
    # 應該包含 summary 和 performance 的內容
    assert "這是總結報告。" in result
    assert "這是效能報告。" in result

    # 不應該包含 detailed_log 的內容
    assert "這是詳細日誌報告。" not in result

    # 斷言內容之間有分隔線
    assert "\n\n---\n\n" in result

def test_read_selected_reports_empty_selection(mock_report_files):
    """
    測試當選擇為空時，函式是否返回空字串。
    """
    reports_dir = mock_report_files / "reports"
    selection = []

    result = read_selected_reports(reports_dir, selection)

    assert result == ""

def test_read_selected_reports_file_not_found(mock_report_files):
    """
    測試當選擇的檔案不存在時，函式是否能正常處理。
    """
    reports_dir = mock_report_files / "reports"
    selection = ['summary_report.md', 'non_existent_report.md']

    result = read_selected_reports(reports_dir, selection)

    # 應只包含存在的檔案內容
    assert "這是總結報告。" in result
    assert "這是效能報告。" not in result
    assert "這是詳細日誌報告。" not in result
    assert "non_existent_report" not in result


import os
from src.phoenix_core.report_generator import archive_selected_reports

def test_archive_selected_reports(mock_report_files):
    """
    測試 archive_selected_reports 函式是否能正確地將報告存檔。
    """
    # mock_report_files 是 tmp_path，這是我們的操作根目錄
    # 報告的源目錄
    source_reports_dir = mock_report_files / "reports"
    # 我們將存檔也放在 tmp_path 下，以保持測試的獨立性
    archive_root_dir = mock_report_files

    selection = ['detailed_log_report.md', 'summary_report.md']

    # 呼叫存檔函式
    new_archive_path = archive_selected_reports(source_reports_dir, archive_root_dir, selection)

    # --- 斷言 ---
    # 1. 斷言返回的路徑是正確的
    assert new_archive_path.parent.name == "報告"
    assert archive_root_dir / "報告" in new_archive_path.parents

    # 2. 斷言目錄結構
    assert (archive_root_dir / "報告").exists()
    assert new_archive_path.exists()

    # 3. 斷言檔案內容
    archived_files = list(os.listdir(new_archive_path))
    assert len(archived_files) == 2
    assert "detailed_log_report.md" in archived_files
    assert "summary_report.md" in archived_files
    assert "performance_report.md" not in archived_files

    # 4. 可以進一步斷言複製後的檔案內容是否正確
    archived_summary_content = (new_archive_path / "summary_report.md").read_text()
    assert archived_summary_content == "這是總結報告。"
