# 【Flask入門】PythonでTodoアプリを作ってみよう

## はじめに

Pythonの軽量WebフレームワークFlaskを使って、シンプルなTodoアプリを作成します。この記事では、Flaskの基本的な使い方からデータベース連携まで、ステップバイステップで解説します。

## 対象読者

- Pythonの基本文法を理解している方
- Webアプリケーション開発を始めたい方
- Flaskを触ってみたい方

## 完成イメージ

今回作成するTodoアプリの機能：
- タスクの作成・編集・削除
- タスクの完了/未完了の切り替え
- 優先度とカテゴリの設定
- 期限の設定

## 環境構築

### 必要なもの

- Python 3.8以上
- pip（Pythonパッケージマネージャー）

### プロジェクトのセットアップ

```bash
# プロジェクトディレクトリを作成
mkdir todo_app
cd todo_app

# 仮想環境を作成・有効化
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### パッケージのインストール

`requirements.txt`を作成：

```text
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-WTF==1.2.1
Werkzeug==3.0.1
```

インストール：

```bash
pip install -r requirements.txt
```

## Step 1: 最小構成のFlaskアプリ

まずは「Hello World」から始めましょう。

### app.py

```python
from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run(debug=True)
```

実行：

```bash
python app.py
```

ブラウザで http://127.0.0.1:5000 にアクセスすると「Hello, World!」と表示されます。

## Step 2: 設定ファイルの作成

### config.py

```python
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///todo.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
```

- `SECRET_KEY`: セッション管理やCSRF対策に使用
- `SQLALCHEMY_DATABASE_URI`: SQLiteデータベースのパス

## Step 3: データベースモデルの定義

### models.py

```python
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(7), default='#6c757d')

    tasks = db.relationship('Task', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    completed = db.Column(db.Boolean, default=False)
    priority = db.Column(db.Integer, default=2)  # 1=高, 2=中, 3=低
    due_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))

    @property
    def is_overdue(self):
        """期限切れかどうかを判定"""
        if self.due_date and not self.completed:
            return self.due_date < datetime.utcnow().date()
        return False

    @property
    def priority_label(self):
        """優先度のラベルを返す"""
        labels = {1: '高', 2: '中', 3: '低'}
        return labels.get(self.priority, '中')

    def __repr__(self):
        return f'<Task {self.title}>'
```

### ポイント解説

1. **リレーション**: `db.relationship`で1対多の関係を定義
2. **プロパティ**: `@property`でモデルに便利なメソッドを追加
3. **デフォルト値**: `default`引数で初期値を設定

## Step 4: フォームの定義

Flask-WTFを使ってフォームを定義します。

### forms.py

```python
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateField
from wtforms.validators import DataRequired, Length, Optional

class TaskForm(FlaskForm):
    title = StringField('タイトル', validators=[
        DataRequired(message='タイトルは必須です'),
        Length(max=200, message='200文字以内で入力してください')
    ])
    description = TextAreaField('説明', validators=[Optional()])
    priority = SelectField('優先度', choices=[
        ('1', '高'),
        ('2', '中'),
        ('3', '低')
    ], default='2')
    due_date = DateField('期限', validators=[Optional()])
    category_id = SelectField('カテゴリ', coerce=int, validators=[Optional()])


class CategoryForm(FlaskForm):
    name = StringField('カテゴリ名', validators=[
        DataRequired(),
        Length(max=50)
    ])
    color = StringField('色', default='#6c757d')
```

### バリデータの種類

| バリデータ | 説明 |
|-----------|------|
| DataRequired | 必須入力 |
| Length | 文字数制限 |
| Optional | 任意入力 |
| Email | メールアドレス形式 |

## Step 5: ルーティングの実装

### app.py（完全版）

```python
from flask import Flask, render_template, redirect, url_for, flash, request
from config import Config
from models import db, Task, Category
from forms import TaskForm, CategoryForm

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)


@app.route('/')
def index():
    return redirect(url_for('tasks'))


@app.route('/tasks')
def tasks():
    """タスク一覧"""
    filter_type = request.args.get('filter', 'all')

    query = Task.query

    if filter_type == 'active':
        query = query.filter_by(completed=False)
    elif filter_type == 'completed':
        query = query.filter_by(completed=True)

    tasks = query.order_by(Task.priority.asc(), Task.created_at.desc()).all()
    categories = Category.query.all()

    return render_template('tasks.html', tasks=tasks, categories=categories,
                          filter_type=filter_type)


@app.route('/tasks/new', methods=['GET', 'POST'])
def new_task():
    """タスク作成"""
    form = TaskForm()
    categories = Category.query.all()
    form.category_id.choices = [(0, '-- なし --')] + [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        task = Task(
            title=form.title.data,
            description=form.description.data,
            priority=int(form.priority.data),
            due_date=form.due_date.data,
            category_id=form.category_id.data if form.category_id.data != 0 else None
        )
        db.session.add(task)
        db.session.commit()
        flash('タスクを作成しました', 'success')
        return redirect(url_for('tasks'))

    return render_template('task_form.html', form=form, title='新規タスク')


@app.route('/tasks/<int:task_id>/toggle', methods=['POST'])
def toggle_task(task_id):
    """完了状態の切り替え"""
    task = Task.query.get_or_404(task_id)
    task.completed = not task.completed
    db.session.commit()
    return redirect(url_for('tasks'))


@app.route('/tasks/<int:task_id>/delete', methods=['POST'])
def delete_task(task_id):
    """タスク削除"""
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    flash('タスクを削除しました', 'info')
    return redirect(url_for('tasks'))


# データベース初期化
with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(debug=True)
```

### ルーティングのポイント

1. **`@app.route`**: URLパターンとビュー関数を紐付け
2. **`methods`**: 許可するHTTPメソッドを指定
3. **`url_for`**: ルート名からURLを生成
4. **`flash`**: ユーザーへのメッセージ通知

## Step 6: テンプレートの作成

Jinja2テンプレートエンジンを使ってHTMLを生成します。

### templates/base.html

```html
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Todo App{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('tasks') }}">Todo App</a>
        </div>
    </nav>

    <main class="container mt-4">
        <!-- フラッシュメッセージ -->
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% for category, message in messages %}
                <div class="alert alert-{{ category }} alert-dismissible fade show">
                    {{ message }}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            {% endfor %}
        {% endwith %}

        {% block content %}{% endblock %}
    </main>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
```

### templates/tasks.html

```html
{% extends "base.html" %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h1>タスク一覧</h1>
    <a href="{{ url_for('new_task') }}" class="btn btn-primary">新規タスク</a>
</div>

<!-- フィルター -->
<div class="btn-group mb-3">
    <a href="{{ url_for('tasks', filter='all') }}"
       class="btn btn-outline-secondary {% if filter_type == 'all' %}active{% endif %}">すべて</a>
    <a href="{{ url_for('tasks', filter='active') }}"
       class="btn btn-outline-secondary {% if filter_type == 'active' %}active{% endif %}">未完了</a>
    <a href="{{ url_for('tasks', filter='completed') }}"
       class="btn btn-outline-secondary {% if filter_type == 'completed' %}active{% endif %}">完了</a>
</div>

<!-- タスクリスト -->
<div class="list-group">
    {% for task in tasks %}
    <div class="list-group-item d-flex justify-content-between align-items-center
                {% if task.completed %}bg-light text-muted{% endif %}
                {% if task.is_overdue %}border-danger{% endif %}">
        <div class="d-flex align-items-center">
            <form action="{{ url_for('toggle_task', task_id=task.id) }}" method="post" class="me-3">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                <button type="submit" class="btn btn-sm
                    {% if task.completed %}btn-success{% else %}btn-outline-secondary{% endif %}">
                    {% if task.completed %}✓{% else %}○{% endif %}
                </button>
            </form>
            <div>
                <span class="{% if task.completed %}text-decoration-line-through{% endif %}">
                    {{ task.title }}
                </span>
                <span class="badge bg-{{ 'danger' if task.priority == 1 else 'warning' if task.priority == 2 else 'secondary' }}">
                    {{ task.priority_label }}
                </span>
                {% if task.due_date %}
                <small class="text-muted ms-2">期限: {{ task.due_date }}</small>
                {% endif %}
            </div>
        </div>
        <form action="{{ url_for('delete_task', task_id=task.id) }}" method="post">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <button type="submit" class="btn btn-sm btn-outline-danger"
                    onclick="return confirm('削除しますか？')">削除</button>
        </form>
    </div>
    {% else %}
    <p class="text-muted">タスクがありません</p>
    {% endfor %}
</div>
{% endblock %}
```

## 動作確認

```bash
python app.py
```

http://127.0.0.1:5000 にアクセスして、タスクの追加・完了・削除ができることを確認してください。

## まとめ

この記事では、Flaskを使ったTodoアプリの基本的な作り方を解説しました。

**学んだこと：**
- Flaskアプリケーションの基本構成
- Flask-SQLAlchemyを使ったデータベース連携
- Flask-WTFを使ったフォーム処理
- Jinja2テンプレートの使い方

**次のステップ：**
- ユーザー認証の実装（次回の記事で解説）
- サブタスク機能の追加
- スケジュール管理機能

## リポジトリ

完成版のコードはGitHubで公開しています：
https://github.com/soratakeuchi-227/todo_app

---

最後まで読んでいただきありがとうございました。質問やフィードバックがあれば、コメントでお知らせください。
