# Fix: note-digitizer 起動失敗・自動起動問題

## ステータス: 実装中

## 問題概要

note-digitizerが起動せず、Windows再起動時にも自動起動しない。

## 根本原因分析

### 原因1: PATHがWindows Storeスタブを参照している（致命的）

`python` コマンドが `C:\Users\keft-\AppData\Local\Microsoft\WindowsApps\python.exe`（Windows Storeスタブ）に解決される。このスタブはPythonをインストールさせるためのリダイレクタであり、実行すると "Python " と出力してexit code 49で即終了する。

- **実際のPython**: `C:\Users\keft-\AppData\Local\Programs\Python\Python313\python.exe`（Python 3.13.5）
- **`start.bat`**: `python -m scripts` と記述しているため、スタブが実行される
- **ログの証拠**: ログに "Python " のみ出力され、アプリケーションバナーやエラーメッセージが一切ない

### 原因2: スタートアップフォルダのbatファイルも同じ問題を持つ

`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\note-digitizer.bat` にログイン時自動起動が登録されているが、このファイルも `python -m scripts` を使用しているため同じスタブ問題で失敗する。

### 原因3: batファイルにエラーハンドリングがない（副次的）

- Python実行に失敗してもバッチファイルはサイレントに終了する
- Google Driveの`G:\`マウントが遅延した場合への対策がない

## 修正計画

### Step 1: スタートアップフォルダの note-digitizer.bat を修正

**変更内容:**
- `python` の代わりに `py -3`（Python Launcher）を使用する
  - `py` は `C:\Windows\py.exe` にインストールされるWindows公式ランチャー
  - 現在 `py --list` で Python 3.13 が検出されることを確認済み
  - Windows Storeスタブの影響を受けない
- Pythonの存在チェックを追加
- Google Drive（`G:\`）マウント待機ロジックを追加（最大60秒）
- 起動失敗時のエラーメッセージをログに記録

### Step 2: プロジェクト内の start.bat も同様に修正

スタートアップフォルダのbatと同じ内容に同期する。

### Step 3: 動作検証

手動実行して正常起動を確認する。

## 検証手順

1. 修正後、手動で bat を実行してログに正常起動が記録されることを確認
2. ログファイルにアプリケーションバナー（`Note Digitizer - 手書きノート自動デジタル化`）が出力されることを確認
