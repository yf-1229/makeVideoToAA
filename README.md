# videoToAscii - ASCII アート動画プレイヤー

動画を ASCII アート（文字ベース）に変換して、ターミナルで再生するツールです。YouTube 動画やローカル動画ファイルを色付き ASCII アートとして表示できます。

## 機能

- YouTube 動画の再生（yt-dlp を使用）
- ローカル動画ファイルの再生
- 64 色カラー表示（4-level per channel 量子化）
- Google Sheets からの動画 URL ポーリング機能
- 30 分を超える動画の自動検出と処理オプション
- Windows および POSIX システム対応

## システム要件

- Python 3.7 以降
- FFmpeg（動画処理に必要）
- インターネット接続（YouTube 動画をダウンロードする場合）

## Windows セットアップ手順

### 1. Python のインストール

1. [Python 公式サイト](https://www.python.org/downloads/) から Python 3.7 以降をダウンロード
2. インストーラーを実行
3. **重要**: インストール時に「Add Python to PATH」にチェックを入れる
4. インストール完了後、コマンドプロンプトで確認:
   ```cmd
   python --version
   ```

### 2. 仮想環境の作成と有効化

プロジェクトディレクトリで仮想環境を作成することを推奨します。

#### コマンドプロンプト（cmd）での操作:

```cmd
REM プロジェクトディレクトリに移動
cd C:\path\to\makeVideo--AA

REM 仮想環境を作成
python -m venv venv

REM 仮想環境を有効化
venv\Scripts\activate.bat

REM 仮想環境が有効化されると、プロンプトに (venv) が表示されます
```

#### PowerShell での操作:

```powershell
# プロジェクトディレクトリに移動
cd C:\path\to\makeVideo--AA

# 仮想環境を作成
python -m venv venv

# 実行ポリシーの確認（初回のみ必要な場合があります）
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 仮想環境を有効化
.\venv\Scripts\Activate.ps1

# 仮想環境が有効化されると、プロンプトに (venv) が表示されます
```

### 3. 必要なパッケージのインストール

仮想環境を有効化した状態で、以下のコマンドを実行します:

```cmd
pip install -r scripts\requirements-windows.txt
```

または個別にインストール:

```cmd
pip install opencv-python numpy yt-dlp gspread oauth2client requests
```

### 4. FFmpeg のインストール

FFmpeg は動画処理に必須です。以下のいずれかの方法でインストールしてください。

#### 方法 A: Chocolatey を使用（推奨）

1. [Chocolatey](https://chocolatey.org/install) をインストール（管理者権限で PowerShell を実行）
2. FFmpeg をインストール:
   ```cmd
   choco install ffmpeg
   ```

#### 方法 B: 手動インストール

1. [FFmpeg 公式サイト](https://ffmpeg.org/download.html) から Windows 用ビルドをダウンロード
2. ダウンロードしたアーカイブを展開（例: `C:\ffmpeg`）
3. 環境変数 PATH に FFmpeg の bin ディレクトリを追加:
   - スタートメニューで「環境変数」を検索
   - 「システム環境変数の編集」を開く
   - 「環境変数」ボタンをクリック
   - 「Path」を選択して「編集」
   - 「新規」をクリックして `C:\ffmpeg\bin` を追加
   - すべてのダイアログで「OK」をクリック
4. 新しいコマンドプロンプトを開いて確認:
   ```cmd
   ffmpeg -version
   ```

### 5. Google サービスアカウントの設定（Google Sheets 連携を使用する場合）

Google Sheets から動画 URL をポーリングする機能を使用する場合、Google サービスアカウントが必要です。

#### サービスアカウントの作成:

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. プロジェクトを作成または選択
3. 「API とサービス」→「認証情報」に移動
4. 「認証情報を作成」→「サービスアカウント」を選択
5. サービスアカウント名を入力して作成
6. 作成したサービスアカウントをクリック
7. 「キー」タブで「鍵を追加」→「新しい鍵を作成」
8. 形式は「JSON」を選択してダウンロード
9. ダウンロードした JSON ファイルを安全な場所に保存（例: `C:\secrets\service-account.json`）

#### Google Sheets API の有効化:

1. Google Cloud Console で「API とサービス」→「ライブラリ」に移動
2. 「Google Sheets API」を検索して有効化
3. 「Google Drive API」も有効化

#### シートへのアクセス権限付与:

1. サービスアカウントの JSON ファイルを開く
2. `client_email` の値（例: `xxxx@yyyy.iam.gserviceaccount.com`）をコピー
3. 対象の Google Sheets を開く
4. 「共有」ボタンをクリック
5. コピーしたメールアドレスを追加し、「編集者」権限を付与

#### 環境変数の設定:

##### 一時的な設定（現在のセッションのみ有効）:

```cmd
set GOOGLE_CREDS=C:\secrets\service-account.json
```

##### 永続的な設定（システム全体で有効）:

```cmd
setx GOOGLE_CREDS "C:\secrets\service-account.json"
```

**注意**: `setx` を使用した場合、現在のコマンドプロンプトでは反映されません。新しいコマンドプロンプトを開く必要があります。

##### 環境変数の確認:

```cmd
echo %GOOGLE_CREDS%
```

## 使い方

### 基本的な使い方

#### YouTube 動画を再生:

```cmd
python videoToAscii.py "https://www.youtube.com/watch?v=XXXXXXXXXXX"
```

#### ローカル動画ファイルを再生:

```cmd
python videoToAscii.py C:\path\to\video.mp4
```

#### Windows バッチランチャーを使用:

```cmd
run_videoToAscii.cmd "https://www.youtube.com/watch?v=XXXXXXXXXXX"
```

または、エクスプローラーで `run_videoToAscii.cmd` をダブルクリック（引数なしで実行）

### オプション

- `--levels N`: チャネルごとの量子化レベル（デフォルト: 4 → 64 色）
- `--clahe`: CLAHE を適用してコントラストを強調
- `--gamma VALUE`: ガンマ補正（デフォルト: 1.0）
- `--no-color`: カラーを使用せず、モノクロで表示
- `--loop`: 動画をループ再生
- `--keep`: ダウンロードしたファイルを削除せずに保持

#### 例:

```cmd
python videoToAscii.py video.mp4 --levels 8 --clahe --loop
```

### Google Sheets ポーリング機能の使用

Google Sheets から動画 URL を自動的に取得して再生する機能があります。

#### 実行例:

```cmd
python videoToAscii.py --sheet-key YOUR_SHEET_KEY_HERE
```

**注意**: この機能を使用するには、`GOOGLE_CREDS` 環境変数が正しく設定されている必要があります。

## サービスとして実行（バックグラウンド実行）

### 方法 A: NSSM（Non-Sucking Service Manager）を使用

1. [NSSM](https://nssm.cc/download) をダウンロードして展開
2. 管理者権限でコマンドプロンプトを開く
3. サービスをインストール:
   ```cmd
   nssm install VideoToAscii "C:\path\to\venv\Scripts\python.exe" "C:\path\to\makeVideo--AA\videoToAscii.py" --sheet-key YOUR_SHEET_KEY
   ```
4. 環境変数を設定:
   ```cmd
   nssm set VideoToAscii AppEnvironmentExtra GOOGLE_CREDS=C:\secrets\service-account.json
   ```
5. サービスを開始:
   ```cmd
   nssm start VideoToAscii
   ```

### 方法 B: Windows タスクスケジューラを使用

1. スタートメニューから「タスクスケジューラ」を検索して起動
2. 「タスクの作成」をクリック
3. 「全般」タブ:
   - 名前: `VideoToAscii`
   - 「ユーザーがログオンしているかどうかにかかわらず実行する」を選択
4. 「トリガー」タブ:
   - 「新規」をクリック
   - 「コンピューターの起動時」を選択
5. 「操作」タブ:
   - 「新規」をクリック
   - プログラム: `C:\path\to\venv\Scripts\python.exe`
   - 引数: `C:\path\to\makeVideo--AA\videoToAscii.py --sheet-key YOUR_SHEET_KEY`
   - 開始場所: `C:\path\to\makeVideo--AA`
6. 「条件」タブと「設定」タブで必要に応じて調整
7. 「OK」をクリックして保存

## トラブルシューティング

### FFmpeg が見つからない

**エラー**: `ffmpeg: command not found` または `'ffmpeg' は、内部コマンドまたは外部コマンド...として認識されていません。`

**解決策**:
1. FFmpeg がインストールされているか確認
2. PATH 環境変数に FFmpeg の bin ディレクトリが含まれているか確認
3. 新しいコマンドプロンプトを開いて再試行

### 色が正しく表示されない

**症状**: ANSI エスケープシーケンスがそのまま表示される

**解決策**:
1. Windows 10 バージョン 1511 以降を使用していることを確認（古いバージョンは ANSI サポートが不完全）
2. Windows Terminal を使用（Microsoft Store から入手可能）
3. ConEmu や Cmder などのサードパーティ端末を使用

### Google Sheets 認証エラー

**エラー**: `gspread.exceptions.APIError` または認証関連エラー

**解決策**:
1. `GOOGLE_CREDS` 環境変数が正しく設定されているか確認
2. JSON ファイルのパスが正しいか確認（バックスラッシュのエスケープに注意）
3. Google Sheets API と Google Drive API が有効になっているか確認
4. サービスアカウントに対象シートへのアクセス権限が付与されているか確認

### 仮想環境が有効化されない（PowerShell）

**エラー**: `...cannot be loaded because running scripts is disabled on this system.`

**解決策**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### ダウンロードエラー

**エラー**: `yt-dlp によるダウンロードに失敗しました`

**解決策**:
1. インターネット接続を確認
2. yt-dlp を最新版に更新: `pip install --upgrade yt-dlp`
3. YouTube URL が正しいか確認
4. FFmpeg が正しくインストールされているか確認

## セキュリティに関する注意事項

### サービスアカウント JSON ファイルの保護

- JSON ファイルには機密情報が含まれています
- アクセス権限を制限してください:
  ```cmd
  icacls C:\secrets\service-account.json /inheritance:r /grant:r "%USERNAME%:F"
  ```
- ファイルをバージョン管理システム（Git など）にコミットしないでください
- 定期的にキーをローテーションすることを推奨

### 環境変数の管理

- 機密情報を含む環境変数は、ユーザーレベルまたはシステムレベルでのみ設定
- スクリプトやログファイルに平文で記録しない

### YouTube URL の検証

- このツールは YouTube の HTTPS URL のみを受け入れます
- 他のドメインやプロトコルはセキュリティ上の理由から拒否されます

## ライセンス

このプロジェクトのライセンスについては、リポジトリの LICENSE ファイルを参照してください。

## 貢献

バグ報告や機能リクエストは、GitHub の Issues で受け付けています。

## 関連リンク

- [Python 公式サイト](https://www.python.org/)
- [FFmpeg 公式サイト](https://ffmpeg.org/)
- [yt-dlp GitHub](https://github.com/yt-dlp/yt-dlp)
- [Google Cloud Console](https://console.cloud.google.com/)
- [gspread ドキュメント](https://docs.gspread.org/)
