@echo off
REM Note Digitizer - Windows startup launcher
REM Windowsタスクスケジューラからログイン時に自動呼び出される

set PROJECT_DIR=C:\development\claude-skills\note-digitizer
set LOG_DIR=%PROJECT_DIR%\logs
set LOG_FILE=%LOG_DIR%\note-digitizer.log

REM ログディレクトリを作成（存在しない場合）
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM 起動マーカーをログに追記
echo ===== Starting Note Digitizer %DATE% %TIME% ===== >> "%LOG_FILE%"

REM パイプライン起動（全出力をログに追記）
cd /d "%PROJECT_DIR%"
python -m scripts >> "%LOG_FILE%" 2>&1
