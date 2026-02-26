"""環境変数の読み込みとバリデーション"""

import sys
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()


class Config:
    """note-digitizer の設定を管理するクラス"""

    REQUIRED_VARS = ["GEMINI_API_KEY", "NOTE_DISCORD_WEBHOOK_URL", "WATCH_FOLDER"]

    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.discord_webhook_url = os.getenv("NOTE_DISCORD_WEBHOOK_URL", "")
        self.watch_folder = Path(os.getenv("WATCH_FOLDER", ""))
        self.obsidian_vault_path = Path(
            os.getenv("OBSIDIAN_VAULT_PATH", r"C:\Users\north\Documents\Obsidian Vault")
        )
        self.obsidian_subfolder = os.getenv("OBSIDIAN_SUBFOLDER", "手書きノート")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self.debounce_seconds = int(os.getenv("DEBOUNCE_SECONDS", "3"))

    @property
    def output_dir(self) -> Path:
        return self.obsidian_vault_path / self.obsidian_subfolder

    def validate(self):
        """必須変数の存在チェック。欠落時はエラーメッセージを表示して終了。"""
        missing = []
        if not self.gemini_api_key:
            missing.append("GEMINI_API_KEY")
        if not self.discord_webhook_url:
            missing.append("NOTE_DISCORD_WEBHOOK_URL")
        if not str(self.watch_folder):
            missing.append("WATCH_FOLDER")

        if missing:
            print(f"[エラー] 必須環境変数が設定されていません: {', '.join(missing)}")
            print("  .env ファイルを確認してください。")
            sys.exit(1)

        if not self.watch_folder.exists():
            print(f"[エラー] 監視フォルダが存在しません: {self.watch_folder}")
            sys.exit(1)
