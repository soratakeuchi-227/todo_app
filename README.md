# Todo App

Flaskで作成したタスク管理アプリケーションです。

## 機能

- **ユーザー認証**: ユーザー登録・ログイン・ログアウト
- **タスク管理**: タスクの作成・編集・削除・完了切替
- **サブタスク**: タスクにサブタスクを追加可能
- **カテゴリ**: タスクをカテゴリで分類（カラー設定可能）
- **優先度**: 高・中・低の3段階で優先度を設定
- **スケジュール**: 日別・週別のスケジュール表示

## 技術スタック

- Python 3
- Flask 3.0
- Flask-SQLAlchemy（データベース）
- Flask-Login（認証）
- Flask-WTF（フォーム）
- SQLite

## セットアップ

### 1. リポジトリをクローン

```bash
git clone https://github.com/soratakeuchi-227/todo_app.git
cd todo_app
```

### 2. 仮想環境を作成・有効化

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. 依存パッケージをインストール

```bash
pip install -r requirements.txt
```

### 4. アプリを起動

```bash
python app.py
```

ブラウザで http://127.0.0.1:5000 にアクセスしてください。

## スクリーンショット

（スクリーンショットを追加予定）

## ライセンス

MIT
