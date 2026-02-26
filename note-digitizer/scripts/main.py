"""Note Digitizer - 手書きノート自動デジタル化パイプライン"""

import logging
import signal
import sys
import time

from analyzer import NoteAnalyzer
from config import Config
from discord_notify import DiscordNotifier
from markdown_writer import MarkdownWriter
from processed_tracker import ProcessedTracker
from watcher import start_watching

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    print("=" * 50)
    print("  Note Digitizer - 手書きノート自動デジタル化")
    print("=" * 50)

    config = Config()
    config.validate()

    analyzer = NoteAnalyzer(config)
    writer = MarkdownWriter(config)
    notifier = DiscordNotifier(config)
    tracker = ProcessedTracker(config.processed_db_path)

    observer = start_watching(config, analyzer, writer, notifier, tracker)

    print()
    print(f"  監視フォルダ: {config.watch_folder}")
    print(f"  出力先:       {config.output_dir}")
    print(f"  モデル:       {config.gemini_model}")
    print()
    print("  Ctrl+C で終了します")
    print("=" * 50)

    shutdown = False

    def handle_signal(signum, frame):
        nonlocal shutdown
        shutdown = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        while not shutdown:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()
        print("\nフォルダ監視を終了しました。")


if __name__ == "__main__":
    main()
