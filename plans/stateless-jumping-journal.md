# note-digitizer スキル作成プラン

## Context

手書きノート（ツバメノート B5、4色ペン使用）の写真を自動でデジタル化するパイプラインを構築する。Google Driveで同期されたフォルダを監視し、Gemini Vision APIで解析、Obsidian互換Markdownとして保存、Discord通知まで一気通貫で自動化する。

元プラン（bubbly-dreaming-clover.md）からの主な変更点：
- **出力先**: `note-digitizer/outputs/` → **Obsidian Vault** (`C:\Users\north\Documents\Obsidian Vault\手書きノート\`)
- **Geminiプロンプト**: 「健太の専属秘書」ロール、4色ペンシステム、INFP-A対応の問いかけ生成
- **config/discord**: youtube-discord-notifierからの流用ではなく**ゼロから作成**

## ディレクトリ構成

```
note-digitizer/
├── SKILL.md                      # スキル定義（session-loggerスタイル準拠）
├── scripts/
│   ├── __init__.py
│   ├── config.py                 # 環境変数ロード・バリデーション
│   ├── watcher.py                # watchdogによるフォルダ監視
│   ├── analyzer.py               # Gemini Vision API解析（中核）
│   ├── markdown_writer.py        # Obsidian Vaultへの Markdown出力
│   ├── discord_notify.py         # Discord Webhook通知
│   └── main.py                   # エントリーポイント
├── references/
│   └── gemini_prompt.md          # Geminiプロンプトテンプレート
├── assets/
│   └── output_template.md        # 出力フォーマット例
├── .env.example
└── requirements.txt
```

## 環境変数

| 変数名 | 必須 | 説明 | デフォルト |
|---|---|---|---|
| `GEMINI_API_KEY` | Yes | Gemini APIキー | - |
| `NOTE_DISCORD_WEBHOOK_URL` | Yes | Discord Webhook URL | - |
| `WATCH_FOLDER` | Yes | 監視対象フォルダ（Google Drive同期先） | - |
| `OBSIDIAN_VAULT_PATH` | No | Obsidian Vaultパス | `C:\Users\north\Documents\Obsidian Vault` |
| `OBSIDIAN_SUBFOLDER` | No | Vault内サブフォルダ名 | `手書きノート` |
| `GEMINI_MODEL` | No | 使用モデル | `gemini-2.0-flash` |
| `DEBOUNCE_SECONDS` | No | ファイル検出後の待機秒数 | `3` |

## 実装ステップ

### Step 1: 初期化・設定ファイル
- `note-digitizer/` ディレクトリと上記構成を作成
- `requirements.txt`: watchdog, google-generativeai, requests, python-dotenv, Pillow
- `.env.example`: 全環境変数のテンプレート
- `scripts/__init__.py`: 空ファイル（パッケージ化）

### Step 2: config.py
- `python-dotenv`で`.env`ロード
- `Config`クラス: 必須変数のバリデーション（欠落時はエラーメッセージ付きで即終了）
- `output_dir`プロパティ: `OBSIDIAN_VAULT_PATH / OBSIDIAN_SUBFOLDER`を結合して返す
- デフォルト値の適用

### Step 3: references/gemini_prompt.md
- ロール定義: 「健太」の専属秘書兼思考整理パートナー
- 4色ペンシステム定義テーブル（黒=事実、赤=重要、青=外部情報、緑=アイデア）
- 解析ステップ: 全体把握 → 文字起こし → 要約 → 拡張提案
- 出力フォーマット指定（YAMLフロントマター + 色別セクション）
- `{date}`プレースホルダ（実行時に日付挿入）

### Step 4: assets/output_template.md
- 出力フォーマットの具体例（記入済みサンプル）

### Step 5: analyzer.py（中核）
- `google-generativeai` SDKでGemini Vision APIを呼び出し
- `references/gemini_prompt.md`をテンプレートとしてロード
- 画像をPILで読み込み、プロンプトと共にマルチモーダルAPI送信
- 戻り値: Geminiが生成したMarkdown文字列
- エラー時は例外をログ出力して再raise

### Step 6: markdown_writer.py
- 出力先: `C:\Users\north\Documents\Obsidian Vault\手書きノート\`
- 出力ディレクトリが存在しない場合は自動作成（`mkdir(parents=True, exist_ok=True)`）
- ファイル名: `YYYYMMDD_HHMMSS_元ファイル名.md`
- エンコーディング: UTF-8

### Step 7: discord_notify.py
- `requests`でDiscord Webhook送信
- Embed: タイトル「📓 ノートを整理しました！」
- フィールド: タイトル、分類タグ、概要（200文字まで）、保存先パス
- 生成されたMarkdownからYAMLフロントマターを解析してメタデータ抽出
- タイムアウト10秒、通知失敗時はログのみ（パイプラインを停止しない）

### Step 8: watcher.py
- `watchdog.FileSystemEventHandler`で`.jpg`, `.jpeg`, `.png`, `.heic`, `.webp`を監視
- デバウンス処理: `threading.Timer`で`DEBOUNCE_SECONDS`秒待機（Google Drive同期完了待ち）
- パイプライン: 検出 → analyzer → markdown_writer → discord_notify
- 重複イベント排除

### Step 9: main.py
- 全コンポーネントの統合・初期化
- `Config()` → フォルダ存在確認 → watchdog Observer起動
- Ctrl+Cでのgraceful shutdown（signal対応）
- 起動・終了メッセージを日本語でコンソール出力

### Step 10: SKILL.md
- [session-logger/SKILL.md](session-logger/SKILL.md) のスタイル準拠
- YAML frontmatter: `name: note-digitizer`, `description: "This skill should be used when..."`
- セクション: 概要、セットアップ、使い方、4色ペンシステム、出力フォーマット、Discord通知、トラブルシューティング

### Step 11: README.md更新
- リポジトリルートのREADME.mdにnote-digitizerを追加

## 注意点

- **Windowsパス**: `pathlib.Path`を全面使用（文字列結合禁止）
- **HEIC対応**: Pillowは非対応のため`pillow-heif`をrequirements.txtに追加
- **Geminiレスポンス**: YAMLフロントマターが不正な場合のフォールバック処理
- **長時間プロセス**: ログ出力を`logging`モジュールで統一

## 検証方法

1. `.env`に各APIキー・パスを設定
2. `pip install -r requirements.txt`で依存関係インストール
3. `python -m note-digitizer.scripts.main`で起動
4. 監視フォルダに手書きノート画像を配置
5. Obsidian Vault（`手書きノート/`）にMarkdownが生成されることを確認
6. Discordに通知Embedが届くことを確認
7. 不正な画像・API障害時のエラーハンドリングを確認
