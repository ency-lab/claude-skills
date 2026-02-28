---
name: note-digitizer
description: このスキルは、手書きノートのデジタル化パイプラインのセットアップ、起動・停止、トラブルシューティングが必要なときに使用される。Google Drive同期フォルダを監視し、Gemini Vision APIで4色ペンシステムに基づく解析を行い、Obsidian互換Markdownとして保存、Discord通知まで自動実行する。
---

# Note Digitizer

## 概要

手書きノート（ツバメノート B5、4色ペン使用）の写真を自動でデジタル化するPythonパイプライン。フォルダ監視 → Gemini Vision API解析 → Obsidian Vault保存 → Discord通知を一気通貫で自動実行する。

## セットアップ

### 1. 依存関係のインストール

```bash
cd note-digitizer
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env.example` を `.env` にコピーし、以下を設定する。

| 変数名 | 必須 | 説明 |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Gemini APIキー |
| `NOTE_DISCORD_WEBHOOK_URL` | Yes | Discord Webhook URL |
| `WATCH_FOLDER` | Yes | 監視対象フォルダ（Google Drive同期先） |
| `OBSIDIAN_VAULT_PATH` | No | Obsidian Vaultパス（デフォルト: `%USERPROFILE%\Documents\Obsidian Vault`） |
| `OBSIDIAN_SUBFOLDER` | No | Vault内サブフォルダ名（デフォルト: `手書きノート`） |
| `GEMINI_MODEL` | No | 使用モデル（デフォルト: `gemini-2.0-flash`） |
| `DEBOUNCE_SECONDS` | No | ファイル検出後の待機秒数（デフォルト: `3`） |

## 起動タイミング

- ユーザーが `/note-digitizer` を実行したとき
- ユーザーが「note-digitizerを起動して」「パイプラインの状態を確認して」「監視を止めて」等と依頼したとき
- Windowsタスクスケジューラによりログイン時に自動起動される（`start.bat` 経由、Claudeは関与しない）

## 実行手順

### 起動を依頼された場合

1. タスクスケジューラ経由での起動を試みる（推奨）
   ```bash
   schtasks /Run /TN "NoteDigitizer"
   ```
2. タスクが登録されていない場合は直接実行する
   ```bash
   cd C:\development\claude-skills\note-digitizer && python -m scripts
   ```
3. ログで起動確認する
   - ログパス: `C:\development\claude-skills\note-digitizer\logs\note-digitizer.log`
4. 起動状況をユーザーに報告する

### 停止を依頼された場合

1. タスクスケジューラ経由で停止する
   ```bash
   schtasks /End /TN "NoteDigitizer"
   ```
2. 停止確認後、ユーザーに報告する

### 状態確認を依頼された場合

1. ログファイルの最新エントリを確認する
   - ログパス: `C:\development\claude-skills\note-digitizer\logs\note-digitizer.log`
2. 状態をユーザーに報告する

### トラブルシューティングを依頼された場合

1. ログファイルを確認してエラー内容を特定する
2. 本ドキュメントの「トラブルシューティング」セクションを参照して対処する
3. 必要に応じて `.env` ファイルの設定を確認する
4. 対処内容と結果をユーザーに報告する

## 使い方（参考）

### パイプラインの起動

```bash
cd C:\development\claude-skills\note-digitizer
python -m scripts
```

監視フォルダに `.jpg`, `.jpeg`, `.png`, `.heic`, `.webp` の画像を配置すると、自動で解析・保存・通知が実行される。

### 停止

`Ctrl+C` で安全に停止する。

### 自動起動（Windowsログイン時）

Windowsタスクスケジューラに `NoteDigitizer` タスクが登録されている場合、ログイン時に自動でwatcherが起動する。

- **ランチャー**: `start.bat`（プロジェクトルートに配置）
- **ログ**: `logs\note-digitizer.log`（起動時刻・処理ログを追記記録）
- **手動テスト**: `schtasks /Run /TN "NoteDigitizer"`
- **停止**: タスクマネージャーでPythonプロセスを終了するか、`schtasks /End /TN "NoteDigitizer"`

## 4色ペンシステム

| 色 | 意味 | 整理方針 |
|---|---|---|
| 黒 | 事実・行動・記録 | 箇条書き、[ ]タスク形式 |
| 赤 | 重要箇所 | 強調表示 |
| 青 | 外部情報・ソース | 引用・参照として区別 |
| 緑 | アイデア・気づき | 創造性の種として最重要扱い |

## 出力フォーマット

Obsidian互換のYAMLフロントマター付きMarkdownとして出力される。出力先は `OBSIDIAN_VAULT_PATH/OBSIDIAN_SUBFOLDER/` ディレクトリ。ファイル名は `YYYYMMDD_HHMMSS_元ファイル名.md` 形式。

具体的な出力例は `assets/output_template.md` を参照。

## Discord通知

処理完了時にEmbed形式で通知される。タイトル、分類、タグ、概要、保存先パスが表示される。

## トラブルシューティング

- **「必須環境変数が設定されていません」**: `.env` ファイルに必須変数がすべて設定されているか確認する
- **「監視フォルダが存在しません」**: `WATCH_FOLDER` のパスが正しいか、フォルダが実際に存在するか確認する
- **HEIC画像が処理されない**: `pillow-heif` がインストールされているか確認する（`pip install pillow-heif`）
- **Discord通知が届かない**: Webhook URLが有効か、Discord側でWebhookが削除されていないか確認する
