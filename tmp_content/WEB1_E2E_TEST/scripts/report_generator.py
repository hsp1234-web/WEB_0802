# 檔案: scripts/report_generator.py
# 說明: 從 state.db 讀取最終狀態並生成 Markdown 報告。
# 作者: Jules
# 版本: V23.2.DB

import argparse
import datetime
import json
import pytz
import psutil
from pathlib import Path
import sqlite3
import pandas as pd
from tabulate import tabulate

# --- 常數 ---
TAIPEI_TZ = pytz.timezone('Asia/Taipei')

# --- 報告生成邏輯 ---

def generate_summary_report(conn: sqlite3.Connection, output_dir: Path):
    """
    產生高層次的綜合情資報告。
    從資料庫的 status 和 logs 表格讀取數據。
    """
    print("正在產生綜合情資報告...")

    # 讀取狀態數據
    final_stage = pd.read_sql("SELECT value FROM status WHERE key = 'final_stage'", conn).iloc[0, 0]
    apps_status_json = pd.read_sql("SELECT value FROM status WHERE key = 'final_apps_status'", conn).iloc[0, 0]
    apps_status = json.loads(apps_status_json)

    # 格式化應用程式狀態
    apps_status_text = "\n".join([f"- {name}: {status}" for name, status in apps_status.items()])

    # 統計日誌級別
    df_summary = pd.read_sql("SELECT level, COUNT(*) as count FROM logs GROUP BY level", conn)
    summary_table = tabulate(df_summary, headers='keys', tablefmt='pipe')

    # 獲取硬體數據 (報告生成時的)
    cpu_avg = psutil.cpu_percent(interval=1)
    mem_percent = psutil.virtual_memory().percent
    now = datetime.datetime.now(TAIPEI_TZ)
    timestamp_str = now.isoformat()

    report_content = f"""
# 綜合戰情簡報

- **報告生成時間**: `{timestamp_str}`
- **最終任務階段**: `{final_stage}`

## 硬體即時狀態
- **CPU 使用率**: `{cpu_avg:.1f}%`
- **記憶體使用率**: `{mem_percent:.1f}%`

## 微服務最終狀態
{apps_status_text}

## 日誌級別統計
{summary_table}
"""
    report_path = output_dir / "summary_report.md"
    report_path.write_text(report_content, encoding='utf-8')
    print(f"報告已儲存至: {report_path}")

def generate_performance_report(output_dir: Path):
    """
    產生一個簡單的效能報告，記錄報告生成時的系統狀態。
    """
    print("正在產生效能分析報告...")
    cpu_avg = psutil.cpu_percent(interval=2)
    memory_info = psutil.virtual_memory()
    mem_percent = memory_info.percent

    now = datetime.datetime.now(TAIPEI_TZ)
    timestamp_str = now.isoformat()

    report_content = f"""
# 效能分析報告

- **報告生成時間**: `{timestamp_str}`
- **平均 CPU 使用率 (2秒)**: `{cpu_avg:.1f}%`
- **記憶體使用率**: `{mem_percent:.1f}%`
"""
    report_path = output_dir / "performance_report.md"
    report_path.write_text(report_content, encoding='utf-8')
    print(f"報告已儲存至: {report_path}")

def generate_detailed_log_report(conn: sqlite3.Connection, output_dir: Path):
    """
    從資料庫的 logs 表格產生詳細的日誌報告。
    """
    print("正在產生詳細日誌報告...")
    df = pd.read_sql("SELECT timestamp, level, message FROM logs ORDER BY timestamp DESC", conn)

    # 格式化時間戳
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')

    md_table = tabulate(df, headers='keys', tablefmt='pipe', showindex=False)

    report_content = f"""
# 詳細日誌報告

以下是從任務開始到結束的所有日誌記錄：

{md_table}
"""
    report_path = output_dir / "detailed_log_report.md"
    report_path.write_text(report_content, encoding='utf-8')
    print(f"報告已儲存至: {report_path}")

# --- 主函式 ---

def main():
    """
    主執行函數，解析參數並呼叫對應的報告生成函式。
    """
    parser = argparse.ArgumentParser(description="鳳凰之心 V23 報告生成器 (資料庫模式)")
    parser.add_argument("--db-file", type=Path, required=True, help="儲存狀態的 SQLite 資料庫檔案路徑。")
    parser.add_argument("--report-dir", type=Path, default=Path("reports"), help="儲存報告的目錄。")
    # 移除 --config-file，因為所有需要的資訊都在資料庫裡

    args = parser.parse_args()

    if not args.db_file.exists():
        print(f"❌ 錯誤: 資料庫檔案不存在於 '{args.db_file}'")
        return

    # 建立輸出目錄
    args.report_dir.mkdir(exist_ok=True)

    conn = None
    try:
        # 使用唯讀模式連接資料庫
        conn = sqlite3.connect(f"file:{args.db_file}?mode=ro", uri=True)
        print(f"✅ 成功連接到資料庫: {args.db_file}")

        # 生成所有三份報告
        generate_summary_report(conn, args.report_dir)
        generate_performance_report(args.report_dir)
        generate_detailed_log_report(conn, args.report_dir)

    except sqlite3.Error as e:
        print(f"❌ 資料庫錯誤: {e}")
    except Exception as e:
        print(f"❌ 產生報告時發生未預期的錯誤: {e}")
    finally:
        if conn:
            conn.close()

    print("\n🎉 所有報告生成完畢。")

if __name__ == "__main__":
    main()
