@echo off
REM ========================================================================
REM run_videoToAscii.cmd
REM Windows用のvideoToAscii.py起動スクリプト
REM
REM 使い方:
REM   run_videoToAscii.cmd "https://www.youtube.com/watch?v=XXXX"
REM   run_videoToAscii.cmd local.mp4 --levels 4 --clahe
REM
REM 環境変数 GOOGLE_CREDS を設定している場合、自動的に --creds オプションで渡されます
REM （Google Sheets 連携機能を使う場合に必要）
REM ========================================================================

REM 仮想環境がある場合はアクティベート（オプション）
REM 例: call venv\Scripts\activate.bat

REM GOOGLE_CREDS 環境変数が設定されている場合は --creds オプションを追加
set CREDS_ARG=
if defined GOOGLE_CREDS (
    set CREDS_ARG=--creds "%GOOGLE_CREDS%"
)

REM Python で videoToAscii.py を実行し、コマンドライン引数をすべて転送
python videoToAscii.py %* %CREDS_ARG%

REM 実行後に一時停止（エラーメッセージを確認できるように）
pause
