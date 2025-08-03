# -*- coding: utf-8 -*-
# 檔案: src/phoenix_core/report_generator.py
# 說明: 此模組包含與報告生成、讀取和存檔相關的函式。

from pathlib import Path
from typing import List

def read_selected_reports(reports_dir: Path, selection: List[str]) -> str:
    """
    讀取指定目錄下被選中的報告檔案，並將其內容合併為一個字串。

    Args:
        reports_dir (Path): 包含報告檔案的目錄路徑。
        selection (List[str]): 一個包含被選中報告檔名的列表。

    Returns:
        str: 合併後的報告內容。每個報告內容之間會以分隔線隔開。
    """
    content_parts = []
    for report_name in selection:
        report_file = reports_dir / report_name
        if report_file.exists() and report_file.is_file():
            # 讀取檔案內容並加入列表
            content_parts.append(report_file.read_text(encoding='utf-8'))

    # 使用分隔線合併所有內容
    return "\n\n---\n\n".join(content_parts)


import shutil
from datetime import datetime

def archive_selected_reports(reports_dir: Path, archive_root_dir: Path, selection: List[str]) -> Path:
    """
    將選定的報告檔案複製到一個新的、帶有時間戳的存檔目錄中。

    Args:
        reports_dir (Path): 包含原始報告檔案的目錄。
        archive_root_dir (Path): 存檔的根目錄。
        selection (List[str]): 需要存檔的報告檔名列表。

    Returns:
        Path: 新建立的存檔目錄的路徑。
    """
    # 建立中文的「報告」目錄
    archive_base = archive_root_dir / "報告"
    archive_base.mkdir(exist_ok=True)

    # 建立時間戳子目錄
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    archive_path = archive_base / timestamp
    archive_path.mkdir()

    # 複製選定的檔案
    for report_name in selection:
        source_file = reports_dir / report_name
        if source_file.exists():
            shutil.copy2(source_file, archive_path)

    return archive_path
