"""watchdogによるフォルダ監視"""

import logging
import threading
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from analyzer import NoteAnalyzer
from config import Config
from discord_notify import DiscordNotifier
from markdown_writer import MarkdownWriter
from processed_tracker import ProcessedTracker

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
        self._in_progress: set[str] = set()  # 現在処理中のファイルパス
        self._lock = threading.Lock()

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
        """デバウンス処理: ファイル書き込み完了を待ってから処理を開始する"""
        key = str(path)
        with self._lock:
            if key in self._timers:
                self._timers[key].cancel()
            timer = threading.Timer(
                self.config.debounce_seconds, self._process, args=[path]
            )
            self._timers[key] = timer
            timer.start()
            logger.debug("スケジュール登録: %s (%d秒後)", path.name, self.config.debounce_seconds)

    def _process(self, image_path: Path):
        """画像解析→Markdown保存→Discord通知のパイプラインを実行する"""
        with self._lock:
            self._timers.pop(str(image_path), None)

        if not image_path.exists():
            logger.warning("ファイルが見つかりません: %s", image_path)
            return

        key = str(image_path)
        with self._lock:
            if key in self._in_progress:
                logger.info("スキップ（処理中）: %s", image_path.name)
                return
            if self.tracker.is_processed(image_path):
                logger.info("スキップ（処理済み）: %s", image_path.name)
                return
            self._in_progress.add(key)

        try:
            logger.info("=== パイプライン開始: %s ===", image_path.name)
            content = self.analyzer.analyze(image_path)
            output_path = self.writer.write(content, image_path.name)
            self.notifier.notify(content, output_path)
            self.tracker.mark_processed(image_path)
            logger.info("=== パイプライン完了: %s → %s ===", image_path.name, output_path.name)
        except Exception:
            logger.exception("パイプライン処理中にエラーが発生しました: %s", image_path.name)
        finally:
            with self._lock:
                self._in_progress.discard(key)


def start_watching(
    config: Config,
    analyzer: NoteAnalyzer,
    writer: MarkdownWriter,
    notifier: DiscordNotifier,
    tracker: ProcessedTracker,
) -> Observer:
    """フォルダ監視を開始してObserverインスタンスを返す"""
    handler = NoteHandler(config, analyzer, writer, notifier, tracker)
    observer = Observer()
    observer.schedule(handler, str(config.watch_folder), recursive=False)
    observer.start()
    logger.info("フォルダ監視を開始しました: %s", config.watch_folder)
    return observer
