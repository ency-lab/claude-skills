# 計画: note-digitizer ログイン時自動起動

## Context

現在、ウォッチャーは毎回2つのコマンドを手動入力して起動している。
Windowsのタスクスケジューラに登録することで、ログイン時に自動起動させる。

## 実装方針

### 1. `start_watcher.bat` を作成

**パス:** `note-digitizer/start_watcher.bat`

- `pythonw.exe`（コンソールウィンドウなし）でウォッチャーを起動
- ログを `note-digitizer/data/watcher.log` に追記保存（デバッグ用）

```bat
@echo off
cd /d C:\Users\north\development\claude-skills\note-digitizer
C:\Users\north\AppData\Local\Programs\Python\Python313\pythonw.exe scripts/__main__.py >> data\watcher.log 2>&1
```

> pythonw.exe を使うと、バックグラウンドで動作しコンソールウィンドウが表示されない

### 2. タスクスケジューラへの登録

ユーザーが PowerShell で1回だけ実行するコマンドを提供する（管理者権限不要）。

```powershell
$action = New-ScheduledTaskAction `
    -Execute "C:\Users\north\development\claude-skills\note-digitizer\start_watcher.bat"
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 0)
Register-ScheduledTask `
    -TaskName "NoteDigitizer" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "手書きノート自動デジタル化ウォッチャー"
```

## 変更ファイル

| ファイル | 操作 |
|---|---|
| `note-digitizer/start_watcher.bat` | 新規作成 |
| `note-digitizer/data/watcher.log` | 自動生成（ログ出力先） |

## 確認方法

1. `start_watcher.bat` をダブルクリックして起動確認（コンソール非表示、タスクマネージャに `pythonw.exe` が表示される）
2. タスクスケジューラ登録後、一度サインアウト→サインインして自動起動することを確認
3. `note-digitizer/data/watcher.log` にログが出力されることを確認
4. 監視フォルダにPDFを入れてObsidianとDiscordに通知が届くことを確認
