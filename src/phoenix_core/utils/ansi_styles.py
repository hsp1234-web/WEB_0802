# -*- coding: utf-8 -*-
"""
ANSI 跳脫序列樣式庫 (ANSI Escape Sequence Style Library)

這個模組集中管理所有用於終端機的 ANSI 控制代碼，
包括文字顏色、背景色以及游標控制。
這有助於保持顯示邏輯的程式碼整潔，並易於維護。

參考資料: https://en.wikipedia.org/wiki/ANSI_escape_code
"""

class AnsiStyles:
    """一個靜態類別，用於存放 ANSI 控制代碼常數。"""
    # --- 顏色重設 ---
    RESET = "\\033[0m"

    # --- 標準顏色 (文字) ---
    BLACK = "\\033[30m"
    RED = "\\033[31m"
    GREEN = "\\033[32m"
    YELLOW = "\\033[33m"
    BLUE = "\\033[34m"
    MAGENTA = "\\033[35m"
    CYAN = "\\033[36m"
    WHITE = "\\033[37m"

    # --- 高亮度顏色 (文字) ---
    BRIGHT_BLACK = "\\033[90m"
    BRIGHT_RED = "\\033[91m"
    BRIGHT_GREEN = "\\033[92m"
    BRIGHT_YELLOW = "\\033[93m"
    BRIGHT_BLUE = "\\033[94m"
    BRIGHT_MAGENTA = "\\033[95m"
    BRIGHT_CYAN = "\\033[96m"
    BRIGHT_WHITE = "\\033[97m"

    # --- 游標控制 ---
    # 將游標移動到目前行的開頭
    CARRIAGE_RETURN = "\\r"
    # 從游標位置清除到行尾
    CLEAR_LINE_FROM_CURSOR = "\\033[K"
    # 清除整行
    CLEAR_ENTIRE_LINE = "\\033[2K"
    # 向上移動游標 N 行
    CURSOR_UP = lambda n: f"\\033[{n}A"
    # 隱藏游標
    CURSOR_HIDE = "\\033[?25l"
    # 顯示游標
    CURSOR_SHOW = "\\033[?25h"

# 為了方便使用，建立一個實例
# 使用方式: from .ansi_styles import styles
#           print(f"{styles.GREEN}這是綠色文字{styles.RESET}")
styles = AnsiStyles()
