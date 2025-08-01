# 檔案: tests/integration/test_api_driven_architecture.py
# 說明: 驗證 V23 API 驅動架構的整合測試。
# 作者: Jules (修正版)

import pytest
import asyncio
import subprocess
import sys
import sqlite3
import json
from pathlib import Path
import os
from aiohttp import web

# 確保可以從 scripts 目錄導入
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts import launch

# --- Fixtures ---

@pytest.fixture
async def client(aiohttp_client):
    """
    一個經過修正的 fixture，它正確地設定 aiohttp 應用程式
    並將其傳遞給 aiohttp_client。
    """
    # 建立 aiohttp 應用
    app = web.Application()
    app.add_routes([
        web.get('/api/v1/status', launch.get_status_handler),
        web.post('/api/v1/shutdown', launch.shutdown_handler),
    ])

    # 將共享狀態附加到 app，以便在測試中存取和控制
    # 每次測試都應該有乾淨的狀態
    app['shared_state'] = {
        "current_stage": "初始化中...",
        "cpu_usage": 0.0,
        "ram_usage": 0.0,
        "apps_status": {},
        "logs": launch.deque(maxlen=100),
        "shutdown_event": asyncio.Event(),
        "db_conn": None # 在測試中不需要實際的資料庫
    }

    # 將共享狀態的引用也放到 launch 模組中，以便處理器可以訪問它
    launch.shared_state = app['shared_state']

    test_client = await aiohttp_client(app)
    yield test_client

# --- 測試案例 ---

@pytest.mark.asyncio
async def test_status_endpoint(client):
    """測試 /api/v1/status 端點是否能返回符合預期結構的 JSON。"""

    # 模擬一些狀態變化
    launch.shared_state['current_stage'] = "測試階段"
    launch.shared_state['cpu_usage'] = 50.5
    launch.shared_state['ram_usage'] = 60.6
    launch.shared_state['apps_status'] = {"test_app": "running"}
    launch.shared_state['logs'].append({"timestamp": "now", "level": "INFO", "message": "log message"})

    # 呼叫 API
    resp = await client.get("/api/v1/status")

    # 斷言狀態碼和內容類型
    assert resp.status == 200
    assert resp.content_type == 'application/json'

    data = await resp.json()

    # 斷言 JSON 結構和內容
    assert "status" in data
    assert "logs" in data
    assert data['status']['current_stage'] == "測試階段"
    assert data['status']['cpu_usage'] == 50.5
    assert data['status']['ram_usage'] == 60.6
    assert json.loads(data['status']['apps_status']) == {"test_app": "running"}
    assert len(data['logs']) == 1
    assert data['logs'][0]['message'] == "log message"


@pytest.mark.asyncio
async def test_shutdown_endpoint(client):
    """測試 /api/v1/shutdown 端點是否能觸發關機事件。"""

    app = client.app
    shutdown_event = app['shared_state']['shutdown_event']

    # 確認關機事件尚未被設定
    assert not shutdown_event.is_set()

    # 呼叫關機 API
    resp = await client.post("/api/v1/shutdown")
    assert resp.status == 200

    # 給事件迴圈一點時間來處理
    await asyncio.sleep(0.01)

    # 確認關機事件已被設定
    assert shutdown_event.is_set()


def test_report_generation(tmp_path):
    """
    測試 report_generator.py 腳本是否能根據模擬的資料庫成功生成報告。
    """
    # --- 準備 ---
    # 1. 建立一個模擬的 state.db
    db_path = tmp_path / "mock_state.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # 建立 status 表
    cursor.execute("CREATE TABLE status (key TEXT PRIMARY KEY, value TEXT)")
    cursor.execute("INSERT INTO status VALUES (?, ?)",
                   ("final_stage", "任務成功完成"))
    apps_status = {"database": "running", "cache": "running"}
    cursor.execute("INSERT INTO status VALUES (?, ?)",
                   ("final_apps_status", json.dumps(apps_status)))
    # 建立 logs 表
    cursor.execute("CREATE TABLE logs (timestamp TEXT, level TEXT, message TEXT)")
    cursor.execute("INSERT INTO logs VALUES (?, ?, ?)",
                   ("2023-10-27T10:00:00", "INFO", "核心任務：啟動中"))
    cursor.execute("INSERT INTO logs VALUES (?, ?, ?)",
                   ("2023-10-27T10:00:02", "ERROR", "快取服務連接失敗"))
    conn.commit()
    conn.close()

    # 2. 定義報告輸出目錄
    report_dir = tmp_path / "reports"

    # --- 執行 ---
    report_script_path = Path(__file__).resolve().parents[2] / "scripts" / "report_generator.py"
    cmd = [
        sys.executable,
        str(report_script_path),
        "--db-file", str(db_path),
        "--report-dir", str(report_dir)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

    # --- 斷言 ---
    assert result.returncode == 0, f"報告生成腳本執行失敗: {result.stderr}"

    # 檢查三份報告是否都已生成
    summary_report = report_dir / "summary_report.md"
    perf_report = report_dir / "performance_report.md"
    log_report = report_dir / "detailed_log_report.md"

    assert summary_report.exists(), "綜合戰情簡報未生成"
    assert perf_report.exists(), "效能分析報告未生成"
    assert log_report.exists(), "詳細日誌報告未生成"

    # 檢查報告內容 (抽樣)
    summary_content = summary_report.read_text(encoding='utf-8')
    assert "最終任務階段" in summary_content
    assert "任務成功完成" in summary_content
    assert "database: running" in summary_content

    log_content = log_report.read_text(encoding='utf-8')
    assert "核心任務：啟動中" in log_content
    assert "快取服務連接失敗" in log_content
