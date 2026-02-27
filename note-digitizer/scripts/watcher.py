"""watchdogによるフォルダ監視"""

import logging
import queue
import threading
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver

from analyzer import NoteAnalyzer
from config import Config
from discord_notify import DiscordNotifier
from markdown_writer import MarkdownWriter
from processed_tracker import ProcessedTracker, normalize_filename

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".pdf"}


class NoteHandler(FileSystemEventHandler):
    """新しい画像ファイルを検出してパイプラインを実行する"""

    def __init__(
        self,
        config: Config,
        analyzer: NoteAnalyzer,
        writer: MarkdownWriter,
        notifier: DiscordNotifier,
        tracker: ProcessedTracker,
    ):
        self.config = config
        self.analyzer = analyzer
        self.writer = writer
        self.notifier = notifier
        self.tracker = tracker
        self._timers: dict[str, threading.Timer] = {}
        self._queued: set[str] = set()  # 正規化キーで二重エンキューを防止
        self._lock = threading.Lock()
        self._queue: queue.Queue = queue.Queue()
        # 単一ワーカースレッド（daemon=True でメイン終了時に自動停止）
        self._worker = threading.Thread(
            target=self._worker_loop, daemon=True, name="note-worker"
        )
        self._worker.start()

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return
        self._schedule(path)

    def on_modified(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return
        self._schedule(path)

    def _schedule(self, path: Path):
        """デバウンス処理: ファイル書き込み完了を待ってから _enqueue を呼ぶ"""
        key = str(path)
        with self._lock:
            if key in self._timers:
                self._timers[key].cancel()
            timer = threading.Timer(
                self.config.debounce_seconds, self._enqueue, args=[path]
            )
            self._timers[key] = timer
            timer.start()
            logger.debug("スケジュール登録: %s (%d秒後)", path.name, self.config.debounce_seconds)

    def _enqueue(self, path: Path):
        """デバウンス完了後に呼ばれる。正規化キーで重複チェックしてキューに積む。"""
        with self._lock:
            self._timers.pop(str(path), None)

        if not path.exists():
            logger.warning("ファイルが見つかりません（エンキュー時）: %s", path.name)
            return

        norm_key = normalize_filename(path.name)

        with self._lock:
            if norm_key in self._queued:
                logger.info(
                    "スキップ（キュー登録済み）: %s -> %s", path.name, norm_key
                )
                return
            if self.tracker.is_processed(path):
                logger.info("スキップ（処理済み）: %s", path.name)
                return
            self._queued.add(norm_key)

        logger.info("キューに追加: %s (キー: %s)", path.name, norm_key)
        self._queue.put(path)

    def _worker_loop(self):
        """単一ワーカー。キューから1件ずつ取り出して逐次処理する。"""
        logger.debug("ワーカースレッド開始")
        while True:
            try:
                path = self._queue.get(timeout=1)
            except queue.Empty:
                continue
            if path is None:  # シャットダウンシグナル
                logger.debug("ワーカースレッド終了シグナルを受信")
                self._queue.task_done()
                break
            try:
                self._process(path)
            finally:
                self._queue.task_done()
        logger.debug("ワーカースレッド終了")

    def _process(self, image_path: Path):
        """ワーカースレッドから逐次呼ばれる。並行処理なし。"""
        norm_key = normalize_filename(image_path.name)

        # 最終防御チェック（エンキュー後にファイル消失 or 別バリアントが先処理された場合）
        if not image_path.exists():
            logger.warning("ファイルが見つかりません（処理開始時）: %s", image_path.name)
            with self._lock:
                self._queued.discard(norm_key)
            return

        if self.tracker.is_processed(image_path):
            logger.info(
                "スキップ（処理済み、処理開始時確認）: %s", image_path.name
            )
            with self._lock:
                self._queued.discard(norm_key)
            return

        try:
            logger.info("=== パイプライン開始: %s ===", image_path.name)
            content = self.analyzer.analyze(image_path)
            output_path = self.writer.write(content, image_path.name)
            self.notifier.notify(content, output_path)
            self.tracker.mark_processed(image_path)
            logger.info(
                "=== パイプライン完了: %s -> %s ===",
                image_path.name,
                output_path.name,
            )
        except Exception:
            logger.exception("パイプライン処理中にエラーが発生しました: %s", image_path.name)
        finally:
            # エラー時もリセット → 次回同ファイルの再試行が可能
            with self._lock:
                self._queued.discard(norm_key)


def _is_virtual_drive(path: str) -> bool:
    """パスが仮想ドライブ（Google DriveFS等）上かどうかを判定する"""
    import ctypes
    import os
    drive = os.path.splitdrive(path)[0]
    if not drive:
        return False
    drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive + "\\")
    # DRIVE_REMOTE=4, DRIVE_NO_ROOT_DIR=1, DRIVE_UNKNOWN=0
    # Google DriveFSは通常DRIVE_REMOTE(4)またはDRIVE_FIXED(3)として見える
    # C:ドライブ(DRIVE_FIXED=3)以外はポーリングを使用する安全策
    return drive.upper() != "C:"


def start_watching(
    config: Config,
    analyzer: NoteAnalyzer,
    writer: MarkdownWriter,
    notifier: DiscordNotifier,
    tracker: ProcessedTracker,
) -> Observer:
    """フォルダ監視を開始してObserverインスタンスを返す"""
    handler = NoteHandler(config, analyzer, writer, notifier, tracker)
    # Google DriveFS等の仮想ファイルシステムではReadDirectoryChangesWが
    # イベントを発火しないため、PollingObserverを使用する
    watch_path = str(config.watch_folder)
    use_polling = _is_virtual_drive(watch_path)
    if use_polling:
        observer = PollingObserver(timeout=config.debounce_seconds)
        logger.info("PollingObserver使用（仮想ドライブ検出）: %s", watch_path)
    else:
        observer = Observer()
    observer.schedule(handler, watch_path, recursive=False)
    observer.start()
    logger.info("フォルダ監視を開始しました: %s", config.watch_folder)
    return observer
