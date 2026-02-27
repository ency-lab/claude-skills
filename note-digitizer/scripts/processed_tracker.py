"""処理済みファイルの管理（重複処理防止）"""

import hashlib
import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Google Drive の同期競合サフィックス " (1)", " (2)" 等を除去するパターン
# (?=\.[^.]+$) の先読みで「直前が .拡張子 の末尾」の場合のみマッチ
_GDRIVE_SUFFIX_RE = re.compile(r"\s*\(\d+\)(?=\.[^.]+$)")

# サイズ判定の誤差許容率（5%）
_SIZE_TOLERANCE = 0.05


def normalize_filename(name: str) -> str:
    """Google Drive の (n) 競合サフィックスを除去した正規化キーを返す。

    例:
        'スキャン_1013 (1).pdf'  -> 'スキャン_1013.pdf'
        'スキャン_1013 (2).pdf'  -> 'スキャン_1013.pdf'
        'スキャン_1013.pdf'      -> 'スキャン_1013.pdf'  (変化なし)
        'report(v2).pdf'        -> 'report(v2).pdf'    (本文中の括弧は除去しない)
    """
    return _GDRIVE_SUFFIX_RE.sub("", name)


class ProcessedTracker:
    """処理済みファイルをJSONで永続管理し、同一ファイルの重複処理を防ぐ。

    ファイル名を正規化（Google Drive の (n) サフィックスを除去）したキーと
    MD5ハッシュ＋ファイルサイズで同一性を判定する。

    JSONスキーマ:
        { "スキャン_1013.pdf": { "hash": "<md5>", "size": <bytes> }, ... }

    旧形式 { "スキャン_1013.pdf": "<md5>" } は起動時に自動マイグレーションされる。
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._processed: dict[str, dict] = {}  # normalized_filename -> {hash, size}
        self._load()

    def _load(self):
        if self.db_path.exists():
            try:
                raw = json.loads(self.db_path.read_text(encoding="utf-8"))
                # 旧形式 {filename: md5str} を検出して自動マイグレーション
                if raw and isinstance(next(iter(raw.values())), str):
                    logger.info("旧形式DBを新形式に自動移行します: %d件", len(raw))
                    migrated: dict[str, dict] = {}
                    for filename, md5 in raw.items():
                        norm_key = normalize_filename(filename)
                        # 同一正規化キーに複数エントリがある場合は最初のものを採用
                        if norm_key not in migrated:
                            migrated[norm_key] = {"hash": md5, "size": None}
                    self._processed = migrated
                    self._save()
                    logger.info(
                        "DB移行完了: %d件 -> %d件（重複キーを統合）",
                        len(raw),
                        len(migrated),
                    )
                else:
                    self._processed = raw
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
        """正規化キー＋（ハッシュ一致 OR サイズ近似）で処理済みかどうかを返す。"""
        norm_key = normalize_filename(path.name)
        if norm_key not in self._processed:
            return False
        try:
            entry = self._processed[norm_key]
            # ハッシュ完全一致 → 確定的に処理済み
            if entry["hash"] == self._hash(path):
                return True
            # サイズ近似（5%以内）→ 同一スキャンとみなす
            stored_size = entry.get("size")
            if stored_size is not None:
                current_size = path.stat().st_size
                ratio = abs(stored_size - current_size) / max(
                    stored_size, current_size, 1
                )
                if ratio <= _SIZE_TOLERANCE:
                    logger.info(
                        "サイズ近似で重複検出: %s (%d vs %d bytes)",
                        path.name,
                        stored_size,
                        current_size,
                    )
                    return True
            return False
        except Exception:
            return False

    def mark_processed(self, path: Path):
        """正規化キーで処理済みとして登録し、DBを保存する。"""
        try:
            norm_key = normalize_filename(path.name)
            self._processed[norm_key] = {
                "hash": self._hash(path),
                "size": path.stat().st_size,
            }
            self._save()
            logger.info("処理済み登録: %s (キー: %s)", path.name, norm_key)
        except Exception as e:
            logger.warning("処理済み登録失敗: %s (%s)", path.name, e)
