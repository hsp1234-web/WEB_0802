# 檔案: scripts/report_generator.py (概念草稿)
# 說明: 這是所有報告生成的統一入口。

import argparse
import datetime
import pytz  # 用於處理時區
import psutil
from pathlib import Path

# --- 概念區塊：報告生成邏輯 ---

def generate_performance_report(output_dir: Path):
    """
    作法：
    1. 使用 psutil 獲取核心硬體數據。
    2. 為了獲取有意義的平均 CPU 使用率，請讓 psutil.cpu_percent 阻塞 2 秒。
    3. 獲取虛擬記憶體使用狀況。
    4. 獲取台北時區的當前時間。
    5. 將上述資訊格式化為一個 Markdown 字串。
    6. 將字串寫入指定的檔案路徑。
    """
    print("正在產生效能分析報告...")

    # 獲取數據 (概念)
    cpu_avg = psutil.cpu_percent(interval=2)
    memory_info = psutil.virtual_memory()
    mem_percent = memory_info.percent

    # 獲取時間 (概念)
    taipei_tz = pytz.timezone('Asia/Taipei')
    now = datetime.datetime.now(taipei_tz)
    timestamp_str = now.isoformat()

    # 組合報告內容 (概念)
    report_content = f"""
# 效能分析報告

- **報告生成時間**: `{timestamp_str}`
- **平均 CPU 使用率 (2秒)**: `{cpu_avg}%`
- **記憶體使用率**: `{mem_percent}%`
"""

    # 寫入檔案 (概念)
    report_path = output_dir / "效能分析報告.md"
    report_path.write_text(report_content, encoding='utf-8')
    print(f"報告已儲存至: {report_path}")


# --- 概念區塊：主函式與參數解析 ---

def main():
    """
    作法：
    1. 使用 argparse 設定命令列介面。
    2. 必須有一個 --report 引數，讓使用者可以指定報告類型。
    3. 根據傳入的報告類型，呼叫對應的生成函式。
    4. 建立一個名為 'reports' 的輸出資料夾（如果它不存在）。
    """
    parser = argparse.ArgumentParser(description="鳳凰之心報告生成器")
    parser.add_argument("--report", type=str, required=True, choices=['performance', 'all'], help="要產生的報告類型")
    args = parser.parse_args()

    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)

    if args.report == "performance":
        generate_performance_report(output_dir)
    # 未來可在此處擴展其他報告類型
    # elif args.report == 'detailed_log':
    #     ...

if __name__ == "__main__":
    main()
