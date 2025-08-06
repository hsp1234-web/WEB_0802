import argparse
import sys
from pathlib import Path

def consolidate_files(source_dir: Path, target_file: Path, pattern: str, append: bool = False):
    """
    Finds all files matching a pattern in a source directory and consolidates
    their content into a single target file.

    Args:
        source_dir: The directory to search for files.
        target_file: The file to write the consolidated content to.
        pattern: The glob pattern to match files (e.g., "*.py").
    """
    if not source_dir.is_dir():
        print(f"錯誤：來源目錄不存在或不是一個目錄: {source_dir}", file=sys.stderr)
        sys.exit(1)

    # 發現所有符合條件的檔案
    files_to_consolidate = sorted(list(source_dir.rglob(pattern)))

    if not files_to_consolidate:
        print(f"警告：在 {source_dir} 中沒有找到符合 '{pattern}' 的檔案。", file=sys.stderr)
        return

    # 確保目標目錄存在
    target_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"正在將 {len(files_to_consolidate)} 個檔案從 {source_dir} 合併到 {target_file}...")

    write_mode = "a" if append else "w"
    print(f"寫入模式: {'附加 (append)' if append else '覆蓋 (overwrite)'}")

    with open(target_file, write_mode, encoding="utf-8") as outfile:
        for filepath in files_to_consolidate:
            relative_path = filepath.relative_to(source_dir)
            print(f"  - 正在處理: {relative_path}")

            # 寫入一個清晰的分隔符
            outfile.write("\n" + "=" * 80 + "\n")
            outfile.write(f"### FILE: {relative_path}\n")
            outfile.write("=" * 80 + "\n\n")

            try:
                # 讀取並寫入檔案內容
                content = filepath.read_text(encoding="utf-8", errors="ignore")
                outfile.write(content)
                outfile.write("\n\n")
            except Exception as e:
                # 如果讀取失敗，寫入錯誤訊息而不是中斷
                outfile.write(f"!!! 無法讀取檔案: {e} !!!\n\n")

    print("合併完成！")

def main():
    parser = argparse.ArgumentParser(
        description="一個輔助工具，用於將指定目錄下的多個檔案合併成一個單一的封存檔案。",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "source_dir",
        type=Path,
        help="要搜索檔案的來源目錄路徑。"
    )
    parser.add_argument(
        "target_file",
        type=Path,
        help="要寫入合併內容的目標檔案路徑。"
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="*.py",
        help="用於尋找檔案的 glob 模式。\n"
             "範例:\n"
             "  '*.py'    - 所有 Python 檔案\n"
             "  '*.md'    - 所有 Markdown 檔案\n"
             "  '*'       - 所有檔案"
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="如果設置此旗標，將會附加到目標檔案而不是覆蓋它。"
    )

    args = parser.parse_args()

    consolidate_files(args.source_dir, args.target_file, args.pattern, args.append)

if __name__ == "__main__":
    main()
