@echo off
REM Note Digitizer - Windows startup launcher
REM スタートアップフォルダからログイン時に自動呼び出される

set PROJECT_DIR=C:\development\claude-skills\note-digitizer
set LOG_DIR=%PROJECT_DIR%\logs
set LOG_FILE=%LOG_DIR%\note-digitizer.log

REM ログディレクトリを作成（存在しない場合）
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM 起動マーカーをログに追記
echo ===== Starting Note Digitizer %DATE% %TIME% ===== >> "%LOG_FILE%"

REM Python Launcherの存在チェック
py -3 --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3 not found via py launcher >> "%LOG_FILE%"
    exit /b 1
)

REM Google Driveマウント待機（最大60秒）
set WAIT_COUNT=0
:wait_drive
if exist "G:\マイドライブ\00_Note_Inbox" goto :drive_ready
set /a WAIT_COUNT+=1
if %WAIT_COUNT% geq 12 (
    echo [ERROR] Google Drive not mounted after 60 seconds >> "%LOG_FILE%"
    exit /b 1
)
echo [INFO] Waiting for Google Drive... (%WAIT_COUNT%/12) >> "%LOG_FILE%"
timeout /t 5 /nobreak >nul
goto :wait_drive

:drive_ready
cd /d "%PROJECT_DIR%"
py -3 -m scripts >> "%LOG_FILE%" 2>&1
set EXIT_CODE=%ERRORLEVEL%

if %EXIT_CODE% neq 0 (
    echo [ERROR] Note Digitizer exited with error code %EXIT_CODE% >> "%LOG_FILE%"
)
