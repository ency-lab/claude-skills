"""Discord Webhook通知"""

import logging
import re
from pathlib import Path

import requests

from config import Config

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """処理完了時にDiscordへEmbed通知を送信する"""

    def __init__(self, config: Config):
        self.webhook_url = config.discord_webhook_url

    def notify(self, content: str, output_path: Path):
        """生成されたMarkdownからメタデータを抽出してDiscord通知を送信する"""
        metadata = self._parse_frontmatter(content)
        title = metadata.get("title", output_path.stem)
        tags = metadata.get("tags", [])
        intent = metadata.get("intent", "")
        summary = self._extract_summary(content)

        embed = {
            "title": "\U0001f4d3 \u30ce\u30fc\u30c8\u3092\u6574\u7406\u3057\u307e\u3057\u305f\uff01",
            "color": 0x4CAF50,
            "fields": [
                {"name": "\u30bf\u30a4\u30c8\u30eb", "value": title, "inline": False},
                {"name": "\u5206\u985e", "value": intent or "\u672a\u5206\u985e", "inline": True},
                {"name": "\u30bf\u30b0", "value": ", ".join(tags) if tags else "\u306a\u3057", "inline": True},
                {"name": "\u6982\u8981", "value": summary[:200] if summary else "\u2014", "inline": False},
                {"name": "\u4fdd\u5b58\u5148", "value": str(output_path), "inline": False},
            ],
        }

        try:
            resp = requests.post(
                self.webhook_url, json={"embeds": [embed]}, timeout=10
            )
            resp.raise_for_status()
            logger.info("Discord通知送信完了")
        except requests.RequestException as e:
            logger.warning("Discord通知に失敗しました: %s", e)

    def _parse_frontmatter(self, content: str) -> dict:
        """YAMLフロントマターを簡易パースする"""
        match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not match:
            return {}

        result = {}
        for line in match.group(1).strip().split("\n"):
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()

            if key == "tags":
                # [tag1, tag2] 形式をパース
                tag_match = re.findall(r"[\w\u3000-\u9fff\uff00-\uffef]+", value)
                result[key] = tag_match
            else:
                result[key] = value

        return result

    def _extract_summary(self, content: str) -> str:
        """概要セクションのテキストを抽出する"""
        match = re.search(r"#\s*(?:\U0001f4dd\s*)?概要\s*\n+(.*?)(?=\n#|\Z)", content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""
