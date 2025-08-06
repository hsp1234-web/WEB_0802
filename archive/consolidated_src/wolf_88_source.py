================================================================================
### FILE: __init__.py
================================================================================



================================================================================
### FILE: prometheus/cli/main.py
================================================================================

import typer
from prometheus.entrypoints.ai_analyst_app import ai_analyst_job
from prometheus.entrypoints.query_gateway import run_dashboard_service
from prometheus.core.logging.log_manager import LogManager

app = typer.Typer()
# 由於 LogManager 不再是單例，我們為 CLI 的主進程創建一個常規的 logger
log_manager = LogManager(log_file="prometheus_cli.log")
logger = log_manager.get_logger("Conductor")

@app.command(name="analyze")
def cli_analyze():
    """
    啟動 AI 分析師報告生成器。
    """
    logger.info("正在啟動 AI 分析師...")
    ai_analyst_job()
    logger.info("AI 分析師工作完成。")


import subprocess
import sys
import os

@app.command(name="dashboard")
def cli_dashboard(
    host: str = typer.Option("127.0.0.1", help="綁定主機"),
    port: int = typer.Option(8000, help="綁定埠號"),
):
    """啟動網頁儀表板。"""
    logger.info(f"準備在 http://{host}:{port} 啟動儀表板...")
    run_dashboard_service(None, host, port)

data_app = typer.Typer()
app.add_typer(data_app, name="data")

@data_app.command("create-dummy")
def create_dummy():
    """
    建立一個用於測試的虛構 OHLCV CSV 檔案。
    """
    from pathlib import Path
    import numpy as np
    import pandas as pd

    DATA_DIR = Path("data")
    DATA_DIR.mkdir(exist_ok=True)
    file_path = DATA_DIR / "ohlcv_data.csv"

    date_range = pd.to_datetime(
        pd.date_range(start="2022-01-01", periods=1000, freq="D")
    )

    open_prices = np.random.uniform(90, 110, size=1000)

    data = {
        "Date": date_range,
        "Open": open_prices,
        "High": open_prices + np.random.uniform(0, 5, size=1000),
        "Low": open_prices - np.random.uniform(0, 5, size=1000),
        "Close": open_prices + np.random.uniform(-2, 2, size=1000),
        "Volume": np.random.randint(100000, 500000, size=1000),
    }

    df = pd.DataFrame(data)

    df.to_csv(file_path, index=False)
    logger.info(f"已成功建立虛構數據檔案於: {file_path}")


results_app = typer.Typer()
app.add_typer(results_app, name="results")

@results_app.command("clear")
def clear_results():
    """
    清除所有生成的結果、佇列、日誌和檢查點。
    """
    import os
    import shutil

    logger.info("開始清除所有執行數據...")

    RESULTS_DB_PATH = "output/results.sqlite"
    QUEUE_DIR = "data/queues"
    LOG_DIR = "data/logs"
    CHECKPOINT_DIR = "data/checkpoints"
    REPORTS_DIR = "data/reports"

    def remove_path(path_str, is_dir=False):
        if is_dir:
            if os.path.isdir(path_str):
                shutil.rmtree(path_str)
                logger.info(f"已刪除並清空目錄: {path_str}")
        else:
            if os.path.exists(path_str):
                os.remove(path_str)
                logger.info(f"已刪除檔案: {path_str}")

    try:
        remove_path(RESULTS_DB_PATH, is_dir=False)
        remove_path(QUEUE_DIR, is_dir=True)
        remove_path(LOG_DIR, is_dir=True)
        remove_path(CHECKPOINT_DIR, is_dir=True)
        remove_path(REPORTS_DIR, is_dir=True)

        # 重建空目錄
        os.makedirs(QUEUE_DIR, exist_ok=True)
        os.makedirs(LOG_DIR, exist_ok=True)
        os.makedirs(CHECKPOINT_DIR, exist_ok=True)
        os.makedirs(REPORTS_DIR, exist_ok=True)

        logger.info("清除程序完成。")
    except Exception as e:
        logger.error(f"清除過程中發生錯誤: {e}", exc_info=True)


@results_app.command("show")
def show_results():
    """
    從 SQLite 資料庫查詢並顯示回測結果。
    """
    import sqlite3
    import pandas as pd

    logger.info("正在從 SQLite 資料庫查詢結果...")
    DB_PATH = "output/results.sqlite"
    TABLE_NAME = "backtest_results"
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(f"SELECT * FROM {TABLE_NAME}", conn)
        conn.close()

        if df.empty:
            logger.warning("資料庫中尚無任何結果。")
        else:
            logger.info("查詢完成。")
            # 使用一個 logger 呼叫來顯示整個 DataFrame
            logger.info(f"\n--- 回測結果 ---\n{df.to_string()}\n----------------")

    except Exception as e:
        logger.error(f"查詢結果時發生錯誤: {e}", exc_info=True)


@results_app.command("generate-report")
def generate_report(
    xml_path: str = typer.Option("output/reports/report.xml", help="JUnit XML 報告的路徑"),
    md_path: str = typer.Option("TEST_REPORT.md", help="要生成的 Markdown 報告的路徑"),
):
    """
    從 JUnit XML 檔案產生 Markdown 報告。
    """
    import xml.etree.ElementTree as ET
    from datetime import datetime

    logger.info(f"AI 報告生成器啟動，正在讀取原始數據: {xml_path}")
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        suite = root.find("testsuite")

        # 提取核心數據
        total = int(suite.get("tests", 0))
        failures = int(suite.get("failures", 0))
        errors = int(suite.get("errors", 0))
        skipped = int(suite.get("skipped", 0))
        exec_time = float(suite.get("time", 0))
        passed = total - failures - errors - skipped

        # 開始構建 Markdown 報告
        report_content = []
        report_content.append("# **【普羅米修斯之火】系統測試作戰報告**")
        report_content.append(
            f"> 報告生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )

        # 總結區塊
        report_content.append("## **一、 戰況總覽**")
        if failures == 0 and errors == 0:
            report_content.append(
                "> **結論：<font color='green'>任務成功 (SUCCESS)</font>** - 所有品質閘門均已通過。系統戰備狀態良好。"
            )
        else:
            report_content.append(
                "> **結論：<font color='red'>任務失敗 (FAILURE)</font>** - 發現關鍵性錯誤。系統存在風險，需立即審查。"
            )

        summary_table = [
            "| 指標 (Metric) | 數量 (Count) |",
            "|:---|:---:|",
            f"| ✅ **測試通過 (Passed)** | {passed} |",
            f"| ❌ **測試失敗 (Failed)** | {failures} |",
            f"| 🔥 **執行錯誤 (Errors)** | {errors} |",
            f"| 🚧 **測試跳過 (Skipped)** | {skipped} |",
            f"| ⏱️ **總執行時間 (Time)** | {exec_time:.2f} 秒 |",
            f"| 🧮 **總執行數量 (Total)** | {total} |",
        ]
        report_content.append("\n".join(summary_table))

        # 失敗與錯誤詳情
        if failures > 0 or errors > 0:
            report_content.append("\n## **二、 失敗與錯誤詳情**")
            count = 1
            for testcase in suite.findall("testcase"):
                failure = testcase.find("failure")
                error = testcase.find("error")

                detail = failure if failure is not None else error

                if detail is not None:
                    test_name = testcase.get("name", "未知測試")
                    class_name = testcase.get("classname", "未知類別")
                    error_type = detail.tag.capitalize()  # "failure" -> "Failure"
                    message = detail.get("message", "無訊息").splitlines()[0]

                    report_content.append(f"\n### {count}. {error_type}: {message}")
                    report_content.append(
                        f"- **測試位置:** `{class_name}.{test_name}`"
                    )
                    report_content.append("- **詳細堆疊追蹤:**")
                    # 檢查 detail.text 是否為 None
                    stack_trace = (
                        detail.text.strip() if detail.text else "無堆疊追蹤資訊。"
                    )
                    report_content.append(f"```\n{stack_trace}\n```")
                    count += 1

        # 寫入檔案
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_content))

        logger.info(f"作戰報告已成功生成至: {md_path}")

    except FileNotFoundError:
        logger.error(f"找不到原始數據檔案: {xml_path}")
    except ET.ParseError:
        logger.error(f"原始數據檔案格式錯誤: {xml_path}")
    except Exception as e:
        logger.error(f"生成報告時發生未知錯誤: {e}")


@results_app.command("add-tasks")
def add_tasks(
    num_tasks: int = typer.Option(10, help="要添加的任務數量"),
):
    """
    向任務佇列中添加指定數量的隨機回測任務。
    """
    import random
    import uuid
    from prometheus.core.context import AppContext

    with AppContext() as ctx:
        logger.info(f"正在生成 {num_tasks} 個回測任務...")
        batch_id = str(uuid.uuid4())
        for i in range(num_tasks):
            # 任務現在是一個字典
            task = {
                "task_id": str(uuid.uuid4()),
                "type": "backtest",
                "strategy": "SMA_Crossover",
                "symbol": random.choice(["BTC/USDT", "ETH/USDT", "XRP/USDT"]),
                "params": {"fast": random.randint(5, 15), "slow": random.randint(20, 40)},
                "batch_id": batch_id,
            }
            ctx.queue.put(task)
            logger.debug(f"已將任務 {i+1}/{num_tasks} ({task['strategy']}) 添加到佇列。")
        logger.info(f"成功將 {num_tasks} 個任務添加到佇列。")


pipelines_app = typer.Typer()
app.add_typer(pipelines_app, name="pipelines")

@pipelines_app.command("run-downloader")
def run_downloader(
    start_date: str = typer.Option(..., help="下載開始日期 (YYYY-MM-DD)"),
    end_date: str = typer.Option(..., help="下載結束日期 (YYYY-MM-DD)"),
    output_dir: str = typer.Option("data/downloads", help="檔案儲存目錄"),
    max_workers: int = typer.Option(16, help="最大同時下載任務數"),
):
    """
    TAIFEX 自動化數據採集器 v1.0
    """
    import os
    import random
    import time
    from collections import Counter
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from datetime import datetime, timedelta
    import requests
    from prometheus.core.config import config

    logger.info("--- 啟動數據採集任務 ---")
    logger.info(f"時間範圍: {start_date} 到 {end_date}")
    logger.info(f"輸出目錄: {output_dir}")

    tasks = []
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    date_range = [
        start_dt + timedelta(days=x) for x in range((end_dt - start_dt).days + 1)
    ]

    base_url = config.get("data_acquisition.taifex.base_url")
    for current_date in date_range:
        date_str = current_date.strftime("%Y_%m_%d")
        # 範例：僅下載期貨逐筆資料
        tasks.append(
            {
                "url": f"{base_url}/file/taifex/Dailydownload/DailydownloadCSV/Daily_{date_str}.zip",
                "file_name": f"Daily_{date_str}.zip",
                "min_delay": 0.2,
                "max_delay": 1.0,
            }
        )

    results_counter = Counter()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        with requests.Session() as session:
            future_to_task = {
                executor.submit(execute_download, session, task, output_dir): task
                for task in tasks
            }
            for future in as_completed(future_to_task):
                try:
                    status, message = future.result()
                    results_counter[status] += 1
                    logger.info(f"[{status.upper()}] {message}")
                except Exception as exc:
                    logger.info(f"[CRITICAL] 任務執行異常: {exc}")

    logger.info("\n--- 採集任務總結 ---")
    for status, count in results_counter.items():
        logger.info(f"  {status}: {count} 個")


def execute_download(session, task_info, output_dir):
    """執行單一檔案下載任務，包含重試與錯誤處理。"""
    import os
    import random
    import time
    import requests
    from prometheus.core.config import config

    file_path = os.path.join(output_dir, task_info["file_name"])
    if os.path.exists(file_path):
        return "exists", f"檔案已存在: {task_info['file_name']}"

    time.sleep(random.uniform(task_info["min_delay"], task_info["max_delay"]))

    user_agents = config.get("data_acquisition.taifex.user_agents")
    base_url = config.get("data_acquisition.taifex.base_url")

    for attempt in range(3):  # 重試3次
        try:
            headers = {
                "User-Agent": random.choice(user_agents),
                "Referer": task_info.get("referer", base_url),
            }
            response = (
                session.post(
                    task_info["url"],
                    data=task_info.get("payload", {}),
                    headers=headers,
                    timeout=120,
                )
                if task_info.get("payload")
                else session.get(task_info["url"], headers=headers, timeout=120)
            )

            if (
                response.status_code == 200
                and len(response.content) > 100
                and "查無資料" not in response.text
            ):
                os.makedirs(output_dir, exist_ok=True)
                with open(file_path, "wb") as f:
                    f.write(response.content)
                return "success", f"成功下載: {task_info['file_name']}"
            elif response.status_code == 404:
                return "not_found", f"404 Not Found: {task_info['file_name']}"
            else:
                return (
                    "error",
                    f"伺服器錯誤 {response.status_code}: {task_info['file_name']}",
                )

        except requests.exceptions.RequestException as e:
            if attempt == 2:
                return "error", f"網路請求失敗: {e}"
            time.sleep(5 * (attempt + 1))

    return "error", f"達到最大重試次數: {task_info['file_name']}"


@pipelines_app.command("run-explorer")
def run_explorer(
    input_dir: str = typer.Option("data/downloads", help="掃描的原始檔案目錄"),
    db_path: str = typer.Option("data/metadata/schema_registry.db", help="格式註冊表資料庫路徑"),
):
    """
    TAIFEX 格式探勘與註冊器 v1.0
    """
    import hashlib
    import os
    from prometheus.core.db.schema_registry import SchemaRegistry
    from prometheus.core.utils.helpers import (
        prospect_file_content,
        read_file_content,
    )

    registry = SchemaRegistry(db_path)
    logger.info(f"開始掃描目錄: {input_dir}")
    new_formats = 0
    updated_formats = 0

    for filename in os.listdir(input_dir):
        file_path = os.path.join(input_dir, filename)
        if not os.path.isfile(file_path):
            continue

        try:
            file_bytes_content = read_file_content(file_path)
            if file_bytes_content is None:
                continue

            result = prospect_file_content(file_bytes_content)

            if result["status"] == "success":
                fingerprint = get_header_fingerprint(result["header"])
                status = registry.add_or_update_schema(fingerprint, result["header"], result["encoding"], filename)
                if status == "new":
                    new_formats += 1
                else:
                    updated_formats += 1

        except Exception as e:
            logger.error(f"處理檔案 {filename} 失敗: {e}", exc_info=True)

    registry.close()
    logger.info("--- 格式探勘總結 ---")
    logger.info(f"發現新格式: {new_formats} 種")
    logger.info(f"更新現有格式計數: {updated_formats} 次")


def get_header_fingerprint(header_line: str) -> str:
    """對標準化後的標頭計算指紋。"""
    import hashlib
    normalized_header = "".join(header_line.lower().split()).replace('"', "")
    return hashlib.sha256(normalized_header.encode("utf-8")).hexdigest()


@pipelines_app.command("run-elt")
def run_elt(
    input_dir: str = typer.Option("data/downloads", help="下載檔案的來源目錄 (供 Loader 使用)"),
    raw_db_path: str = typer.Option("data/raw_warehouse/raw_taifex.duckdb", help="原始數據艙資料庫路徑"),
    schema_db_path: str = typer.Option("data/metadata/schema_registry.db", help="格式註冊表資料庫路徑"),
    analytics_db_path: str = typer.Option("data/analytics_warehouse/analytics_taifex.duckdb", help="分析數據庫路徑"),
):
    """
    TAIFEX ELT 加工管線 v1.0
    """
    import os
    from prometheus.core.db.data_warehouse import AnalyticsDataWarehouse, RawDataWarehouse
    from prometheus.core.db.schema_registry import SchemaRegistry

    # Ensure parent directories for database files exist
    os.makedirs(os.path.dirname(raw_db_path), exist_ok=True)
    os.makedirs(os.path.dirname(schema_db_path), exist_ok=True)
    os.makedirs(os.path.dirname(analytics_db_path), exist_ok=True)

    run_loader(input_dir, raw_db_path, schema_db_path)
    run_transformer(raw_db_path, schema_db_path, analytics_db_path)


def run_loader(input_dir, raw_db_path, schema_db_path):
    import os
    from prometheus.core.db.data_warehouse import RawDataWarehouse
    from prometheus.core.db.schema_registry import SchemaRegistry
    from prometheus.core.utils.helpers import (
        prospect_file_content,
        read_file_content,
    )

    logger.info("--- [階段 2] 執行 Loader ---")
    raw_wh = RawDataWarehouse(raw_db_path)
    schema_registry = SchemaRegistry(schema_db_path)

    known_fingerprints = schema_registry.get_known_fingerprints()
    if not known_fingerprints:
        logger.info("Loader: No known fingerprints loaded from schema registry. Only files matching these will be processed.")

    files_loaded = 0
    if not os.path.exists(input_dir):
        logger.warning(f"Loader input directory {input_dir} does not exist. Skipping loading.")
        raw_wh.close()
        schema_registry.close()
        return

    for filename in os.listdir(input_dir):
        file_path = os.path.join(input_dir, filename)

        if not os.path.isfile(file_path):
            continue

        if raw_wh.is_file_processed(file_path):
            logger.debug(f"Loader: File {filename} already in raw_import_log. Skipping.")
            continue

        try:
            file_bytes_content = read_file_content(file_path)
            if file_bytes_content is None:
                continue

            result = prospect_file_content(file_bytes_content)
            if result["status"] == "success":
                fingerprint = get_header_fingerprint(result["header"])
                if fingerprint in known_fingerprints:
                    raw_wh.log_processed_file(file_path, file_bytes_content, fingerprint)
                    files_loaded += 1
                    logger.info(f"Loader: Loaded {filename} (fingerprint: {fingerprint[:8]}...) as it's a known schema.")
                else:
                    logger.info(f"Loader: Skipped {filename} (fingerprint: {fingerprint[:8]}...) as its schema is not in the registry.")
            else:
                logger.warning(f"Loader: Skipped file {filename} due to content prospecting failure: {result.get('error', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Loader 處理 {filename} 失敗: {e}", exc_info=True)

    raw_wh.close()
    schema_registry.close()
    logger.info(f"Loader 完成，新載入 {files_loaded} 個檔案。")


def run_transformer(raw_db_path, schema_db_path, analytics_db_path):
    import io
    import pandas as pd
    from prometheus.core.db.data_warehouse import AnalyticsDataWarehouse, RawDataWarehouse
    from prometheus.core.db.schema_registry import SchemaRegistry

    logger.info("--- [階段 3] 執行 Transformer ---")
    schema_registry = SchemaRegistry(schema_db_path)
    raw_wh = RawDataWarehouse(raw_db_path)
    analytics_wh = AnalyticsDataWarehouse(analytics_db_path)

    schema_map = schema_registry.get_all_schemas()
    if not schema_map:
        logger.warning("Transformer: 格式註冊表為空或讀取失敗，Transformer 無法執行有效轉換。")
        schema_registry.close()
        raw_wh.close()
        analytics_wh.close()
        return

    daily_futures_header_str = "交易日期,契約代碼,到期月份(週別),開盤價,最高價,最低價,收盤價,成交量"
    target_daily_futures_fingerprint = get_header_fingerprint(daily_futures_header_str)

    if target_daily_futures_fingerprint not in schema_map:
        logger.warning(f"Transformer: Did not find fingerprint for daily_futures_header '{daily_futures_header_str}' in schema_map. Cannot process daily_futures.")
    else:
        logger.info(f"Transformer: Target fingerprint for daily_futures is {target_daily_futures_fingerprint[:8]}...")

    analytics_wh.create_daily_futures_table()

    records = raw_wh.execute_query("SELECT content_blob, format_fingerprint FROM raw_import_log").fetchall()
    transformed_count = 0
    for blob, fingerprint in records:
        if fingerprint != target_daily_futures_fingerprint:
            continue

        if fingerprint not in schema_map:
            continue

        header_str_from_registry, encoding = schema_map[fingerprint]
        try:
            df = pd.read_csv(io.BytesIO(blob), encoding=encoding, thousands=",", header=0, on_bad_lines="skip")
            df.columns = [str(col).strip().replace('"', "") for col in df.columns]

            target_columns_canonical = [
                "交易日期", "契約代碼", "到期月份(週別)", "開盤價",
                "最高價", "最低價", "收盤價", "成交量",
            ]

            df_to_load = pd.DataFrame()
            for canonical_col_name in target_columns_canonical:
                if canonical_col_name in df.columns:
                    df_to_load[canonical_col_name] = df[canonical_col_name]
                else:
                    df_to_load[canonical_col_name] = None

            if not df_to_load.empty:
                analytics_wh.insert_daily_futures(df_to_load)
                transformed_count += 1

        except pd.errors.EmptyDataError:
            logger.warning(f"Transformer: No data or columns found in CSV for fingerprint {fingerprint[:8]}...")
        except Exception as e:
            logger.error(f"Transformer 處理指紋 {fingerprint[:8]}... 的資料時失敗: {e}", exc_info=True)

    raw_wh.close()
    analytics_wh.close()
    schema_registry.close()
    logger.info(f"Transformer 完成，成功轉換 {transformed_count} 筆記錄。")


@pipelines_app.command("run-stock-factors")
def run_stock_factors():
    """
    執行第四號生產線：股票因子生成。
    """
    from prometheus.pipelines.p4_stock_factor_generation import main as p4_main
    logger.info("--- 啟動 P4：股票因子生成管線 ---")
    p4_main()
    logger.info("--- P4：股票因子生成管線執行完畢 ---")


@pipelines_app.command("run-crypto-factors")
def run_crypto_factors():
    """
    執行第五號生產線：加密貨幣因子生成。
    """
    from prometheus.pipelines.p5_crypto_factor_generation import main as p5_main
    logger.info("--- 啟動 P5：加密貨幣因子生成管線 ---")
    p5_main()
    logger.info("--- P5：加密貨幣因子生成管線執行完畢 ---")


@app.command(name="build-feature-store")
def build_feature_store():
    """
    【作戰指令】統一數據倉儲重構：建造特徵倉儲。
    """
    import asyncio
    from prometheus.core.db.db_manager import DBManager
    # from prometheus.pipelines.p1_factor_generation import p1_factor_generation_pipeline
    # from prometheus.pipelines.p2_index_factor_generation import p2_index_factor_pipeline
    # from prometheus.pipelines.p3_bond_factor_generation import p3_bond_factor_pipeline
    from prometheus.pipelines.p4_stock_factor_generation import main as p4_main
    from prometheus.pipelines.p5_crypto_factor_generation import main as p5_main

    logger.info("--- 啟動統一數據倉儲建構流程 ---")
    db_manager = DBManager()

    # --- P1, P2, P3 (已停用) ---
    # 根據目前的檔案結構，這些管線不存在，暫時註解以確保命令可執行
    # logger.info("執行 P1 通用因子生成...")
    # p1_df = asyncio.run(p1_factor_generation_pipeline.run())
    # db_manager.save_data(p1_df, 'factors')
    # logger.info("P1 通用因子數據已合併。")

    # logger.info("執行 P2 指數因子生成...")
    # p2_df = asyncio.run(p2_index_factor_pipeline.run())
    # db_manager.save_data(p2_df, 'factors')
    # logger.info("P2 指數因子數據已合併。")

    # logger.info("執行 P3 債券因子生成...")
    # p3_df = asyncio.run(p3_bond_factor_pipeline.run())
    # db_manager.save_data(p3_df, 'factors')
    # logger.info("P3 債券因子數據已合併。")

    # --- P4, P5 ---
    # 這些管線的 main 函數內部直接調用 DBManager，我們暫時保持這種方式
    # 未來可以進一步重構，但目前足以滿足作戰目標
    logger.info("執行 P4 股票因子生成...")
    p4_main()
    logger.info("P4 股票因子數據已合併。")

    logger.info("執行 P5 加密貨幣因子生成...")
    p5_main()
    logger.info("P5 加密貨幣因子數據已合併。")

    logger.info("--- 統一數據倉儲建構流程完畢 ---")


@pipelines_app.command("run-simulation-training")
def run_simulation_training(
    target_factor: str = typer.Option(..., help="要模擬的目標因子名稱"),
):
    """
    執行第六號生產線：因子代理模擬模型訓練。
    """
    from prometheus.pipelines.p6_simulation_training import run_main as p6_run_main
    logger.info(f"--- 啟動 P6：因子代理模擬模型訓練管線，目標為 {target_factor} ---")
    p6_run_main(target_factor=target_factor)
    logger.info(f"--- P6：因子代理模擬模型訓練管線執行完畢 ---")


@pipelines_app.command("run")
def run_pipeline(
    name: str = typer.Option(..., help="要執行的管線名稱"),
    ticker: str = typer.Option(None, "--ticker", "-t", help="要處理的資產代號")
):
    """
    執行指定的數據管線。
    """
    import asyncio
    pipeline_context = {"ticker": ticker} if ticker else {}
    logger.info(f"--- 啟動 {name} 管線，上下文: {pipeline_context} ---")

    if name == "p1_factor_generation":
        from prometheus.pipelines.p1_factor_generation import p1_factor_generation_pipeline
        asyncio.run(p1_factor_generation_pipeline.run(context=pipeline_context))
    elif name == "p2_index_factor_generation":
        from prometheus.pipelines.p2_index_factor_generation import p2_index_factor_pipeline
        asyncio.run(p2_index_factor_pipeline.run(context=pipeline_context))
    elif name == "p3_bond_factor_generation":
        from prometheus.pipelines.p3_bond_factor_generation import p3_bond_factor_pipeline
        asyncio.run(p3_bond_factor_pipeline.run(context=pipeline_context))
    else:
        logger.error(f"錯誤：找不到名為 '{name}' 的管線。")
        raise typer.Exit(code=1)

    logger.info(f"--- {name} 管線執行完畢 ---")


@pipelines_app.command("run-backfill")
def run_backfill_cli(
    start_date: str = typer.Option(..., help="回填開始日期 (YYYY-MM-DD)"),
    end_date: str = typer.Option(..., help="回填結束日期 (YYYY-MM-DD)"),
):
    """
    執行歷史數據回填管線。
    """
    import pandas as pd
    from prometheus.core.analysis.data_engine import DataEngine
    from prometheus.core.clients.client_factory import ClientFactory

    logger.info(f"--- 開始執行數據回填作業：從 {start_date} 到 {end_date} ---")

    data_engine = DataEngine()
    hourly_timestamps = pd.date_range(start=start_date, end=end_date, freq="H")
    total_tasks = len(hourly_timestamps)

    for i, ts in enumerate(hourly_timestamps):
        logger.debug(f"--- 正在處理 ({i + 1}/{total_tasks}): {ts} ---")
        try:
            data_engine.generate_snapshot(ts)
        except Exception as e:
            logger.error(f"❌ 處理 {ts} 時發生錯誤: {e}", exc_info=True)

    data_engine.close()
    ClientFactory.close_all()
    logger.info("--- 數據回填作業完成 ---")


from prometheus.models.strategy_models import Strategy
from prometheus.services.backtesting_service import BacktestingService
from prometheus.services.evolution_chamber import EvolutionChamber
from prometheus.services.strategy_reporter import StrategyReporter
from prometheus.core.db.db_manager import DBManager

@app.command()
def run_evolution_cycle():
    """
    🚀 [端到端] 執行一次完整的演化週期：演化 -> 回測 -> 報告。
    """
    print("--- 啟動【演化室行動】完整作戰週期 ---")

    # 1. 初始化核心服務
    db_manager = DBManager()
    backtester = BacktestingService(db_manager)

    # 2. 準備演化所需數據
    # 假設因子數據已存在
    all_factors_df = db_manager.fetch_table('factors')
    # 排除非因子欄位
    available_factors = [col for col in all_factors_df.columns if col not in ['date', 'symbol', 'close']]

    if not available_factors:
        print("錯誤：數據庫中找不到可用的因子。請先執行 build-feature-store。")
        return

    target_asset_for_evolution = 'AAPL' # 選擇一個數據庫中存在的資產
    print(f"INFO: 將使用 '{target_asset_for_evolution}' 作為本次演化的目標資產。")
    chamber = EvolutionChamber(backtester, available_factors, target_asset=target_asset_for_evolution)

    # 3. 執行演化
    # 為了快速演示，使用較小的參數
    hof = chamber.run_evolution(n_pop=20, n_gen=5)

    if not hof:
        print("錯誤：演化未能產生有效結果。")
        return

    # 4. 對最優策略進行最終回測以獲得完整報告
    best_individual = hof[0]
    best_factors = [available_factors[i] for i in best_individual]
    final_strategy = Strategy(
        factors=best_factors,
        weights={factor: 1.0 / len(best_factors) for factor in best_factors},
        target_asset='AAPL' # 修正：明確指定一個存在的資產
    )
    final_report = backtester.run(final_strategy)

    # 5. 生成報告
    reporter = StrategyReporter()
    reporter.generate_report(hof, final_report, available_factors)

    print("--- 【演化室行動】作戰週期結束 ---")

if __name__ == "__main__":
    app()


================================================================================
### FILE: prometheus/core/__init__.py
================================================================================



================================================================================
### FILE: prometheus/core/analysis/data_engine.py
================================================================================

# 檔案路徑: core/analysis/data_engine.py
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import duckdb
import pandas as pd

from prometheus.core.clients.client_factory import ClientFactory
from prometheus.core.logging.log_manager import LogManager

logger = LogManager.get_instance().get_logger("DataEngine")


class DataEngine:
    """
    數據引擎核心。
    負責協調所有數據客戶端，計算多維度指標，
    並生成一份「高密度市場狀態快照」。
    """

    def __init__(
        self,
        db_connection=None,
    ):
        """
        透過依賴注入初始化，傳入所有需要的數據客戶端。
        """
        self.yf_client = ClientFactory.get_client("yfinance")
        self.fred_client = ClientFactory.get_client("fred")
        self.taifex_client = ClientFactory.get_client("taifex")

        # --- 新增程式碼 ---
        if db_connection:
            self.db_con = db_connection
            logger.info("使用傳入的 DuckDB 連接。")
        else:
            db_path = Path("prometheus_fire.duckdb")
            self.db_con = duckdb.connect(database=str(db_path), read_only=False)
            logger.info("DuckDB 連接已建立。")

        self._initialize_db()

    def _initialize_db(self):
        """如果 hourly_time_series 表不存在，則創建它。"""
        try:
            self.db_con.execute("SELECT 1 FROM hourly_time_series LIMIT 1")
            logger.debug("'hourly_time_series' 表已存在。")
        except duckdb.CatalogException:
            logger.info("'hourly_time_series' 表不存在，正在創建...")
            schema = {
                "timestamp": "TIMESTAMP",
                "spy_open": "DOUBLE",
                "spy_high": "DOUBLE",
                "spy_low": "DOUBLE",
                "spy_close": "DOUBLE",
                "spy_volume": "BIGINT",
                "qqq_close": "DOUBLE",
                "tlt_close": "DOUBLE",
                "btc_usd_close": "DOUBLE",
                "nq_f_close": "DOUBLE",
                "es_f_close": "DOUBLE",
                "ym_f_close": "DOUBLE",
                "cl_f_close": "DOUBLE",
                "gc_f_close": "DOUBLE",
                "si_f_close": "DOUBLE",
                "zb_f_close": "DOUBLE",
                "zn_f_close": "DOUBLE",
                "zt_f_close": "DOUBLE",
                "zf_f_close": "DOUBLE",
                "gld_close": "DOUBLE",
                "shy_close": "DOUBLE",
                "iei_close": "DOUBLE",
                "aapl_close": "DOUBLE",
                "msft_close": "DOUBLE",
                "nvda_close": "DOUBLE",
                "goog_close": "DOUBLE",
                "tsm_close": "DOUBLE",
                "601318_ss_close": "DOUBLE",
                "688981_ss_close": "DOUBLE",
                "0981_hk_close": "DOUBLE",
                "spy_rsi_14_1h": "DOUBLE",
                "spy_macd_signal_1h": "DOUBLE",
                "spy_bbands_width_pct_1h": "DOUBLE",
                "spy_vwap_1h": "DOUBLE",
                "spy_atr_14_1h": "DOUBLE",
                "spy_vwap_deviation_pct_1h": "DOUBLE",
                "spy_momentum_1h_100": "DOUBLE",
                "spy_bollinger_band_upper_1h": "DOUBLE",
                "spy_bollinger_band_lower_1h": "DOUBLE",
                "spy_bb_middle_band_20h": "DOUBLE",
                "spy_bb_upper_band_20h": "DOUBLE",
                "spy_bb_lower_band_20h": "DOUBLE",
                "spy_bb_band_width_pct_20h": "DOUBLE",
                "spy_bb_percent_b_20h": "DOUBLE",
                "spy_gex_total": "DOUBLE",
                "spy_gex_flip_level": "DOUBLE",
                "spy_max_pain": "DOUBLE",
                "spy_call_wall_strike": "DOUBLE",
                "spy_put_wall_strike": "DOUBLE",
                "spy_pc_ratio_volume": "DOUBLE",
                "spy_pc_ratio_oi": "DOUBLE",
                "spy_iv_atm_1m": "DOUBLE",
                "spy_skew_quantified": "DOUBLE",
                "spy_vanna_exposure": "DOUBLE",
                "spy_charm_exposure": "DOUBLE",
                "vvix_close": "DOUBLE",
            }
            columns_def = ", ".join(
                [f'"{col}" {dtype}' for col, dtype in schema.items()]
            )
            create_table_sql = f"CREATE TABLE hourly_time_series ({columns_def})"
            self.db_con.execute(create_table_sql)
            logger.info("'hourly_time_series' 表已成功創建。")

    def close(self):
        self.db_con.close()
        logger.info("DuckDB 連接已關閉。")

    def _query_cache(self, dt):
        """
        從 DuckDB 快取中查詢單一時間點的數據。
        :param dt: (datetime) 要查詢的時間戳。
        :return: (pandas.DataFrame) 如果找到數據則返回單行 DataFrame，否則返回 None。
        """
        query = "SELECT * FROM hourly_time_series WHERE timestamp = ?"
        result_df = self.db_con.execute(query, [dt]).fetch_df()

        if not result_df.empty:
            logger.debug(f"CACHE HIT: 於 {dt} 找到數據。")
            return result_df
        else:
            logger.debug(f"CACHE MISS: 於 {dt} 未找到數據。")
            return None

    def _write_cache(self, data_df):
        """
        將新的數據 DataFrame 寫入 DuckDB 快取。
        :param data_df: (pandas.DataFrame) 包含單行待寫入數據的 DataFrame。
        """
        self.db_con.append("hourly_time_series", data_df)
        logger.debug(f"CACHE WRITE: 已將 {data_df['timestamp'].iloc[0]} 的數據寫入快取。")

    def _calculate_technicals(self, ohlcv: pd.DataFrame) -> Dict[str, Any]:
        """
        私有方法：計算基礎技術指標。
        【Jules的任務】: 在此實現 RSI, MACD, BBands 等計算邏輯。
        """
        technicals = {}
        # 範例：計算20日均線
        if "close" in ohlcv.columns and len(ohlcv) >= 20:
            technicals["MA20"] = round(
                ohlcv["close"].rolling(window=20).mean().iloc[-1], 2
            )
        else:
            technicals["MA20"] = None

        # TODO: 實現 RSI, MACD, BBands 等指標計算
        technicals["RSI_14D"] = 70  # 暫用假數據
        technicals["RSI_status"] = "超買"  # 暫用假數據

        return technicals

    def _calculate_approx_credit_spread(self) -> float:
        """
        計算近似信用利差 (HYG價格 / IEF價格)。
        """
        import asyncio
        try:
            hyg_data = asyncio.run(self.yf_client.fetch_data("HYG", period="1d"))
            ief_data = asyncio.run(self.yf_client.fetch_data("IEF", period="1d"))

            if (
                hyg_data.empty
                or "close" not in hyg_data.columns
                or hyg_data["close"].iloc[-1] is None
            ):
                logger.warning("無法獲取 HYG 的最新收盤價。")
                return float("nan")
            if (
                ief_data.empty
                or "close" not in ief_data.columns
                or ief_data["close"].iloc[-1] is None
            ):
                logger.warning("無法獲取 IEF 的最新收盤價。")
                return float("nan")

            hyg_price = hyg_data["close"].iloc[-1]
            ief_price = ief_data["close"].iloc[-1]

            if ief_price == 0:
                logger.warning("IEF 價格為零，無法計算信用利差。")
                return float("nan")

            return round(hyg_price / ief_price, 4)
        except Exception as e:
            logger.error(f"計算近似信用利差時發生錯誤: {e}", exc_info=True)
            return float("nan")

    def _calculate_proxy_move(self) -> float:
        """
        計算代理債市波動率 (TLT 60天日線數據的20天滾動標準差)。
        """
        import asyncio
        try:
            tlt_data = asyncio.run(self.yf_client.fetch_data("TLT", period="60d"))
            if (
                tlt_data.empty or "close" not in tlt_data.columns or len(tlt_data) < 21
            ):  # Need at least 20 periods + 1 for pct_change
                logger.warning("TLT 數據不足以計算代理波動率。")
                return float("nan")

            daily_returns = tlt_data["close"].pct_change()
            proxy_move = daily_returns.rolling(window=20).std().iloc[-1]
            return round(proxy_move, 4)
        except Exception as e:
            logger.error(f"計算代理債市波動率時發生錯誤: {e}", exc_info=True)
            return float("nan")

    def _calculate_gold_copper_ratio(self) -> float:
        """
        計算金銅比 (GLD價格 / HG=F價格)。
        """
        import asyncio
        try:
            gld_data = asyncio.run(self.yf_client.fetch_data("GLD", period="1d"))
            copper_data = asyncio.run(self.yf_client.fetch_data("HG=F", period="1d"))

            if (
                gld_data.empty
                or "close" not in gld_data.columns
                or gld_data["close"].iloc[-1] is None
            ):
                logger.warning("無法獲取 GLD 的最新收盤價。")
                return float("nan")
            if (
                copper_data.empty
                or "close" not in copper_data.columns
                or copper_data["close"].iloc[-1] is None
            ):
                logger.warning("無法獲取 HG=F 的最新收盤價。")
                return float("nan")

            gld_price = gld_data["close"].iloc[-1]
            copper_price = copper_data["close"].iloc[-1]

            if copper_price == 0:
                logger.warning("銅價為零，無法計算金銅比。")
                return float("nan")

            return round(gld_price / copper_price, 4)
        except Exception as e:
            logger.error(f"計算金銅比時發生錯誤: {e}", exc_info=True)
            return float("nan")

    def generate_snapshot(self, dt: datetime):
        # 1. 首先，嘗試從快取讀取數據
        cached_data = self._query_cache(dt)

        # 2. 判斷快取是否命中
        if cached_data is not None:
            # --- 快取命中 ---
            # 直接返回從資料庫讀取的數據
            return cached_data
        else:
            # --- 快取未命中 ---
            # a. 執行現有的 API 呼叫邏輯，獲取所有原始市場數據
            #    (例如: yfinance_client.get_data(), fred_client.fetch_data() ...)

            # b. 執行現有的所有計算邏輯 (技術指標、選擇權數據等)
            #    ...

            # c. 將所有獲取和計算出的數據組裝成一個符合表格結構的單行 DataFrame
            # new_data_df = self._build_snapshot_df(...) # 假設有此方法

            # 為了演示，這裡我們回傳一個假資料
            data = {
                "timestamp": [dt],
                "spy_open": [None],
                "spy_high": [None],
                "spy_low": [None],
                "spy_close": [500.0],
                "spy_volume": [None],
                "qqq_close": [None],
                "tlt_close": [None],
                "btc_usd_close": [None],
                "nq_f_close": [None],
                "es_f_close": [None],
                "ym_f_close": [None],
                "cl_f_close": [None],
                "gc_f_close": [None],
                "si_f_close": [None],
                "zb_f_close": [None],
                "zn_f_close": [None],
                "zt_f_close": [None],
                "zf_f_close": [None],
                "gld_close": [None],
                "shy_close": [None],
                "iei_close": [None],
                "aapl_close": [None],
                "msft_close": [None],
                "nvda_close": [None],
                "goog_close": [None],
                "tsm_close": [None],
                "601318_ss_close": [None],
                "688981_ss_close": [None],
                "0981_hk_close": [None],
                "spy_rsi_14_1h": [None],
                "spy_macd_signal_1h": [None],
                "spy_bbands_width_pct_1h": [None],
                "spy_vwap_1h": [None],
                "spy_atr_14_1h": [None],
                "spy_vwap_deviation_pct_1h": [None],
                "spy_momentum_1h_100": [None],
                "spy_bollinger_band_upper_1h": [None],
                "spy_bollinger_band_lower_1h": [None],
                "spy_bb_middle_band_20h": [None],
                "spy_bb_upper_band_20h": [None],
                "spy_bb_lower_band_20h": [None],
                "spy_bb_band_width_pct_20h": [None],
                "spy_bb_percent_b_20h": [None],
                "spy_gex_total": [None],
                "spy_gex_flip_level": [None],
                "spy_max_pain": [None],
                "spy_call_wall_strike": [None],
                "spy_put_wall_strike": [None],
                "spy_pc_ratio_volume": [None],
                "spy_pc_ratio_oi": [None],
                "spy_iv_atm_1m": [None],
                "spy_skew_quantified": [None],
                "spy_vanna_exposure": [None],
                "spy_charm_exposure": [None],
                "vvix_close": [None],
            }
            new_data_df = pd.DataFrame(data)

            # d. 將這筆新數據寫入快取，供未來使用
            self._write_cache(new_data_df)

            # e. 返回這筆剛從 API 獲取的新數據
            return new_data_df

    def get_hourly_series(
        self, ticker: str, column: str, start_date: str, end_date: str
    ) -> "pd.Series":
        """
        從 DuckDB 獲取指定時間範圍內的小時級數據。
        """
        query = f"SELECT timestamp, {ticker}_{column} FROM hourly_time_series WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp"
        result_df = self.db_con.execute(query, [start_date, end_date]).fetch_df()

        if result_df.empty:
            return pd.Series(dtype="float64")

        result_df = result_df.set_index("timestamp")
        return result_df[f"{ticker}_{column}"]


================================================================================
### FILE: prometheus/core/analysis/stress_index.py
================================================================================

import logging
from datetime import datetime, timedelta

import numpy as np
from prometheus.core.logging.log_manager import LogManager
import pandas as pd
import plotly.graph_objects as go

from prometheus.core.clients.fred import FredClient
from prometheus.core.clients.nyfed import NYFedClient

logger = LogManager.get_instance().get_logger("StressIndexCalculator")


class StressIndexCalculator:
    def __init__(self, rolling_window=252):
        logger.info("正在初始化壓力指數計算引擎...")
        self.fred_client = FredClient()
        self.nyfed_client = NYFedClient()
        self.rolling_window = rolling_window
        self.logger = logging.getLogger(self.__class__.__name__)

    def _fetch_all_data(self, force_refresh=False):
        data_frames = {}
        nyfed_df = self.nyfed_client.fetch_data(force_refresh=force_refresh)
        if not nyfed_df.empty and "Date" in nyfed_df.columns and "Total_Positions" in nyfed_df.columns:
            data_frames["NYFed_Positions"] = nyfed_df[["Date", "Total_Positions"]].set_index("Date")
        fred_symbols = {"VIX": "VIXCLS", "Yield_Spread": "T10Y2Y", "Reserves": "WTREGEN", "SOFR": "SOFR"}
        for name, symbol in fred_symbols.items():
            df_item = self.fred_client.fetch_data(symbol, force_refresh=force_refresh)
            if not df_item.empty:
                data_frames[name] = df_item
        return data_frames

    def _align_and_preprocess(self, data_frames):
        if not data_frames:
            return pd.DataFrame()
        combined_df = pd.concat(data_frames.values(), axis=1, join="outer")
        combined_df = combined_df.ffill().dropna()
        return combined_df

    def _normalize_to_zscore(self, df):
        zscore_df = pd.DataFrame(index=df.index)
        for col in df.columns:
            series = pd.to_numeric(df[col], errors="coerce")
            if series.isnull().all():
                continue
            rolling_mean = series.rolling(window=self.rolling_window, min_periods=1).mean()
            rolling_std = series.rolling(window=self.rolling_window, min_periods=1).std()
            rolling_std.loc[rolling_std.abs() < 1e-6] = 1.0
            zscore_values = (series - rolling_mean) / rolling_std
            zscore_df[f"{col}_zscore"] = zscore_values
        return zscore_df.dropna()

    def _invert_and_weight(self, zscore_df):
        if "VIX_zscore" in zscore_df.columns:
            zscore_df["VIX_zscore"] = -zscore_df["VIX_zscore"]
        if "Yield_Spread_zscore" in zscore_df.columns:
            zscore_df["Yield_Spread_zscore"] = -zscore_df["Yield_Spread_zscore"]
        return zscore_df

    def calculate_stress_index(self, force_refresh=False):
        data_frames = self._fetch_all_data(force_refresh=force_refresh)
        aligned_df = self._align_and_preprocess(data_frames)
        if aligned_df.empty:
            return pd.Series(dtype="float64")
        zscore_df = self._normalize_to_zscore(aligned_df)
        weighted_df = self._invert_and_weight(zscore_df)
        stress_index = weighted_df.mean(axis=1)
        return stress_index.dropna()

    def plot_stress_index(self, stress_index, zscore_components):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=stress_index.index, y=stress_index, mode='lines', name='Stress Index', line=dict(color='red', width=2)))
        for col in zscore_components.columns:
            fig.add_trace(go.Scatter(x=zscore_components.index, y=zscore_components[col], mode='lines', name=col, visible='legendonly'))
        fig.update_layout(title="Financial Stress Index and Components", xaxis_title="Date", yaxis_title="Z-Score / Index Value")
        fig.show()

if __name__ == "__main__":
    calculator = StressIndexCalculator()
    stress_index = calculator.calculate_stress_index()
    if not stress_index.empty:
        print("Stress Index calculated successfully:")
        print(stress_index.tail())
        data_frames = calculator._fetch_all_data()
        aligned_df = calculator._align_and_preprocess(data_frames)
        zscore_df = calculator._normalize_to_zscore(aligned_df)
        calculator.plot_stress_index(stress_index, zscore_df)
    else:
        print("Failed to calculate Stress Index.")


================================================================================
### FILE: prometheus/core/analyzers/__init__.py
================================================================================



================================================================================
### FILE: prometheus/core/analyzers/base_analyzer.py
================================================================================

# core/analyzers/base_analyzer.py
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import pandas as pd


class BaseAnalyzer(ABC):
    """
    所有分析器應用的抽象基礎類 (Abstract Base Class)。

    它採用了「模板方法」設計模式，定義了一個標準化的分析工作流程骨架 (`run` 方法)，
    同時允許子類通過實現抽象方法來定義具體的步驟。

    所有繼承此類的分析器都將自動獲得標準化的日誌記錄和執行流程。
    """

    def __init__(self, analyzer_name: str):
        """
        初始化基礎分析器。

        Args:
            analyzer_name: 分析器的名稱，將用於日誌記錄。
        """
        self.analyzer_name = analyzer_name
        self.logger = logging.getLogger(f"analyzer.{self.analyzer_name}")
        self.logger.info(f"分析器 '{self.analyzer_name}' 已初始化。")

    @abstractmethod
    def _load_data(self) -> pd.DataFrame:
        """
        【子類必須實現】載入分析所需的原始數據。

        Returns:
            一個包含原始數據的 Pandas DataFrame。
        """
        pass

    @abstractmethod
    def _perform_analysis(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        【子類必須實現】執行具體的核心分析邏輯。

        Args:
            data: 從 _load_data() 方法載入的數據。

        Returns:
            一個包含分析結果的 Pandas DataFrame。
        """
        pass

    @abstractmethod
    def _save_results(self, results: pd.DataFrame) -> None:
        """
        【子類必須實現】將分析結果進行保存（例如存入數據庫、寫入 CSV 文件等）。

        Args:
            results: 從 _perform_analysis() 方法返回的結果。
        """
        pass

    def run(self) -> None:
        """
        執行完整的分析工作流程。
        這是一個模板方法，它以固定的順序調用各個步驟。
        """
        self.logger.info(f"--- 開始執行分析流程：{self.analyzer_name} ---")
        try:
            # 第一步：載入數據
            self.logger.info("步驟 1/3：正在載入數據...")
            source_data = self._load_data()
            self.logger.info(f"數據載入成功，共 {len(source_data)} 筆記錄。")

            # 第二步：執行分析
            self.logger.info("步驟 2/3：正在執行核心分析...")
            analysis_results = self._perform_analysis(source_data)
            self.logger.info("核心分析執行完畢。")

            # 第三步：保存結果
            self.logger.info("步驟 3/3：正在保存結果...")
            self._save_results(analysis_results)
            self.logger.info("結果保存成功。")

        except Exception as e:
            self.logger.error(
                f"分析流程 '{self.analyzer_name}' 發生嚴重錯誤：{e}", exc_info=True
            )
            # 可以在此處添加失敗通知等邏輯
            raise  # 重新拋出異常，讓上層調用者知道發生了問題
        finally:
            self.logger.info(f"--- 分析流程執行完畢：{self.analyzer_name} ---")


================================================================================
### FILE: prometheus/core/client_factory.py
================================================================================

from prometheus.core.clients.fred import FredClient
from prometheus.core.config import ConfigManager

import logging

logger = logging.getLogger(__name__)

class ClientFactory:
    def __init__(self):
        self.config = ConfigManager()._config
        self._clients = {}

    def get_client(self, client_name):
        logger.info(f"Attempting to get client for: {client_name}")
        if client_name not in self._clients:
            if client_name == "fred":
                logger.info("Getting fred client")
                api_key = self.config.get("api_keys", {}).get("fred")
                self._clients[client_name] = FredClient(api_key=api_key)
            else:
                raise ValueError(f"Unknown client name: {client_name}")
        return self._clients[client_name]


================================================================================
### FILE: prometheus/core/clients/__init__.py
================================================================================

# prometheus/core/clients/__init__.py

from .base import BaseAPIClient
from .finmind import FinMindClient
from .fmp import FMPClient
from .fred import FredClient
from .nyfed import NYFedClient
from .yfinance import YFinanceClient

__all__ = [
    "BaseAPIClient",
    "FMPClient",
    "FinMindClient",  # <-- 更新為 FinMindClient
    "FredClient",  # <-- 已修正為 FredClient
    "NYFedClient",
    "YFinanceClient",
]


================================================================================
### FILE: prometheus/core/clients/base.py
================================================================================

# -*- coding: utf-8 -*-
"""
核心客戶端模組：基礎 API 客戶端 (v2.0 - 快取注入版)

功能：
- 作為所有特定 API 客戶端 (如 FRED, NYFed) 的父類別。
- **關鍵升級**: 內建並整合了來自 core.utils.caching 的中央快取引擎。
- 為所有子類別提供統一的、具備永久快取和手動刷新能力的 requests Session。
"""

from contextlib import contextmanager
from typing import Iterator, Optional

import requests

from prometheus.core.utils.helpers import get_cached_session, temporary_disabled_cache
from prometheus.core.logging.log_manager import LogManager

logger = LogManager.get_instance().get_logger("BaseAPIClient")


class BaseAPIClient:
    """
    所有 API 客戶端的基礎類別，內建了基於 requests-cache 的同步快取機制。
    """

    def __init__(self, api_key: str = None, base_url: str = None):
        """
        初始化基礎客戶端。

        Args:
            api_key (str, optional): API 金鑰 (如果需要)。
            base_url (str, optional): API 的基礎 URL。
        """
        self.api_key = api_key
        self.base_url = base_url
        self._session: requests.Session = get_cached_session()
        logger.info(f"{self.__class__.__name__} 已初始化，並注入了永久快取 Session。")

    @contextmanager
    def _get_request_context(self, force_refresh: bool = False) -> Iterator[None]:
        """
        一個上下文管理器，根據 force_refresh 參數決定是否要暫時禁用快取。
        這是實現「手動刷新」的統一入口點。

        Args:
            force_refresh (bool): 是否強制刷新。
        """
        if force_refresh:
            logger.info(f"{self.__class__.__name__} 偵測到強制刷新指令。")
            with temporary_disabled_cache(self._session):
                yield
        else:
            yield

    def close_session(self):
        """
        關閉 requests session。
        """
        if self._session:
            self._session.close()
            logger.info(f"{self.__class__.__name__} 的 Session 已關閉。")

    def fetch_data(self, symbol: str, **kwargs):
        """
        獲取數據的抽象方法，應由子類別實現。
        這確保了所有子類別都有一個統一的數據獲取入口點。

        Args:
            symbol (str): 要獲取的數據標的 (例如股票代碼、指標代碼)。
            **kwargs: 其他特定於該次請求的參數，例如 `force_refresh`。

        Raises:
            NotImplementedError: 如果子類別沒有實現此方法。
        """
        raise NotImplementedError("子類別必須實現 fetch_data 方法")

    def _perform_request(
        self, endpoint: str, params: Optional[dict] = None, method: str = "GET"
    ) -> requests.Response:
        """
        執行實際的 HTTP 請求。

        Args:
            endpoint (str): API 的端點路徑。
            params (Optional[dict]): 請求參數。
            method (str): HTTP 方法 (例如 "GET", "POST")。

        Returns:
            requests.Response: API 的回應物件。

        Raises:
            requests.exceptions.HTTPError: 如果 API 回應 HTTP 錯誤。
            ValueError: 如果 base_url 未設定。
        """
        if not self.base_url:
            raise ValueError(
                f"{self.__class__.__name__}: base_url is not set, cannot make a request."
            )

        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        logger.debug(f"{self.__class__.__name__} 正在向 {method} {url} 發送請求，參數：{params}")

        if method.upper() == "GET":
            response = self._session.get(url, params=params)
        elif method.upper() == "POST":
            response = self._session.post(
                url, params=params
            )  # Or json=params if API expects JSON body
        else:
            raise ValueError(f"不支援的 HTTP 方法: {method}")

        response.raise_for_status()
        return response


# 範例使用 (主要用於開發時測試)
if __name__ == "__main__":
    print("--- BaseAPIClient 升級後測試 (直接執行 core/clients/base.py) ---")

    class MockClient(BaseAPIClient):
        def __init__(self):
            super().__init__(base_url="https://httpbin.org")

        def fetch_data(self, symbol: str, **kwargs):
            endpoint = f"/delay/{symbol}"
            url = self.base_url + endpoint

            # 從 kwargs 中提取 force_refresh 參數
            force_refresh = kwargs.get("force_refresh", False)

            # 使用 _get_request_context 來控制快取
            with self._get_request_context(force_refresh=force_refresh):
                response = self._session.get(url)

            print(f"請求 URL: {url}, 是否來自快取: {response.from_cache}")
            response.raise_for_status()
            return response.json()

    client = MockClient()
    try:
        print("\n--- 執行第一次 (應會下載) ---")
        client.fetch_data("2")  # 延遲 2 秒

        print("\n--- 執行第二次 (應從快取讀取) ---")
        client.fetch_data("2")

        print("\n--- 執行第三次 (強制刷新) ---")
        client.fetch_data("2", force_refresh=True)

    finally:
        client.close_session()

    print("\n--- BaseAPIClient 升級後測試結束 ---")


================================================================================
### FILE: prometheus/core/clients/client_factory.py
================================================================================

from typing import Dict

from ..config import config
from .base import BaseAPIClient
from .fred import FredClient
from .taifex_db import TaifexDBClient
from .yfinance import YFinanceClient


class ClientFactory:
    _clients: Dict[str, BaseAPIClient] = {}

    @classmethod
    def get_client(cls, client_name: str) -> BaseAPIClient:
        if client_name not in cls._clients:
            if client_name == "fred":
                cls._clients[client_name] = FredClient(api_key=config.get("api_keys.fred"))
            elif client_name == "yfinance":
                cls._clients[client_name] = YFinanceClient()
            elif client_name == "taifex":
                cls._clients[client_name] = TaifexDBClient()
            elif client_name == "finmind":
                from .finmind import FinMindClient
                cls._clients[client_name] = FinMindClient(api_token=config.get("api_keys.finmind"))
            else:
                raise ValueError(f"Unknown client: {client_name}")
        return cls._clients[client_name]

    @classmethod
    def close_all(cls):
        for client in cls._clients.values():
            client.close_session()
        cls._clients = {}


================================================================================
### FILE: prometheus/core/clients/finmind.py
================================================================================

# core/clients/finmind.py
# 此模組包含與 FinMind API 互動的客戶端邏輯。
from __future__ import annotations

import os
from datetime import datetime
from io import StringIO
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

from .base import BaseAPIClient
from prometheus.core.logging.log_manager import LogManager

logger = LogManager.get_instance().get_logger("FinMindClient")

# FinMind API 基礎 URL (所有請求都使用此 URL)
FINMIND_API_BASE_URL = "https://api.finmindtrade.com/api/v4/data"


class FinMindClient(BaseAPIClient):
    """
    用於與 FinMind API 互動的客戶端。
    FinMind API 的特點是所有數據請求都使用同一個基礎 URL，
    具體的數據集和參數在請求的 params 中指定。
    它可能返回 JSON 或 CSV 格式的數據。
    """

    def __init__(self, api_token: Optional[str] = None):
        """
        初始化 FinMindClient。

        Args:
            api_token (Optional[str]): FinMind API Token。如果未提供，
                                       將嘗試從環境變數 FINMIND_API_TOKEN 讀取。
        Raises:
            ValueError: 如果 API Token 未提供且環境變數中也未設定。
        """
        finmind_api_token = api_token or os.getenv("FINMIND_API_TOKEN")
        if not finmind_api_token:
            raise ValueError(
                "FinMind API token 未設定。請設定 FINMIND_API_TOKEN 環境變數或在初始化時傳入 api_token。"
            )

        super().__init__(api_key=finmind_api_token, base_url=FINMIND_API_BASE_URL)
        logger.info("FinMindClient 初始化完成。")

    async def _request(
        self, endpoint: str = "", params: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        import asyncio
        if not params:
            raise ValueError("請求 FinMind API 時，params 參數不得為空。")

        request_params = params.copy()
        request_params["token"] = self.api_key

        if not self.base_url:
            raise ValueError(
                "FinMindClient: base_url is not set, cannot make a request."
            )

        current_url = (
            f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            if endpoint
            else self.base_url
        )

        logger.debug(f"向 FinMind API 發送請求，URL: {current_url}, 資料集：'{request_params.get('dataset')}', 資料ID：'{request_params.get('data_id')}'")

        def _sync_request():
            try:
                if not current_url:
                    raise ValueError("FinMindClient: Calculated URL is empty, cannot make a request.")
                response: requests.Response = self._session.get(current_url, params=request_params)
                response.raise_for_status()

                content_type = response.headers.get("Content-Type", "")
                if "text/csv" in content_type:
                    df = pd.read_csv(StringIO(response.text))
                    return df if not df.empty else pd.DataFrame()
                elif "application/json" in content_type:
                    json_response: Dict[str, Any] = response.json()
                    if json_response.get("status") != 200:
                        error_msg = json_response.get("msg", "未知 API 內部錯誤")
                        status_code = json_response.get("status", "N/A")
                        logger.error(f"FinMind API 邏輯錯誤 (內部 status {status_code}): {error_msg}")
                        return pd.DataFrame()
                    data_list: Optional[List[Dict[str, Any]]] = json_response.get("data")
                    if data_list:
                        return pd.DataFrame(data_list)
                    else:
                        logger.info(f"FinMind API 未返回任何數據。")
                        return pd.DataFrame()
                else:
                    logger.error(f"未知的 FinMind API 回應 Content-Type: {content_type}")
                    return pd.DataFrame()
            except requests.exceptions.HTTPError as http_err:
                logger.error(f"FinMind API HTTP 錯誤：{http_err}", exc_info=True)
                raise
            except requests.exceptions.RequestException as req_err:
                logger.error(f"請求 FinMind API 時發生網路或請求配置錯誤：{req_err}", exc_info=True)
                return pd.DataFrame()
            except Exception as e:
                logger.error(f"處理 FinMind API 回應時發生未知錯誤：{e}", exc_info=True)
                return pd.DataFrame()

        return await asyncio.to_thread(_sync_request)

    async def fetch_data(self, symbol: str, **kwargs) -> pd.DataFrame:
        dataset = kwargs.get("dataset")
        start_date = kwargs.get("start_date")

        if not dataset:
            raise ValueError("'dataset' 參數為必填項。")
        if not start_date:
            raise ValueError("'start_date' 參數為必填項。")

        params: Dict[str, Any] = {
            "dataset": dataset,
            "data_id": symbol,
            "start_date": start_date,
            "end_date": kwargs.get("end_date", datetime.now().strftime("%Y-%m-%d")),
        }

        for key, value in kwargs.items():
            if key not in ["dataset", "start_date", "end_date", "data_id", "symbol"]:
                params[key] = value

        try:
            return await self._request(endpoint="", params=params)
        except requests.exceptions.HTTPError:
            raise

    def get_monthly_revenue(self, stock_id: str, start_year: int, start_month: int) -> pd.DataFrame:
        """
        獲取月營收數據。
        """
        start_date = f"{start_year}-{start_month:02d}-01"
        end_date = datetime.now().strftime("%Y-%m-%d")
        return self.fetch_data(
            symbol=stock_id,
            dataset="TaiwanStockMonthRevenue",
            start_date=start_date,
            end_date=end_date,
        )

    def get_taiwan_stock_institutional_investors_buy_sell(
        self, stock_id: str, start_date: str, end_date: Optional[str] = None
    ) -> pd.DataFrame:
        return self.fetch_data(
            symbol=stock_id,
            dataset="TaiwanStockInstitutionalInvestorsBuySell",
            start_date=start_date,
            end_date=end_date,
        )


if __name__ == "__main__":
    print("--- FinMindClient 重構後測試 (直接執行 core/clients/finmind.py) ---")
    try:
        client = FinMindClient()
        print("FinMindClient 初始化成功。")

        print("\n測試獲取台積電 (2330) 法人買賣超 (2024-01-01 至 2024-01-05)...")
        investor_data = client.get_taiwan_stock_institutional_investors_buy_sell(
            stock_id="2330", start_date="2024-01-01", end_date="2024-01-05"
        )
        if not investor_data.empty:
            print(f"成功獲取股票 2330 的法人買賣超數據 (共 {len(investor_data)} 筆):")
            print(investor_data.head())
        else:
            print(
                "股票 2330 的法人買賣超數據請求成功，但返回為空 DataFrame (請檢查 API Key, 日期範圍或日誌)。"
            )

        print(
            "\n測試使用 fetch_data 獲取聯發科 (2454) 股價 (2024-03-01 至 2024-03-05)..."
        )
        stock_price_data = client.fetch_data(
            symbol="2454",
            dataset="TaiwanStockPrice",
            start_date="2024-03-01",
            end_date="2024-03-05",
        )
        if not stock_price_data.empty:
            print(f"成功獲取股票 2454 的股價數據 (共 {len(stock_price_data)} 筆):")
            print(stock_price_data.head())
        else:
            print("股票 2454 的股價數據請求成功，但返回為空 DataFrame。")

        print("\n測試一個不存在的股票代碼 (XYZABC) 使用 fetch_data...")
        non_existent_data = client.fetch_data(
            symbol="XYZABC",
            dataset="TaiwanStockPrice",
            start_date="2023-01-01",
            end_date="2023-01-05",
        )
        if non_existent_data.empty:
            print(
                "獲取 XYZABC 數據返回空 DataFrame (符合預期，因為股票不存在或請求錯誤)。"
            )
        else:
            print(f"獲取 XYZABC 數據返回了非預期的數據: \n{non_existent_data.head()}")

        try:
            print("\n測試 fetch_data 缺少 'dataset'...")
            client.fetch_data(symbol="2330", start_date="2024-01-01")  # Missing dataset
        except ValueError as ve:
            print(f"成功捕獲錯誤 (符合預期): {ve}")

    except ValueError as ve_init:
        print(f"初始化錯誤: {ve_init}")
    except requests.exceptions.HTTPError as http_e:
        print(f"捕獲到 HTTP 錯誤 (可能是 API Token 無效或網路問題): {http_e}")
    except Exception as e:
        print(f"執行期間發生未預期錯誤: {e}")

    print("--- FinMindAPIClient 重構後測試結束 ---")


================================================================================
### FILE: prometheus/core/clients/fmp.py
================================================================================

# core/clients/fmp.py
# 此模組包含與 Financial Modeling Prep (FMP) API 互動的客戶端邏輯。

import os
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

from .base import BaseAPIClient
from prometheus.core.logging.log_manager import LogManager

logger = LogManager.get_instance().get_logger("FMPClient")

# 假設配置統一由 BaseAPIClient 或環境變數處理，不再從 core.config 導入 settings
# 如果有統一的 settings 物件，可以後續加入

# FMP API 基礎 URL (不含版本號，版本號將在 endpoint 中處理)
FMP_API_BASE_URL_NO_VERSION = "https://financialmodelingprep.com/api"


class FMPClient(BaseAPIClient):
    """
    Financial Modeling Prep (FMP) API 客戶端。
    用於獲取全球市場（尤其是美股）的財經數據，如歷史價格、公司財報等。
    """

    def __init__(self, api_key: Optional[str] = None, default_api_version: str = "v3"):
        """
        初始化 FMPClient。

        Args:
            api_key (Optional[str]): FMP API key。如果未提供，將嘗試從環境變數 FMP_API_KEY 讀取。
            default_api_version (str): 預設使用的 API 版本 (例如 "v3", "v4")。
                                       實際請求時，端點路徑應包含版本號。
        """
        fmp_api_key = api_key or os.getenv("FMP_API_KEY")
        if not fmp_api_key:
            raise ValueError(
                "FMP API key 未設定。請設定 FMP_API_KEY 環境變數或在初始化時傳入 api_key。"
            )

        super().__init__(api_key=fmp_api_key, base_url=FMP_API_BASE_URL_NO_VERSION)
        self.default_api_version = default_api_version
        logger.info(f"FMPClient 初始化完成，預設 API 版本 '{self.default_api_version}'。")

    def _prepare_params(
        self, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        準備請求參數，特別是添加 FMP 所需的 'apikey'。
        """
        request_params = params.copy() if params else {}
        request_params["apikey"] = self.api_key  # FMP 使用 'apikey'
        return request_params

    def fetch_data(self, symbol: str, **kwargs) -> pd.DataFrame:
        """
        從 FMP API 獲取數據。此方法作為一個統一的入口，
        通過 kwargs 中的 data_type 參數來決定獲取何種數據。

        Args:
            symbol (str): 商品代碼 (例如 "AAPL")。
            **kwargs:
                data_type (str): 必須提供。指定要獲取的數據類型。
                                 可選值: "historical_price", "income_statement",
                                          "balance_sheet_statement", "cash_flow_statement"。
                api_version (str, optional): 指定此次請求使用的 API 版本，預設為客戶端初始化時的 default_api_version。
                from_date (str, optional): 開始日期 (YYYY-MM-DD)，用於歷史價格。
                to_date (str, optional): 結束日期 (YYYY-MM-DD)，用於歷史價格。
                period (str, optional): 財報週期 ("quarter" 或 "annual")，用於財報。預設 "quarter"。
                limit (int, optional): 返回的財報期數或歷史數據點數。預設 20 (用於財報)。

        Returns:
            pd.DataFrame: 包含請求數據的 DataFrame。如果失敗或無數據，則返回空的 DataFrame。

        Raises:
            ValueError: 如果 data_type 未提供或不受支持。
            requests.exceptions.HTTPError: 如果 API 請求失敗。
        """
        data_type = kwargs.pop("data_type", None)
        if not data_type:
            raise ValueError(
                "必須在 kwargs 中提供 'data_type' 參數 (例如 'historical_price', 'income_statement')。"
            )

        api_version = kwargs.pop("api_version", self.default_api_version)
        params: Dict[str, Any] = {}
        endpoint_path_template: str = ""

        if data_type == "historical_price":
            endpoint_path_template = f"{api_version}/historical-price-full/{symbol}"
            if "from_date" in kwargs:
                params["from"] = kwargs["from_date"]
            if "to_date" in kwargs:
                params["to"] = kwargs["to_date"]
            # FMP 的 limit for historical prices might be 'serietype' or implied by date range
            if "limit" in kwargs:
                params["limit"] = str(kwargs["limit"])

        elif data_type in [
            "income-statement",
            "balance-sheet-statement",
            "cash-flow-statement",
        ]:
            endpoint_path_template = f"{api_version}/{data_type}/{symbol}"
            params["period"] = kwargs.get("period", "quarter")
            params["limit"] = str(kwargs.get("limit", 20))

        else:
            raise ValueError(
                f"不支援的 data_type: {data_type}。支援的值為 'historical_price', 'income_statement', 'balance_sheet_statement', 'cash_flow_statement'。"
            )

        final_params = self._prepare_params(params)

        logger.debug(f"正在獲取 '{data_type}' 數據，代碼: {symbol}, Endpoint: {endpoint_path_template}, Params: {params}")

        try:
            response = super()._perform_request(
                endpoint=endpoint_path_template, params=final_params, method="GET"
            )
            json_response = response.json()

            if isinstance(json_response, dict) and "Error Message" in json_response:
                error_msg = json_response["Error Message"]
                logger.error(f"FMP API 返回業務邏輯錯誤：'{error_msg}' (Endpoint: {endpoint_path_template})")
                return pd.DataFrame()

            data_list: Optional[List[Dict[str, Any]]] = None
            if isinstance(json_response, list):
                data_list = json_response
            elif isinstance(json_response, dict):
                possible_data_keys = ["historical"]
                found_key = False
                for key in possible_data_keys:
                    if key in json_response and isinstance(json_response[key], list):
                        data_list = json_response[key]
                        found_key = True
                        break
                if not found_key and data_type not in ["historical_price"]:
                    logger.warning(f"FMP API 返回了一個字典，但未在預期鍵下找到數據列表。Endpoint: {endpoint_path_template}")
                    return pd.DataFrame()

            if data_list is None:
                logger.warning(f"FMP API 回應無法解析為預期的列表結構。Endpoint: {endpoint_path_template}")
                return pd.DataFrame()

            if not data_list:
                logger.info(f"FMP API 未返回 '{symbol}' 的 '{data_type}' 數據。")
                return pd.DataFrame()

            df = pd.DataFrame(data_list)

            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                if data_type == "historical_price":
                    df = df.sort_values(by="date").reset_index(drop=True)
                elif data_type in ["income-statement", "balance-sheet-statement", "cash-flow-statement"]:
                    df = df.sort_values(by="date", ascending=False).reset_index(drop=True)

            logger.info(f"成功獲取並處理了 {len(df)} 筆 '{data_type}' 數據，代碼: {symbol}。")
            return df

        except requests.exceptions.HTTPError as http_err:
            logger.error(f"請求失敗 (HTTP 錯誤)：{http_err}。Endpoint: {endpoint_path_template}", exc_info=True)
            return pd.DataFrame()
        except ValueError as json_err:
            logger.error(f"解析 JSON 回應失敗：{json_err}。Endpoint: {endpoint_path_template}", exc_info=True)
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"處理數據時發生未知錯誤：{e}。Endpoint: {endpoint_path_template}", exc_info=True)
            return pd.DataFrame()


# 範例使用 (主要用於開發時測試)
if __name__ == "__main__":
    print("--- FMPClient 重構後測試 (直接執行 core/clients/fmp.py) ---")
    # 執行此測試前，請確保設定了 FMP_API_KEY 環境變數
    try:
        client = FMPClient(default_api_version="v3")
        print("FMPClient 初始化成功。")

        # 測試獲取歷史股價
        print("\n測試獲取 AAPL 歷史日線價格 (2023-12-01 至 2023-12-05)...")
        aapl_prices = client.fetch_data(
            symbol="AAPL",
            data_type="historical_price",
            from_date="2023-12-01",
            to_date="2023-12-05",
        )
        if not aapl_prices.empty:
            print(f"成功獲取 AAPL 歷史價格數據 (共 {len(aapl_prices)} 筆):")
            print(aapl_prices.head())
        else:
            print(
                "獲取 AAPL 歷史價格數據返回空 DataFrame (請檢查 API Key 權限、日期範圍或日誌中的錯誤)。"
            )

        # 測試獲取財報數據 (v3 income-statement)
        print("\n測試獲取 MSFT 季度損益表 (最近1期, v3)...")
        income_statement_msft = client.fetch_data(
            symbol="MSFT",
            data_type="income-statement",
            period="quarter",
            limit=1,
            api_version="v3",  # 明確指定版本
        )
        if not income_statement_msft.empty:
            print(f"成功獲取 MSFT 季度損益表數據 (共 {len(income_statement_msft)} 筆):")
            print(income_statement_msft.head())
        else:
            print("獲取 MSFT 季度損益表數據返回空 DataFrame。")

        # 測試一個不存在的股票
        print("\n測試獲取不存在股票 'XYZNOTASTOCK' 的歷史價格...")
        non_existent_prices = client.fetch_data(
            symbol="XYZNOTASTOCK",
            data_type="historical_price",
            from_date="2023-01-01",
            to_date="2023-01-05",
        )
        if non_existent_prices.empty:
            print(
                "獲取不存在股票價格數據返回空 DataFrame (符合預期，或 API 返回錯誤)。"
            )
        else:
            print(
                f"獲取不存在股票價格數據返回了非預期的數據: {non_existent_prices.head()}"
            )

        # 測試無效 data_type
        try:
            print("\n測試無效的 data_type...")
            client.fetch_data(symbol="AAPL", data_type="invalid_type")
        except ValueError as ve:
            print(f"成功捕獲到錯誤 (符合預期): {ve}")

    except ValueError as ve_init:  # API Key 未設定等初始化問題
        print(f"初始化錯誤: {ve_init}")
    except Exception as e:
        print(f"執行期間發生未預期錯誤: {e}")

    print("--- FMPClient 重構後測試結束 ---")


================================================================================
### FILE: prometheus/core/clients/fred.py
================================================================================

# -*- coding: utf-8 -*-
"""
核心數據客戶端：聯準會經濟數據庫 (FRED) (v2.1 - 快取與金鑰管理升級版)
"""

from typing import Any, Optional

import pandas as pd

from fredapi import Fred as FredAPILib

from prometheus.core.config import get_fred_api_key
from prometheus.core.logging.log_manager import LogManager

from .base import BaseAPIClient

logger = LogManager.get_instance().get_logger("FredClient")


class FredClient(BaseAPIClient):
    """
    用於從 FRED API 獲取經濟數據的客戶端。
    使用官方 fredapi 函式庫進行數據獲取。
    """

    def __init__(
        self, api_key: Optional[str] = None, session: Optional[Any] = None
    ):  # 添加 session 以便測試時傳入
        """
        初始化 FredClient。

        Args:
            api_key (Optional[str]): 要使用的 FRED API 金鑰。
                                     如果提供，則使用此金鑰。
                                     如果為 None，則嘗試從 config.yml 讀取。
            session (Optional[Any]): requests session 物件，主要用於測試時注入 mock session。
                                     fredapi 函式庫本身不直接使用此 session，但 BaseAPIClient 可能會。
        """
        final_api_key: Optional[str] = None
        if api_key:
            final_api_key = api_key
            logger.info("初始化時偵測到直接傳入的 API 金鑰。")
        else:
            try:
                logger.debug("初始化時未直接傳入 API 金鑰，嘗試從設定檔獲取...")
                final_api_key = get_fred_api_key()
            except ValueError as e:
                logger.error(f"無法初始化 FredClient: {e}", exc_info=True)
                raise ValueError(f"FredClient 初始化失敗: {e}") from e

        if not final_api_key:
            error_msg = "FredClient 初始化失敗：API 金鑰既未直接提供，也無法從設定檔中獲取。"
            logger.error(error_msg)
            raise ValueError(error_msg)

        super().__init__(
            api_key=final_api_key, base_url="https://api.stlouisfed.org/fred"
        )

        if session:
            self._session = session
            logger.info("已使用傳入的 session 物件。")

        self._fred_official_client = FredAPILib(api_key=self.api_key)
        self._emergency_cache = {}
        logger.info(f"{self.__class__.__name__} 初始化成功。FredAPILib 將自行管理其網路請求。已啟用應急快取。")

    def fetch_data(self, symbol: str, **kwargs: Any) -> pd.DataFrame:
        """
        從 FRED 獲取單個時間序列數據。
        """
        logger.info(f"正在獲取指標 {symbol}...")
        force_refresh = kwargs.get("force_refresh", False)
        cache_key_params = tuple(
            sorted((k, v) for k, v in kwargs.items() if k != "force_refresh")
        )
        cache_key = (symbol, cache_key_params)

        if not force_refresh and cache_key in self._emergency_cache:
            logger.debug(f"使用應急快取獲取指標 {symbol} 及參數 {cache_key_params}...")
            return self._emergency_cache[cache_key].copy()

        fred_params = {
            k: v
            for k, v in kwargs.items()
            if k in ["observation_start", "observation_end", "realtime_start", "realtime_end", "limit", "offset", "sort_order", "aggregation_method", "frequency", "units"]
        }

        with self._get_request_context(force_refresh=force_refresh):
            if force_refresh and cache_key in self._emergency_cache:
                logger.debug(f"應急快取因 force_refresh 而清除 {symbol} / {cache_key_params}。")
                del self._emergency_cache[cache_key]

            try:
                logger.debug(f"正在透過 FredAPILib 請求 {symbol}...")
                series_data = self._fred_official_client.get_series(series_id=symbol, **fred_params)
            except Exception as e:
                logger.error(f"使用 fredapi 獲取 {symbol} 時發生錯誤: {e}", exc_info=True)
                return pd.DataFrame(columns=["Date", symbol]).set_index("Date")

        if not isinstance(series_data, pd.Series):
            logger.warning(f"從 FRED 獲取的指標 {symbol} 數據類型不是 pd.Series，而是 {type(series_data)}。")
            return pd.DataFrame(columns=["Date", symbol]).set_index("Date")

        if series_data.empty:
            logger.warning(f"從 FRED 獲取的指標 {symbol} 數據為空。")
            return pd.DataFrame(columns=["Date", symbol]).set_index("Date")

        df = series_data.to_frame(name=symbol)
        df.index.name = "Date"

        if df.empty or (symbol in df and df[symbol].isnull().all()):
            logger.warning(f"獲取的指標 {symbol} 數據轉換後無效或全為空值。")
            return pd.DataFrame(columns=["Date", symbol]).set_index("Date")

        self._emergency_cache[cache_key] = df.copy()
        logger.debug(f"成功獲取並已存入應急快取 {len(df)} 筆 {symbol} / {cache_key_params} 數據。")
        return df

    def close_session(self):
        """
        關閉由 BaseAPIClient 管理的 requests session。
        """
        super().close_session()
        logger.info("基礎 session (如果已初始化) 已關閉。")


if __name__ == "__main__":
    print("--- FredClient 金鑰與快取升級後測試 ---")
    print("請確保您的 config.yml 中已填寫有效的 FRED API Key。")

    client: Optional[FredClient] = None
    try:
        client = FredClient()

        test_series_id = "DGS10"  # 10年期公債殖利率
        test_params_initial = {
            "observation_start": "2023-01-01",
            "observation_end": "2023-01-10",
        }

        print(f"\n--- 測試獲取 {test_series_id} (第一次, 應實際請求) ---")
        data_first = client.fetch_data(test_series_id, **test_params_initial)
        if not data_first.empty:
            print(f"{test_series_id} 數據範例 (第一次):")
            print(data_first.tail(3))
        else:
            print(f"無法獲取 {test_series_id} 數據 (第一次)。")

        # 由於 fredapi 不使用我們的 requests-cache，重複請求通常會再次命中 API。
        # BaseAPIClient 的快取上下文在這裡主要是日誌作用和概念上的一致性。
        # 若要測試 fredapi 自身的潛在快取或避免重複 API 呼叫，需更複雜的 mock。
        print(f"\n--- 測試獲取 {test_series_id} (第二次, 參數相同) ---")
        data_second = client.fetch_data(test_series_id, **test_params_initial)
        if not data_second.empty:
            print(f"{test_series_id} 數據範例 (第二次):")
            print(data_second.tail(3))
            if data_first.equals(data_second):
                print("INFO: 第二次獲取數據與第一次一致。")
            else:
                print("WARNING: 第二次獲取數據與第一次不一致。")
        else:
            print(f"無法獲取 {test_series_id} 數據 (第二次)。")

        print(f"\n--- 測試獲取 {test_series_id} (強制刷新, 意圖) ---")
        data_refresh = client.fetch_data(
            test_series_id, force_refresh=True, **test_params_initial
        )
        if not data_refresh.empty:
            print(f"{test_series_id} 數據範例 (強制刷新):")
            print(data_refresh.tail(3))
        else:
            print(f"無法獲取 {test_series_id} 數據 (強制刷新)。")

        # 測試一個可能不存在的指標
        print("\n--- 測試獲取不存在的指標 (FAKEID123) ---")
        fake_data = client.fetch_data("FAKEID123")
        if fake_data.empty:
            print("成功處理不存在的指標 FAKEID123，返回空 DataFrame。")
        else:
            print("錯誤：獲取不存在指標 FAKEID123 時未返回空 DataFrame。")

    except ValueError as ve:  # 例如金鑰未設定
        print(f"\n測試過程中發生設定錯誤: {ve}")
    except Exception as e:
        print(f"\n測試過程中發生未預期錯誤: {e}")
        import traceback

        traceback.print_exc()
    finally:
        if client:
            client.close_session()

    print("\n--- FredClient 測試結束 ---")


================================================================================
### FILE: prometheus/core/clients/nyfed.py
================================================================================

# core/clients/nyfed.py
# 此模組包含從紐約聯儲 (NY Fed) 下載和解析一級交易商持有量數據的客戶端邏輯。

import traceback
from io import BytesIO
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

from .base import BaseAPIClient
from prometheus.core.logging.log_manager import LogManager

logger = LogManager.get_instance().get_logger("NYFedClient")

# NY Fed API URLs 和解析設定 (保持不變)
NYFED_DATA_CONFIGS: List[Dict[str, Any]] = [
    {
        "url": "https://markets.newyorkfed.org/api/pd/get/SBN2024/timeseries/PDPOSGSC-L2_PDPOSGSC-G2L3_PDPOSGSC-G3L6_PDPOSGSC-G6L7_PDPOSGSC-G7L11_PDPOSGSC-G11L21_PDPOSGSC-G21.xlsx",
        "type": "SBN",
        "sheet_name": 0,
        "header_row": 0,
        "date_column_names": ["AS OF DATE"],
        "value_column_name": "VALUE (MILLIONS)",
        "notes": "SBN2024 - PDPOSGSC series",
    },
    {
        "url": "https://markets.newyorkfed.org/api/pd/get/SBN2022/timeseries/PDPOSGSC-L2_PDPOSGSC-G2L3_PDPOSGSC-G3L6_PDPOSGSC-G6L7_PDPOSGSC-G7L11_PDPOSGSC-G11L21_PDPOSGSC-G21.xlsx",
        "type": "SBN",
        "sheet_name": 0,
        "header_row": 0,
        "date_column_names": ["AS OF DATE"],
        "value_column_name": "VALUE (MILLIONS)",
        "notes": "SBN2022 - PDPOSGSC series",
    },
    {
        "url": "https://markets.newyorkfed.org/api/pd/get/SBN2015/timeseries/PDPOSGSC-L2_PDPOSGSC-G2L3_PDPOSGSC-G3L6_PDPOSGSC-G6L7_PDPOSGSC-G7L11_PDPOSGSC-G11.xlsx",
        "type": "SBN",
        "sheet_name": 0,
        "header_row": 0,
        "date_column_names": ["AS OF DATE"],
        "value_column_name": "VALUE (MILLIONS)",
        "notes": "SBN2015 - PDPOSGSC series (G11 結尾)",
    },
    {
        "url": "https://markets.newyorkfed.org/api/pd/get/SBN2013/timeseries/PDPOSGSC-L2_PDPOSGSC-G2L3_PDPOSGSC-G3L6_PDPOSGSC-G6L7_PDPOSGSC-G7L11_PDPOSGSC-G11.xlsx",
        "type": "SBN",
        "sheet_name": 0,
        "header_row": 0,
        "date_column_names": ["AS OF DATE"],
        "value_column_name": "VALUE (MILLIONS)",
        "notes": "SBN2013 - PDPOSGSC series",
    },
    {
        "url": "https://markets.newyorkfed.org/api/pd/get/SBP2013/timeseries/PDPUSGCS3LNOP_PDPUSGCS36NOP_PDPUSGCS611NOP_PDPUSGCSM11NOP.xlsx",
        "type": "SBP",
        "sheet_name": 0,
        "header_row": 0,
        "date_column_names": ["AS OF DATE"],
        "value_column_name": "VALUE (MILLIONS)",
        "cols_to_sum_if_sbp": [
            "PDPUSGCS3LNOP",
            "PDPUSGCS36NOP",
            "PDPUSGCS611NOP",
            "PDPUSGCSM11NOP",
        ],
        "notes": "SBP2013 - 加總指定欄位",
    },
    {
        "url": "https://markets.newyorkfed.org/api/pd/get/SBP2001/timeseries/PDPUSGCS5LNOP_PDPUSGCS5MNOP.xlsx",
        "type": "SBP",
        "sheet_name": 0,
        "header_row": 0,
        "date_column_names": ["AS OF DATE"],
        "value_column_name": "VALUE (MILLIONS)",
        "cols_to_sum_if_sbp": ["PDPUSGCS5LNOP", "PDPUSGCS5MNOP"],
        "notes": "SBP2001 - 加總指定欄位",
    },
]


class NYFedClient(BaseAPIClient):  # 類名從 NYFedAPIClient 改為 NYFedClient
    """
    用於從紐約聯儲 (NY Fed) API 下載和解析一級交易商持有量數據的客戶端。
    此客戶端不使用傳統的 API Key 或 JSON API，而是下載 Excel 檔案。
    """

    def __init__(self, data_configs: Optional[List[Dict[str, Any]]] = None):
        """
        初始化 NYFedClient。

        Args:
            data_configs (Optional[List[Dict[str, Any]]]):
                用於指定下載來源和解析方式的配置列表。
                如果未提供，則使用模組中定義的預設 NYFED_DATA_CONFIGS。
        """
        # NYFed 不使用 API Key 和標準的 base_url 模式，但仍調用父類構造函數
        super().__init__(api_key=None, base_url=None)
        self.data_configs = data_configs or NYFED_DATA_CONFIGS
        logger.info(f"NYFedClient 初始化完成，將使用 {len(self.data_configs)} 個數據源配置。")

    def _download_excel_to_dataframe(
        self, config: Dict[str, Any]
    ) -> Optional[pd.DataFrame]:
        """
        從指定的 API URL 下載 Excel 檔案並讀取特定 sheet 到 DataFrame。
        """
        url = config["url"]
        sheet_name = config.get("sheet_name", 0)
        header_row = config.get("header_row", 0)

        logger.debug(f"正在從 {url} 下載 Excel 數據 (Sheet: {sheet_name}, Header: {header_row})...")
        try:
            response: requests.Response = self._session.get(url, timeout=60)
            response.raise_for_status()

            excel_file = BytesIO(response.content)
            df = pd.read_excel(excel_file, sheet_name=sheet_name, header=header_row, engine="openpyxl")

            df.columns = [str(col).strip().upper().replace("\n", " ").replace("\r", " ").replace("  ", " ") for col in df.columns]

            logger.debug(f"成功從 {url} 下載並讀取了 {len(df)} 行數據。")
            return df
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"下載 Excel 檔案 {url} 時發生 HTTP 錯誤: {http_err}", exc_info=True)
            return None
        except requests.exceptions.RequestException as req_err:
            logger.error(f"下載 Excel 檔案 {url} 時發生網路錯誤: {req_err}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"處理來自 {url} 的 Excel 檔案時發生錯誤: {e}", exc_info=True)
            return None

    def _parse_dealer_positions(
        self, df_raw: pd.DataFrame, config: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        根據設定解析從單個 Excel 檔案讀取的一級交易商持有量數據。
        """
        date_col_name = config["date_column_names"][0]
        if date_col_name not in df_raw.columns:
            logger.error(f"在來源 {config['url']} 的數據中找不到預期日期欄位 '{date_col_name}'。可用欄位: {df_raw.columns.tolist()}")
            return pd.DataFrame(columns=["Date", "Total_Positions"])

        df = df_raw.copy()
        df.rename(columns={date_col_name: "Date"}, inplace=True)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

        value_col_name = config.get("value_column_name", "VALUE (MILLIONS)")
        required_core_cols = [value_col_name]
        if config["type"] == "SBP":
            required_core_cols.append("TIME SERIES")

        missing_core_cols = [col for col in required_core_cols if col not in df.columns]
        if missing_core_cols:
            logger.error(f"類型 {config['type']} 的數據 ({config['url']}) 缺少核心欄位: {missing_core_cols}。可用欄位: {df.columns.tolist()}")
            return pd.DataFrame(columns=["Date", "Total_Positions"])

        df[value_col_name] = pd.to_numeric(df[value_col_name], errors="coerce")

        if config["type"] == "SBP":
            cols_to_sum = config.get("cols_to_sum_if_sbp")
            if not cols_to_sum:
                logger.error(f"SBP 類型數據 ({config['url']}) 未在配置中提供 'cols_to_sum_if_sbp' 列表。")
                return pd.DataFrame(columns=["Date", "Total_Positions"])
            target_series_codes = [code.upper() for code in cols_to_sum]
            df_filtered = df[df["TIME SERIES"].isin(target_series_codes)]
            if df_filtered.empty:
                logger.warning(f"SBP 類型數據 ({config['url']}) 在篩選目標 TIME SERIES {target_series_codes} 後為空。")
                return pd.DataFrame(columns=["Date", "Total_Positions"])
            summed_df = df_filtered.groupby("Date")[value_col_name].sum().reset_index()
            summed_df.rename(columns={value_col_name: "Total_Positions"}, inplace=True)
            df_processed = summed_df
        elif config["type"] == "SBN":
            summed_df = df.groupby("Date")[value_col_name].sum().reset_index()
            summed_df.rename(columns={value_col_name: "Total_Positions"}, inplace=True)
            df_processed = summed_df
        else:
            logger.error(f"未知的數據類型 '{config['type']}' for url {config['url']}")
            return pd.DataFrame(columns=["Date", "Total_Positions"])

        df_processed.dropna(subset=["Date", "Total_Positions"], inplace=True)
        if df_processed.empty:
            logger.warning(f"處理後 DataFrame ({config['url']}) 為空。")
            return pd.DataFrame(columns=["Date", "Total_Positions"])

        df_processed["Total_Positions"] = df_processed["Total_Positions"] * 1_000_000
        if df_processed["Date"].dt.tz is not None:
            df_processed["Date"] = df_processed["Date"].dt.tz_localize(None)
        return df_processed[["Date", "Total_Positions"]].sort_values(by="Date").reset_index(drop=True)

    def fetch_data(self, symbol: str = "", **kwargs) -> pd.DataFrame:
        """
        從 NY Fed API 獲取所有設定的一級交易商持有量數據，並進行合併和處理。
        """
        force_refresh = kwargs.get("force_refresh", False)

        if symbol:
            logger.debug(f"接收到 symbol='{symbol}'，但此參數當前被忽略。")

        all_data_frames: List[pd.DataFrame] = []
        logger.info(f"開始獲取所有一級交易商數據 (強制刷新={force_refresh})...")

        with self._get_request_context(force_refresh=force_refresh):
            for config in self.data_configs:
                logger.debug(f"處理配置: {config.get('notes', config['url'])}")
                df_raw = self._download_excel_to_dataframe(config)
                if df_raw is not None and not df_raw.empty:
                    df_parsed = self._parse_dealer_positions(df_raw, config)
                    if not df_parsed.empty:
                        all_data_frames.append(df_parsed)
                        logger.debug(f"成功解析來自 {config['url']} 的 {len(df_parsed)} 筆有效數據。")
                    else:
                        logger.warning(f"解析來自 {config['url']} 的數據後無有效記錄。")
                else:
                    logger.warning(f"下載或讀取來自 {config['url']} 的數據失敗或原始數據為空。")

        if not all_data_frames:
            logger.error("未能從任何 NY Fed 來源成功獲取和解析一級交易商數據。")
            return pd.DataFrame(columns=["Date", "Total_Positions"])

        combined_df = pd.concat(all_data_frames, ignore_index=True)
        combined_df.sort_values(by="Date", inplace=True)
        combined_df.drop_duplicates(subset=["Date"], keep="first", inplace=True)
        combined_df.reset_index(drop=True, inplace=True)

        logger.info(f"成功合併所有 NY Fed 一級交易商數據，最終共 {len(combined_df)} 筆唯一日期記錄。")
        return combined_df


# 範例使用 (主要用於開發時測試)
if __name__ == "__main__":
    print("--- NYFedClient 快取整合後測試 (直接執行 core/clients/nyfed.py) ---")
    client = NYFedClient()
    try:
        print("\n--- 執行第一次 (應會下載所有檔案) ---")
        data_first_run = client.fetch_data()
        if not data_first_run.empty:
            print(f"第一次執行成功，獲取 {len(data_first_run)} 筆數據。")
            # 檢查是否有快取相關的日誌 (在 _download_excel_to_dataframe 或 BaseAPIClient 中)
            # 注意：由於 NYFedClient 下載多個檔案，此處的 from_cache 可能不明顯
            # 真正的快取效果體現在第二次運行時，請求不應實際發出

        print("\n--- 執行第二次 (應從快取讀取所有檔案) ---")
        data_second_run = client.fetch_data()
        if not data_second_run.empty:
            print(f"第二次執行成功，獲取 {len(data_second_run)} 筆數據。")
            # 這裡需要依賴 BaseAPIClient 中 get_cached_session 的日誌
            # 或 _download_excel_to_dataframe 中 response.from_cache (如果適用)
            # 來確認是否從快取讀取。

        print("\n--- 執行第三次 (強制刷新，應重新下載所有檔案) ---")
        data_third_run = client.fetch_data(force_refresh=True)
        if not data_third_run.empty:
            print(f"第三次執行 (強制刷新) 成功，獲取 {len(data_third_run)} 筆數據。")

        # 基本的健全性檢查
        if not (
            data_first_run.equals(data_second_run)
            and data_first_run.equals(data_third_run)
        ):
            print("\n警告：不同執行之間的數據不一致，請檢查！")
            print(f"第一次 vs 第二次是否相等: {data_first_run.equals(data_second_run)}")
            print(f"第一次 vs 第三次是否相等: {data_first_run.equals(data_third_run)}")
        else:
            print("\n數據一致性檢查通過。")

        if not data_first_run.empty:
            print(
                f"\n最終合併的一級交易商持有量數據範例 (共 {len(data_first_run)} 筆):"
            )
            print("最早的 5 筆數據:")
            print(data_first_run.head())
            print("\n最新的 5 筆數據:")
            print(data_first_run.tail())
        else:
            print("錯誤：未能獲取任何一級交易商持有量數據。")

    except Exception as e:
        print(f"執行 NYFedClient 測試期間發生未預期錯誤: {e}")
        traceback.print_exc()
    finally:
        client.close_session()  # 確保關閉 session

    print("\n--- NYFedClient 快取整合後測試結束 ---")


================================================================================
### FILE: prometheus/core/clients/taifex_db.py
================================================================================

# 檔案路徑: core/clients/taifex_db.py
from typing import Any, Dict

import pandas as pd


class TaifexDBClient:
    """
    台灣期貨交易所數據庫客戶端 (佔位符)。
    未來將實現從數據庫讀取數據的功能。
    """

    def __init__(self, db_connection_string: str = None):
        """
        初始化 TaifexDBClient。
        :param db_connection_string: 資料庫連線字串 (未來使用)
        """
        self.db_connection_string = db_connection_string
        print("TaifexDBClient (佔位符) 已初始化。")

    def get_institutional_positions(
        self, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """
        獲取三大法人期貨及選擇權籌碼分佈 (佔位符)。
        :param start_date: 開始日期 (YYYY-MM-DD)
        :param end_date: 結束日期 (YYYY-MM-DD)
        :return: 包含籌碼數據的 DataFrame
        """
        print(
            f"TaifexDBClient (佔位符): 正在獲取 {start_date} 到 {end_date} 的三大法人數據..."
        )
        # 返回一個空的 DataFrame 作為佔位符
        return pd.DataFrame()

    def get_futures_ohlcv(
        self, contract: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """
        獲取指定期貨合約的 OHLCV 數據 (佔位符)。
        :param contract: 合約代碼 (例如 TXF1)
        :param start_date: 開始日期 (YYYY-MM-DD)
        :param end_date: 結束日期 (YYYY-MM-DD)
        :return: 包含 OHLCV 數據的 DataFrame
        """
        print(
            f"TaifexDBClient (佔位符): 正在獲取 {contract} 從 {start_date} 到 {end_date} 的 OHLCV 數據..."
        )
        # 返回一個空的 DataFrame 作為佔位符
        return pd.DataFrame()

    # 可以根據需要添加更多方法
    def some_other_method(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        另一個示例方法 (佔位符)。
        """
        print(f"TaifexDBClient (佔位符): 呼叫 some_other_method，參數: {params}")
        return {"status": "success", "data": "some_placeholder_data"}


================================================================================
### FILE: prometheus/core/clients/yfinance.py
================================================================================

# core/clients/yfinance.py
# 此模組包含從 Yahoo Finance 下載市場數據的客戶端邏輯。

import traceback
from typing import (
    Any,
    List,
    cast,
)

import pandas as pd
import yfinance as yf

from .base import BaseAPIClient
from prometheus.core.logging.log_manager import LogManager

logger = LogManager.get_instance().get_logger("YFinanceClient")


class YFinanceClient(BaseAPIClient):
    """
    用於從 Yahoo Finance 下載市場數據的客戶端。
    此客戶端使用 yfinance 套件，不直接進行 HTTP 請求，
    因此不使用 BaseAPIClient 的 _request 方法。
    """

    def __init__(self):
        """
        初始化 YFinanceClient。
        Yahoo Finance 不需要 API Key 或特定的 Base URL (由 yfinance 套件處理)。
        """
        super().__init__(api_key=None, base_url=None)
        logger.info("YFinanceClient 初始化完成。")

    async def fetch_data(
        self, symbol: str, **kwargs
    ) -> pd.DataFrame:
        """
        非同步地從 Yahoo Finance 抓取指定商品代碼的 OHLCV 數據。
        """
        import asyncio

        start_date = kwargs.get("start_date")
        end_date = kwargs.get("end_date")
        period = kwargs.get("period")

        if not period and not (start_date and end_date):
            raise ValueError("必須提供 'period' 或 'start_date' 與 'end_date' 其中之一。")

        history_params = {
            "start": start_date,
            "end": end_date,
            "auto_adjust": kwargs.get("auto_adjust", False),
            "interval": kwargs.get("interval", "1d"),
            "actions": kwargs.get("actions", False),
        }
        if period:
            history_params["period"] = period
            history_params.pop("start", None)
            history_params.pop("end", None)

        logger.info(f"開始抓取數據：商品 {symbol}, 參數: {history_params}")

        def _sync_fetch():
            try:
                ticker_obj: Any = yf.Ticker(symbol)
                history_params.pop("progress", None)
                hist_data: Any = ticker_obj.history(**history_params)

                if hist_data is None or hist_data.empty:
                    logger.warning(f"商品 {symbol} 使用參數 {history_params} 未找到數據或返回為空。")
                    return pd.DataFrame()

                hist_data = cast(pd.DataFrame, hist_data)
                hist_data.reset_index(inplace=True)
                hist_data["symbol"] = symbol

                date_col_name = "Datetime" if "Datetime" in hist_data.columns else "Date"
                if date_col_name not in hist_data.columns:
                    logger.warning(f"未找到預期的日期欄位 ('Date' 或 'Datetime')。可用欄位: {hist_data.columns.tolist()}")
                    return pd.DataFrame()

                hist_data[date_col_name] = pd.to_datetime(hist_data[date_col_name], utc=True)
                hist_data[date_col_name] = hist_data[date_col_name].dt.tz_convert(None)

                if date_col_name != "date":
                    hist_data.rename(columns={date_col_name: "date"}, inplace=True)

                rename_map = {"Adj Close": "Adj_Close"}
                final_df = hist_data.rename(columns=rename_map)
                final_df["date"] = pd.to_datetime(final_df["date"])

                required_cols = ["date", "symbol", "Open", "High", "Low", "Close", "Adj_Close", "Volume"]
                cols_to_keep = []
                missing_cols = []

                for col in required_cols:
                    if col in final_df.columns:
                        cols_to_keep.append(col)
                    elif col == "Adj_Close" and "Close" in final_df.columns and history_params.get("auto_adjust") is True:
                        final_df["Adj_Close"] = final_df["Close"]
                        cols_to_keep.append("Adj_Close")
                    elif col not in final_df.columns:
                        missing_cols.append(col)

                if missing_cols:
                    logger.warning(f"抓取的數據中缺少以下預期欄位: {missing_cols} (Symbol: {symbol})。")

                valid_cols_to_keep = [col for col in cols_to_keep if col in final_df.columns]
                if not valid_cols_to_keep:
                    logger.warning(f"沒有有效的欄位可供選擇 (Symbol: {symbol})")
                    return pd.DataFrame()

                final_df = final_df[valid_cols_to_keep]

                logger.info(f"成功抓取並處理 {len(final_df)} 筆數據，商品: {symbol}。")
                return final_df

            except Exception as e:
                logger.error(f"抓取數據時發生錯誤 (Symbol: {symbol})：{e}", exc_info=True)
                return pd.DataFrame()

        return await asyncio.to_thread(_sync_fetch)

    async def fetch_multiple_symbols_data(
        self, symbols: List[str], **kwargs
    ) -> pd.DataFrame:
        import asyncio

        if not isinstance(symbols, list) or not symbols:
            logger.error("symbols 參數必須是一個非空列表。")
            return pd.DataFrame()

        tasks = [self.fetch_data(symbol=s, **kwargs) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_data_list = []
        for i, res in enumerate(results):
            if isinstance(res, pd.DataFrame) and not res.empty:
                all_data_list.append(res)
            elif isinstance(res, Exception):
                logger.error(
                    f"處理商品 {symbols[i]} 時發生錯誤: {res}", exc_info=True
                )

        if not all_data_list:
            logger.info("未從任何指定商品抓取到數據。")
            return pd.DataFrame()

        combined_df = pd.concat(all_data_list, ignore_index=True)
        logger.info(
            f"成功合併 {len(combined_df)} 筆來自 {len(all_data_list)} 個商品的數據。"
        )
        return combined_df

    def get_ticker(self, symbol: str) -> yf.Ticker:
        """
        獲取一個 yfinance Ticker 物件。
        """
        return yf.Ticker(symbol)

    def get_move_index(self, start_date: str, end_date: str) -> pd.Series:
        """從 yfinance 獲取 ICE BofA MOVE Index (^MOVE) 的歷史收盤價。"""
        logger.info(f"正在獲取 ^MOVE 指數數據，日期範圍: {start_date} 至 {end_date}")
        try:
            move_ticker = yf.Ticker("^MOVE")
            start_date_dt = pd.to_datetime(start_date)
            end_date_dt = pd.to_datetime(end_date)
            end_date_for_yf = (end_date_dt + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            start_date_for_yf = start_date_dt.strftime("%Y-%m-%d")
            history = move_ticker.history(start=start_date_for_yf, end=end_date_for_yf)

            if history.empty:
                logger.warning(f"^MOVE 指數在 {start_date_for_yf} 至 {end_date_for_yf} 未返回任何數據。")
                return pd.Series(dtype="float64", name="Close")

            close_series = history["Close"]
            if not isinstance(close_series.index, pd.DatetimeIndex):
                close_series.index = pd.to_datetime(close_series.index)

            close_series = close_series[close_series.index <= end_date_dt]

            if close_series.empty:
                logger.warning(f"^MOVE 指數在篩選日期 ({start_date_dt.date()} 至 {end_date_dt.date()}) 後數據為空。")
                return pd.Series(dtype="float64", name="Close")

            logger.info(f"成功獲取 {len(close_series)} 筆 ^MOVE 指數數據。")
            return close_series
        except Exception as e:
            logger.error(f"獲取 ^MOVE 指數時失敗: {e}", exc_info=True)
            return pd.Series(dtype="float64", name="Close")


if __name__ == "__main__":
    print("--- YFinanceClient 重構後測試 (直接執行 core/clients/yfinance.py) ---")
    try:
        client = YFinanceClient()
        print("YFinanceClient 初始化成功。")

        print("\n測試獲取 AAPL 數據 (2023-12-01 至 2023-12-05)...")
        aapl_data = client.fetch_data(
            symbol="AAPL", start_date="2023-12-01", end_date="2023-12-05"
        )
        if aapl_data is not None and not aapl_data.empty:
            print(f"成功獲取 AAPL 數據 (共 {len(aapl_data)} 筆):")
            print(aapl_data.head())
        else:
            print("獲取 AAPL 數據返回空 DataFrame 或 None。")

        print("\n測試獲取 AAPL 和 MSFT 數據 (最近5天, 1d 間隔)...")
        multi_data = client.fetch_multiple_symbols_data(
            symbols=["AAPL", "MSFT", "NONEXISTENTICKER"],
            period="5d",
            interval="1d",
        )
        if multi_data is not None and not multi_data.empty:
            print(f"成功獲取多個商品數據 (共 {len(multi_data)} 筆):")
            print(multi_data.head())
            print("...")
            print(multi_data.tail())
            print(f"數據中包含的 Symbols: {multi_data['symbol'].unique()}")
        else:
            print("獲取多個商品數據返回空 DataFrame 或 None。")

        print("\n測試獲取 ^GSPC 數據 (最近1個月)...")
        gspc_data = client.fetch_data(symbol="^GSPC", period="1mo")
        if gspc_data is not None and not gspc_data.empty:
            print(f"成功獲取 ^GSPC 數據 (最近1個月，共 {len(gspc_data)} 筆):")
            print(gspc_data.head())
        else:
            print("獲取 ^GSPC 數據返回空 DataFrame 或 None。")

        print("\n測試獲取 SPY 數據 (最近1天, 1m 間隔)...")
        spy_intraday = client.fetch_data(symbol="SPY", period="1d", interval="1m")
        if spy_intraday is not None and not spy_intraday.empty:
            print(f"成功獲取 SPY 1分鐘數據 (共 {len(spy_intraday)} 筆):")
            assert "Date" in spy_intraday.columns
            assert "Datetime" not in spy_intraday.columns
            print(spy_intraday.head())
        else:
            print(
                "獲取 SPY 1分鐘數據返回空 DataFrame 或 None (可能是市場未開盤或超出 yfinance 限制)。"
            )

    except Exception as e:
        print(f"執行 YFinanceClient 測試期間發生未預期錯誤: {e}")
        traceback.print_exc()

    print("--- YFinanceClient 重構後測試結束 ---")


================================================================================
### FILE: prometheus/core/config.py
================================================================================

# -*- coding: utf-8 -*-
from typing import Any, Dict

import yaml

from prometheus.core.logging.log_manager import LogManager

logger = LogManager.get_instance().get_logger("ConfigManager")


class ConfigManager:
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls, config_path: str = "config.yml"):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        cls._instance._load_config(config_path)
        return cls._instance

    def _load_config(self, config_path: str):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self.__class__._config.update(yaml.safe_load(f))
                logger.info(f"設定檔 '{config_path}' 載入成功。")
        except FileNotFoundError:
            logger.warning(f"找不到設定檔 '{config_path}'。將使用預設值或空值。")
        except Exception as e:
            logger.error(f"載入設定檔 '{config_path}' 時發生錯誤: {e}", exc_info=True)

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value = self.__class__._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value


# 建立一個全域實例，方便在專案中各處直接導入使用
# 確保在模組加載時，ConfigManager('config.yml') 被調用一次以加載配置。
config = ConfigManager(config_path="config.yml")  # 指定路徑


def get_fred_api_key() -> str:
    """一個專用的輔助函數，用於安全地獲取 FRED API 金鑰。"""
    key = config.get("api_keys.fred")
    if not key or "YOUR_REAL" in key:
        error_msg = "FRED API 金鑰未在 config.yml 中正確設定或仍為預留位置。"
        logger.error(error_msg)
        raise ValueError(error_msg)
    return key


if __name__ == "__main__":
    print("--- 設定檔管理器測試 ---")
    # 重新載入設定以確保測試時是最新的（或創建一個新的臨時實例）
    # test_config = ConfigManager(config_path='config.yml') # 確保測試使用的是最新的

    db_path = config.get("database.path", "default.db")
    print(f"資料庫路徑: {db_path}")

    retries = config.get("data_acquisition.retries", 0)
    print(f"重試次數: {retries}")

    non_existent = config.get("non_existent.key", "預設值")
    print(f"不存在的鍵: {non_existent}")

    try:
        api_key = get_fred_api_key()
        # 安全起見，不在日誌中打印金鑰本身
        print(f"成功讀取 FRED API Key (長度: {len(api_key)})")
    except ValueError as e:
        print(e)

    # 測試直接從 config 實例獲取金鑰
    fred_key_direct = config.get("api_keys.fred")
    if fred_key_direct and fred_key_direct != "YOUR_FRED_API_KEY_HERE":
        print(f"直接從 config 實例獲取 FRED API Key (長度: {len(fred_key_direct)})")
    else:
        print("無法直接從 config 實例獲取有效的 FRED API Key。")

    print("--- 測試結束 ---")


================================================================================
### FILE: prometheus/core/constants.py
================================================================================



================================================================================
### FILE: prometheus/core/context.py
================================================================================

# 檔案: src/core/context.py
import os

import aiosqlite

from prometheus.core.events.event_store import PersistentEventStream


class AppContext:
    _instance = None

    def __init__(self, db_path: str = "output/results.sqlite", config_path: str = "config.yml"):
        self.db_path = db_path
        from prometheus.core.config import ConfigManager
        self.config = ConfigManager(config_path=config_path)._config
        self.conn = None
        self.event_stream: PersistentEventStream | None = None

    async def __aenter__(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        self.conn = await aiosqlite.connect(self.db_path)
        # 啟用 WAL 模式以獲得更好的並發性能
        await self.conn.execute("PRAGMA journal_mode=WAL;")

        # 初始化事件流
        self.event_stream = PersistentEventStream(self.conn)
        await self.event_stream.initialize()

        return self

    @classmethod
    def get_instance(cls, **kwargs):
        if cls._instance is None:
            if 'config_path' not in kwargs:
                kwargs['config_path'] = 'config.yml'
            cls._instance = cls(config_path=kwargs.get('config_path', 'config.yml'))
        return cls._instance

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            await self.conn.close()


================================================================================
### FILE: prometheus/core/db/__init__.py
================================================================================

import duckdb

def get_db_connection(db_path):
    return duckdb.connect(database=db_path, read_only=False)


================================================================================
### FILE: prometheus/core/db/data_warehouse.py
================================================================================

from pathlib import Path

import duckdb
import pandas as pd


class DataWarehouse:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(str(self.db_path))

    def execute_query(self, query: str, params=None):
        return self.conn.execute(query, params)

    def get_results(self, query: str, params=None) -> pd.DataFrame:
        return self.conn.execute(query, params).fetchdf()

    def table_exists(self, table_name: str) -> bool:
        try:
            self.conn.execute(f"DESCRIBE {table_name}")
            return True
        except duckdb.CatalogException:
            return False

    def close(self):
        self.conn.close()


class RawDataWarehouse(DataWarehouse):
    def __init__(self, db_path: str):
        super().__init__(db_path)
        self._create_log_table()

    def _create_log_table(self):
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS raw_import_log (
                file_path VARCHAR PRIMARY KEY,
                content_blob BLOB,
                format_fingerprint VARCHAR
            );
        """)

    def is_file_processed(self, file_path: str) -> bool:
        result = self.execute_query(
            "SELECT COUNT(*) FROM raw_import_log WHERE file_path = ?", (file_path,)
        ).fetchone()
        return result[0] > 0 if result else False

    def log_processed_file(self, file_path: str, content: bytes, fingerprint: str):
        self.execute_query(
            "INSERT INTO raw_import_log VALUES (?, ?, ?)",
            (file_path, content, fingerprint),
        )


class AnalyticsDataWarehouse(DataWarehouse):
    def create_daily_futures_table(self):
        self.execute_query("""
            CREATE TABLE IF NOT EXISTS daily_futures (
                "交易日期" VARCHAR,
                "契約代碼" VARCHAR,
                "到期月份(週別)" VARCHAR,
                "開盤價" VARCHAR,
                "最高價" VARCHAR,
                "最低價" VARCHAR,
                "收盤價" VARCHAR,
                "成交量" VARCHAR
            );
        """)

    def insert_daily_futures(self, df: pd.DataFrame):
        self.conn.register('df_to_load', df)
        self.execute_query(
            "INSERT INTO daily_futures SELECT * FROM df_to_load"
        )


================================================================================
### FILE: prometheus/core/db/db_manager.py
================================================================================

import duckdb
import os
import pandas as pd
from prometheus.core.logging.log_manager import LogManager

class DBManager:
    def __init__(self, db_path: str = "data/analytics_warehouse/factors.duckdb"):
        self.db_path = db_path
        self.logger = LogManager.get_instance().get_logger(self.__class__.__name__)

        # 確保數據庫目錄存在
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)

    def save_data(self, data: pd.DataFrame, table_name: str):
        """
        一個類型感知的穩健寫入函數，能夠自動偵察、演進並寫入數據。
        """
        if data.empty:
            self.logger.warning("數據為空，沒有可以儲存的內容。")
            return

        try:
            with duckdb.connect(self.db_path) as con:
                db_columns = self._get_table_columns(con, table_name)

                if not db_columns:
                    self.logger.info(f"表格 '{table_name}' 不存在，將根據 DataFrame 結構創建。")

                    # --- [核心改造] ---
                    # 為了實現穩健的 UPSERT，我們必須在創建時就定義主鍵。
                    # 我們假設 'date' 和 'symbol' 是必然存在的核心欄位。
                    create_sql = f"""
                    CREATE TABLE {table_name} (
                        date TIMESTAMP,
                        symbol VARCHAR,
                        PRIMARY KEY (date, symbol)
                    );
                    """
                    con.execute(create_sql)
                    self.logger.info(f"成功創建表格 '{table_name}' 並定義了 (date, symbol) 複合主鍵。")

                    # 註冊 DataFrame 以便後續插入
                    con.register('df_to_insert', data)

                    # 動態添加其餘欄位
                    initial_cols = {'date', 'symbol'}
                    remaining_cols = [col for col in data.columns if col not in initial_cols]

                    for col in remaining_cols:
                        col_dtype = data[col].dtype
                        sql_type = self._map_dtype_to_sql(col_dtype)
                        con.execute(f"ALTER TABLE {table_name} ADD COLUMN \"{col}\" {sql_type};")

                    # 插入完整數據
                    all_cols = ['date', 'symbol'] + remaining_cols
                    col_names_str = ", ".join(f'"{c}"' for c in all_cols)
                    con.execute(f"INSERT INTO {table_name} ({col_names_str}) SELECT {col_names_str} FROM df_to_insert")

                    self.logger.info(f"成功將 {len(data)} 筆初始數據插入到新創建的 '{table_name}' 表格中。")
                    # 在創建後，重新獲取欄位資訊以進行後續的合併操作
                    db_columns = self._get_table_columns(con, table_name)
                else:
                    df_columns = data.columns.tolist()
                    new_columns = set(df_columns) - set(db_columns)

                    if new_columns:
                        self.logger.info(f"偵測到新欄位: {new_columns}。正在演進表格結構...")
                        for col in new_columns:
                            col_dtype = data[col].dtype
                            sql_type = self._map_dtype_to_sql(col_dtype)
                            con.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} {sql_type};")
                        self.logger.info("表格結構演進完成。")
                        db_columns = self._get_table_columns(con, table_name)

                    # --- [核心改造] ---
                    # 使用 DuckDB 的 ON CONFLICT (UPSERT) 語法實現高效、原子性的數據合併。
                    con.register('df_to_upsert', data)

                    all_columns = [f'"{c}"' for c in data.columns]
                    update_columns = [col for col in all_columns if col.lower() not in ('"date"', '"symbol"')]

                    if not update_columns:
                        self.logger.warning("沒有需要更新的欄位（除了主鍵），將只執行插入操作。")
                        # 如果只有主鍵，那麼 ON CONFLICT 就不需要 DO UPDATE
                        upsert_sql = f"""
                        INSERT INTO {table_name} ({', '.join(all_columns)})
                        SELECT {', '.join(all_columns)} FROM df_to_upsert
                        ON CONFLICT (date, symbol) DO NOTHING;
                        """
                    else:
                        set_clause = ", ".join([f'{col} = excluded.{col}' for col in update_columns])
                        upsert_sql = f"""
                        INSERT INTO {table_name} ({', '.join(all_columns)})
                        SELECT {', '.join(all_columns)} FROM df_to_upsert
                        ON CONFLICT (date, symbol) DO UPDATE SET
                            {set_clause};
                        """

                    con.execute(upsert_sql)
                    self.logger.info(f"成功將 {len(data)} 筆數據 UPSERT 到 '{table_name}'。")
        except Exception as e:
            self.logger.error(f"儲存數據時發生錯誤: {e}", exc_info=True)
            raise

    def _get_table_columns(self, con, table_name):
        """查詢並返回資料庫表的欄位列表（全部轉為小寫）。"""
        try:
            table_info = con.execute(f"PRAGMA table_info('{table_name}')").fetchall()
            # 將所有列名轉為小寫，以實現不區分大小寫的比較
            return [str(info[1]).lower() for info in table_info]
        except duckdb.CatalogException:
            return []

    def fetch_table(self, table_name: str) -> pd.DataFrame:
        """
        從數據庫中讀取整個表格並返回一個 Pandas DataFrame。

        Args:
            table_name (str): 要讀取的表格名稱。

        Returns:
            pd.DataFrame: 包含表格數據的 DataFrame。如果表格不存在或為空，則返回一個空的 DataFrame。
        """
        try:
            with duckdb.connect(self.db_path, read_only=True) as con:
                # 檢查表格是否存在
                tables = con.execute("SHOW TABLES").fetchall()
                if (table_name,) not in tables:
                    self.logger.warning(f"表格 '{table_name}' 在數據庫中不存在。")
                    return pd.DataFrame()

                df = con.table(table_name).to_df()
                self.logger.info(f"成功從 '{table_name}' 表格中讀取 {len(df)} 筆數據。")
                return df
        except Exception as e:
            self.logger.error(f"讀取表格 '{table_name}' 時發生錯誤: {e}", exc_info=True)
            return pd.DataFrame() # 在出錯時返回一個空的 DataFrame

    def _map_dtype_to_sql(self, dtype):
        """將 Pandas 的 dtype 轉換為 SQL 類型字串。"""
        if pd.api.types.is_integer_dtype(dtype):
            return 'BIGINT'
        elif pd.api.types.is_float_dtype(dtype):
            return 'DOUBLE'
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            return 'TIMESTAMP'
        elif pd.api.types.is_string_dtype(dtype) or pd.api.types.is_object_dtype(dtype):
            return 'VARCHAR'
        else:
            return 'VARCHAR'


================================================================================
### FILE: prometheus/core/db/evolution_logger.py
================================================================================

# 檔案: src/core/db/evolution_logger.py
from typing import Dict

DB_PATH = "prometheus_fire.duckdb"
TABLE_NAME = "evolution_logs"


def log_generation_stats(generation: int, stats: Dict):
    """
    將單一代的演化統計數據儲存至 DuckDB。
    """
    # This function is now a no-op
    pass


def clear_evolution_logs():
    """安全地清除所有演化日誌。"""
    # This function is now a no-op
    pass


================================================================================
### FILE: prometheus/core/db/schema_registry.py
================================================================================

import sqlite3
from pathlib import Path
from typing import Set


class SchemaRegistry:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self._create_table()

    def _create_table(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_registry (
                    format_fingerprint TEXT PRIMARY KEY,
                    header TEXT,
                    encoding TEXT,
                    file_count INTEGER DEFAULT 1,
                    first_seen_file TEXT
                )
            """)

    def add_or_update_schema(self, fingerprint: str, header: str, encoding: str, filename: str):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT file_count FROM schema_registry WHERE format_fingerprint = ?",
                (fingerprint,),
            )
            existing = cursor.fetchone()

            if existing:
                new_count = existing[0] + 1
                cursor.execute(
                    "UPDATE schema_registry SET file_count = ? WHERE format_fingerprint = ?",
                    (new_count, fingerprint),
                )
                return "updated"
            else:
                cursor.execute(
                    "INSERT INTO schema_registry VALUES (?, ?, ?, 1, ?)",
                    (fingerprint, header, encoding, filename),
                )
                return "new"

    def get_known_fingerprints(self) -> Set[str]:
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("SELECT format_fingerprint FROM schema_registry")
            return {row[0] for row in cursor.fetchall()}

    def get_all_schemas(self) -> dict:
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("SELECT format_fingerprint, header, encoding FROM schema_registry")
            return {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

    def close(self):
        self.conn.close()


================================================================================
### FILE: prometheus/core/db/transactional_writer.py
================================================================================

import json
import sqlite3
from pathlib import Path


class TransactionalWriter:
    """
    交易型寫入器：專門負責將回測結果安全地寫入 SQLite 資料庫。
    """

    def __init__(self, db_path: str | Path = "output/results.sqlite"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=10)
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS backtest_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    params TEXT,
                    crossover_points INTEGER,
                    last_price REAL,
                    batch_id TEXT,
                    timestamp TEXT
                )
            """)

    def save_result(self, result_data: dict):
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO backtest_results
                (symbol, params, crossover_points, last_price, batch_id, timestamp)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                [
                    result_data.get("symbol"),
                    json.dumps(result_data.get("params", {})),
                    result_data.get("crossover_points"),
                    result_data.get("last_price"),
                    result_data.get("batch_id"),
                ],
            )


================================================================================
### FILE: prometheus/core/engines/__init__.py
================================================================================

# This file intentionally left blank.


================================================================================
### FILE: prometheus/core/engines/bond_factor_engine.py
================================================================================

import pandas as pd
import numpy as np

class BondFactorEngine:
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        計算債券和利率特定因子。
        """
        result_df = df.copy()

        # 確保必要的欄位存在
        required_columns = ['yield_curve_slope', 'credit_spread', 'real_yield']
        if not all(col in result_df.columns for col in required_columns):
            missing_cols = [col for col in required_columns if col not in result_df.columns]
            raise ValueError(f"缺少必要的欄位來計算債券因子: {missing_cols}")

        # 殖利率曲線斜率 (直接使用)
        result_df['factor_yield_curve_slope'] = result_df['yield_curve_slope']

        # 高收益債信用利差 Z-score
        if 'credit_spread' in result_df.columns:
            # 將 credit_spread 轉換為數字類型，並將錯誤轉換為 NaN
            credit_spread_numeric = pd.to_numeric(result_df['credit_spread'], errors='coerce')

            # 計算 252 天滾動 Z-score
            rolling_mean = credit_spread_numeric.rolling(window=252).mean()
            rolling_std = credit_spread_numeric.rolling(window=252).std()
            result_df['factor_credit_spread_zscore'] = (credit_spread_numeric - rolling_mean) / rolling_std

        # 實質利率 (直接使用)
        result_df['factor_real_yield'] = result_df['real_yield']

        return result_df


================================================================================
### FILE: prometheus/core/engines/crypto_factor_engine.py
================================================================================

# src/prometheus/core/engines/crypto_factor_engine.py

import pandas as pd
import logging
from typing import Dict, Any

from src.prometheus.core.analyzers.base_analyzer import BaseAnalyzer
from src.prometheus.core.clients.client_factory import ClientFactory


logger = logging.getLogger(__name__)


class CryptoFactorEngine(BaseAnalyzer):
    """
    加密貨幣因子引擎，專門計算與加密貨幣相關的因子。
    """

    def __init__(self, client_factory: ClientFactory):
        """
        初始化加密貨幣因子引擎。
        """
        super().__init__(analyzer_name="CryptoFactorEngine")
        self.client_factory = client_factory
        self.yfinance_client = self.client_factory.get_client('yfinance')

    def _load_data(self) -> pd.DataFrame:
        """
        此方法在此引擎中不使用，因為數據由 Pipeline 提供。
        """
        self.logger.debug("CryptoFactorEngine._load_data called, but not used in pipeline context.")
        return pd.DataFrame()

    def _perform_analysis(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        此方法被 run 方法覆蓋，因此不會被直接調用。
        """
        self.logger.debug("CryptoFactorEngine._perform_analysis called, but logic is in run.")
        return data

    def _save_results(self, results: pd.DataFrame) -> None:
        """
        此方法在此引擎中不使用，因為結果由 Pipeline 保存。
        """
        self.logger.debug("CryptoFactorEngine._save_results called, but not used in pipeline context.")
        pass

    async def run(self, data: pd.DataFrame, config: Dict[str, Any] = None) -> pd.DataFrame:
        """
        執行因子計算。

        :param data: 包含加密貨幣價格數據的 DataFrame，索引為日期，應包含 'symbol' 欄位。
        :param config: 可選的配置字典。
        :return: 包含新計算因子的 DataFrame。
        """
        if 'symbol' not in data.columns:
            raise ValueError("輸入的 DataFrame 必須包含 'symbol' 欄位。")

        symbol = data['symbol'].iloc[0]
        self.logger.info(f"開始為加密貨幣 {symbol} 計算因子...")

        # 複製數據以避免修改原始 DataFrame
        result_df = data.copy()

        # 計算與納斯達克指數的相關性
        result_df = await self._calculate_nasdaq_correlation(result_df)

        # 計算恐懼與貪婪指數代理
        result_df = self._calculate_fear_greed_proxy(result_df)

        self.logger.info(f"加密貨幣 {symbol} 的因子計算完成。")
        return result_df

    async def _calculate_nasdaq_correlation(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        計算與納斯達克100指數期貨 (NQ=F) 的 30 日滾動相關性。
        """
        self.logger.debug("正在計算與納斯達克指數的相關性...")
        try:
            # 獲取 NQ=F 的數據
            start_date = df.index.min()
            end_date = df.index.max()
            nasdaq_data = await self.yfinance_client.fetch_data('NQ=F', start_date=start_date, end_date=end_date)
            if nasdaq_data is None or nasdaq_data.empty:
                self.logger.warning("無法獲取納斯達克數據 (NQ=F)，跳過相關性計算。")
                df['factor_corr_nq'] = None
                return df

            # 確保兩個 DataFrame 的索引都是日期時間類型且沒有重複
            df.index = pd.to_datetime(df.index)
            df = df[~df.index.duplicated(keep='first')]

            nasdaq_data.index = pd.to_datetime(nasdaq_data.index)
            nasdaq_data = nasdaq_data[~nasdaq_data.index.duplicated(keep='first')]

            # 合併數據並計算日收益率
            merged_df = pd.merge(df[['close']], nasdaq_data[['close']], left_index=True, right_index=True, suffixes=('_crypto', '_nasdaq'))
            merged_df['crypto_returns'] = merged_df['close_crypto'].pct_change()
            merged_df['nasdaq_returns'] = merged_df['close_nasdaq'].pct_change()

            # 計算 30 日滾動相關性
            correlation = merged_df['crypto_returns'].rolling(window=30).corr(merged_df['nasdaq_returns'])

            # 將計算出的相關性合併回原始 DataFrame
            df['factor_corr_nq'] = correlation

            self.logger.debug("成功計算與納斯達克指數的相關性。")

        except Exception as e:
            self.logger.error(f"計算納斯達克相關性時出錯: {e}", exc_info=True)
            df['factor_corr_nq'] = None

        return df

    def _calculate_fear_greed_proxy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        計算 7 日的已實現波動率，作為市場情緒的代理指標。
        已實現波動率越高，通常表示市場恐懼情緒越濃。
        """
        self.logger.debug("正在計算恐懼與貪婪指數代理（7日已實現波動率）...")
        try:
            # 計算日收益率
            returns = df['close'].pct_change()
            # 計算 7 日滾動標準差（波動率）
            volatility = returns.rolling(window=7).std()
            df['factor_fear_greed_proxy'] = volatility
            self.logger.debug("成功計算恐懼與貪婪指數代理。")
        except Exception as e:
            self.logger.error(f"計算恐懼與貪婪指數代理時出錯: {e}", exc_info=True)
            df['factor_fear_greed_proxy'] = None
        return df


================================================================================
### FILE: prometheus/core/engines/index_factor_engine.py
================================================================================

import pandas as pd
import numpy as np

class IndexFactorEngine:
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        計算指數特定因子。
        """
        result_df = df.copy()

        # 確保必要的欄位存在
        required_columns = ['vix', 'move', 'close']
        if not all(col in result_df.columns for col in required_columns):
            missing_cols = [col for col in required_columns if col not in result_df.columns]
            raise ValueError(f"缺少必要的欄位來計算指數因子: {missing_cols}")

        # 股債波動率比率 (VIX / MOVE)
        # 避免除以零
        if 'vix' in result_df.columns and 'move' in result_df.columns:
            result_df['factor_vix_move_ratio'] = result_df['vix'] / result_df['move'].replace(0, np.nan)

        # 波動率風險溢價 (VIX - 已實現波動率)
        # 計算 20 日已實現波動率
        result_df['realized_vol_20d'] = result_df['close'].pct_change().rolling(window=20).std() * np.sqrt(252)
        if 'vix' in result_df.columns:
            result_df['factor_vrp'] = result_df['vix'] - result_df['realized_vol_20d']

        return result_df


================================================================================
### FILE: prometheus/core/engines/stock_factor_engine.py
================================================================================

# src/prometheus/core/engines/stock_factor_engine.py

import pandas as pd
import logging
from typing import Dict, Any, List

from src.prometheus.core.analyzers.base_analyzer import BaseAnalyzer
from src.prometheus.core.clients.client_factory import ClientFactory

logger = logging.getLogger(__name__)


class StockFactorEngine(BaseAnalyzer):
    """
    股票因子引擎，專門計算與個股相關的財務因子。
    """

    def __init__(self, client_factory: ClientFactory):
        """
        初始化股票因子引擎。

        :param client_factory: 客戶端工廠，用於獲取 yfinance 和 FinMind 的客戶端。
        """
        super().__init__(analyzer_name="StockFactorEngine")
        self.client_factory = client_factory
        self.yfinance_client = self.client_factory.get_client('yfinance')
        self.finmind_client = self.client_factory.get_client('finmind')

    def _load_data(self) -> pd.DataFrame:
        """
        此方法在此引擎中不使用，因為數據由 Pipeline 提供。
        """
        self.logger.debug("StockFactorEngine._load_data called, but not used in pipeline context.")
        return pd.DataFrame()

    def _perform_analysis(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        此方法被 run 方法覆蓋，因此不會被直接調用。
        """
        self.logger.debug("StockFactorEngine._perform_analysis called, but logic is in run.")
        return data

    def _save_results(self, results: pd.DataFrame) -> None:
        """
        此方法在此引擎中不使用，因為結果由 Pipeline 保存。
        """
        self.logger.debug("StockFactorEngine._save_results called, but not used in pipeline context.")
        pass

    async def run(self, data: pd.DataFrame, config: Dict[str, Any] = None) -> pd.DataFrame:
        """
        執行因子計算。

        :param data: 包含股票價格數據的 DataFrame，索引為日期，應包含 'symbol' 欄位。
        :param config: 可選的配置字典。
        :return: 包含新計算因子的 DataFrame。
        """
        if 'symbol' not in data.columns:
            raise ValueError("輸入的 DataFrame 必須包含 'symbol' 欄位。")

        # 複製數據以避免修改原始 DataFrame
        result_df = data.copy()

        # 計算基本面因子
        result_df = await self._calculate_fundamental_factors(result_df)

        # 計算技術面因子 (如果需要)
        # ...

        return result_df

    async def _calculate_fundamental_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        計算並合併所有基本面因子。
        """
        symbol = df['symbol'].iloc[0]
        self.logger.info(f"開始為股票 {symbol} 計算基本面因子...")

        # 獲取 yfinance 的 ticker 物件
        ticker = self.yfinance_client.get_ticker(symbol)

        # 計算本益比 (P/E Ratio)
        pe_ratio = self._calculate_pe_ratio(ticker)
        df['factor_pe_ratio'] = pe_ratio

        # 計算股價淨值比 (P/B Ratio)
        pb_ratio = self._calculate_pb_ratio(ticker)
        df['factor_pb_ratio'] = pb_ratio

        # 計算月營收年增率 (僅限台股)
        if '.TW' in symbol:
            df = await self._calculate_monthly_revenue_yoy(df, symbol)
        else:
            df['factor_monthly_revenue_yoy'] = None


        self.logger.info(f"股票 {symbol} 的基本面因子計算完成。")
        return df

    def _calculate_pe_ratio(self, ticker: Any) -> float | None:
        """
        使用 yfinance.info 獲取 P/E Ratio (TTM)。
        """
        try:
            # TTM = Trailing Twelve Months
            pe = ticker.info.get('trailingPE')
            self.logger.debug(f"成功獲取 P/E Ratio: {pe}")
            return pe
        except Exception as e:
            self.logger.warning(f"無法獲取 P/E Ratio: {e}")
            return None

    def _calculate_pb_ratio(self, ticker: Any) -> float | None:
        """
        使用 yfinance.info 獲取 P/B Ratio。
        """
        try:
            pb = ticker.info.get('priceToBook')
            self.logger.debug(f"成功獲取 P/B Ratio: {pb}")
            return pb
        except Exception as e:
            self.logger.warning(f"無法獲取 P/B Ratio: {e}")
            return None

    async def _calculate_monthly_revenue_yoy(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        計算台股的月營收年增率 (YoY)。
        """
        stock_id = symbol.replace('.TW', '')
        # 我們只需要最新的日期來獲取對應月份的營收
        latest_date = pd.to_datetime(df.index.max(), unit='ns')

        try:
            # 使用 FinMind 客戶端獲取月營收數據
            revenue_data = await self.finmind_client.get_monthly_revenue(stock_id, latest_date.year - 2, latest_date.month)
            if revenue_data.empty:
                self.logger.warning(f"股票 {symbol} 在 {latest_date} 附近無月營收數據。")
                df['factor_monthly_revenue_yoy'] = None
                return df

            # 將營收數據的日期設為索引
            revenue_data['date'] = pd.to_datetime(revenue_data['date'])
            revenue_data.set_index('date', inplace=True)

            # 計算年增率
            # 找到與 df 中每個日期對應的月份
            df['year'] = df.index.year
            df['month'] = df.index.month

            def get_revenue_yoy(row):
                current_month_revenue = revenue_data[
                    (revenue_data.index.year == row['year']) &
                    (revenue_data.index.month == row['month'])
                ]

                last_year_month_revenue = revenue_data[
                    (revenue_data.index.year == row['year'] - 1) &
                    (revenue_data.index.month == row['month'])
                ]

                if not current_month_revenue.empty and not last_year_month_revenue.empty:
                    current_revenue = current_month_revenue['revenue'].iloc[0]
                    last_year_revenue = last_year_month_revenue['revenue'].iloc[0]
                    if last_year_revenue != 0:
                        return (current_revenue - last_year_revenue) / last_year_revenue
                return None

            df['factor_monthly_revenue_yoy'] = df.apply(get_revenue_yoy, axis=1)
            df.drop(columns=['year', 'month'], inplace=True)

            self.logger.debug(f"成功計算股票 {symbol} 的月營收年增率。")

        except Exception as e:
            self.logger.error(f"計算股票 {symbol} 的月營收年增率時出錯: {e}")
            df['factor_monthly_revenue_yoy'] = None

        return df


================================================================================
### FILE: prometheus/core/events/event_store.py
================================================================================

"""
基於 aiosqlite 的持久化事件流實現。
這是系統的「唯一事實來源」。
"""

import asyncio
import json
from typing import List, Tuple


class PersistentEventStream:
    def __init__(self, conn):
        self._conn = conn
        # 使用一個非同步鎖來處理潛在的並發寫入
        self._lock = asyncio.Lock()

    async def initialize(self):
        """初始化事件儲存與檢查點儲存。"""
        async with self._lock:
            await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                data TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)
            await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS consumer_checkpoints (
                consumer_id TEXT PRIMARY KEY,
                last_processed_id INTEGER NOT NULL
            )
            """)
            await self._conn.commit()

    async def append(self, event):
        """將一個事件附加到流的末尾。"""
        event_type = type(event).__name__
        # 將 dataclass 序列化為 JSON 字串
        data = json.dumps(event.__dict__)
        async with self._lock:
            await self._conn.execute(
                "INSERT INTO events (event_type, data) VALUES (?, ?)",
                (event_type, data),
            )
            await self._conn.commit()

    async def subscribe(self, last_seen_id: int, batch_size: int = 100) -> List[Tuple]:
        """從上次看到的位置讀取新事件。"""
        cursor = await self._conn.execute(
            "SELECT id, event_type, data FROM events WHERE id > ? ORDER BY id ASC LIMIT ?",
            (last_seen_id, batch_size),
        )
        return await cursor.fetchall()

    async def get_checkpoint(self, consumer_id: str) -> int:
        """獲取指定消費者的最後處理事件ID。"""
        cursor = await self._conn.execute(
            "SELECT last_processed_id FROM consumer_checkpoints WHERE consumer_id = ?",
            (consumer_id,),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def update_checkpoint(self, consumer_id: str, last_processed_id: int):
        """更新指定消費者的檢查點。"""
        async with self._lock:
            await self._conn.execute(
                """
                INSERT INTO consumer_checkpoints (consumer_id, last_processed_id)
                VALUES (?, ?)
                ON CONFLICT(consumer_id) DO UPDATE SET last_processed_id = excluded.last_processed_id
                """,
                (consumer_id, last_processed_id),
            )
            await self._conn.commit()

    async def get_total_event_count(self) -> int:
        """獲取事件流中的事件總數。"""
        cursor = await self._conn.execute("SELECT MAX(id) FROM events")
        row = await cursor.fetchone()
        return row[0] if row and row[0] is not None else 0

    async def get_all_checkpoints(self) -> dict[str, int]:
        """獲取所有消費者的檢查點。"""
        cursor = await self._conn.execute(
            "SELECT consumer_id, last_processed_id FROM consumer_checkpoints"
        )
        return dict(await cursor.fetchall())


================================================================================
### FILE: prometheus/core/events/event_types.py
================================================================================

"""
定義系統中所有領域事件的標準資料結構。
使用 dataclasses 確保事件的不可變性與結構清晰。
"""

import dataclasses
from typing import Any, Dict


@dataclasses.dataclass(frozen=True)
class BaseEvent:
    """事件基類"""

    pass


@dataclasses.dataclass(frozen=True)
class GenomeGenerated(BaseEvent):
    """當一個新的策略基因體被創造出來時觸發"""

    genome_id: str
    genome: Dict[str, Any]
    generation: int


@dataclasses.dataclass(frozen=True)
class BacktestCompleted(BaseEvent):
    """當一個基因體的回測完成時觸發"""

    genome_id: str
    sharpe_ratio: float
    generation: int
    genome: Dict[str, Any]


@dataclasses.dataclass(frozen=True)
class SystemShutdown(BaseEvent):
    """一個特殊的信號事件，通知所有消費者優雅地關閉。"""

    reason: str


================================================================================
### FILE: prometheus/core/logging/log_manager.py
================================================================================

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
import os

class LogManager:
    """
    一個單例的日誌管理器。
    它能為整個應用程式配置日誌，將日誌輸出到控制台和指定的可輪替檔案中。
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(LogManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, log_dir: str = "data/logs", log_file: str = "prometheus.log", log_level=logging.INFO):
        """
        初始化日誌管理器。

        :param log_dir: 日誌檔案存放的目錄。
        :param log_file: 日誌檔案的名稱。
        :param log_level: 日誌級別。
        """
        if self._initialized:
            return

        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        self.log_file_path = log_path / log_file
        self.log_level = log_level
        self.formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        self._initialized = True

    @classmethod
    def get_instance(cls):
        """
        獲取 LogManager 的單例實例。
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_logger(self, name: str) -> logging.Logger:
        """
        獲取一個配置好的日誌記錄器。

        :param name: 日誌記錄器的名稱。
        :return: 一個配置好的 logging.Logger 實例。
        """
        logger = logging.getLogger(name)
        logger.setLevel(self.log_level)

        # 為了防止重複添加 handlers，每次都清空
        if logger.hasHandlers():
            logger.handlers.clear()

        # 確保日誌事件不會向上传播到 root logger
        logger.propagate = False

        # 檔案 handler (帶輪替功能)
        file_handler = RotatingFileHandler(
            self.log_file_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(self.formatter)
        logger.addHandler(file_handler)

        # 控制台 handler
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(self.formatter)
        logger.addHandler(stream_handler)

        return logger


================================================================================
### FILE: prometheus/core/monitoring/dashboard.py
================================================================================

import time

from rich.table import Table


def generate_status_table(metrics: dict) -> Table:
    table = Table(title=f"作戰情報中心 (更新於 {time.strftime('%H:%M:%S')})")
    table.add_column("監控指標", justify="right", style="cyan", no_wrap=True)
    table.add_column("數值", style="magenta")
    total_events = metrics.get("total_events", 0)
    table.add_row("事件流總量", str(total_events))
    table.add_row("---", "---")
    checkpoints = metrics.get("checkpoints", {})
    if not checkpoints:
        table.add_row("消費者進度", "[yellow]正在等待消費者上線...[/yellow]")
    else:
        for consumer_id, last_id in checkpoints.items():
            lag = total_events - last_id
            table.add_row(f"消費者 [{consumer_id}] 進度", str(last_id))
            table.add_row(
                f"消費者 [{consumer_id}] 延遲",
                f"[red]{lag}[/red]" if lag > 10 else f"[green]{lag}[/green]",
            )
            table.add_row("---", "---")
    return table


================================================================================
### FILE: prometheus/core/pipelines/__init__.py
================================================================================



================================================================================
### FILE: prometheus/core/pipelines/base_step.py
================================================================================

# core/pipelines/base_step.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

import pandas as pd


class BaseStep(ABC):
    """
    同步數據處理管線中單個步驟的抽象基礎類。
    """

    @abstractmethod
    async def run(self, data: Any, context: Dict[str, Any]) -> Any:
        """
        執行此步驟的核心邏輯。

        :param data: 上一個步驟傳入的數據。
        :param context: Pipeline 的共享上下文。
        :return: 處理完成後，傳遞給下一步驟的數據。
        """
        pass


class BaseETLStep(BaseStep):
    """
    數據處理管線中單個步驟的抽象基礎類。
    每個繼承此類的具體步驟，都必須實現一個 execute 方法。
    """

    @abstractmethod
    def execute(self, data: pd.DataFrame | None = None, **kwargs) -> pd.DataFrame | None:
        """
        執行此步驟的核心邏輯。

        Args:
            data: 上一個步驟傳入的數據，對於第一個步驟，此項為 None。
            **kwargs: 可選的關鍵字參數。

        Returns:
            處理完成後，傳遞給下一步驟的數據。如果此步驟為終點，可返回 None。
        """
        pass

    def run(self, data: Any, context: Dict[str, Any]) -> Any:
        return self.execute(data, **context)


================================================================================
### FILE: prometheus/core/pipelines/pipeline.py
================================================================================

# core/pipelines/pipeline.py
from __future__ import annotations

import logging
from typing import List, Any
import pandas as pd

from prometheus.core.pipelines.base_step import BaseETLStep, BaseStep


class DataPipeline:
    """
    一個可組合的數據處理管線執行器。
    它可以按順序執行一系列的 ETL 步驟。
    """

    def __init__(self, steps: List[BaseETLStep]):
        """
        初始化數據管線。

        Args:
            steps: 一個包含多個 BaseETLStep 子類實例的列表。
        """
        self._steps = steps
        self.logger = logging.getLogger(self.__class__.__name__)

    async def run(self, initial_data=None, context: dict | None = None) -> None:
        """
        執行完整的数据處理流程。
        """
        import asyncio
        data = initial_data
        if context is None:
            context = {}

        self.logger.info(f"數據管線開始執行，共 {len(self._steps)} 個步驟。")
        # step_name 在循環外部可能未定義，因此在此處初始化
        step_name = "Unknown"
        try:
            for i, step in enumerate(self._steps, 1):
                # 修正: 獲取類名應為 step.__class__.__name__
                step_name = step.__class__.__name__
                self.logger.info(
                    f"--- [步驟 {i}/{len(self._steps)}]：正在執行 {step_name} ---"
                )
                if asyncio.iscoroutinefunction(step.execute):
                    data = await step.execute(data, **context)
                else:
                    data = step.execute(data, **context)
                self.logger.info(f"步驟 {step_name} 執行完畢。")

            self.logger.info("數據管線所有步驟均已成功執行。")
            return data  # 返回最後一個步驟的結果

        except Exception as e:
            self.logger.error(
                f"數據管線在執行步驟 '{step_name}' 時發生嚴重錯誤：{e}", exc_info=True
            )
            # 考慮到管線執行失敗時的健壯性，這裡可以選擇重新拋出異常
            # 或者根據需求決定是否要抑制異常並繼續（儘管通常建議拋出）
            raise


class Pipeline:
    """
    一個同步的、可組合的數據處理管線執行器。
    """

    def __init__(self, steps: List[BaseStep]):
        """
        初始化管線。

        :param steps: 一個包含多個 BaseStep 子類實例的列表。
        """
        self.steps = steps
        self.logger = logging.getLogger(self.__class__.__name__)
        self.context = {}

    async def run(self, initial_data: Any = None) -> Any:
        """
        執行完整的數據處理流程。
        """
        data = initial_data
        self.logger.info(f"Pipeline 開始執行，共 {len(self.steps)} 個步驟。")

        for i, step in enumerate(self.steps, 1):
            step_name = step.__class__.__name__
            self.logger.info(f"--- [步驟 {i}/{len(self.steps)}]：正在執行 {step_name} ---")

            try:
                if isinstance(data, pd.DataFrame):
                    result = step.run(data, self.context)
                    if hasattr(result, '__aiter__'):
                        processed_list = [item async for item in result]
                        data = pd.concat(processed_list) if all(isinstance(i, pd.DataFrame) for i in processed_list) else processed_list
                    else:
                        data = await result
                elif isinstance(data, list):
                    processed_list = [await step.run(item, self.context) for item in data]
                    data = pd.concat(processed_list) if all(isinstance(i, pd.DataFrame) for i in processed_list) else processed_list
                else:
                    data = await step.run(data, self.context)

                self.logger.info(f"步驟 {step_name} 執行完畢。")

            except Exception as e:
                self.logger.error(
                    f"Pipeline 在執行步驟 '{step_name}' 時發生嚴重錯誤：{e}", exc_info=True
                )
                raise

        self.logger.info("Pipeline 所有步驟均已成功執行。")
        return data


================================================================================
### FILE: prometheus/core/pipelines/steps/__init__.py
================================================================================



================================================================================
### FILE: prometheus/core/pipelines/steps/aggregators.py
================================================================================

# core/pipelines/steps/aggregators.py
from __future__ import annotations

import datetime  # Required for type hinting and potentially for internal logic
import logging

import pandas as pd

from ..base_step import BaseETLStep

# We will not import TimeAggregator from apps.time_aggregator.core.aggregator
# Instead, its core logic will be embedded into the TimeAggregatorStep.


class TimeAggregatorStep(BaseETLStep):
    """
    一個 ETL 步驟，用於將 Tick 數據聚合為指定時間間隔的 OHLCV 數據。
    """

    def __init__(
        self, aggregation_level: str = "1Min", db_writer_step: BaseETLStep | None = None
    ):
        """
        初始化 TimeAggregatorStep。

        Args:
            aggregation_level (str): 聚合的時間級別，例如 "1Min", "5Min"。
                                     目前主要實現 "1Min"。
            db_writer_step (BaseETLStep | None): 可選的下一步驟，用於將聚合數據寫入數據庫。
                                                 此參數是為了未來擴展，目前 execute 方法直接返回 DataFrame。
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        # Correcting Pandas frequency string: 'T' or 'min' for minutes.
        # Pandas documentation suggests 'min' is preferred over 'T' for minutes.
        if "Min" in aggregation_level:
            self.aggregation_level_pd = aggregation_level.replace("Min", "min")
        elif "H" in aggregation_level:  # For hours
            self.aggregation_level_pd = aggregation_level.replace(
                "H", "h"
            )  # Pandas uses lowercase 'h'
        else:  # Add more rules or a default if needed
            self.aggregation_level_pd = (
                aggregation_level  # Use as is if no specific replacement rule
            )

        self.db_writer_step = (
            db_writer_step  # Not used in current execute, but for future design
        )
        self.logger.info(
            f"TimeAggregatorStep initialized for aggregation level: {aggregation_level} (Pandas rule: {self.aggregation_level_pd})"
        )

    def execute(self, data: pd.DataFrame | None = None) -> pd.DataFrame | None:
        """
        執行時間序列聚合。

        Args:
            data: 上一個步驟傳入的 Tick 數據 DataFrame。
                  預期包含 'timestamp', 'price', 'volume', 'instrument' 欄位。
                  'timestamp' 欄位必須是 datetime-like。

        Returns:
            一個包含聚合後 OHLCV 數據的 Pandas DataFrame。
            欄位為 ['timestamp', 'instrument', 'open', 'high', 'low', 'close', 'volume']。
            如果輸入數據為 None 或為空，則返回 None 或空 DataFrame。
        """
        if data is None or data.empty:
            self.logger.warning(
                "Input data is None or empty. TimeAggregatorStep cannot proceed."
            )
            return pd.DataFrame(
                columns=[
                    "timestamp",
                    "instrument",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                ]
            )

        self.logger.info(f"Executing TimeAggregatorStep with {len(data)} tick records.")

        expected_columns = ["timestamp", "price", "volume", "instrument"]
        if not all(col in data.columns for col in expected_columns):
            missing_cols = [col for col in expected_columns if col not in data.columns]
            self.logger.error(
                f"Input DataFrame is missing required columns: {missing_cols}"
            )
            raise ValueError(
                f"Input DataFrame for TimeAggregatorStep is missing columns: {missing_cols}"
            )

        if not pd.api.types.is_datetime64_any_dtype(data["timestamp"]):
            self.logger.info(
                "Attempting to convert 'timestamp' column to datetime objects."
            )
            try:
                data["timestamp"] = pd.to_datetime(data["timestamp"])
                self.logger.info(
                    "Successfully converted 'timestamp' column to datetime objects."
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to convert 'timestamp' column to datetime: {e}",
                    exc_info=True,
                )
                raise TypeError(
                    "Input DataFrame 'timestamp' column must be datetime-like or convertible to datetime."
                )

        ticks_df = data.copy()

        if (
            not isinstance(ticks_df.index, pd.DatetimeIndex)
            or ticks_df.index.name != "timestamp"
        ):
            if "timestamp" in ticks_df.columns:
                ticks_df = ticks_df.set_index("timestamp")
            else:
                self.logger.error(
                    "Critical: 'timestamp' column not found for setting index after initial checks."
                )
                raise ValueError(
                    "Cannot set 'timestamp' as index as it's not available."
                )

        ohlcv_list = []
        if "instrument" not in ticks_df.columns:
            self.logger.error("Critical: 'instrument' column not found for grouping.")
            raise ValueError("'instrument' column is required for aggregation.")

        for instrument, group_df in ticks_df.groupby("instrument"):
            self.logger.debug(
                f"Aggregating for instrument: {instrument}, {len(group_df)} ticks, rule: {self.aggregation_level_pd}"
            )

            agg_rules = {"price": ["first", "max", "min", "last"], "volume": "sum"}

            try:
                # Ensure the index is sorted for resampling to work correctly and avoid UserWarning
                group_df_sorted = group_df.sort_index()
                resampled_group = group_df_sorted.resample(
                    self.aggregation_level_pd
                ).agg(agg_rules)
            except Exception as e:
                self.logger.error(
                    f"Error during resampling for instrument {instrument} with rule '{self.aggregation_level_pd}': {e}",
                    exc_info=True,
                )
                continue

            if resampled_group.empty:
                self.logger.debug(
                    f"No data after resampling for instrument {instrument} at {self.aggregation_level_pd} interval."
                )
                continue

            resampled_group.columns = [
                "_".join(col).strip() for col in resampled_group.columns.values
            ]

            resampled_group.rename(
                columns={
                    "price_first": "open",
                    "price_max": "high",
                    "price_min": "low",
                    "price_last": "close",
                    "volume_sum": "volume",
                },
                inplace=True,
            )

            resampled_group["instrument"] = instrument
            ohlcv_list.append(resampled_group)

        if not ohlcv_list:
            self.logger.warning(
                "Aggregation resulted in an empty list. No OHLCV data produced."
            )
            return pd.DataFrame(
                columns=[
                    "timestamp",
                    "instrument",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                ]
            )

        final_ohlcv_df = pd.concat(ohlcv_list)
        final_ohlcv_df.reset_index(inplace=True)

        output_columns = [
            "timestamp",
            "instrument",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]
        # Ensure all expected columns are present, fill with NaN if any are missing (e.g. if agg_rules somehow failed for a column)
        for col in output_columns:
            if col not in final_ohlcv_df.columns:
                final_ohlcv_df[col] = (
                    pd.NA
                )  # Or appropriate default like 0 for volume, NaN for prices

        final_ohlcv_df = final_ohlcv_df[output_columns]
        final_ohlcv_df.dropna(
            subset=["open", "high", "low", "close"], how="all", inplace=True
        )
        # Convert volume to integer type if it's float after aggregation (e.g. if NaNs were present then filled)
        if "volume" in final_ohlcv_df.columns:
            final_ohlcv_df["volume"] = (
                final_ohlcv_df["volume"].fillna(0).astype("int64")
            )

        self.logger.info(
            f"TimeAggregatorStep successfully aggregated {len(data)} ticks into {len(final_ohlcv_df)} OHLCV records."
        )

        return final_ohlcv_df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    sample_ticks_data = [
        {
            "timestamp": datetime.datetime(2023, 1, 1, 9, 0, 5),
            "price": 100.0,
            "volume": 10,
            "instrument": "INSTR_A",
        },
        {
            "timestamp": datetime.datetime(2023, 1, 1, 9, 0, 15),
            "price": 101.0,
            "volume": 5,
            "instrument": "INSTR_A",
        },
        {
            "timestamp": datetime.datetime(2023, 1, 1, 9, 0, 30),
            "price": 99.0,
            "volume": 8,
            "instrument": "INSTR_A",
        },
        {
            "timestamp": datetime.datetime(2023, 1, 1, 9, 0, 50),
            "price": 100.5,
            "volume": 12,
            "instrument": "INSTR_A",
        },
        {
            "timestamp": datetime.datetime(2023, 1, 1, 9, 1, 10),
            "price": 102.0,
            "volume": 7,
            "instrument": "INSTR_A",
        },
        {
            "timestamp": datetime.datetime(2023, 1, 1, 9, 0, 10),
            "price": 2000.0,
            "volume": 20,
            "instrument": "INSTR_B",
        },
        {
            "timestamp": datetime.datetime(2023, 1, 1, 9, 0, 40),
            "price": 1995.0,
            "volume": 15,
            "instrument": "INSTR_B",
        },
    ]
    input_df = pd.DataFrame(sample_ticks_data)
    # 'timestamp' column is already datetime objects from creation

    print("--- Input DataFrame (Sample Ticks) ---")
    print(input_df)
    print(f"\nInput types:\n{input_df.dtypes}")

    aggregator_step = TimeAggregatorStep(aggregation_level="1Min")
    aggregated_data = aggregator_step.execute(input_df)

    if aggregated_data is not None:
        print("\n--- Aggregated Data (OHLCV) ---")
        print(aggregated_data)
        print(f"\nAggregated types:\n{aggregated_data.dtypes}")

        if not aggregated_data.empty:
            assert "timestamp" in aggregated_data.columns
            assert pd.api.types.is_datetime64_any_dtype(aggregated_data["timestamp"])
            assert "instrument" in aggregated_data.columns
            assert "open" in aggregated_data.columns
            assert "volume" in aggregated_data.columns
            assert pd.api.types.is_integer_dtype(aggregated_data["volume"])

            instr_a_first_min = aggregated_data[
                (aggregated_data["instrument"] == "INSTR_A")
                & (aggregated_data["timestamp"] == pd.Timestamp("2023-01-01 09:00:00"))
            ]
            if not instr_a_first_min.empty:
                print("\nINSTR_A 09:00:00 OHLCV:")
                print(instr_a_first_min)
                assert instr_a_first_min.iloc[0]["open"] == 100.0
                assert instr_a_first_min.iloc[0]["high"] == 101.0
                assert instr_a_first_min.iloc[0]["low"] == 99.0
                assert instr_a_first_min.iloc[0]["close"] == 100.5
                assert instr_a_first_min.iloc[0]["volume"] == 35  # 10+5+8+12
                print("INSTR_A 09:00:00 assertions passed.")
            else:
                print("Warning: INSTR_A 09:00:00 data not found in aggregated output.")
    else:
        print("Aggregator step did not return data.")


================================================================================
### FILE: prometheus/core/pipelines/steps/financial_steps.py
================================================================================

from prometheus.core.pipelines.base_step import BaseETLStep
from prometheus.core.analysis.stress_index import StressIndexCalculator
import pandas as pd
import logging
from typing import Dict, Any

from src.prometheus.core.pipelines.base_step import BaseStep
from src.prometheus.core.engines.stock_factor_engine import StockFactorEngine
from src.prometheus.core.engines.crypto_factor_engine import CryptoFactorEngine

logger = logging.getLogger(__name__)


class BuildGoldLayerStep(BaseETLStep):
    """
    將多個來源的數據融合成「黃金層」數據的管線步驟。
    """

    def execute(self, data=None):
        print("\n--- [Step] Executing BuildGoldLayerStep ---")
        # 在此執行黃金層數據的複雜ETL邏輯
        # ...
        print("--- [Success] Gold layer data built. ---")
        # 為了測試，返回一個成功的標誌
        return {"status": "gold_layer_ok"}


class CalculateStressIndexStep(BaseETLStep):
    """
    計算市場壓力指數的管線步驟。
    """

    def execute(self, data=None):
        print("\n--- [Step] Executing CalculateStressIndexStep ---")
        calculator = None
        try:
            calculator = StressIndexCalculator()
            stress_index_df = calculator.calculate()
            if not stress_index_df.empty:
                latest_stress_index = stress_index_df["Stress_Index"].iloc[-1]
                print("--- [Success] Stress index calculated. ---")
                print(f"壓力指數當前值: {latest_stress_index:.2f}")
                return {"status": "success", "stress_index": latest_stress_index}
            else:
                print("--- [Failed] Stress index calculation returned empty data. ---")
                return {"status": "failed", "reason": "Empty data from calculator"}
        except Exception as e:
            print(
                f"--- [Error] An error occurred during stress index calculation: {e} ---"
            )
            return {"status": "error", "reason": str(e)}
        finally:
            if calculator:
                calculator.close_all_sessions()


class RunStockFactorEngineStep(BaseStep):
    """
    一個 Pipeline 步驟，用於執行股票因子引擎。
    """

    def __init__(self, engine: StockFactorEngine):
        """
        初始化步驟。

        :param engine: 一個 StockFactorEngine 的實例。
        """
        self.engine = engine

    async def run(self, data: pd.DataFrame, context: Dict[str, Any]) -> pd.DataFrame:
        """
        對輸入的 DataFrame 執行因子引擎。

        :param data: 包含價格數據的 DataFrame。
        :param context: Pipeline 的共享上下文。
        :return: 處理後、包含新因子欄位的 DataFrame。
        """
        logger.info("正在執行 RunStockFactorEngineStep...")

        if data.empty:
            logger.warning("輸入的數據為空，跳過因子計算。")
            return data

        # StockFactorEngine 的 run 方法是按 symbol 處理的
        # 我們需要確保輸入的 data 是單一 symbol 的
        # 或者修改引擎以處理多個 symbol
        # 這裡我們假設 Pipeline 的上一步 (Loader) 已經將數據按 symbol 分組

        processed_data = await self.engine.run(data)

        logger.info("RunStockFactorEngineStep 執行完畢。")
        return processed_data


class RunCryptoFactorEngineStep(BaseStep):
    """
    一個 Pipeline 步驟，用於執行加密貨幣因子引擎。
    """

    def __init__(self, engine: CryptoFactorEngine):
        """
        初始化步驟。

        :param engine: 一個 CryptoFactorEngine 的實例。
        """
        self.engine = engine

    async def run(self, data: pd.DataFrame, context: Dict[str, Any]) -> pd.DataFrame:
        """
        對輸入的 DataFrame 執行因子引擎。

        :param data: 包含價格數據的 DataFrame。
        :param context: Pipeline 的共享上下文。
        :return: 處理後、包含新因子欄位的 DataFrame。
        """
        logger.info("正在執行 RunCryptoFactorEngineStep...")

        if data.empty:
            logger.warning("輸入的數據為空，跳過因子計算。")
            return data

        processed_data = await self.engine.run(data)

        logger.info("RunCryptoFactorEngineStep 執行完畢。")
        return processed_data


================================================================================
### FILE: prometheus/core/pipelines/steps/loaders.py
================================================================================

# core/pipelines/steps/loaders.py
from __future__ import annotations

import datetime
import logging
import os

import duckdb
import pandas as pd
import numpy as np
from typing import List, Dict, Any

from prometheus.core.pipelines.base_step import BaseETLStep, BaseStep
from src.prometheus.core.clients.client_factory import ClientFactory

# --- 依賴管理的說明 ---
# 理想情況下，`DatabaseManager` 和 `TaifexTick` 應該是 `core` 的一部分，
# 或者位於一個可被 `core` 和 `apps` 共享的通用庫中。
# 目前，`apps.taifex_tick_loader.core` 依賴於 `pydantic`。
# 如果 `pydantic` 未安裝或 `PYTHONPATH` 未正確設定，導致以下導入失敗，
# 此步驟將使用簡化的 fallback 邏輯。
# 警告：Fallback 邏輯可能與完整實現存在差異。

try:
    # 假設 apps 目錄與 core 目錄在同一級別，並且都在 PYTHONPATH 中
    from apps.taifex_tick_loader.core.db_manager import DatabaseManager
    from apps.taifex_tick_loader.core.schemas import TaifexTick

    # 檢查 TaifexTick 是否真的是 Pydantic 模型，以確認導入是否符合預期
    if not hasattr(TaifexTick, "model_fields"):  # Pydantic v2 check
        raise ImportError(
            "TaifexTick from apps.taifex_tick_loader.core.schemas does not appear to be a Pydantic v2 model."
        )
    IMPORTED_APP_DEPS = True
    logging.info(
        "Successfully imported DatabaseManager and TaifexTick from apps.taifex_tick_loader.core"
    )
except ImportError as e:
    logging.warning(
        f"Could not import dependencies from apps.taifex_tick_loader.core: {e}. "
        "TaifexTickLoaderStep will use simplified fallback logic for DB interaction and schema. "
        "Ensure 'pydantic' is installed and PYTHONPATH is correctly configured if full functionality is required."
    )
    IMPORTED_APP_DEPS = False

    # Fallback: Define a simple TaifexTick if import fails
    class TaifexTick(dict):  # Simplified fallback
        @staticmethod
        def model_validate(data_dict):  # Mock Pydantic v2's model_validate
            return TaifexTick(data_dict)

        def model_dump(self):  # Mock Pydantic v2's model_dump
            return self

    # Fallback: Define a simplified DatabaseManager
    class DatabaseManager:
        def __init__(self, db_path):
            self.db_path = db_path
            self.conn = None
            self.logger = logging.getLogger("FallbackDatabaseManager")

        def __enter__(self):
            self.logger.info(f"Using fallback DatabaseManager for {self.db_path}")
            if os.path.exists(self.db_path):
                self.logger.debug(
                    f"Fallback: Removing existing DB file: {self.db_path}"
                )
                os.remove(self.db_path)
            if os.path.exists(f"{self.db_path}.wal"):
                self.logger.debug(
                    f"Fallback: Removing existing WAL file: {self.db_path}.wal"
                )
                os.remove(f"{self.db_path}.wal")
            self.conn = duckdb.connect(self.db_path)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.conn:
                self.conn.close()
                self.logger.info(
                    f"Fallback DatabaseManager connection closed for {self.db_path}"
                )

        def create_table_if_not_exists(
            self, table_name: str, model_schema_ignored
        ):  # schema ignored in fallback
            if not self.conn:
                return  # noqa: E701
            # Fallback schema based on expected DataFrame structure
            # This must align with the DataFrame created from simulated_ticks_data
            fallback_schema_sql = """
                CREATE TABLE IF NOT EXISTS {} (
                    timestamp TIMESTAMP,
                    price DOUBLE,
                    volume BIGINT,
                    instrument VARCHAR,
                    tick_type VARCHAR
                )
            """.format(
                table_name
            )  # Use format for duckdb compatibility if f-string causes issues
            self.conn.execute(fallback_schema_sql)
            self.logger.info(
                f"Fallback: Ensured table '{table_name}' with predefined schema."
            )

        def insert_ticks(self, table_name: str, ticks_input: list | pd.DataFrame):
            if not self.conn:
                return  # noqa: E701

            if isinstance(ticks_input, pd.DataFrame):
                ticks_df = ticks_input
            elif isinstance(ticks_input, list) and all(
                isinstance(t, dict) for t in ticks_input
            ):
                ticks_df = pd.DataFrame(ticks_input)
            elif isinstance(ticks_input, list) and all(
                hasattr(t, "model_dump") for t in ticks_input
            ):  # Pydantic-like objects
                ticks_df = pd.DataFrame([t.model_dump() for t in ticks_input])
            else:
                self.logger.error("Fallback: Unsupported type for insert_ticks.")
                return

            if not ticks_df.empty:
                # Ensure column types are compatible with DuckDB table
                # Convert timestamp to datetime if it's not (e.g. from Pydantic's datetime)
                if "timestamp" in ticks_df.columns:
                    ticks_df["timestamp"] = pd.to_datetime(ticks_df["timestamp"])

                self.conn.register("ticks_df_temp_view", ticks_df)
                self.conn.execute(
                    f"INSERT INTO {table_name} SELECT * FROM ticks_df_temp_view"
                )
                self.conn.unregister("ticks_df_temp_view")
                self.logger.info(
                    f"Fallback: Inserted {len(ticks_df)} records into '{table_name}'."
                )
            else:
                self.logger.info("Fallback: No data to insert.")


class LoadRawDataFromWarehouseStep(BaseETLStep):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def execute(self, data: pd.DataFrame | None = None, **kwargs) -> pd.DataFrame:
        ticker = kwargs.get("ticker")

        # --- [臨時修復] ---
        # 如果沒有提供 ticker，我們假設這是一個通用管線，並載入一個預設的、廣泛的數據集。
        # 這是為了讓 P1, P2, P3 能夠在沒有特定 ticker 的情況下運行。
        if not ticker:
            self.logger.info("未提供 ticker，載入通用數據集...")
            # 模擬一個包含多個 tickers 的通用數據集
            dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=100))
            df1 = pd.DataFrame({
                "date": dates, "symbol": "SPY",
                "open": [300 + i for i in range(100)], "high": [305 + i for i in range(100)],
                "low": [295 + i for i in range(100)], "close": [302 + i for i in range(100)],
                "volume": [10000000 + i * 10000 for i in range(100)],
            })
            df2 = pd.DataFrame({
                "date": dates, "symbol": "QQQ",
                "open": [200 + i for i in range(100)], "high": [205 + i for i in range(100)],
                "low": [195 + i for i in range(100)], "close": [202 + i for i in range(100)],
                "volume": [15000000 + i * 12000 for i in range(100)],
            })
            return pd.concat([df1, df2], ignore_index=True)

        self.logger.info(f"正在為資產 {ticker} 載入原始數據...")
        # 模擬返回一個包含虛擬數據的 DataFrame
        date_range = pd.to_datetime(
            pd.date_range(start="2022-01-01", periods=300, freq="D")
        )
        open_prices = np.random.uniform(90, 110, size=300)
        df = pd.DataFrame({
            "open": open_prices,
            "high": open_prices + np.random.uniform(0, 5, size=300),
            "low": open_prices - np.random.uniform(0, 5, size=300),
            "close": open_prices + np.random.uniform(-2, 2, size=300),
            "volume": np.random.randint(100000, 500000, size=300),
        }, index=date_range)
        df.columns = [col.lower() for col in df.columns]
        return df

class TaifexTickLoaderStep(BaseETLStep):
    def __init__(
        self,
        db_path: str = "market_data_loader_step.duckdb",
        table_name: str = "bronze_taifex_ticks_loader_step",
    ):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.db_path = db_path
        self.table_name = table_name
        self.logger.info(
            f"TaifexTickLoaderStep initialized. DB: '{self.db_path}', Table: '{self.table_name}'. Imported app deps: {IMPORTED_APP_DEPS}"
        )

    def execute(self, data: pd.DataFrame | None = None, **kwargs) -> pd.DataFrame | None:
        self.logger.info(
            f"Executing TaifexTickLoaderStep. Output to table '{self.table_name}' in db '{self.db_path}'."
        )

        simulated_ticks_data_dicts = [
            {
                "timestamp": datetime.datetime(2023, 10, 1, 9, 0, 0, 100000),
                "price": 16500.0,
                "volume": 2,
                "instrument": "TXF202310",
                "tick_type": "Trade",
            },
            {
                "timestamp": datetime.datetime(2023, 10, 1, 9, 0, 1, 200000),
                "price": 16501.0,
                "volume": 3,
                "instrument": "TXF202310",
                "tick_type": "Trade",
            },
            {
                "timestamp": datetime.datetime(2023, 10, 1, 9, 0, 2, 300000),
                "price": 16500.5,
                "volume": 1,
                "instrument": "TXF202310",
                "tick_type": "Trade",
            },
        ]

        ticks_df = pd.DataFrame(simulated_ticks_data_dicts)
        ticks_df["timestamp"] = pd.to_datetime(ticks_df["timestamp"])
        # Ensure 'volume' is integer as per fallback schema if it was float from DataFrame creation
        ticks_df["volume"] = ticks_df["volume"].astype("int64")

        self.logger.info(
            f"Successfully simulated fetching {len(ticks_df)} Tick records."
        )

        try:
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
                self.logger.info(f"Created directory for database: {db_dir}")

            with DatabaseManager(db_path=self.db_path) as db_manager:
                if IMPORTED_APP_DEPS:
                    # Using original DatabaseManager, expects Pydantic model for schema and list of Pydantic objects
                    db_manager.create_table_if_not_exists(self.table_name, TaifexTick)
                    simulated_pydantic_ticks = [
                        TaifexTick.model_validate(row)
                        for row in simulated_ticks_data_dicts
                    ]
                    db_manager.insert_ticks(self.table_name, simulated_pydantic_ticks)
                    self.logger.info(
                        f"Used original DatabaseManager. Wrote {len(simulated_pydantic_ticks)} records."
                    )
                else:
                    # Using fallback DatabaseManager, expects table name and DataFrame (or list of dicts)
                    db_manager.create_table_if_not_exists(
                        self.table_name, None
                    )  # Schema ignored in fallback
                    db_manager.insert_ticks(
                        self.table_name, ticks_df.to_dict("records")
                    )  # Pass list of dicts to fallback
                    self.logger.info(
                        f"Used fallback DatabaseManager. Wrote {len(ticks_df)} records."
                    )

        except Exception as e:
            self.logger.error(
                f"Error during database operation in TaifexTickLoaderStep: {e}",
                exc_info=True,
            )
            # Decide if this error should halt the pipeline or just log and return the DataFrame
            # For now, log and return DataFrame to allow pipeline to continue if DB write is not critical for next step

        self.logger.info("TaifexTickLoaderStep execution finished.")
        return ticks_df


class LoadStockDataStep(BaseStep):
    """
    一個 Pipeline 步驟，用於從 yfinance 加載股票數據。
    """

    def __init__(self, symbols: List[str], client_factory: ClientFactory):
        """
        初始化步驟。

        :param symbols: 要加載的股票代號列表。
        :param client_factory: 客戶端工廠。
        """
        self.symbols = symbols
        self.yfinance_client = client_factory.get_client('yfinance')
        self.logger = logging.getLogger(self.__class__.__name__)

    async def run(self, data: Any = None, context: Dict[str, Any] = None) -> pd.DataFrame:
        """
        執行數據加載。

        :param data: 上一步的輸出 (在此被忽略)。
        :param context: Pipeline 的共享上下文。
        :return: 包含所有股票數據的單一 DataFrame。
        """
        self.logger.info(f"開始從 yfinance 加載股票數據，目標: {self.symbols}")
        all_data = []

        for symbol in self.symbols:
            try:
                self.logger.debug(f"正在為 {symbol} 獲取數據...")
                stock_data = await self.yfinance_client.fetch_data(symbol, period="1y") # 載入一年數據作為範例
                if stock_data.empty:
                    self.logger.warning(f"無法為 {symbol} 獲取數據，可能該代號無效或無數據。")
                    continue

                stock_data['symbol'] = symbol
                all_data.append(stock_data)
                self.logger.debug(f"成功加載 {symbol} 的 {len(stock_data)} 筆數據。")

            except Exception as e:
                self.logger.error(f"加載 {symbol} 數據時出錯: {e}", exc_info=True)

        if not all_data:
            self.logger.error("未能加載任何股票數據。")
            # 返回一個空的 DataFrame，下游步驟應能處理這種情況
            return pd.DataFrame()

        # 將所有數據合併成一個大的 DataFrame
        combined_df = pd.concat(all_data)
        self.logger.info(f"成功加載並合併了 {len(all_data)} 支股票的數據。")

        # --- [修復] ---
        # 將所有列名標準化為小寫，以避免與數據庫模式的大小寫不匹配問題
        combined_df.columns = [col.lower() for col in combined_df.columns]

        # 重置索引，因為 yfinance 返回的數據中，日期是索引
        combined_df = combined_df.reset_index()

        return combined_df


class LoadCryptoDataStep(BaseStep):
    """
    一個 Pipeline 步驟，用於從 yfinance 加載加密貨幣數據。
    """

    def __init__(self, symbols: List[str], client_factory: ClientFactory):
        """
        初始化步驟。

        :param symbols: 要加載的加密貨幣代號列表 (例如: ['BTC-USD', 'ETH-USD'])。
        :param client_factory: 客戶端工廠。
        """
        self.symbols = symbols
        self.yfinance_client = client_factory.get_client('yfinance')
        self.logger = logging.getLogger(self.__class__.__name__)

    async def run(self, data: Any = None, context: Dict[str, Any] = None) -> pd.DataFrame:
        """
        執行數據加載。

        :param data: 上一步的輸出 (在此被忽略)。
        :param context: Pipeline 的共享上下文。
        :return: 包含所有加密貨幣數據的單一 DataFrame。
        """
        self.logger.info(f"開始從 yfinance 加載加密貨幣數據，目標: {self.symbols}")
        all_data = []

        for symbol in self.symbols:
            try:
                self.logger.debug(f"正在為 {symbol} 獲取數據...")
                # 為加密貨幣獲取更長的歷史數據以進行相關性計算
                crypto_data = await self.yfinance_client.fetch_data(symbol, period="2y")
                if crypto_data.empty:
                    self.logger.warning(f"無法為 {symbol} 獲取數據，可能該代號無效或無數據。")
                    continue

                crypto_data['symbol'] = symbol
                all_data.append(crypto_data)
                self.logger.debug(f"成功加載 {symbol} 的 {len(crypto_data)} 筆數據。")

            except Exception as e:
                self.logger.error(f"加載 {symbol} 數據時出錯: {e}", exc_info=True)

        if not all_data:
            self.logger.error("未能加載任何加密貨幣數據。")
            return pd.DataFrame()

        combined_df = pd.concat(all_data)
        self.logger.info(f"成功加載並合併了 {len(all_data)} 種加密貨幣的數據。")

        # --- [修復] ---
        # 將所有列名標準化為小寫，以避免與數據庫模式的大小寫不匹配問題
        combined_df.columns = [col.lower() for col in combined_df.columns]

        # 重置索引，因為 yfinance 返回的數據中，日期是索引
        combined_df = combined_df.reset_index()

        return combined_df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    test_db_path = "temp_test_tick_loader_step.duckdb"
    # Clean up before test
    if os.path.exists(test_db_path):
        os.remove(test_db_path)  # noqa: E701
    if os.path.exists(f"{test_db_path}.wal"):
        os.remove(f"{test_db_path}.wal")  # noqa: E701

    loader_step = TaifexTickLoaderStep(db_path=test_db_path, table_name="test_ticks")
    loaded_data = loader_step.execute()

    if loaded_data is not None:
        print("\n--- Loaded Data (DataFrame) ---")
        print(loaded_data)
        print(f"\nData types:\n{loaded_data.dtypes}")

        if os.path.exists(test_db_path):
            print(
                f"\n--- Verifying data in database '{test_db_path}', table '{loader_step.table_name}' ---"
            )
            try:
                with duckdb.connect(test_db_path) as conn:
                    count = conn.execute(
                        f"SELECT COUNT(*) FROM {loader_step.table_name}"
                    ).fetchone()[0]
                    print(f"Number of records in table: {count}")
                    assert count == len(
                        loaded_data
                    ), "Mismatch in DB count and DataFrame length"
                    if count > 0:
                        sample_records = conn.execute(
                            f"SELECT * FROM {loader_step.table_name} LIMIT 3"
                        ).df()
                        print("Sample records from DB:")
                        print(sample_records)
            except Exception as e:
                print(f"Error verifying data in DB: {e}")
    else:
        print("Loader step did not return data.")

    # Clean up after test
    # if os.path.exists(test_db_path): os.remove(test_db_path)
    # if os.path.exists(f"{test_db_path}.wal"): os.remove(f"{test_db_path}.wal")
    # print(f"\nCleaned up test database: {test_db_path}")


================================================================================
### FILE: prometheus/core/pipelines/steps/normalize_columns_step.py
================================================================================

# src/prometheus/core/pipelines/steps/normalize_columns_step.py

import pandas as pd
from typing import Dict, Any
import logging

from prometheus.core.pipelines.base_step import BaseStep

logger = logging.getLogger(__name__)

class NormalizeColumnsStep(BaseStep):
    """
    一個 Pipeline 步驟，用於將 DataFrame 的所有欄位名稱標準化為小寫。
    它同時實現了 run 和 execute 方法，以兼容不同的 Pipeline 設計。
    """

    def __init__(self):
        """
        初始化步驟。
        """
        pass

    def _normalize(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        執行標準化的核心邏輯。
        """
        if not isinstance(data, pd.DataFrame) or data.empty:
            logger.warning("輸入的數據不是一個有效的 DataFrame 或為空，跳過標準化。")
            return data

        logger.info("正在將所有欄位名稱轉換為小寫...")
        original_columns = data.columns.tolist()
        data.columns = [col.lower() for col in original_columns]
        new_columns = data.columns.tolist()

        if original_columns != new_columns:
            logger.info(f"欄位已標準化：從 {original_columns} -> {new_columns}")
        else:
            logger.info("所有欄位名稱已經是小寫，無需更改。")

        return data

    async def run(self, data: pd.DataFrame, context: Dict[str, Any] = None) -> pd.DataFrame:
        """
        異步執行欄位名稱標準化 (兼容 BaseStep)。
        """
        return self._normalize(data)

    def execute(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        同步執行欄位名稱標準化 (兼容 BaseETLStep)。
        """
        return self._normalize(data)


================================================================================
### FILE: prometheus/core/pipelines/steps/savers.py
================================================================================

import pandas as pd
from prometheus.core.pipelines.base_step import BaseETLStep, BaseStep
from prometheus.core.logging.log_manager import LogManager
import duckdb
import os
from typing import Dict, Any
from src.prometheus.core.db.db_manager import DBManager


class SaveFactorsToWarehouseStep(BaseETLStep):
    def __init__(self, table_name: str, db_path: str = "data/analytics_warehouse/factors.duckdb"):
        self.table_name = table_name
        self.db_path = db_path
        self.logger = LogManager.get_instance().get_logger(self.__class__.__name__)

        # 確保數據庫目錄存在
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)

    def execute(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        將因子儲存到數據倉庫。
        """
        ticker = kwargs.get("ticker")
        if not ticker:
            self.logger.warning("在上下文中找不到 ticker，無法儲存。")
            return data

        self.logger.info(f"正在將因子儲存到數據庫 '{self.db_path}' 的表格 '{self.table_name}' for ticker {ticker}...")
        if data.empty:
            self.logger.warning("數據為空，沒有因子可以儲存。")
        else:
            try:
                with duckdb.connect(self.db_path) as con:
                    # Add ticker column
                    data_to_save = data.copy()
                    data_to_save['ticker'] = ticker

                    # Check if table exists
                    res = con.execute(f"SELECT table_name FROM information_schema.tables WHERE table_name = '{self.table_name}'").fetchone()
                    if res: # Table exists, so append
                        # Remove existing data for the same ticker to avoid duplicates
                        con.execute(f"DELETE FROM {self.table_name} WHERE ticker = '{ticker}'")
                        con.register('factors_df', data_to_save.reset_index())
                        con.execute(f"INSERT INTO {self.table_name} SELECT * FROM factors_df")
                    else: # Table does not exist, so create
                        con.register('factors_df', data_to_save.reset_index())
                        con.execute(f"CREATE TABLE {self.table_name} AS SELECT * FROM factors_df")

                    self.logger.info(f"成功將 {len(data)} 筆因子儲存到 '{self.table_name}' for ticker {ticker}。")
            except Exception as e:
                self.logger.error(f"儲存因子時發生錯誤: {e}", exc_info=True)
                raise
        return data


class SaveToWarehouseStep(BaseStep):
    """
    一個 Pipeline 步驟，用於將 DataFrame 儲存到資料倉儲。
    """

    def __init__(self, db_manager: DBManager, table_name: str):
        """
        初始化步驟。

        :param db_manager: 資料庫管理器。
        :param table_name: 要儲存的目標表格名稱。
        """
        self.db_manager = db_manager
        self.table_name = table_name
        self.logger = LogManager.get_instance().get_logger(self.__class__.__name__)

    async def run(self, data: pd.DataFrame, context: Dict[str, Any]) -> pd.DataFrame:
        """
        將 DataFrame 儲存到資料倉儲。

        :param data: 要儲存的 DataFrame。
        :param context: Pipeline 的共享上下文。
        :return: 未經修改的原始 DataFrame。
        """
        if data.empty:
            self.logger.warning("數據為空，沒有可以儲存的內容。")
            return data

        try:
            self.logger.info(f"正在將 {len(data)} 筆數據儲存到表格 '{self.table_name}'...")
            self.db_manager.save_data(data, self.table_name)
            self.logger.info("數據儲存成功。")
        except Exception as e:
            self.logger.error(f"儲存數據到倉儲時發生錯誤: {e}", exc_info=True)
            raise

        return data


================================================================================
### FILE: prometheus/core/pipelines/steps/splitters.py
================================================================================

# src/prometheus/core/pipelines/steps/splitters.py

import pandas as pd
import logging
from typing import Dict, Any, List

from src.prometheus.core.pipelines.base_step import BaseStep

logger = logging.getLogger(__name__)


class GroupBySymbolStep(BaseStep):
    """
    一個 Pipeline 步驟，用於將 DataFrame 按 'symbol' 欄位分組。
    """

    async def run(self, data: pd.DataFrame, context: Dict[str, Any]):
        """
        將輸入的 DataFrame 按 'symbol' 分組。

        :param data: 包含 'symbol' 欄位的 DataFrame。
        :param context: Pipeline 的共享上下文。
        :return: 一個 DataFrame 的列表，每個 DataFrame 對應一個 symbol。
        """
        logger.info("正在執行 GroupBySymbolStep...")

        if 'symbol' not in data.columns:
            raise ValueError("輸入的 DataFrame 必須包含 'symbol' 欄位。")

        grouped = data.groupby('symbol')

        logger.info(f"成功將數據分為 {len(grouped)} 組。")
        for _, group in grouped:
            yield group


================================================================================
### FILE: prometheus/core/pipelines/steps/verifiers.py
================================================================================

# 檔案: src/prometheus/pipelines/steps/verifiers.py
# --- 抽象程式碼草圖 ---

# 概念：
# 一個用於在管線中驗證 DataFrame 完整性的步驟。

import pandas as pd
from prometheus.core.pipelines.base_step import BaseETLStep
from prometheus.core.logging.log_manager import LogManager

class VerifyDataFrameNotEmptyStep(BaseETLStep):
    def __init__(self):
        self.logger = LogManager.get_instance().get_logger(self.__class__.__name__)

    def execute(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        執行驗證。如果 DataFrame 為空，則拋出致命錯誤。
        """
        self.logger.info("正在進行記憶體驗證...")

        if data.empty:
            # 核心邏輯：如果數據為空，則主動拋出錯誤，中斷管線
            error_message = "管線中斷：前一環節產出的數據為空！"
            self.logger.error(error_message)
            raise ValueError(error_message)

        self.logger.debug("記憶體驗證通過，數據完整。")
        return data # 將未經修改的數據傳遞給下一步


================================================================================
### FILE: prometheus/core/queue/__init__.py
================================================================================



================================================================================
### FILE: prometheus/core/queue/sqlite_queue.py
================================================================================

import json
import sqlite3
import time
import abc
from pathlib import Path
from typing import Any, Optional

import logging

# 為此模組創建一個標準的 logger，而不是依賴 LogManager
# 這使得模組更加獨立和可重用
logger = logging.getLogger(__name__)


class BaseQueue(abc.ABC):
    """
    任務佇列抽象基底類別。
    定義了所有佇列實現都必須提供的標準介面。
    """

    @abc.abstractmethod
    def put(self, task_data: dict) -> None:
        """
        將一個新任務放入佇列。

        Args:
            task_data (dict): 要執行的任務內容，必須是可序列化為 JSON 的字典。
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get(self) -> dict | None:
        """
        從佇列中取出一個待處理的任務。
        此操作應具備原子性，防止多個工作者取得同一個任務。

        Returns:
            dict | None: 如果佇列中有任務，則返回任務內容；否則返回 None。
        """
        raise NotImplementedError

    @abc.abstractmethod
    def task_done(self, task_id: any) -> None:
        """
        標記一個任務已完成。

        Args:
            task_id (any): 已完成任務的唯一識別碼。
        """
        raise NotImplementedError

    @abc.abstractmethod
    def qsize(self) -> int:
        """
        返回佇列中待處理任務的數量。

        Returns:
            int: 待處理任務的數量。
        """
        raise NotImplementedError


class SQLiteQueue(BaseQueue):
    """
    一個基於 SQLite 的、支持阻塞和毒丸關閉的持久化佇列。
    """

    def __init__(self, db_path: str | Path, table_name: str = "queue"):
        self.db_path = Path(db_path)
        self.table_name = table_name
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # 允許多執行緒共享同一個連線，並增加超時
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=10)
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def put(self, item: Any):
        """將一個項目放入佇列。"""
        with self.conn:
            self.conn.execute(
                f"INSERT INTO {self.table_name} (item) VALUES (?)", (json.dumps(item),)
            )

    def get(self, block: bool = True, timeout: Optional[float] = None) -> Optional[Any]:
        """
        從佇列中取出一個項目。
        如果 block=True，則會等待直到有項目可用。
        """
        start_time = time.time()
        while True:
            try:
                with self.conn:
                    cursor = self.conn.cursor()
                    cursor.execute(
                        f"SELECT id, item FROM {self.table_name} ORDER BY id LIMIT 1"
                    )
                    row = cursor.fetchone()

                    if row:
                        item_id, item_json = row
                        cursor.execute(
                            f"DELETE FROM {self.table_name} WHERE id = ?", (item_id,)
                        )
                        return json.loads(item_json)
            except sqlite3.Error as e:
                # 如果發生資料庫錯誤，短暫等待後重試
                logger.error(f"從佇列讀取時發生資料庫錯誤: {e}", exc_info=True)
                time.sleep(0.1)

            if not block:
                return None

            if timeout and (time.time() - start_time) > timeout:
                return None

            time.sleep(0.1)  # 避免過於頻繁地查詢

    def qsize(self) -> int:
        """返回佇列中的項目數量。"""
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            return cursor.fetchone()[0]

    def task_done(self, task_id: any) -> None:
        """在這個實作中，get() 已經是原子性的，所以這個方法可以留空。"""
        pass

    def close(self):
        """關閉資料庫連線。"""
        if self.conn:
            self.conn.close()
            self.conn = None


================================================================================
### FILE: prometheus/core/utils/__init__.py
================================================================================



================================================================================
### FILE: prometheus/core/utils/helpers.py
================================================================================

# -*- coding: utf-8 -*-
"""
核心工具模組：中央快取引擎 (v2.0 - 永久保存版)

功能：
- 提供一個全專案共用的、配置好快取策略的 requests Session 物件。
- 預設永久保存所有成功獲取的數據。
- 支援透過上下文管理器手動禁用快取，以實現強制刷新。
"""

from contextlib import contextmanager

try:
    import requests_cache
except ImportError:
    requests_cache = None
from prometheus.core.logging.log_manager import LogManager

logger = LogManager.get_instance().get_logger("Helpers")

# 定義快取檔案的路徑與名稱
CACHE_NAME = ".financial_data_cache"
# 關鍵變更：將過期時間設定為 None，代表「永不過期」
# 數據一經寫入，除非手動清理快取檔案，否則將永久保存。
CACHE_EXPIRE_AFTER = None


def get_cached_session() -> requests_cache.CachedSession:
    """
    獲取一個配置好的、帶有永久快取的 Session 物件。

    Returns:
        requests_cache.CachedSession: 配置完成的快取 Session。
    """
    return requests_cache.CachedSession(
        cache_name=CACHE_NAME,
        backend="sqlite",
        expire_after=CACHE_EXPIRE_AFTER,
        allowable_methods=["GET", "POST"],
    )


@contextmanager
def temporary_disabled_cache(session: requests_cache.CachedSession):
    """
    一個上下文管理器，用於暫時禁用給定 Session 的快取功能。
    這對於實現「強制刷新」功能至關重要。

    Args:
        session (requests_cache.CachedSession): 需要暫時禁用快取的 Session。
    """
    with session.cache_disabled():
        yield


if __name__ == "__main__":
    # (自我測試代碼維持不變，用於驗證新策略)
    logger.info("--- [自我測試] 正在驗證中央快取引擎 (v2.0 永久保存模式) ---")
    test_url = "https://httpbin.org/delay/2"
    session = get_cached_session()
    logger.info("正在進行第一次請求 (應有 2 秒延遲)...")
    import time

    start_time = time.time()
    response1 = session.get(test_url)
    end_time = time.time()
    logger.info(
        f"第一次請求完成。耗時: {end_time - start_time:.2f} 秒。From Cache: {response1.from_cache}"
    )

    logger.info("\n正在進行第二次請求 (應立即完成)...")
    start_time = time.time()
    response2 = session.get(test_url)
    end_time = time.time()
    logger.info(
        f"第二次請求完成。耗時: {end_time - start_time:.2f} 秒。From Cache: {response2.from_cache}"
    )

    logger.info("\n正在進行強制刷新請求 (應再次有 2 秒延遲)...")
    start_time = time.time()
    with temporary_disabled_cache(session):
        response3 = session.get(test_url)
    end_time = time.time()
    logger.info(
        f"強制刷新請求完成。耗時: {end_time - start_time:.2f} 秒。From Cache: {response3.from_cache}"
    )

    logger.info("\n--- [自我測試] 完成 ---")
    session.cache.clear()
    logger.info("測試快取已清理。")


from pathlib import Path
from typing import Tuple

import pandas as pd


def load_ohlcv_data(
    file_path: Path, split_ratio: float = 0.7
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    從 CSV 檔案加載 OHLCV 數據，並將其分割為樣本內和樣本外數據集。

    :param file_path: CSV 檔案的路徑。
    :param split_ratio: 樣本內數據所佔的比例 (例如 0.7 代表 70%)。
    :return: 一個包含 (in_sample_df, out_of_sample_df) 的元組。
    """
    if not file_path.exists():
        raise FileNotFoundError(f"數據檔案不存在: {file_path}")

    # 根據作戰手冊，索引應為 'Date' 且欄位名稱應為小寫
    df = pd.read_csv(file_path, index_col="Date", parse_dates=True)
    df.columns = [col.lower() for col in df.columns]

    # 根據比例計算分割點
    split_point = int(len(df) * split_ratio)

    in_sample_df = df.iloc[:split_point]
    out_of_sample_df = df.iloc[split_point:]

    logger.info(
        f"[DataLoader] 數據已分割：樣本內 {len(in_sample_df)} 筆, 樣本外 {len(out_of_sample_df)} 筆。"
    )

    return in_sample_df, out_of_sample_df


import zipfile
from typing import Dict, Optional


def prospect_file_content(file_bytes: bytes) -> Dict[str, str]:
    """嘗試解碼並讀取第一行(標頭)。"""
    for encoding in ["ms950", "big5", "utf-8", "utf-8-sig"]:
        try:
            content = file_bytes.decode(encoding)
            header = content.splitlines()[0].strip()
            return {"status": "success", "encoding": encoding, "header": header}
        except (UnicodeDecodeError, IndexError):
            continue
    return {"status": "failure", "error": "無法解碼或檔案為空"}


def read_file_content(file_path: str) -> Optional[bytes]:
    """讀取檔案內容，支援 ZIP 檔案。"""
    if zipfile.is_zipfile(file_path):
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                for member_name in zf.namelist():
                    if member_name.lower().endswith((".csv", ".txt")):
                        return zf.read(member_name)
        except zipfile.BadZipFile:
            return None
    elif file_path.lower().endswith((".csv", ".txt")):
        with open(file_path, "rb") as f:
            return f.read()
    return None


def correct_path():
    pass


================================================================================
### FILE: prometheus/entrypoints/__init__.py
================================================================================

# -*- coding: utf-8 -*-
# 使得 apps 可以被視為一個套件


================================================================================
### FILE: prometheus/entrypoints/ai_analyst_app.py
================================================================================

# 檔案: src/prometheus/entrypoints/ai_analyst_app.py
import json
from pathlib import Path
import pandas as pd
import vectorbt as vbt

# --- 檔案路徑 ---
DATA_DIR = Path("data")
REPORTS_DIR = DATA_DIR / "reports"
HALL_OF_FAME_PATH = DATA_DIR / "hall_of_fame.json"
OHLCV_DATA_PATH = DATA_DIR / "ohlcv_data.csv"
EQUITY_CURVE_PATH = REPORTS_DIR / "equity_curve.png"
ANALYSIS_REPORT_PATH = REPORTS_DIR / "analysis_report.md"

# --- 模擬 Gemini 客戶端 ---
class MockGeminiClient:
    def generate_report(self, prompt: str) -> str:
        print("\n[AI-Analyst] 正在調用模擬的 Gemini API...")
        # 在真實場景中，這裡會是 API 呼叫
        # 為了演示，我們返回一個基於提示的簡單模板化回應
        return """
**AI 洞察**

*   **行為模式分析**: 根據回測數據，此策略似乎在市場呈現溫和上漲趨勢時表現最佳。它利用短期動量進場，並在相對強弱指標（RSI）顯示超買時退出，這是一種典型的「趨勢跟隨」與「均值回歸」的混合策略。

*   **潛在風險**: 該策略在橫盤震盪市場中可能會因為頻繁的進出場而產生較多交易成本，從而侵蝕利潤。此外，在市場出現劇烈反轉時，基於RSI的出場信號可能滯後，導致較大的回撤。

*   **建議**: 建議在實際部署前，對策略的參數進行更細緻的優化，特別是針對不同的市場波動率進行調整。同時，可以考慮加入止損訂單來限制最大虧損。
"""

def get_best_strategy():
    """從名人堂讀取最佳策略。"""
    if not HALL_OF_FAME_PATH.exists():
        print(f"[AI-Analyst] 錯誤: 名人堂檔案不存在於 {HALL_OF_FAME_PATH}")
        return None
    with open(HALL_OF_FAME_PATH, "r") as f:
        return json.load(f)

def run_backtest(strategy_genome, price_data):
    """使用 vectorbt 執行回測。"""
    # 這裡我們需要一個策略函數來解釋基因體
    # 為了簡化，我們假設基因體直接對應到某個指標的參數
    # 例如：基因體的前兩個值是快慢均線的窗口
    fast_ma_window = int(strategy_genome[0] * 10) + 5  # 示例：窗口範圍 5-15
    slow_ma_window = int(strategy_genome[1] * 30) + 20 # 示例：窗口範圍 20-50

    fast_ma = vbt.MA.run(price_data, fast_ma_window)
    slow_ma = vbt.MA.run(price_data, slow_ma_window)

    entries = fast_ma.ma_crossed_above(slow_ma)
    exits = fast_ma.ma_crossed_below(slow_ma)

    portfolio = vbt.Portfolio.from_signals(price_data, entries, exits, init_cash=100000)
    return portfolio

def generate_markdown_report(stats, equity_curve_path):
    """生成 Markdown 格式的分析報告。"""

    # 從 stats Series 中提取指標
    total_return = stats['Total Return [%]']
    max_drawdown = stats['Max Drawdown [%]']
    sharpe_ratio = stats['Sharpe Ratio']
    calmar_ratio = stats['Calmar Ratio']

    # 模擬 Gemini 客戶端生成 AI 洞察
    client = MockGeminiClient()
    # 為了簡化，我們傳遞一個固定的 prompt
    ai_insights = client.generate_report("請分析此策略")

    report_content = f"""
# AI 首席分析師報告

## 策略概述

本報告旨在分析從演化計算中脫穎而出的最佳交易策略。我們將透過回測來評估其歷史表現，並提供由 AI 生成的洞察。

## 核心績效指標

| 指標           | 數值                  |
| -------------- | --------------------- |
| 總回報 (%)     | {total_return:.2f}    |
| 最大回撤 (%)   | {max_drawdown:.2f}    |
| 夏普比率       | {sharpe_ratio:.2f}    |
| 卡瑪比率       | {calmar_ratio:.2f}    |

## 權益曲線

![權益曲線]({equity_curve_path.name})

{ai_insights}
"""
    return report_content.strip()


def ai_analyst_job():
    """AI 分析師的主工作流程。"""
    print("[AI-Analyst] AI 首席分析師已啟動。")

    # 1. 確保報告目錄存在
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # 2. 讀取最佳策略和價格數據
    strategy_data = get_best_strategy()
    if not strategy_data:
        return

    if not OHLCV_DATA_PATH.exists():
        print(f"[AI-Analyst] 錯誤: 價格數據檔案不存在於 {OHLCV_DATA_PATH}")
        return

    price_data = pd.read_csv(OHLCV_DATA_PATH, index_col='Date', parse_dates=True)['Close']

    # 3. 執行回測
    print("[AI-Analyst] 正在對最佳策略進行回測...")
    portfolio = run_backtest(strategy_data["genome"], price_data)
    stats = portfolio.stats()

    # 4. 生成並儲存權益曲線圖
    print(f"[AI-Analyst] 正在生成權益曲線圖並儲存至 {EQUITY_CURVE_PATH}...")
    fig = portfolio.plot()
    fig.write_image(EQUITY_CURVE_PATH)

    # 5. 生成並儲存 Markdown 報告
    print(f"[AI-Analyst] 正在生成 Markdown 分析報告...")
    report_content = generate_markdown_report(stats, EQUITY_CURVE_PATH)

    try:
        with open(ANALYSIS_REPORT_PATH, "w", encoding="utf-8") as f:
            f.write(report_content)
        print("\n" + "="*20 + " 任務完成 " + "="*20)
        print(f"🎉 分析報告已成功生成！請查看: {ANALYSIS_REPORT_PATH}")
        print(f"📈 權益曲線圖已儲存！請查看: {EQUITY_CURVE_PATH}")
        print("="*52)
    except Exception as e:
        print(f"!!!!!! [AI-Analyst] 儲存報告失敗: {e} !!!!!!")

if __name__ == "__main__":
    ai_analyst_job()


================================================================================
### FILE: prometheus/entrypoints/backtest_worker_app.py
================================================================================

import time

from prometheus.core.queue.sqlite_queue import SQLiteQueue
from prometheus.services.backtesting_service import BacktestingService
from prometheus.core.logging.log_manager import LogManager

POISON_PILL = "STOP_WORKING"


def backtest_worker_loop(
    task_queue: SQLiteQueue, results_queue: SQLiteQueue, price_data, worker_id: int
):
    """
    一個遵守鋼鐵契約的回測工作者：永不放棄，直到收到毒丸。
    """
    logger = LogManager.get_instance().get_logger(f"Backtest-Worker-{worker_id}")
    logger.info("回測工作者已啟動，正在等待任務...")
    backtester = BacktestingService(price_data)

    while True:
        try:
            task = task_queue.get(block=True)

            if task == POISON_PILL:
                logger.info("收到關閉信號，正在優雅退出...")
                break

            if not isinstance(task, (list, tuple)) or len(task) != 2:
                logger.warning(f"收到無效任務格式，已忽略: {task}")
                continue

            item_id, genome_task = task

            if not isinstance(genome_task, dict):
                logger.warning(f"收到無效的 genome_task 格式，已忽略: {genome_task}")
                continue

            params = genome_task.get("params", {})
            logger.info(f"正在回測任務 #{item_id}...")
            logger.debug(f"任務 #{item_id} 的基因: {params}")

            try:
                # 【萬象引擎】調用新的回測方法
                report = backtester.run_backtest(genome=params)
            except Exception as e:
                logger.error(f"回測函數內部出錯: {e}", exc_info=True)
                report = {"error": str(e), "is_valid": False}

            result_payload = {
                "genome_id": genome_task.get("id"),
                "params": params,
                "report": report,
                "processed_by": worker_id,
            }
            results_queue.put(result_payload)
            logger.debug(f"任務 #{item_id} 回測完成。")

        except Exception as e:
            logger.error(f"處理迴圈發生嚴重錯誤: {e}", exc_info=True)
            time.sleep(10)

    logger.info("已成功關閉。")


================================================================================
### FILE: prometheus/entrypoints/evolution_app.py
================================================================================

import json
import random
import uuid
from pathlib import Path

from deap import creator, tools

from prometheus.core.queue.sqlite_queue import SQLiteQueue
from prometheus.services.checkpoint_manager import CheckpointManager
from prometheus.services.evolution_chamber import EvolutionChamber
from prometheus.core.logging.log_manager import LogManager

# --- 演化設定 ---
POPULATION_SIZE = 10
MAX_GENERATIONS = 5
CHECKPOINT_FREQ = 2

# --- 檔案路徑 ---
HALL_OF_FAME_PATH = Path("data/hall_of_fame.json")
CHECKPOINT_PATH = Path("data/checkpoints/evolution_state.pkl")

# 初始化日誌記錄器
logger = LogManager.get_instance().get_logger("Evolution-Engine")


def evolution_loop(
    task_queue: SQLiteQueue,
    results_queue: SQLiteQueue,
    resume: bool = False,
    clean: bool = False,
):
    """
    智慧演化引擎 v4：整合了結構化日誌與萬象引擎。
    """
    logger.info("策略演化引擎已啟動...")
    chamber = EvolutionChamber()
    checkpoint_manager = CheckpointManager(CHECKPOINT_PATH)

    start_gen = 0
    population = None
    hall_of_fame = tools.HallOfFame(1)

    if clean:
        logger.info("--clean 模式：將進行一次全新的演化。")
        checkpoint_manager.clear_checkpoint()

    if resume:
        state = checkpoint_manager.load_checkpoint()
        if state:
            population = state["population"]
            start_gen = state["generation"] + 1
            hall_of_fame = state["hall_of_fame"]
            random.setstate(state["random_state"])
            logger.info(f"從第 {start_gen} 代恢復演化。")

    if population is None:
        logger.info("正在創建初始族群...")
        population = chamber.create_population(n=POPULATION_SIZE)

    # --- 演化主迴圈 ---
    for gen in range(start_gen, MAX_GENERATIONS):
        logger.info(f"正在處理第 {gen} 代...")

        pending_tasks = {}
        for i, individual in enumerate(population):
            task_id = str(uuid.uuid4())
            genome_task = {"id": task_id, "params": individual}
            task_queue.put((task_id, genome_task))
            pending_tasks[task_id] = individual
            logger.debug(f"已發送任務: {genome_task}")

        logger.info("等待所有回測結果...")
        evaluated_count = 0
        while evaluated_count < len(pending_tasks):
            result = results_queue.get(block=True, timeout=20)
            if result:
                if isinstance(result, tuple) and len(result) == 2:
                    _, result_payload = result
                else:
                    result_payload = result

                if not result_payload:
                    continue

                genome_id = result_payload.get("genome_id")
                if genome_id in pending_tasks:
                    individual = pending_tasks.pop(genome_id)
                    report = result_payload.get("report", {})
                    fitness = report.get("sharpe_ratio", -1.0) if report.get("is_valid") else -1.0
                    individual.fitness.values = (fitness,)
                    evaluated_count += 1
                    logger.debug(f"收到結果: {genome_id}, 適應度: {fitness:.2f} ({evaluated_count}/{len(population)})")
            else:
                logger.warning("等待結果超時，可能部分任務已丟失。")
                for task_id in pending_tasks:
                    pending_tasks[task_id].fitness.values = (-1.0,)
                    evaluated_count += 1
                break

        hall_of_fame.update(population)

        if len(hall_of_fame) > 0:
            best_ind = hall_of_fame[0]
            logger.info(f"第 {gen} 代最佳策略: 夏普比率 = {best_ind.fitness.values[0]:.2f}, 基因 = {best_ind}")

        if (gen + 1) % CHECKPOINT_FREQ == 0:
            current_state = {
                "population": population, "generation": gen,
                "hall_of_fame": hall_of_fame, "random_state": random.getstate(),
            }
            checkpoint_manager.save_checkpoint(current_state)

        if gen < MAX_GENERATIONS - 1:
            logger.info("正在產生下一代族群...")
            offspring = chamber.select_offspring(population)
            new_population = chamber.apply_mating_and_mutation(offspring)
            if len(hall_of_fame) > 0:
                new_population[0] = hall_of_fame[0]
            population = new_population

    logger.info("演化完成")
    if len(hall_of_fame) > 0:
        best_overall = hall_of_fame[0]
        logger.info(f"歷史最佳策略 (名人堂): 夏普比率 = {best_overall.fitness.values[0]:.2f}, 基因 = {best_overall}")

        try:
            HALL_OF_FAME_PATH.parent.mkdir(exist_ok=True, parents=True)
            with open(HALL_OF_FAME_PATH, "w") as f:
                fitness_data = {"sharpe_ratio": best_overall.fitness.values[0]}
                # 將 deap 個體轉換為可序列化的列表
                genome_list = list(best_overall)
                json.dump([{"params": genome_list, "fitness": fitness_data}], f, indent=4)
            logger.info(f"名人堂已儲存至: {HALL_OF_FAME_PATH}")
        except Exception as e:
            logger.error(f"儲存名人堂失敗: {e}", exc_info=True)

    logger.info("演化引擎已停止。")


================================================================================
### FILE: prometheus/entrypoints/optimizer_app.py
================================================================================

import time
from prometheus.core.logging.log_manager import LogManager
from prometheus.core.queue.sqlite_queue import SQLiteQueue
from prometheus.services.optimizer_service import OptimizerService

def optimizer_loop(task_queue: SQLiteQueue, results_queue: SQLiteQueue):
    log_manager = LogManager(session_name="optimizer_app")
    optimizer = OptimizerService()

    while True:
        log_manager.log_info("Optimizer loop running...")
        # This is a placeholder for the actual optimization logic.
        # In a real scenario, this would involve reading from the results_queue,
        # running some optimization algorithm, and putting new tasks into the task_queue.
        time.sleep(10)

if __name__ == '__main__':
    task_q = SQLiteQueue("task_queue.db")
    results_q = SQLiteQueue("results_queue.db")
    optimizer_loop(task_q, results_q)


================================================================================
### FILE: prometheus/entrypoints/query_gateway.py
================================================================================

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path

# --- 檔案路徑 ---
REPORTS_DIR = Path("data/reports")
ANALYSIS_REPORT_PATH = REPORTS_DIR / "analysis_report.md"
EQUITY_CURVE_PATH = REPORTS_DIR / "equity_curve.png"

app = FastAPI(
    title="普羅米修斯之火 - 神諭儀表板 API",
    description="提供由 AI 分析師生成的最新策略洞察報告。",
    version="1.0.0",
)

@app.get("/api/v1/reports/latest",
         summary="獲取最新分析報告",
         response_description="包含 Markdown 報告內容的 JSON 物件")
def get_latest_report():
    """
    讀取並回傳最新的 Markdown 分析報告。
    """
    if not ANALYSIS_REPORT_PATH.exists():
        raise HTTPException(status_code=404, detail="分析報告不存在。請先執行 'analyze' 指令。")

    try:
        with open(ANALYSIS_REPORT_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        return JSONResponse(content={"report_content": content})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"讀取報告時發生錯誤: {e}")

@app.get("/api/v1/reports/equity_curve.png",
         summary="獲取權益曲線圖",
         response_description="權益曲線的 PNG 圖片檔案")
def get_equity_curve():
    """
    直接提供權益曲線的圖片檔案。
    """
    if not EQUITY_CURVE_PATH.exists():
        raise HTTPException(status_code=404, detail="權益曲線圖不存在。請先執行 'analyze' 指令。")

    return FileResponse(EQUITY_CURVE_PATH, media_type="image/png")

@app.get("/")
def serve_report_at_root():
    """
    直接在根目錄提供最新的分析報告 JSON。
    """
    return get_latest_report()

def run_dashboard_service(ctx, host: str, port: int):
    """啟動 FastAPI 儀表板服務。"""
    # ctx 參數保留以符合現有 cli 結構，但在此處未使用
    print(f"INFO:     正在於 http://{host}:{port} 啟動神諭儀表板後端...")
    uvicorn.run(app, host=host, port=port, log_level="info")


================================================================================
### FILE: prometheus/entrypoints/results_projector_app.py
================================================================================

import time

from prometheus.core.queue.sqlite_queue import SQLiteQueue

# 【核心】定義一個所有工作者都認可的、明確的關閉信號
POISON_PILL = "STOP_WORKING"


def projector_loop(results_queue: SQLiteQueue):
    """
    一個遵守鋼鐵契約的結果投影器：永不放棄，直到收到毒丸。
    """
    print("[Projector] 結果投影器已啟動，正在等待結果...")

    while True:
        try:
            # 【核心改變】get() 現在會一直阻塞，直到拿到結果或毒丸
            result = results_queue.get(block=True)

            # 【核心改變】檢查是否收到了下班指令
            if result == POISON_PILL:
                print("[Projector] 收到關閉信號，正在優雅退出...")
                break  # 退出 while 迴圈

            # 簡單地打印結果，在真實應用中這裡會寫入數據庫
            print(f"[Projector] 收到結果: {result}")

        except Exception as e:
            # 即使單一結果出錯，也絕不退出，繼續等待下一個
            print(f"!!!!!! [Projector] 處理結果時發生錯誤: {e} !!!!!!")
            time.sleep(5)

    print("[Projector] 已成功關閉。")


================================================================================
### FILE: prometheus/entrypoints/validation_app.py
================================================================================

import json
from pathlib import Path

from prometheus.core.queue.sqlite_queue import SQLiteQueue
from prometheus.core.logging.log_manager import LogManager

HALL_OF_FAME_PATH = Path("data/hall_of_fame.json")
VALIDATION_REPORT_PATH = Path("data/reports/validation_report.json")
logger = LogManager.get_instance().get_logger("Validator")


def validation_loop(task_queue: SQLiteQueue, results_queue: SQLiteQueue):
    """
    驗證者的主迴圈。它只執行一次，用於驗證名人堂中的最佳策略。
    """
    logger.info("驗證者已啟動。")

    if not HALL_OF_FAME_PATH.exists():
        logger.error(f"找不到名人堂檔案 {HALL_OF_FAME_PATH}。無法進行驗證。")
        return

    try:
        with open(HALL_OF_FAME_PATH, "r") as f:
            # 【萬象引擎】名人堂現在是一個列表
            best_strategies = json.load(f)
            best_strategy = best_strategies[0]

        in_sample_params = best_strategy["params"]
        in_sample_fitness = best_strategy.get("fitness", {})
        in_sample_sharpe = in_sample_fitness.get("sharpe_ratio", "N/A")

        sharpe_to_print = (
            f"{in_sample_sharpe:.2f}"
            if isinstance(in_sample_sharpe, (int, float))
            else in_sample_sharpe
        )
        logger.info(f"已從名人堂讀取到最佳策略 (樣本內夏普: {sharpe_to_print})")

        task_id = "out_of_sample_validation"
        validation_task = {"id": task_id, "params": in_sample_params}
        task_queue.put((task_id, validation_task))
        logger.info(f"已發送樣本外回測任務: {in_sample_params}")

        logger.info("等待樣本外回測結果...")
        result = results_queue.get(block=True, timeout=60)
        _, result_payload = result

        if result_payload:
            out_of_sample_report = result_payload.get("report", {})

            report_str = "\n" + "=" * 20 + " 最終驗證報告 " + "=" * 20 + "\n"
            report_str += f"策略參數: {in_sample_params}\n"
            report_str += "-" * 55 + "\n"
            report_str += "樣本內表現 (學習區):\n"
            report_str += f"  - 夏普比率: {in_sample_sharpe:.2f}\n"
            report_str += "樣本外表現 (未知區):\n"
            report_str += f"  - 夏普比率: {out_of_sample_report.get('sharpe_ratio', 'N/A')}\n"
            report_str += f"  - 總報酬率: {out_of_sample_report.get('total_return', 'N/A')}%\n"
            report_str += f"  - 最大回撤: {out_of_sample_report.get('max_drawdown', 'N/A')}%\n"
            report_str += "=" * 55
            logger.info(report_str)

            if out_of_sample_report.get("is_valid") and out_of_sample_report.get("sharpe_ratio", -99) > 0.5:
                logger.info("結論：[通過] 策略在樣本外表現穩健，具備一定的泛化能力。")
            else:
                logger.warning("結論：[警告] 策略在樣本外表現不佳，可能存在過擬合風險。")

            VALIDATION_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(VALIDATION_REPORT_PATH, "w", encoding="utf-8") as f:
                json.dump(result_payload, f, indent=4)
            logger.info(f"驗證結果已儲存至 {VALIDATION_REPORT_PATH}")

    except Exception as e:
        logger.error(f"驗證過程中發生錯誤: {e}", exc_info=True)

    logger.info("驗證完成，即將關閉。")


================================================================================
### FILE: prometheus/models/strategy_models.py
================================================================================

# -*- coding: utf-8 -*-
"""
本模組定義了策略回測所需的核心數據契約。
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Strategy:
    """
    定義一個抽象的交易策略。

    Attributes:
        factors (List[str]): 此策略所使用的因子名稱列表。
        weights (Dict[str, float]): 各個因子的權重。
        target_asset (str): 交易的目標資產代碼，例如 'SPY'。
    """
    factors: List[str]
    weights: Dict[str, float]
    target_asset: str = 'SPY'

@dataclass
class PerformanceReport:
    """
    定義回測後的績效報告。

    Attributes:
        sharpe_ratio (float): 夏普比率。
        annualized_return (float): 年化報酬率。
        max_drawdown (float): 最大回撤。
        total_trades (int): 總交易次數。
    """
    sharpe_ratio: float = 0.0
    annualized_return: float = 0.0
    max_drawdown: float = 0.0
    total_trades: int = 0


================================================================================
### FILE: prometheus/pipelines/p4_stock_factor_generation.py
================================================================================

# src/prometheus/pipelines/p4_stock_factor_generation.py

import logging
import pandas as pd
from typing import List

from src.prometheus.core.config import config
from src.prometheus.core.clients.client_factory import ClientFactory
from src.prometheus.core.db.db_manager import DBManager
from src.prometheus.core.engines.stock_factor_engine import StockFactorEngine
from src.prometheus.core.pipelines.pipeline import Pipeline
from src.prometheus.core.pipelines.steps.loaders import LoadStockDataStep
from src.prometheus.core.pipelines.steps.savers import SaveToWarehouseStep
from src.prometheus.core.pipelines.steps.financial_steps import RunStockFactorEngineStep
from src.prometheus.core.pipelines.steps.splitters import GroupBySymbolStep

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_stock_factor_pipeline(symbols: List[str], db_manager: DBManager, client_factory: ClientFactory) -> Pipeline:
    """
    創建一個用於生成股票因子的標準化 Pipeline。

    :param symbols: 要處理的股票代號列表。
    :param db_manager: 資料庫管理器。
    :param client_factory: 客戶端工廠。
    :return: 一個配置好的 Pipeline 實例。
    """
    # 初始化股票因子引擎
    stock_factor_engine = StockFactorEngine(client_factory)

    from src.prometheus.core.pipelines.steps.normalize_columns_step import NormalizeColumnsStep
    # 定義 Pipeline 的步驟
    steps = [
        LoadStockDataStep(symbols=symbols, client_factory=client_factory),
        NormalizeColumnsStep(),
        GroupBySymbolStep(),
        RunStockFactorEngineStep(engine=stock_factor_engine),
        SaveToWarehouseStep(db_manager=db_manager, table_name="factors"),
    ]

    return Pipeline(steps=steps)


import asyncio

def main():
    """
    主執行函數，設置並運行股票因子生成流程。
    """
    logger.info("===== 開始執行第四號生產線：股票因子生成 =====")

    # --- 配置區 ---
    # 定義目標股票清單
    # 'AAPL' - 美股, '2330.TW' - 台股
    target_symbols = ['AAPL', '2330.TW']

    # 初始化資料庫管理器
    db_manager = DBManager(db_path=config.get('database.main_db_path'))

    # 初始化客戶端工廠
    client_factory = ClientFactory()

    # --- 執行區 ---
    logger.info(f"目標股票: {target_symbols}")

    # 創建 Pipeline
    pipeline = create_stock_factor_pipeline(
        symbols=target_symbols,
        db_manager=db_manager,
        client_factory=client_factory,
    )

    # 執行 Pipeline
    try:
        asyncio.run(pipeline.run())
        logger.info("Pipeline 執行成功。")
    except Exception as e:
        logger.error(f"Pipeline 執行過程中發生錯誤: {e}", exc_info=True)
        # 可以在此處添加錯誤處理邏輯，例如發送通知

    # --- 清理區 ---
    logger.info("===== 第四號生產線執行完畢 =====")


if __name__ == "__main__":
    main()


================================================================================
### FILE: prometheus/pipelines/p5_crypto_factor_generation.py
================================================================================

# src/prometheus/pipelines/p5_crypto_factor_generation.py

import logging
import asyncio
from typing import List

from src.prometheus.core.config import config
from src.prometheus.core.clients.client_factory import ClientFactory
from src.prometheus.core.db.db_manager import DBManager
from src.prometheus.core.engines.crypto_factor_engine import CryptoFactorEngine
from src.prometheus.core.pipelines.pipeline import Pipeline
from src.prometheus.core.pipelines.steps.loaders import LoadCryptoDataStep
from src.prometheus.core.pipelines.steps.savers import SaveToWarehouseStep
from src.prometheus.core.pipelines.steps.financial_steps import RunCryptoFactorEngineStep
from src.prometheus.core.pipelines.steps.splitters import GroupBySymbolStep

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_crypto_factor_pipeline(symbols: List[str], db_manager: DBManager, client_factory: ClientFactory) -> Pipeline:
    """
    創建一個用於生成加密貨幣因子的標準化 Pipeline。

    :param symbols: 要處理的加密貨幣代號列表。
    :param db_manager: 資料庫管理器。
    :param client_factory: 客戶端工廠。
    :return: 一個配置好的 Pipeline 實例。
    """
    # 初始化加密貨幣因子引擎
    crypto_factor_engine = CryptoFactorEngine(client_factory=client_factory)

    from src.prometheus.core.pipelines.steps.normalize_columns_step import NormalizeColumnsStep
    # 定義 Pipeline 的步驟
    steps = [
        LoadCryptoDataStep(symbols=symbols, client_factory=client_factory),
        NormalizeColumnsStep(),
        GroupBySymbolStep(),
        RunCryptoFactorEngineStep(engine=crypto_factor_engine),
        SaveToWarehouseStep(db_manager=db_manager, table_name="factors"),
    ]

    return Pipeline(steps=steps)


def main():
    """
    主執行函數，設置並運行加密貨幣因子生成流程。
    """
    logger.info("===== 開始執行第五號生產線：加密貨幣因子生成 =====")

    # --- 配置區 ---
    # 定義目標加密貨幣清單
    target_symbols = ['BTC-USD', 'ETH-USD']

    # 初始化資料庫管理器
    db_manager = DBManager(db_path=config.get('database.main_db_path'))

    # 初始化客戶端工廠
    client_factory = ClientFactory()

    # --- 執行區 ---
    logger.info(f"目標加密貨幣: {target_symbols}")

    # 創建 Pipeline
    pipeline = create_crypto_factor_pipeline(
        symbols=target_symbols,
        db_manager=db_manager,
        client_factory=client_factory,
    )

    # 執行 Pipeline
    try:
        asyncio.run(pipeline.run())
        logger.info("Pipeline 執行成功。")
    except Exception as e:
        logger.error(f"Pipeline 執行過程中發生錯誤: {e}", exc_info=True)
        # 可以在此處添加錯誤處理邏輯，例如發送通知

    # --- 清理區 ---
    logger.info("===== 第五號生產線執行完畢 =====")


if __name__ == "__main__":
    main()


================================================================================
### FILE: prometheus/pipelines/p6_simulation_training.py
================================================================================

# -*- coding: utf-8 -*-
from prometheus.core.pipelines.pipeline import Pipeline
from prometheus.pipelines.steps.load_all_factors_step import LoadAllFactorsStep
from prometheus.pipelines.steps.load_historical_target_step import LoadHistoricalTargetStep
from prometheus.pipelines.steps.train_factor_simulator_step import TrainFactorSimulatorStep

import asyncio

async def main(target_factor: str):
    """
    執行因子模擬模型訓練生產線。

    :param target_factor: 要模擬的目標因子名稱。
    """
    pipeline = Pipeline(
        steps=[
            LoadAllFactorsStep(),
            LoadHistoricalTargetStep(target_factor=target_factor),
            TrainFactorSimulatorStep(target_factor=target_factor),
        ]
    )
    await pipeline.run()

def run_main(target_factor: str):
    asyncio.run(main(target_factor))

if __name__ == "__main__":
    # 這裡可以添加一個簡單的測試，例如：
    # main(target_factor="T10Y2Y")
    pass


================================================================================
### FILE: prometheus/pipelines/steps/load_all_factors_step.py
================================================================================

# -*- coding: utf-8 -*-
import pandas as pd
import duckdb
from prometheus.core.pipelines.base_step import BaseStep
from prometheus.core.config import config

class LoadAllFactorsStep(BaseStep):
    """
    從 factors.duckdb 載入所有可用的因子。
    """

    async def run(self, data, context):
        """
        執行載入步驟。

        :param data: 上一個步驟的數據。
        :param context: 管線上下文。
        """
        db_path = config.get('database.main_db_path')
        with duckdb.connect(db_path) as con:
            all_factors = con.execute("SELECT * FROM factors").fetchdf()
            all_factors['date'] = pd.to_datetime(all_factors['date'])
            all_factors = all_factors.set_index('date')
            context['all_factors'] = all_factors
        return data


================================================================================
### FILE: prometheus/pipelines/steps/load_historical_target_step.py
================================================================================

# -*- coding: utf-8 -*-
from prometheus.core.pipelines.base_step import BaseStep

class LoadHistoricalTargetStep(BaseStep):
    """
    載入目標因子的歷史數據。
    """

    def __init__(self, target_factor: str):
        """
        初始化 LoadHistoricalTargetStep。

        :param target_factor: 要載入的目標因子名稱。
        """
        super().__init__()
        self.target_factor = target_factor

    async def run(self, data, context):
        """
        執行載入步驟。

        :param data: 上一個步驟的數據。
        :param context: 管線上下文。
        """
        all_factors = context.get('all_factors')
        target_factor_lower = self.target_factor.lower()

        if target_factor_lower not in all_factors.columns:
            raise KeyError(f"目標因子 '{target_factor_lower}' 在 all_factors 中找不到。可用的因子有: {all_factors.columns.tolist()}")

        target_series = all_factors[[target_factor_lower]].dropna()
        context['target_series'] = target_series[target_factor_lower]
        return data


================================================================================
### FILE: prometheus/pipelines/steps/train_factor_simulator_step.py
================================================================================

# -*- coding: utf-8 -*-
from prometheus.core.pipelines.base_step import BaseStep
from prometheus.services.factor_simulator import FactorSimulator

class TrainFactorSimulatorStep(BaseStep):
    """
    訓練因子模擬器模型。
    """

    def __init__(self, target_factor: str):
        """
        初始化 TrainFactorSimulatorStep。

        :param target_factor: 要模擬的目標因子名稱。
        """
        super().__init__()
        self.target_factor = target_factor
        self.simulator = FactorSimulator()

    async def run(self, data, context):
        """
        執行訓練步驟。

        :param data: 上一個步驟的數據。
        :param context: 管線上下文。
        """
        all_factors = context.get('all_factors')
        target_series = context.get('target_series')

        if target_series.empty:
            print(f"警告：目標因子 '{self.target_factor}' 的數據為空，跳過模型訓練。")
            return data

        # 排除目標因子本身作為預測變數
        predictors_df = all_factors.drop(columns=[self.target_factor.lower()])

        self.simulator.train(target_series, predictors_df)
        return data


================================================================================
### FILE: prometheus/services/__init__.py
================================================================================



================================================================================
### FILE: prometheus/services/backtesting_service.py
================================================================================

# -*- coding: utf-8 -*-
"""
回測服務：負責評估單一策略的歷史績效。
"""
import pandas as pd
import numpy as np
from prometheus.core.db.db_manager import DBManager
from prometheus.models.strategy_models import Strategy, PerformanceReport

class BacktestingService:
    """
    一個獨立、高效的回測服務。
    此服務是整個演化系統的心臟，專職負責精準評估任何單一策略（基因組）的歷史績效。
    """
    def __init__(self, db_manager: DBManager):
        """
        初始化回測服務。

        Args:
            db_manager (DBManager): 用於從數據倉儲讀取因子與價格數據的數據庫管理器。
        """
        self.db_manager = db_manager

    def _load_data(self, strategy: Strategy) -> pd.DataFrame:
        """
        從數據庫加載並合併因子與目標資產價格數據。
        """
        # 1. 加載所有因子數據
        all_factors_df = self.db_manager.fetch_table('factors')

        # 2. 篩選出策略所需的因子
        required_factors = all_factors_df[['date', 'symbol'] + strategy.factors]

        # 3. 加載目標資產的價格數據 (假設價格也存在 'factors' 表中，以 'close' 欄位表示)
        #    在真實場景中，這可能會從一個專門的價格表中獲取
        target_prices_df = all_factors_df[all_factors_df['symbol'] == strategy.target_asset][['date', 'close']]

        # 4. 合併數據
        merged_df = pd.merge(required_factors[required_factors['symbol'] == strategy.target_asset], target_prices_df, on='date')
        merged_df['date'] = pd.to_datetime(merged_df['date'])
        merged_df = merged_df.set_index('date').sort_index()

        return merged_df

    def run(self, strategy: Strategy) -> PerformanceReport:
        """
        執行一次完整的策略回測。
        """
        # 1. 數據加載
        data = self._load_data(strategy)
        if data.empty:
            print(f"WARN: 找不到策略 {strategy.target_asset} 的數據，跳過回測。")
            return PerformanceReport()

        # 2. 訊號生成 (正規化 + 加權)
        # 對因子進行 z-score 正規化
        for factor in strategy.factors:
            data[f'{factor}_norm'] = (data[factor] - data[factor].mean()) / data[factor].std()

        # 計算加權後的組合訊號
        data['signal'] = 0
        for factor in strategy.factors:
            data['signal'] += data[f'{factor}_norm'] * strategy.weights.get(factor, 0)

        # 3. 投資組合模擬
        # 計算目標資產的日報酬率
        data['asset_returns'] = data['close'].pct_change()

        # 根據訊號計算策略報酬率 (假設 T+1 生效)
        # 訊號為正 -> 做多, 訊號為負 -> 做空
        data['strategy_returns'] = data['signal'].shift(1) * data['asset_returns']

        # 4. 績效計算
        # 處理可能出現的 NaN 或 Inf
        data.replace([np.inf, -np.inf], np.nan, inplace=True)
        data.dropna(inplace=True)

        if data.empty:
            return PerformanceReport()

        # 計算累積報酬
        cumulative_returns = (1 + data['strategy_returns']).cumprod()

        # 計算年化報酬
        days = (data.index[-1] - data.index[0]).days
        annualized_return = (cumulative_returns.iloc[-1]) ** (365.0 / days) - 1 if days > 0 else 0.0

        # 計算年化夏普比率 (假設無風險利率為 0)
        annualized_volatility = data['strategy_returns'].std() * np.sqrt(252)
        sharpe_ratio = (annualized_return / annualized_volatility) if annualized_volatility != 0 else 0.0

        # 計算最大回撤
        peak = cumulative_returns.expanding(min_periods=1).max()
        drawdown = (cumulative_returns - peak) / peak
        max_drawdown = drawdown.min()

        return PerformanceReport(
            sharpe_ratio=float(sharpe_ratio),
            annualized_return=float(annualized_return),
            max_drawdown=float(max_drawdown),
            total_trades=len(data) # 簡化為交易天數
        )


================================================================================
### FILE: prometheus/services/checkpoint_manager.py
================================================================================

import pickle
from pathlib import Path
from typing import Optional

from prometheus.core.logging.log_manager import LogManager

logger = LogManager.get_instance().get_logger("CheckpointManager")


class CheckpointManager:
    """
    一個負責儲存和讀取演化過程狀態的檢查點管理器。
    """

    def __init__(self, checkpoint_path: Path):
        self.path = checkpoint_path

    def save_checkpoint(self, state: dict):
        """將演化狀態以 pickle 格式儲存到檔案。"""
        try:
            self.path.parent.mkdir(exist_ok=True, parents=True)
            with open(self.path, "wb") as f:
                pickle.dump(state, f)
            logger.info(f"演化狀態已成功儲存至: {self.path}")
        except Exception as e:
            logger.error(f"儲存檢查點失敗: {e}", exc_info=True)

    def load_checkpoint(self) -> Optional[dict]:
        """從檔案讀取演化狀態。"""
        if not self.path.exists():
            return None

        try:
            with open(self.path, "rb") as f:
                state = pickle.load(f)
            logger.info(f"成功從 {self.path} 讀取到檢查點。")
            return state
        except Exception as e:
            logger.error(f"讀取檢查點失敗: {e}", exc_info=True)
            return None

    def clear_checkpoint(self):
        """清除舊的檢查點檔案。"""
        if self.path.exists():
            self.path.unlink()
            logger.info(f"已清除舊的檢查點檔案: {self.path}")


================================================================================
### FILE: prometheus/services/evolution_chamber.py
================================================================================

# -*- coding: utf-8 -*-
"""
演化室：使用遺傳演算法來發現高效的交易策略。
"""
import random
from typing import List, Tuple
import numpy as np

from deap import base, creator, tools

from prometheus.services.backtesting_service import BacktestingService
from prometheus.models.strategy_models import Strategy

class EvolutionChamber:
    """
    一個「演化室」，將因子庫轉化為基因池，並使用遺傳演算法進行策略演化。
    """
    def __init__(self, backtesting_service: BacktestingService, available_factors: List[str], target_asset: str = 'SPY'):
        """
        初始化演化室。

        Args:
            backtesting_service (BacktestingService): 用於評估策略適應度的回測服務。
            available_factors (List[str]): 可供演化選擇的所有因子名稱列表。
            target_asset (str): 演化和回測的目標資產。
        """
        self.backtester = backtesting_service
        self.available_factors = available_factors
        self.target_asset = target_asset
        self.num_factors_to_select = 5 # 暫定每個策略由5個因子構成

        # --- DEAP 核心設定 ---
        # 確保 FitnessMax 和 Individual 只被創建一次，避免在多個實例中重複創建導致錯誤
        if not hasattr(creator, "FitnessMax"):
            creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        if not hasattr(creator, "Individual"):
            # 每個「個體」都是一個列表，代表一個策略
            creator.create("Individual", list, fitness=creator.FitnessMax)

        self.toolbox = base.Toolbox()
        self._setup_toolbox()

    def _evaluate_strategy(self, individual: List[int]) -> Tuple[float]:
        """
        評估單一個體的適應度，此為演化核心的「適應度函數」。
        """
        # 1. 解碼基因：將因子索引轉換為因子名稱
        raw_factors = [self.available_factors[i] for i in individual]
        # 【修正】確保因子列表的唯一性，防止因交叉突變導致的重複
        selected_factors = list(dict.fromkeys(raw_factors))

        # 如果去重後因子少於1個，這是一個無效策略
        if not selected_factors:
            return (0.0,)

        # 2. 建立策略物件 (此處使用等權重作為範例)
        strategy_to_test = Strategy(
            factors=selected_factors,
            weights={factor: 1.0 / len(selected_factors) for factor in selected_factors},
            target_asset=self.target_asset # 使用演化室指定的目標資產
        )

        # 3. 執行回測以獲得績效
        report = self.backtester.run(strategy_to_test)

        # 4. 返回適應度分數 (以元組形式)
        return (report.sharpe_ratio,)

    def _setup_toolbox(self):
        """
        設定 DEAP 的 toolbox，定義基因、個體、族群的生成規則與演化算子。
        """
        # 定義「基因」：一個代表因子索引的整數
        self.toolbox.register("factor_indices", random.sample, range(len(self.available_factors)), self.num_factors_to_select)

        # 定義「個體」：由一組不重複的因子索引構成
        self.toolbox.register("individual", tools.initIterate, creator.Individual, self.toolbox.factor_indices)

        # 定義「族群」：由多個「個體」組成的列表
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)

        # --- 新增：註冊核心遺傳算子 ---
        self.toolbox.register("evaluate", self._evaluate_strategy)
        # 交叉算子：兩點交叉
        self.toolbox.register("mate", tools.cxTwoPoint)
        # 突變算子：隨機交換索引，indpb 為每個基因的突變機率
        self.toolbox.register("mutate", tools.mutShuffleIndexes, indpb=0.1)
        # 選擇算子：錦標賽選擇，tournsize 為每次競賽的個體數
        self.toolbox.register("select", tools.selTournament, tournsize=3)

    def run_evolution(self, n_pop: int = 50, n_gen: int = 10, cxpb: float = 0.5, mutpb: float = 0.2):
        """
        執行完整的演化流程。

        Args:
            n_pop (int): 族群大小。
            n_gen (int): 演化世代數。
            cxpb (float): 交叉機率。
            mutpb (float): 突變機率。

        Returns:
            tools.HallOfFame: 包含演化過程中發現的最優個體。
        """
        pop = self.toolbox.population(n=n_pop)
        hof = tools.HallOfFame(1) # 名人堂，只儲存最優的一個個體
        stats = tools.Statistics(lambda ind: ind.fitness.values)
        stats.register("avg", np.mean)
        stats.register("std", np.std)
        stats.register("min", np.min)
        stats.register("max", np.max)

        # 1. 首次評估所有個體
        fitnesses = map(self.toolbox.evaluate, pop)
        for ind, fit in zip(pop, fitnesses):
            ind.fitness.values = fit

        print(f"--- 開始演化，共 {n_gen} 代 ---")

        for g in range(n_gen):
            # 2. 選擇下一代的個體
            offspring = self.toolbox.select(pop, len(pop))
            offspring = list(map(self.toolbox.clone, offspring))

            # 3. 執行交叉與突變
            for child1, child2 in zip(offspring[::2], offspring[1::2]):
                if random.random() < cxpb:
                    self.toolbox.mate(child1, child2)
                    del child1.fitness.values
                    del child2.fitness.values

            for mutant in offspring:
                if random.random() < mutpb:
                    self.toolbox.mutate(mutant)
                    del mutant.fitness.values

            # 4. 評估被改變的個體
            invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
            fitnesses = map(self.toolbox.evaluate, invalid_ind)
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = fit

            # 5. 更新族群與名人堂
            pop[:] = offspring
            hof.update(pop)

            record = stats.compile(pop)
            print(f"> 第 {g+1} 代: 最優夏普 = {record['max']:.4f}, 平均夏普 = {record['avg']:.4f}")

        print("--- 演化結束 ---")
        return hof


================================================================================
### FILE: prometheus/services/factor_simulator.py
================================================================================

# -*- coding: utf-8 -*-
import joblib
import pandas as pd
from sklearn.linear_model import LinearRegression
from pathlib import Path

class FactorSimulator:
    """
    因子代理模擬器，負責模型的訓練、保存與預測。
    """

    def __init__(self, model_dir: str = "data/models"):
        """
        初始化 FactorSimulator。

        :param model_dir: 存放模型的目錄。
        """
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.model = None

    def train(self, target_series: pd.Series, predictors_df: pd.DataFrame):
        """
        訓練模型並保存。

        :param target_series: 目標因子 (例如 T10Y2Y 的歷史數據)。
        :param predictors_df: 預測因子 (來自 factors.duckdb)。
        """
        target_name = target_series.name
        model_path = self.model_dir / f"{target_name}_simulator.joblib"

        # 處理數據對齊
        aligned_df = predictors_df.join(target_series, how='inner')

        # 處理缺失值
        aligned_df = aligned_df.dropna()

        X = aligned_df[predictors_df.columns]
        y = aligned_df[target_name]

        self.model = LinearRegression()
        self.model.fit(X, y)

        joblib.dump(self.model, model_path)
        print(f"模型已成功訓練並保存至：{model_path}")

    def predict(self, predictors_df: pd.DataFrame, target_name: str) -> pd.Series:
        """
        載入已保存的模型並進行預測。

        :param predictors_df: 當前的預測因子數據。
        :param target_name: 目標因子的名稱。
        :return: 模擬出的目標因子值。
        """
        model_path = self.model_dir / f"{target_name}_simulator.joblib"
        if not model_path.exists():
            raise FileNotFoundError(f"找不到模型檔案：{model_path}")

        model = joblib.load(model_path)

        # 確保預測數據的欄位順序與訓練時一致
        predictors_df = predictors_df.reindex(columns=model.feature_names_in_, fill_value=0)

        return pd.Series(model.predict(predictors_df), index=predictors_df.index)


================================================================================
### FILE: prometheus/services/optimizer_service.py
================================================================================

import json
import duckdb
from prometheus.core.logging.log_manager import LogManager
from prometheus.core.db import get_db_connection
from prometheus.core.config import config

class OptimizerService:
    def __init__(self, db_path=None, table_name="optimized_strategies"):
        self.db_path = db_path or config.get("database.main_db_path")
        self.table_name = table_name
        self.log_manager = LogManager(session_name="optimizer_service")
        self._initialize_db()

    def _initialize_db(self):
        with get_db_connection(self.db_path) as conn:
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    strategy_id VARCHAR PRIMARY KEY,
                    params VARCHAR,
                    fitness_score FLOAT,
                    crossover_points INTEGER
                )
            """)

    def get_best_strategy(self):
        with get_db_connection(self.db_path) as conn:
            try:
                best_result = conn.execute(
                    f"SELECT params FROM {self.table_name} ORDER BY crossover_points DESC LIMIT 1"
                ).fetchone()
                if best_result:
                    return json.loads(best_result[0])
            except duckdb.CatalogException:
                self.log_manager.log_error(f"Table {self.table_name} not found.")
            return None

    def save_strategy(self, strategy_id, params, fitness_score, crossover_points):
        with get_db_connection(self.db_path) as conn:
            conn.execute(
                f"INSERT OR REPLACE INTO {self.table_name} VALUES (?, ?, ?, ?)",
                (strategy_id, json.dumps(params), fitness_score, crossover_points)
            )
        self.log_manager.log_info(f"Strategy {strategy_id} saved successfully.")

if __name__ == "__main__":
    service = OptimizerService()
    # Example usage:
    # service.save_strategy("strategy_1", {"param1": 10}, 0.95, 5)
    # best_params = service.get_best_strategy()
    # print(f"Best strategy params: {best_params}")


================================================================================
### FILE: prometheus/services/strategy_reporter.py
================================================================================

# -*- coding: utf-8 -*-
"""
策略報告生成器。
"""
import os
from typing import List
from deap import tools
from prometheus.models.strategy_models import PerformanceReport, Strategy

class StrategyReporter:
    """
    將演化過程中發現的最優策略，生成一份清晰的報告。
    """
    def __init__(self, report_dir: str = 'reports'):
        self.report_dir = report_dir
        if not os.path.exists(self.report_dir):
            os.makedirs(self.report_dir)

    def generate_report(
        self,
        best_individual: tools.HallOfFame,
        performance_report: PerformanceReport,
        available_factors: List[str]
    ):
        """
        生成並儲存策略報告。

        Args:
            best_individual (tools.HallOfFame): 包含最優個體的名人堂。
            performance_report (PerformanceReport): 最優個體的回測績效報告。
            available_factors (List[str]): 所有可用因子的列表。
        """
        if not best_individual:
            print("WARN: 名人堂為空，無法生成報告。")
            return

        best_strategy_indices = best_individual[0]
        best_strategy_factors = [available_factors[i] for i in best_strategy_indices]

        report_content = f"""# 【普羅米修斯之火：最優策略報告】

演化完成，這是本次發現的最佳策略詳細資訊。

## 📈 核心績效指標

| 指標                        | 數值                  |
| --------------------------- | --------------------- |
| 夏普比率 (Sharpe Ratio)     | {performance_report.sharpe_ratio:.4f} |
| 年化報酬率 (Annualized Return) | {performance_report.annualized_return:.2%}  |
| 最大回撤 (Max Drawdown)     | {performance_report.max_drawdown:.2%}   |
| 總交易天數 (Total Trades)   | {performance_report.total_trades}     |

## 🧬 策略基因構成

此策略由以下 **{len(best_strategy_factors)}** 個因子等權重構成：

```
{', '.join(best_strategy_factors)}
```
"""
        report_path = os.path.join(self.report_dir, 'best_strategy_report.md')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        print(f"✅ 策略報告已成功生成於: {report_path}")
