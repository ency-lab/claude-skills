"""Gemini Vision APIによる手書きノート解析"""

import logging
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import types
import PIL.Image

PDF_EXTENSIONS = {".pdf"}

from config import Config

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "references" / "gemini_prompt.md"


class NoteAnalyzer:
    """手書きノート画像をGemini Vision APIで解析し、Markdownを生成する"""

    def __init__(self, config: Config):
        self.client = genai.Client(api_key=config.gemini_api_key)
        self.model_name = config.gemini_model
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> str:
        """プロンプトテンプレートを読み込む"""
        return PROMPT_PATH.read_text(encoding="utf-8")

    def analyze(self, image_path: Path) -> str:
        """画像またはPDFを解析してMarkdown文字列を返す"""
        logger.info("解析開始: %s", image_path.name)

        today = datetime.now().strftime("%Y-%m-%d")
        prompt = self.prompt_template.replace("{date}", today)

        if image_path.suffix.lower() in PDF_EXTENSIONS:
            # PDFはバイトデータとして送信
            pdf_bytes = image_path.read_bytes()
            file_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
            contents = [prompt, file_part]
        else:
            # 画像はPILで読み込み
            image = PIL.Image.open(image_path)
            contents = [prompt, image]

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
        )
        content = response.text

        # Geminiがコードブロックで囲んで返す場合の除去
        if content.startswith("```markdown"):
            content = content[len("```markdown"):].strip()
        if content.startswith("```"):
            content = content[3:].strip()
        if content.endswith("```"):
            content = content[:-3].strip()

        logger.info("解析完了: %s", image_path.name)
        return content
