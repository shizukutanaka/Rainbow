# Rainbow ファイル転送（MVP）

Windows・スマホ間で簡単・安全にファイルを送受信できる、超シンプルなオープンソースWebアプリです。

## 特長（MVP仕様）
- Windows⇔スマホ/PC間でファイル送受信（同一LAN内）
- QRコードでスマホから即アクセス
- 複数ファイル同時アップロード対応
- 受信ファイル一覧・ダウンロード・削除
- シンプルなWeb UI（PC/スマホ両対応）
- 追加インストール不要（Pythonだけ）

## セットアップ
1. Python 3.8以上をインストール
2. 必要パッケージをインストール
   ```bash
   pip install -r requirements.txt
   ```
3. サーバーを起動
   ```bash
   python app.py
   ```
4. 表示されたURL（例: http://192.168.x.x:5000/）にアクセス
   - スマホからはQRコードを読み取ってアクセス

## 使い方
- ブラウザでアクセスし、ファイルをドラッグ＆ドロップまたは選択してアップロード
- 受信ファイルは一覧からダウンロード・削除可能
- スマホ・PCどちらからも利用OK

## 注意・制限事項
- 同一LAN内のみ利用可能（インターネット越し不可）
- 認証・暗号化なし（家庭・小規模利用向けMVP）
- 大容量ファイルはブラウザ依存

## ライセンス
MIT

## リンク
- [GitHubリポジトリ](https://github.com/shizukutanaka/Rainbow)
