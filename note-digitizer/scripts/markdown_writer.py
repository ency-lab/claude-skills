"""Obsidian VaultへのMarkdown出力"""

import logging
from datetime import datetime
from pathlib import Path

from .config import Config

logger = logging.getLogger(__name__)


class MarkdownWriter:
    """生成されたMarkdownをObsidian Vaultに保存する"""

    def __init__(self, config: Config):
        self.output_dir = config.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("出力先: %s", self.output_dir)

    def write(self, content: str, source_filename: str) -> Path:
        """Markdownを保存してファイルパスを返す"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = Path(source_filename).stem
        output_path = self.output_dir / f"{timestamp}_{stem}.md"

        output_path.write_text(content, encoding="utf-8")
        logger.info("保存完了: %s", output_path.name)
        return output_path
