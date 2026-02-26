"""処理済みファイルの管理（重複処理防止）"""

import hashlib
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ProcessedTracker:
    """処理済みファイルをJSONで永続管理し、同一ファイルの重複処理を防ぐ。

    ファイル名 + MD5ハッシュで同一性を判定する。
    ファイル内容が変わった場合（再スキャンなど）は再処理される。
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._processed: dict[str, str] = {}  # filename -> md5hash
        self._load()

    def _load(self):
        if self.db_path.exists():
            try:
                self._processed = json.loads(self.db_path.read_text(encoding="utf-8"))
                logger.debug("処理済みDB読み込み: %d件", len(self._processed))
            except Exception as e:
                logger.warning("処理済みDB読み込み失敗、空で起動します: %s", e)
                self._processed = {}

    def _save(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path.write_text(
            json.dumps(self._processed, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _hash(self, path: Path) -> str:
        return hashlib.md5(path.read_bytes()).hexdigest()

    def is_processed(self, path: Path) -> bool:
        """同一ファイル（名前+内容）が処理済みかどうかを返す。"""
        key = path.name
        if key not in self._processed:
            return False
        try:
            return self._processed[key] == self._hash(path)
        except Exception:
            return False

    def mark_processed(self, path: Path):
        """ファイルを処理済みとして登録し、DBを保存する。"""
        try:
            self._processed[path.name] = self._hash(path)
            self._save()
            logger.info("処理済み登録: %s", path.name)
        except Exception as e:
            logger.warning("処理済み登録失敗: %s (%s)", path.name, e)
