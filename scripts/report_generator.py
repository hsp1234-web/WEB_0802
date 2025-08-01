# 檔案: scripts/report_generator.py
# 說明: 這是所有報告生成的統一入口。

import argparse
import datetime
import pytz  # 用於處理時區
import psutil
from pathlib import Path
import sqlite3
import pandas as pd
from tabulate import tabulate
import re

# --- 核心 ETL 邏輯 ---

def parse_log_to_db(log_file_path: Path) -> sqlite3.Connection:
    """
    作法：
    1. 建立一個記憶體中的 SQLite 資料庫連線。
    2. 在資料庫中建立一個名為 'logs' 的表格 (欄位: timestamp, level, message)。
    3. 逐行讀取指定的 log 檔案。
    4. 使用正規表示式 (regex) 解析每一行，提取時間、日誌級別和訊息。
    5. 將解析出的數據插入 'logs' 表格。
    6. 返回建立好的資料庫連線。
    """
    print("正在解析日誌並載入至記憶體資料庫...")
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE logs (
            timestamp TEXT,
            level TEXT,
            message TEXT
        )
    ''')

    log_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (\w+) - (.*)')

    if not log_file_path.exists():
        print(f"警告: 日誌檔案 {log_file_path} 不存在。將產生空的日誌報告。")
        return conn

    with open(log_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = log_pattern.match(line)
            if match:
                timestamp, level, message = match.groups()
                cursor.execute("INSERT INTO logs VALUES (?, ?, ?)", (timestamp, level, message))

    conn.commit()
    print("日誌解析完成。")
    return conn

# --- 報告生成邏輯 (已升級) ---

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
    cpu_avg = psutil.cpu_percent(interval=2)
    memory_info = psutil.virtual_memory()
    mem_percent = memory_info.percent
    taipei_tz = pytz.timezone('Asia/Taipei')
    now = datetime.datetime.now(taipei_tz)
    timestamp_str = now.isoformat()
    report_content = f"""
# 效能分析報告

- **報告生成時間**: `{timestamp_str}`
- **平均 CPU 使用率 (2秒)**: `{cpu_avg}%`
- **記憶體使用率**: `{mem_percent}%`
"""
    report_path = output_dir / "效能分析報告.md"
    report_path.write_text(report_content, encoding='utf-8')
    print(f"報告已儲存至: {report_path}")

def generate_detailed_log_report(conn: sqlite3.Connection, output_dir: Path):
    """
    作法：
    1. 使用 pandas 的 read_sql 函式，從傳入的資料庫連線中查詢 'logs' 表格的內容。
    2. 使用 tabulate 套件，將查詢到的 DataFrame 轉換為格式精美的 Markdown 表格。
    3. 組合報告內容，並寫入 "詳細日誌報告.md" 檔案。
    """
    print("正在產生詳細日誌報告...")
    df = pd.read_sql("SELECT timestamp, level, message FROM logs ORDER BY timestamp DESC LIMIT 200", conn)
    md_table = tabulate(df, headers='keys', tablefmt='pipe')

    report_content = f"""
# 詳細日誌報告

以下是最近的 200 筆日誌記錄：

{md_table}
"""
    report_path = output_dir / "詳細日誌報告.md"
    report_path.write_text(report_content, encoding='utf-8')
    print(f"報告已儲存至: {report_path}")

def generate_summary_report(conn: sqlite3.Connection, output_dir: Path):
    """
    作法：
    1. 執行 SQL 查詢，統計各個日誌級別 (INFO, WARNING, ERROR) 的數量。
    2. 呼叫 psutil 獲取即時的硬體效能數據。
    3. 將上述兩部分資訊，組合成一份高層次的綜合情資報告。
    4. 寫入 "綜合情資報告.md" 檔案。
    """
    print("正在產生綜合情資報告...")

    # 統計日誌級別
    df_summary = pd.read_sql("SELECT level, COUNT(*) as count FROM logs GROUP BY level", conn)
    summary_table = tabulate(df_summary, headers='keys', tablefmt='pipe')

    # 獲取硬體數據
    cpu_avg = psutil.cpu_percent(interval=1)
    mem_percent = psutil.virtual_memory().percent
    taipei_tz = pytz.timezone('Asia/Taipei')
    now = datetime.datetime.now(taipei_tz)
    timestamp_str = now.isoformat()

    report_content = f"""
# 綜合情資報告

- **報告生成時間**: `{timestamp_str}`

## 硬體即時狀態
- **CPU 使用率**: `{cpu_avg}%`
- **記憶體使用率**: `{mem_percent}%`

## 日誌級別統計
{summary_table}
"""
    report_path = output_dir / "綜合情資報告.md"
    report_path.write_text(report_content, encoding='utf-8')
    print(f"報告已儲存至: {report_path}")

# --- 主函式 (已升級) ---

def main():
    """
    作法：
    1. 修改 argparse，增加 'log' 和 'summary' 的選項。
    2. 在所有報告生成之前，先呼叫一次 parse_log_to_db，獲取資料庫連線。
    3. 根據 --report 參數，將資料庫連線傳遞給對應的報告生成函式。
    """
    parser = argparse.ArgumentParser(description="鳳凰之心報告生成器")
    parser.add_argument("--report", type=str, required=True, choices=['performance', 'log', 'summary', 'all'], help="要產生的報告類型")
    args = parser.parse_args()

    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)

    # 核心變更：先建立資料庫連線
    log_conn = parse_log_to_db(Path("uvicorn.log"))

    if args.report == "log" or args.report == "all":
        generate_detailed_log_report(log_conn, output_dir)
    if args.report == "summary" or args.report == "all":
        generate_summary_report(log_conn, output_dir)
    if args.report == "performance" or args.report == "all":
        generate_performance_report(output_dir)

    log_conn.close() # 關閉連線
    print("所有報告生成完畢。")

if __name__ == "__main__":
    main()
