"""Obsidian手書きノートフォルダの重複ファイルを削除する（古い方を削除、新しい方を残す）"""

import sys
from collections import defaultdict
from pathlib import Path

VAULT_DIR = Path("C:/Users/north/Documents/Obsidian Vault/手書きノート")

def main(dry_run: bool = True):
    groups: dict[str, list[Path]] = defaultdict(list)
    for f in VAULT_DIR.glob("*.md"):
        # ファイル名形式: YYYYMMDD_HHMMSS_スキャン_....md
        parts = f.name.split("_", 2)
        if len(parts) >= 3:
            source_name = parts[2]  # タイムスタンプを除いたソース名
            groups[source_name].append(f)

    to_delete: list[Path] = []
    for source, files in sorted(groups.items()):
        if len(files) > 1:
            files.sort(key=lambda f: f.name)  # タイムスタンプ昇順 → 最後が最新
            keep = files[-1]
            for old in files[:-1]:
                to_delete.append(old)
            print(f"[KEEP]   {keep.name}")
            for d in files[:-1]:
                print(f"[DELETE] {d.name}")
            print()

    print(f"=== 削除対象合計: {len(to_delete)} ファイル ===")

    if dry_run:
        print("\n※ DRY RUNモードです。実際の削除は行っていません。")
        print("  削除を実行するには: python cleanup_duplicates.py --execute")
        return

    print("\n削除を開始します...")
    deleted = 0
    for f in to_delete:
        try:
            f.unlink()
            print(f"  削除済み: {f.name}")
            deleted += 1
        except Exception as e:
            print(f"  ERROR: {f.name} → {e}")

    print(f"\n完了: {deleted}/{len(to_delete)} ファイルを削除しました。")


if __name__ == "__main__":
    execute = "--execute" in sys.argv
    main(dry_run=not execute)
