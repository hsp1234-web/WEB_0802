# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║              📊 鳳凰之心 - 互動式報告儀表板 V31 (UI)                  ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║ - 說明: 此腳本在 Colab 或 Jupyter 環境中渲染一個互動式儀表板，      ║
# ║         讓使用者可以選擇、預覽、複製和存檔報告。                   ║
# ║ - 依賴: `ipywidgets`, `report_generator.py`                        ║
# ║ - 版本: 0.5.0 (互動式 UI)                                          ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

# --- 導入必要的函式庫 ---
import ipywidgets as widgets
from IPython.display import display, Javascript
from pathlib import Path
import time

# --- 導入我們在階段五中經過驗證的後端邏輯 ---
# 假設 report_generator 模組與此腳本在同一個 Python 環境中
try:
    from src.phoenix_core.report_generator import read_selected_reports, archive_selected_reports
except ImportError as e:
    print(f"❌ 錯誤: 無法導入核心模組 ({e})。")
    print("   請確保您在專案的根目錄下執行此腳本，並且 Python 環境已設定正確。")
    # 提供一個退路，以便在沒有完整專案結構的環境中進行基本測試
    # from report_generator import read_selected_reports, archive_selected_reports

# --- 全域變數與設定 ---
# 假設報告檔案位於 'reports' 資料夾中
REPORTS_DIR = Path("./reports")
ARCHIVE_ROOT_DIR = Path("./")

# --- UI 元件定義 ---
header = widgets.HTML("<h1>📊 鳳凰之心 - 互動式報告儀表板 📊</h1>")

# 勾選框
chk_all = widgets.Checkbox(value=True, description='全部報告', indent=False)
chk_perf = widgets.Checkbox(value=True, description='📈 效能分析報告 (performance_report.md)', indent=False)
chk_summary = widgets.Checkbox(value=True, description='📄 總結報告 (summary_report.md)', indent=False)
chk_detail = widgets.Checkbox(value=True, description='📋 詳細日誌報告 (detailed_log_report.md)', indent=False)
checkboxes = [chk_perf, chk_summary, chk_detail]

# 按鈕
btn_generate = widgets.Button(description='產生報告', button_style='primary', icon='cogs')
btn_copy = widgets.Button(description='📋 複製選中報告', button_style='info', icon='copy', layout={'visibility': 'hidden'})
btn_archive = widgets.Button(description='💾 存檔選中報告', button_style='success', icon='archive', layout={'visibility': 'hidden'})

# 輸出區域
output_area = widgets.Output(layout={'border': '1px solid #ccc', 'padding': '10px', 'margin_top': '10px'})
with output_area:
    print("(點擊「產生報告」按鈕後，此處將顯示報告內容)")

# --- 互動邏輯 ---
def get_selection():
    """根據勾選框狀態獲取選擇的報告檔名"""
    selection = []
    if chk_perf.value: selection.append('performance_report.md')
    if chk_summary.value: selection.append('summary_report.md')
    if chk_detail.value: selection.append('detailed_log_report.md')
    return selection

def on_chk_all_changed(change):
    """處理「全部報告」勾選框的連動"""
    is_checked = change.new
    for chk in checkboxes:
        chk.value = is_checked
chk_all.observe(on_chk_all_changed, names='value')

def on_generate_clicked(b):
    """「產生報告」按鈕的回呼函式"""
    selection = get_selection()
    output_area.clear_output(wait=True)
    with output_area:
        if not selection:
            print("⚠️ 請至少選擇一份報告。")
            btn_copy.layout.visibility = 'hidden'
            btn_archive.layout.visibility = 'hidden'
            return

        # 呼叫後端邏輯
        try:
            report_content = read_selected_reports(REPORTS_DIR, selection)
            if not report_content:
                 print(f"⚠️ 在 '{REPORTS_DIR}' 目錄下找不到任何選定的報告檔案。請確認檔案是否存在。")
                 return
            print(report_content)
            # 成功生成後顯示操作按鈕
            btn_copy.layout.visibility = 'visible'
            btn_archive.layout.visibility = 'visible'
        except Exception as e:
            print(f"❌ 讀取報告時發生錯誤: {e}")


btn_generate.on_click(on_generate_clicked)

def on_archive_clicked(b):
    """「存檔報告」按鈕的回呼函式"""
    selection = get_selection()
    original_text = b.description
    try:
        # 呼叫後端邏輯
        archive_path = archive_selected_reports(REPORTS_DIR, ARCHIVE_ROOT_DIR, selection)
        b.description = f'✅ 已存檔至 {archive_path}'
        b.button_style = 'success'
    except Exception as e:
        b.description = f'❌ 存檔失敗'
        b.button_style = 'danger'
        with output_area:
            print(f"\n存檔錯誤: {e}")

    time.sleep(2)
    b.description = original_text
    b.button_style = 'success'
btn_archive.on_click(on_archive_clicked)

def on_copy_clicked(b):
    """「複製報告」按鈕的回呼函式，使用 Javascript"""
    selection = get_selection()
    report_content_for_js = read_selected_reports(REPORTS_DIR, selection)

    # 為了在 Javascript 中正確處理，我們需要對字串進行轉義
    escaped_content = report_content_for_js.replace('`', '\\`').replace('\\n', '\\\\n')

    js_code = f'''
    navigator.clipboard.writeText(`{escaped_content}`).then(function() {{
        console.log('複製成功!');
    }}, function(err) {{
        console.error('複製失敗: ', err);
    }});
    '''
    display(Javascript(js_code))

    original_text = b.description
    b.description = '✅ 已複製到剪貼簿!'
    b.button_style = 'success'
    time.sleep(1)
    b.description = original_text
    b.button_style = 'info'
btn_copy.on_click(on_copy_clicked)

# --- UI 佈局 ---
checkbox_layout = widgets.VBox([
    chk_all,
    widgets.HBox([
        widgets.Label(value=""),
        widgets.VBox(checkboxes)],
        layout=widgets.Layout(padding='0 0 0 20px') # 左側縮排
    )
])
button_layout = widgets.HBox([btn_generate, btn_copy, btn_archive])
report_preview = widgets.VBox([widgets.HTML("<h3>報告內容預覽</h3>"), output_area])

# 最終顯示的 UI
# 透過一個函式來封裝，以便在需要時才顯示
def display_dashboard():
    """顯示完整的儀表板 UI"""
    ui = widgets.VBox([
        header,
        widgets.HTML("請選擇您需要產生的報告類型："),
        checkbox_layout,
        button_layout,
        report_preview
    ])
    display(ui)

# --- 主程式入口 ---
if __name__ == "__main__":
    # 當此腳本被直接執行時 (例如在 Colab 中 %run report.py)，顯示儀表板
    if not REPORTS_DIR.exists():
        print(f"‼️ 警告：報告目錄 '{REPORTS_DIR}' 不存在。")
        print("   腳本將繼續執行，但您可能無法產生報告。請確保後端已生成報告檔案。")

    display_dashboard()
