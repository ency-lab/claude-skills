"""エントリーポイント: python scripts/ で実行可能にする"""

import sys
from pathlib import Path

# scriptsディレクトリをパスに追加して直接インポートを可能にする
sys.path.insert(0, str(Path(__file__).parent))

from main import main  # noqa: E402

main()
