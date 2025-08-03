# -*- coding: utf-8 -*-
"""
鳳凰之心終端顯示管理器 (Phoenix Heart Terminal Display Manager)

這個模組負責在終端機中渲染動態儀表板，實現了 v82.0 報告中
描述的「雙區塊智能監控」使用者介面。
"""
import threading
import time
import sys
from datetime import datetime
from collections import deque

# 從專案內部模組匯入
from src.phoenix_core.utils.logger import logger, TAIPEI_TZ
from src.phoenix_core.utils.ansi_styles import styles
from src.phoenix_core.kernel.hardware import get_system_usage

class DisplayManager:
    """
    管理終端機儀表板的顯示、更新和渲染。
    """
    def __init__(self, shared_state: dict, log_lines: int = 10, refresh_rate: float = 0.1):
        """
        初始化顯示管理器。

        Args:
            shared_state (dict): 用於在執行緒間共享狀態的字典。
            log_lines (int): 在儀表板上顯示的日誌行數。
            refresh_rate (float): 儀表板的刷新率（秒）。
        """
        self.shared_state = shared_state
        self.log_lines = log_lines
        self.refresh_rate = refresh_rate

        self.stop_event = threading.Event()
        self.display_thread = threading.Thread(target=self._run, daemon=True)

        # 用於追蹤日誌是否有更新，以決定是否重繪上半部
        self._last_log_id = -1
        # 用於儲存日誌，避免頻繁查詢資料庫
        self._log_buffer = deque(maxlen=self.log_lines)

    def _run(self):
        """
        顯示執行緒的主迴圈。
        """
        # 隱藏游標，避免在更新時閃爍
        sys.stdout.write(styles.CURSOR_HIDE)
        sys.stdout.flush()

        # 首次執行，先為日誌區域留出空間
        sys.stdout.write("\n" * self.log_lines)
        sys.stdout.flush()

        try:
            while not self.stop_event.is_set():
                self._update_and_draw()
                time.sleep(self.refresh_rate)
        finally:
            # 程式結束時，確保游標可見
            sys.stdout.write(styles.CURSOR_SHOW)
            sys.stdout.flush()

    def _update_and_draw(self):
        """
        獲取最新數據並重繪整個儀表板。
        """
        # --- 數據獲取 ---
        # 1. 獲取系統資源
        system_usage = get_system_usage()

        # 2. 獲取最新日誌 (僅在需要時)
        # 這裡我們簡化為每次都獲取，但在真實應用中可以增加快取策略
        logs = logger.get_recent_logs(self.log_lines, levels=["INFO", "SUCCESS", "ERROR", "CRITICAL", "WARN", "BATTLE"])
        self._log_buffer.clear()
        self._log_buffer.extend(logs)

        # --- 繪製 ---
        # 組合所有輸出，最後一次性寫入，減少閃爍
        output = []

        # 1. 準備日誌面板 (上半部)
        # 將游標移動到日誌區的起始位置
        output.append(styles.CURSOR_UP(self.log_lines + 1))

        for i in range(self.log_lines):
            output.append(styles.CLEAR_ENTIRE_LINE)
            if i < len(self._log_buffer):
                timestamp, level, message = self._log_buffer[i]
                # 格式化時間戳
                ts_obj = datetime.fromisoformat(timestamp)
                time_str = ts_obj.strftime('%H:%M:%S.%f')[:-3]

                # 根據日誌等級設定顏色
                color = styles.WHITE
                if level == "SUCCESS": color = styles.BRIGHT_GREEN
                elif level in ["ERROR", "CRITICAL"]: color = styles.BRIGHT_RED
                elif level == "WARN": color = styles.BRIGHT_YELLOW
                elif level == "BATTLE": color = styles.BRIGHT_CYAN

                log_line = f"[{time_str}] [{level.ljust(8)}] {message}"
                # 截斷過長的日誌以避免換行
                max_len = 120
                if len(log_line) > max_len:
                    log_line = log_line[:max_len-3] + "..."

                output.append(f"{color}{log_line}{styles.RESET}")
            output.append("\n")

        # 2. 準備狀態行 (下半部)
        current_time = datetime.now(TAIPEI_TZ).strftime('%H:%M:%S')
        cpu = f"CPU: {system_usage.cpu_percent:5.1f}%"
        ram = f"RAM: {system_usage.memory_percent:5.1f}%"

        task_status = self.shared_state.get('current_task', '初始化中...')
        status_color = styles.WHITE
        if self.shared_state.get('error'):
            task_status = f"錯誤: {self.shared_state.get('error')}"
            status_color = styles.BRIGHT_RED
        elif "成功" in task_status or "完成" in task_status:
            status_color = styles.BRIGHT_GREEN

        status_line = (
            f"{styles.CARRIAGE_RETURN}{styles.CLEAR_ENTIRE_LINE}"
            f"{styles.BRIGHT_WHITE}{current_time}{styles.RESET} | "
            f"{cpu} | {ram} | "
            f"{status_color}{task_status}{styles.RESET}"
        )
        output.append(status_line)

        # --- 一次性寫入到 stdout ---
        sys.stdout.write("".join(output))
        sys.stdout.flush()

    def start(self):
        """啟動顯示執行緒。"""
        self.display_thread.start()

    def stop(self):
        """停止顯示執行緒。"""
        self.stop_event.set()
        try:
            # 等待執行緒結束，設定超時以防萬一
            self.display_thread.join(timeout=2)
        except Exception as e:
            # 記錄可能的錯誤，但不影響主程式關閉
            logger.log("ERROR", f"停止 DisplayManager 時發生錯誤: {e}")
