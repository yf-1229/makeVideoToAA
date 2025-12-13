# videoToAscii.py - ASCII アート動画プレイヤー

YouTube 動画やローカル動画ファイルを ASCII アートとしてターミナルで再生するツールです。
カラー表示に対応し、Windows/Linux/macOS で動作します。

## 機能

- YouTube 動画のダウンロードと ASCII アート再生（yt-dlp 使用）
- ローカル動画ファイルの ASCII アート再生
- ANSI カラー表示（64色パレット、4-level per channel）
- 30分を超える動画の自動検出と先頭30分のみの処理オプション
- Windows コンソールでの ANSI エスケープシーケンス自動有効化
- Google Sheets 連携機能（オプション、別途設定が必要）

## システム要件

### 共通要件
- Python 3.7 以上
- FFmpeg（動画処理に必須）

### Windows の場合
- Windows 10 以降（ANSI サポートのため）
- PowerShell または コマンドプロンプト

### Linux/macOS の場合
- 標準のターミナル（ANSI カラー対応）

---

## インストール手順

### Windows の場合

#### 1. Python のインストール
[Python 公式サイト](https://www.python.org/downloads/) から Python 3.7 以上をダウンロードしてインストールします。
インストール時に「Add Python to PATH」にチェックを入れてください。

#### 2. FFmpeg のインストール

**方法 A: Chocolatey を使用（推奨）**
```cmd
choco install ffmpeg
```

**方法 B: 手動インストール**
1. [FFmpeg 公式サイト](https://ffmpeg.org/download.html) から Windows 用バイナリをダウンロード
2. ZIP ファイルを展開し、`bin` フォルダを `C:\ffmpeg\bin` などに配置
3. システム環境変数 PATH に `C:\ffmpeg\bin` を追加

**FFmpeg の確認:**
```cmd
ffmpeg -version
```

#### 3. 仮想環境の作成（推奨）
```cmd
cd path\to\makeVideo--AA
python -m venv venv
venv\Scripts\activate.bat
```

#### 4. 依存パッケージのインストール
```cmd
pip install -r scripts\requirements-windows.txt
```

または個別にインストール:
```cmd
pip install opencv-python numpy yt-dlp gspread oauth2client requests
```

#### 5. 実行確認
```cmd
python videoToAscii.py --help
```

---

### Linux/macOS の場合

#### 1. Python のインストール
多くのディストリビューションでは Python 3 が標準でインストールされています。
インストールされていない場合:

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

**macOS (Homebrew):**
```bash
brew install python3
```

#### 2. FFmpeg のインストール

**Ubuntu/Debian:**
```bash
sudo apt install ffmpeg
```

**macOS (Homebrew):**
```bash
brew install ffmpeg
```

**FFmpeg の確認:**
```bash
ffmpeg -version
```

#### 3. 仮想環境の作成（推奨）
```bash
cd path/to/makeVideo--AA
python3 -m venv venv
source venv/bin/activate
```

#### 4. 依存パッケージのインストール
```bash
pip install opencv-python numpy yt-dlp gspread oauth2client requests
```

---

## 基本的な使い方

### Windows

**コマンドプロンプトの場合:**
```cmd
REM YouTube 動画を再生
run_videoToAscii.cmd "https://www.youtube.com/watch?v=XXXX"

REM ローカルファイルを再生
run_videoToAscii.cmd video.mp4

REM オプション付きで再生
run_videoToAscii.cmd video.mp4 --levels 4 --clahe
```

**PowerShell の場合:**
```powershell
# YouTube 動画を再生
python videoToAscii.py "https://www.youtube.com/watch?v=XXXX"

# ローカルファイルを再生
python videoToAscii.py video.mp4

# オプション付きで再生
python videoToAscii.py video.mp4 --levels 4 --clahe
```

### Linux/macOS

```bash
# YouTube 動画を再生
python3 videoToAscii.py "https://www.youtube.com/watch?v=XXXX"

# ローカルファイルを再生
python3 videoToAscii.py video.mp4

# オプション付きで再生
python3 videoToAscii.py video.mp4 --levels 4 --clahe
```

---

## コマンドラインオプション

```
usage: videoToAscii.py [-h] [--chars CHARS] [--aspect ASPECT] [--no-color]
                       [--gamma GAMMA] [--clahe] [--dither] [--levels LEVELS]
                       [--loop] [--no-clear] [--keep]
                       input

引数:
  input                 YouTube の URL またはローカル動画ファイルパス

オプション:
  -h, --help            ヘルプメッセージを表示
  --chars CHARS, -c CHARS
                        文字ランプ（左が濃い、デフォルト: "$@B%8&WM#*oahkbdpqwmZ0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,\"^`'. "）
  --aspect ASPECT, -a ASPECT
                        縦横補正（デフォルト: 0.55）
  --no-color            カラーを使わない（モノクロ表示）
  --gamma GAMMA         ガンマ補正（デフォルト: 1.0）
  --clahe               CLAHE を適用してコントラストを強める
  --dither              誤差拡散ディザ（速度低下注意）
  --levels LEVELS       チャネル当たりの量子化レベル（デフォルト: 4 → 4^3=64色）
  --loop                動画をループ再生
  --no-clear            開始時に画面をクリアしない
  --keep                ダウンロードしたファイルを削除せず残す
```

**注意:** width は 100 に固定されており、変更できません。

---

## Google Sheets 連携（オプション）

Google Sheets からプレイリストを取得して自動再生する機能を使用する場合は、以下の追加設定が必要です。

### 1. Google Cloud Platform でサービスアカウントを作成

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. プロジェクトを作成または選択
3. 「APIとサービス」→「認証情報」に移動
4. 「認証情報を作成」→「サービスアカウント」を選択
5. サービスアカウント名を入力して作成
6. 作成したサービスアカウントの詳細画面で「キー」タブを開く
7. 「鍵を追加」→「新しい鍵を作成」→「JSON」を選択
8. ダウンロードされた JSON ファイルを安全な場所に保存

### 2. Google Sheets API を有効化

1. Google Cloud Console で「APIとサービス」→「ライブラリ」に移動
2. "Google Sheets API" を検索して有効化

### 3. Google Sheets でシートを共有

1. Google Sheets でプレイリスト用のシートを作成
2. シートをサービスアカウントのメールアドレス（JSON ファイル内の `client_email`）と共有
3. 編集権限を付与

### 4. 環境変数の設定

**Windows (コマンドプロンプト):**
```cmd
set GOOGLE_CREDS=C:\path\to\service-account.json
```

**Windows (PowerShell):**
```powershell
$env:GOOGLE_CREDS="C:\path\to\service-account.json"
```

**Linux/macOS:**
```bash
export GOOGLE_CREDS=/path/to/service-account.json
```

恒久的に設定する場合は `.bashrc` または `.bash_profile` に追加してください。

### 5. Google Sheets 連携での実行

```cmd
REM Windows
run_videoToAscii.cmd --sheet-key YOUR_SHEET_KEY

REM Linux/macOS
python3 videoToAscii.py --sheet-key YOUR_SHEET_KEY
```

または、コマンドラインで直接指定:
```cmd
python videoToAscii.py --creds C:\path\to\service-account.json --sheet-key YOUR_SHEET_KEY
```

---

## Windows でのバックグラウンド実行

### 方法 1: NSSM (Non-Sucking Service Manager) を使用

1. [NSSM 公式サイト](https://nssm.cc/download) から NSSM をダウンロード
2. 管理者権限でコマンドプロンプトを開く
3. サービスをインストール:
```cmd
nssm install VideoToAsciiService "C:\path\to\python.exe" "C:\path\to\makeVideo--AA\videoToAscii.py" --sheet-key YOUR_SHEET_KEY
```
4. 環境変数を設定（NSSM GUI から設定可能）:
```cmd
nssm set VideoToAsciiService AppEnvironmentExtra GOOGLE_CREDS=C:\path\to\service-account.json
```
5. サービスを開始:
```cmd
nssm start VideoToAsciiService
```

### 方法 2: タスクスケジューラを使用

1. 「タスクスケジューラ」を開く
2. 「タスクの作成」を選択
3. 「全般」タブ:
   - 名前: VideoToAscii Monitor
   - 「ユーザーがログオンしているときのみ実行する」を選択
4. 「トリガー」タブ:
   - 「新規」をクリックして起動タイミングを設定（例: システム起動時）
5. 「操作」タブ:
   - 「新規」→「プログラムの開始」
   - プログラム/スクリプト: `C:\path\to\makeVideo--AA\run_videoToAscii.cmd`
   - 引数の追加: `--sheet-key YOUR_SHEET_KEY`
6. 「OK」をクリックしてタスクを保存

---

## トラブルシューティング

### Windows で ANSI カラーが表示されない

**解決策:**
- Windows 10 バージョン 1511 以降であることを確認
- Windows Terminal または PowerShell 7 以降を使用
- レガシーコンソールの場合は「プロパティ」で「レガシーコンソールを使う」のチェックを外す

### FFmpeg が見つからないエラー

**解決策:**
```cmd
REM FFmpeg がインストールされているか確認
ffmpeg -version

REM PATH に追加されているか確認
echo %PATH%
```

### YouTube 動画のダウンロードに失敗

**解決策:**
- yt-dlp を最新版に更新: `pip install --upgrade yt-dlp`
- URL が正しいか確認（https://www.youtube.com/... または https://youtu.be/...）
- FFmpeg がインストールされているか確認

### モジュールが見つからないエラー

**解決策:**
```cmd
REM 必要なパッケージを再インストール
pip install --upgrade opencv-python numpy yt-dlp
```

### 30分を超える動画について

プログラムは自動的に検出し、以下のオプションを提示します:
1. 先頭30分だけ処理して続行（`y` を入力）
2. キャンセルして短い動画を指定（`n` を入力）

---

## テスト手順

### Windows でのテスト

1. **環境確認:**
```cmd
python --version
ffmpeg -version
pip list | findstr "opencv-python numpy yt-dlp"
```

2. **ローカルファイルでテスト:**
```cmd
REM 短いテスト動画を用意して実行
run_videoToAscii.cmd test.mp4
```

3. **YouTube 動画でテスト:**
```cmd
REM 短い YouTube 動画で試す（例: 公式のテスト動画）
run_videoToAscii.cmd "https://www.youtube.com/watch?v=jNQXAC9IVRw"
```

4. **Google Sheets 連携テスト（オプション）:**
```cmd
set GOOGLE_CREDS=C:\path\to\service-account.json
run_videoToAscii.cmd --sheet-key YOUR_SHEET_KEY
```

### Linux/macOS でのテスト

1. **環境確認:**
```bash
python3 --version
ffmpeg -version
pip list | grep -E "opencv-python|numpy|yt-dlp"
```

2. **ローカルファイルでテスト:**
```bash
python3 videoToAscii.py test.mp4
```

3. **YouTube 動画でテスト:**
```bash
python3 videoToAscii.py "https://www.youtube.com/watch?v=jNQXAC9IVRw"
```

4. **Google Sheets 連携テスト（オプション）:**
```bash
export GOOGLE_CREDS=/path/to/service-account.json
python3 videoToAscii.py --sheet-key YOUR_SHEET_KEY
```

---

## プロジェクト構造

```
makeVideo--AA/
├── videoToAscii.py              # メインスクリプト
├── run_videoToAscii.cmd         # Windows用起動スクリプト
├── scripts/
│   └── requirements-windows.txt # Windows用依存パッケージリスト
└── README.md                    # このファイル
```

---

## ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。

---

## 貢献

バグ報告や機能リクエストは Issue で受け付けています。
プルリクエストも歓迎します。

---

## 技術仕様

- **幅:** 100文字固定
- **カラーパレット:** 64色（4-level per channel: 4^3 = 64）
- **文字ランプ:** 濃度ベースの ASCII 文字（ブロック文字は不使用）
- **最大処理時間:** 30分（それ以上は先頭30分のみ処理）
- **フレームレート:** 入力動画の FPS を維持

---

## 既知の制限事項

- width は 100 に固定されており、コマンドラインオプションで変更できません
- 30分を超える動画は先頭30分のみ処理されます（インタラクティブ確認あり）
- YouTube の HTTPS リンク以外の URL は受け付けません（セキュリティ制限）
- CI 環境など非対話的な環境では動作しない場合があります

---

## 更新履歴

### v1.1.0 (2024-12)
- Windows サポートを追加（ANSI VT 処理の自動有効化）
- Windows 用バッチランチャー `run_videoToAscii.cmd` を追加
- 包括的な日本語 README を追加
- Windows 用セットアップ手順とトラブルシューティングを追加

### v1.0.0
- 初回リリース
- ASCII アート動画再生機能
- YouTube ダウンロード機能
- Google Sheets 連携機能（オプション）
