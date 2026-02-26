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
| `OBSIDIAN_VAULT_PATH` | No | Obsidian Vaultパス（デフォルト: `C:\Users\north\Documents\Obsidian Vault`） |
| `OBSIDIAN_SUBFOLDER` | No | Vault内サブフォルダ名（デフォルト: `手書きノート`） |
| `GEMINI_MODEL` | No | 使用モデル（デフォルト: `gemini-2.0-flash`） |
| `DEBOUNCE_SECONDS` | No | ファイル検出後の待機秒数（デフォルト: `3`） |

## 使い方

### パイプラインの起動

```bash
python -m note-digitizer.scripts.main
```

監視フォルダに `.jpg`, `.jpeg`, `.png`, `.heic`, `.webp` の画像を配置すると、自動で解析・保存・通知が実行される。

### 停止

`Ctrl+C` で安全に停止する。

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
