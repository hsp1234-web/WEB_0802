# -*- coding: utf-8 -*-
# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                      ║
# ║              📊 鳳凰之心 - 互動式報告儀表板 V33 (UI)                  ║
# ║                                                                      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║                                                                      ║
# ║ - 說明: 在 Colab 或 Jupyter 環境中渲染一個互動式儀表板，讓使用者     ║
# ║         可以選擇、預覽、複製和存檔由後端生成的報告。               ║
# ║ - 依賴: `ipywidgets`, `src.phoenix_core.report_generator`          ║
# ║ - 版本: 1.1.0 (HTML 可折疊報告與進階複製)                          ║
# ║                                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

# --- 導入必要的函式庫 ---
import ipywidgets as widgets
from IPython.display import display, Javascript, HTML
from pathlib import Path
import time
import sys
import os
import html

# --- 路徑修正 ---
project_root = os.getcwd()
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- 導入後端邏輯 ---
try:
    from src.phoenix_core.report_generator import read_selected_reports, archive_selected_reports
except ImportError as e:
    print(f"❌ 錯誤: 無法導入核心模組 ({e})。請確保在專案根目錄下執行。")
    # Fallback for basic testing without full project structure
    # from report_generator import read_selected_reports, archive_selected_reports

# --- 全域變數與設定 ---
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
btn_copy = widgets.Button(description='📋 複製選中報告 (Markdown)', button_style='info', icon='copy', layout={'visibility': 'hidden'})
btn_archive = widgets.Button(description='💾 存檔選中報告', button_style='success', icon='archive', layout={'visibility': 'hidden'})
btn_copy_full = widgets.Button(description='複製完整輸出為純文字', button_style='primary')

# 輸出區域
output_area = widgets.Output(layout={'border': '1px solid #ccc', 'padding': '10px', 'margin_top': '10px'})
with output_area:
    print("(點擊「產生報告」按鈕後，此處將顯示報告內容)")

# --- 互動邏輯 ---
def get_selection():
    selection = []
    if chk_perf.value: selection.append('performance_report.md')
    if chk_summary.value: selection.append('summary_report.md')
    if chk_detail.value: selection.append('detailed_log_report.md')
    return selection

def on_chk_all_changed(change):
    for chk in checkboxes:
        chk.value = change.new
chk_all.observe(on_chk_all_changed, names='value')

def on_generate_clicked(b):
    selection = get_selection()
    output_area.clear_output(wait=True)

    if not selection:
        with output_area: print("⚠️ 請至少選擇一份報告。")
        btn_copy.layout.visibility = 'hidden'
        btn_archive.layout.visibility = 'hidden'
        panel_operations.layout.visibility = 'hidden'
        return

    try:
        report_content = read_selected_reports(REPORTS_DIR, selection)
        if not report_content:
            with output_area: print(f"⚠️ 在 '{REPORTS_DIR}' 目錄下找不到任何選定的報告檔案。")
            return

        reports = report_content.split("\n\n---\n\n")
        final_html = ""
        for report in reports:
            # 確保即使報告為空也能處理
            if not report.strip(): continue

            lines = report.strip().split('\n')
            title = lines[0].replace('#', '').strip() if lines else "無標題報告"
            escaped_report_body = html.escape(report)

            final_html += f"""
            <details open style="border: 1px solid #ddd; padding: 10px; margin-top: 10px; border-radius: 5px; background: #fff;">
                <summary style="cursor: pointer; font-weight: bold; font-size: 1.1em;">{html.escape(title)}</summary>
                <pre style="background-color: #f9f9f9; padding: 10px; border-radius: 5px; margin-top: 8px;">{escaped_report_body}</pre>
            </details>
            """

        with output_area:
            display(HTML(final_html))

        btn_copy.layout.visibility = 'visible'
        btn_archive.layout.visibility = 'visible'
        panel_operations.layout.visibility = 'visible'

    except Exception as e:
        with output_area: print(f"❌ 讀取報告時發生錯誤: {e}")

btn_generate.on_click(on_generate_clicked)

def on_archive_clicked(b):
    selection = get_selection()
    original_text = b.description
    try:
        archive_path = archive_selected_reports(REPORTS_DIR, ARCHIVE_ROOT_DIR, selection)
        b.description = f'✅ 已存檔至 {archive_path}'
        b.button_style = 'success'
    except Exception as e:
        b.description = '❌ 存檔失敗'
        b.button_style = 'danger'
        with output_area: print(f"\n存檔錯誤: {e}")
    time.sleep(2); b.description = original_text; b.button_style = 'success'
btn_archive.on_click(on_archive_clicked)

def on_copy_clicked(b):
    selection = get_selection()
    report_content_for_js = read_selected_reports(REPORTS_DIR, selection)
    escaped_content = report_content_for_js.replace('`', '\\`').replace('\\n', '\\\\n')
    js_code = f"navigator.clipboard.writeText(`{escaped_content}`);"
    display(Javascript(js_code))
    original_text = b.description
    b.description = '✅ 已複製到剪貼簿!'; b.button_style = 'success'
    time.sleep(1); b.description = original_text; b.button_style = 'info'
btn_copy.on_click(on_copy_clicked)

def on_copy_full_clicked(b):
    # output_area.outputs[0]['data']['text/html'] 獲取 HTML 內容
    # 但更簡單的方法是直接讓 JS 從 DOM 獲取
    js_code = f"""
    const outputElement = document.querySelector('#output-area-div > .jp-OutputArea-output > .jp-OutputArea-child > .jp-RenderedHTMLCommon');
    if (outputElement) {{
        const textToCopy = outputElement.innerText;
        navigator.clipboard.writeText(textToCopy).then(() => {{
            const button = document.getElementById('{b.model_id}');
            if(button) {{
                const originalText = button.innerText;
                button.innerText = '✅ 複製成功';
                setTimeout(() => {{ button.innerText = originalText; }}, 2000);
            }}
        }});
    }}
    """
    # 為了讓 JS 能找到按鈕，我們需要為按鈕的 DOM 元素設定一個 ID
    b.add_class("copy-full-button") # 添加一個 class 以便選取
    js_code_with_selector = f"""
    const btn = document.querySelector('.copy-full-button');
    const outputElement = btn.closest('.jp-OutputArea-item').querySelector('.jp-RenderedHTMLCommon');
    const textToCopy = outputElement ? outputElement.innerText : "未找到預覽內容";
    navigator.clipboard.writeText(textToCopy).then(() => {{
        btn.innerText = '✅ 複製成功';
        setTimeout(() => {{ btn.innerText = '複製完整輸出為純文字'; }}, 2000);
    }});
    """
    # 更穩健的作法是直接給 output_area 一個 ID
    js_code_final = f"""
    const outputPreview = document.getElementById("report-preview-div");
    if (outputPreview) {{
        const textToCopy = outputPreview.innerText;
        navigator.clipboard.writeText(textToCopy).then(() => {{
            const button = document.getElementById('{b.model_id}');
            if (button) {{
                 button.innerText = '✅ 複製成功!';
                 setTimeout(() => {{ button.innerText = '複製完整輸出為純文字'; }}, 2000);
            }}
        }});
    }}
    """
    display(Javascript(js_code_final))
btn_copy_full.on_click(on_copy_full_clicked)


# --- UI 佈局 ---
checkbox_layout = widgets.VBox([
    chk_all,
    widgets.HBox([
        widgets.Label(value=""),
        widgets.VBox(checkboxes)],
        layout=widgets.Layout(padding='0 0 0 20px')
    )
])
button_layout = widgets.HBox([btn_generate, btn_copy, btn_archive])
report_preview = widgets.VBox([widgets.HTML("<h3>報告內容預覽</h3>"), output_area],
                              layout=widgets.Layout(width='100%'))
report_preview.add_class("report-preview-div") # 為了讓 JS 選取

panel_operations = widgets.VBox([
    widgets.HTML("<h4>📋 面板內容操作</h4>"),
    btn_copy_full
], layout={'border': '1px solid #ddd', 'padding': '10px', 'margin_top': '10px', 'visibility': 'hidden'})


def display_dashboard():
    ui = widgets.VBox([
        header,
        widgets.HTML("請選擇您需要產生的報告類型："),
        checkbox_layout,
        button_layout,
        report_preview,
        panel_operations
    ])
    display(ui)

# --- 主程式入口 ---
if __name__ == "__main__":
    if not REPORTS_DIR.exists():
        REPORTS_DIR.mkdir()
        print(f"‼️ 警告：報告目錄 '{REPORTS_DIR}' 不存在，已自動建立。")
        print("   請確保後端已生成報告檔案至此目錄。")
    display_dashboard()
