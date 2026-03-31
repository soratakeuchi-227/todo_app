# 【Flask-Login】ユーザー認証機能を実装する

## はじめに

前回の記事では、Flaskで基本的なTodoアプリを作成しました。今回は、Flask-Loginを使ってユーザー認証機能を実装します。

これにより、ユーザーごとにタスクを管理できる本格的なアプリケーションになります。

## 完成イメージ

追加する機能：
- ユーザー登録
- ログイン/ログアウト
- ユーザーごとのタスク管理
- 認証が必要なページの保護

## 環境構築

前回の環境に追加パッケージをインストールします。

```bash
pip install Flask-Login email-validator
```

`requirements.txt`に追加：

```text
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
Flask-WTF==1.2.1
Werkzeug==3.0.1
email-validator==2.1.0
```

## Step 1: Userモデルの作成

### models.py

```python
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """ユーザーモデル"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # リレーション
    tasks = db.relationship('Task', backref='user', lazy='dynamic',
                           cascade='all, delete-orphan')
    categories = db.relationship('Category', backref='user', lazy='dynamic',
                                cascade='all, delete-orphan')

    def set_password(self, password):
        """パスワードをハッシュ化して保存"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """パスワードを検証"""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(7), default='#6c757d')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    tasks = db.relationship('Task', backref='category', lazy='dynamic')


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    completed = db.Column(db.Boolean, default=False)
    priority = db.Column(db.Integer, default=2)
    due_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))

    @property
    def is_overdue(self):
        if self.due_date and not self.completed:
            return self.due_date < datetime.utcnow().date()
        return False

    @property
    def priority_label(self):
        labels = {1: '高', 2: '中', 3: '低'}
        return labels.get(self.priority, '中')
```

### ポイント解説

#### UserMixin

Flask-Loginが必要とするメソッドを提供：

| メソッド | 説明 |
|----------|------|
| is_authenticated | 認証済みならTrue |
| is_active | アクティブならTrue |
| is_anonymous | 匿名ユーザーならTrue |
| get_id() | ユーザーIDを返す |

#### パスワードのハッシュ化

```python
from werkzeug.security import generate_password_hash, check_password_hash

# 保存時
password_hash = generate_password_hash('plain_password')

# 検証時
is_valid = check_password_hash(password_hash, 'input_password')
```

**重要**: パスワードを平文で保存するのは絶対にNG！必ずハッシュ化しましょう。

## Step 2: 認証フォームの作成

### forms.py

```python
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from models import User


class LoginForm(FlaskForm):
    """ログインフォーム"""
    username = StringField('ユーザー名', validators=[DataRequired()])
    password = PasswordField('パスワード', validators=[DataRequired()])
    remember_me = BooleanField('ログイン状態を保持')


class RegisterForm(FlaskForm):
    """ユーザー登録フォーム"""
    username = StringField('ユーザー名', validators=[
        DataRequired(),
        Length(min=3, max=80, message='ユーザー名は3〜80文字で入力してください')
    ])
    email = StringField('メールアドレス', validators=[
        DataRequired(),
        Email(message='有効なメールアドレスを入力してください')
    ])
    password = PasswordField('パスワード', validators=[
        DataRequired(),
        Length(min=6, message='パスワードは6文字以上で入力してください')
    ])
    password2 = PasswordField('パスワード（確認）', validators=[
        DataRequired(),
        EqualTo('password', message='パスワードが一致しません')
    ])

    def validate_username(self, username):
        """ユーザー名の重複チェック"""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('このユーザー名は既に使用されています')

    def validate_email(self, email):
        """メールアドレスの重複チェック"""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('このメールアドレスは既に登録されています')
```

### カスタムバリデーション

`validate_<フィールド名>`というメソッドを定義すると、自動的にそのフィールドのバリデーションとして実行されます。

```python
def validate_username(self, username):
    # usernameフィールドに対するカスタムバリデーション
    if User.query.filter_by(username=username.data).first():
        raise ValidationError('エラーメッセージ')
```

## Step 3: Flask-Loginの設定

### app.py

```python
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, User, Task, Category
from forms import LoginForm, RegisterForm, TaskForm, CategoryForm

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

# Flask-Loginの設定
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # 未認証時のリダイレクト先
login_manager.login_message = 'このページにアクセスするにはログインが必要です'


@login_manager.user_loader
def load_user(user_id):
    """セッションからユーザーを読み込む"""
    return User.query.get(int(user_id))
```

### Flask-Loginの設定項目

| 設定 | 説明 |
|------|------|
| login_view | 未認証時のリダイレクト先ルート |
| login_message | リダイレクト時に表示するメッセージ |
| login_message_category | メッセージのカテゴリ（info, warning等） |

## Step 4: 認証ルートの実装

### ログイン

```python
@app.route('/login', methods=['GET', 'POST'])
def login():
    # 既にログイン済みならリダイレクト
    if current_user.is_authenticated:
        return redirect(url_for('tasks'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and user.check_password(form.password.data):
            # ログイン成功
            login_user(user, remember=form.remember_me.data)
            flash('ログインしました', 'success')

            # 元々アクセスしようとしていたページにリダイレクト
            next_page = request.args.get('next')
            return redirect(next_page or url_for('tasks'))

        flash('ユーザー名またはパスワードが正しくありません', 'danger')

    return render_template('login.html', form=form)
```

### ユーザー登録

```python
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('tasks'))

    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('アカウントを作成しました。ログインしてください', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)
```

### ログアウト

```python
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('ログアウトしました', 'info')
    return redirect(url_for('login'))
```

## Step 5: ページの保護

### @login_required デコレータ

認証が必要なルートには`@login_required`を付けます：

```python
@app.route('/tasks')
@login_required
def tasks():
    # current_userで現在のユーザーを取得できる
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    return render_template('tasks.html', tasks=tasks)
```

### 重要: データのフィルタリング

ユーザーが自分のデータのみアクセスできるよう、必ず`user_id`でフィルタリングします：

```python
# Good: ユーザーのタスクのみ取得
tasks = Task.query.filter_by(user_id=current_user.id).all()

# Bad: 全ユーザーのタスクが見えてしまう
tasks = Task.query.all()

# Good: 編集時も所有者チェック
task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()

# Bad: 他ユーザーのタスクも編集できてしまう
task = Task.query.get_or_404(task_id)
```

## Step 6: テンプレートの作成

### templates/login.html

```html
{% extends "base.html" %}

{% block title %}ログイン{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6 col-lg-4">
        <div class="card">
            <div class="card-header">
                <h4 class="mb-0">ログイン</h4>
            </div>
            <div class="card-body">
                <form method="post">
                    {{ form.hidden_tag() }}

                    <div class="mb-3">
                        {{ form.username.label(class="form-label") }}
                        {{ form.username(class="form-control") }}
                        {% for error in form.username.errors %}
                            <div class="text-danger">{{ error }}</div>
                        {% endfor %}
                    </div>

                    <div class="mb-3">
                        {{ form.password.label(class="form-label") }}
                        {{ form.password(class="form-control") }}
                        {% for error in form.password.errors %}
                            <div class="text-danger">{{ error }}</div>
                        {% endfor %}
                    </div>

                    <div class="mb-3 form-check">
                        {{ form.remember_me(class="form-check-input") }}
                        {{ form.remember_me.label(class="form-check-label") }}
                    </div>

                    <button type="submit" class="btn btn-primary w-100">ログイン</button>
                </form>
            </div>
            <div class="card-footer text-center">
                <a href="{{ url_for('register') }}">アカウントを作成</a>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### templates/register.html

```html
{% extends "base.html" %}

{% block title %}ユーザー登録{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6 col-lg-4">
        <div class="card">
            <div class="card-header">
                <h4 class="mb-0">ユーザー登録</h4>
            </div>
            <div class="card-body">
                <form method="post">
                    {{ form.hidden_tag() }}

                    <div class="mb-3">
                        {{ form.username.label(class="form-label") }}
                        {{ form.username(class="form-control") }}
                        {% for error in form.username.errors %}
                            <div class="text-danger">{{ error }}</div>
                        {% endfor %}
                    </div>

                    <div class="mb-3">
                        {{ form.email.label(class="form-label") }}
                        {{ form.email(class="form-control", type="email") }}
                        {% for error in form.email.errors %}
                            <div class="text-danger">{{ error }}</div>
                        {% endfor %}
                    </div>

                    <div class="mb-3">
                        {{ form.password.label(class="form-label") }}
                        {{ form.password(class="form-control") }}
                        {% for error in form.password.errors %}
                            <div class="text-danger">{{ error }}</div>
                        {% endfor %}
                    </div>

                    <div class="mb-3">
                        {{ form.password2.label(class="form-label") }}
                        {{ form.password2(class="form-control") }}
                        {% for error in form.password2.errors %}
                            <div class="text-danger">{{ error }}</div>
                        {% endfor %}
                    </div>

                    <button type="submit" class="btn btn-primary w-100">登録</button>
                </form>
            </div>
            <div class="card-footer text-center">
                <a href="{{ url_for('login') }}">ログインはこちら</a>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### ナビゲーションバーの更新（base.html）

```html
<nav class="navbar navbar-expand-lg navbar-dark bg-primary">
    <div class="container">
        <a class="navbar-brand" href="{{ url_for('tasks') }}">Todo App</a>

        {% if current_user.is_authenticated %}
        <div class="navbar-nav ms-auto">
            <span class="navbar-text me-3">
                {{ current_user.username }}
            </span>
            <a class="nav-link" href="{{ url_for('logout') }}">ログアウト</a>
        </div>
        {% endif %}
    </div>
</nav>
```

## セキュリティのベストプラクティス

### 1. パスワードは必ずハッシュ化

```python
# 保存時
user.set_password(plain_password)  # 内部でハッシュ化

# 検証時
user.check_password(input_password)  # ハッシュ同士で比較
```

### 2. CSRF対策

Flask-WTFが自動的にCSRFトークンを生成・検証します：

```html
<form method="post">
    {{ form.hidden_tag() }}  <!-- CSRFトークンが含まれる -->
    ...
</form>
```

### 3. データアクセスの制限

```python
# 必ずuser_idでフィルタリング
Task.query.filter_by(user_id=current_user.id, id=task_id).first_or_404()
```

### 4. セッションの設定

```python
# config.py
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24)
    SESSION_COOKIE_SECURE = True  # HTTPS時のみ（本番環境）
    SESSION_COOKIE_HTTPONLY = True  # JavaScriptからアクセス不可
```

## まとめ

Flask-Loginを使うことで、以下の機能を簡単に実装できました：

- ユーザー登録とログイン/ログアウト
- セッション管理（ログイン状態の保持）
- ページの保護（未認証ユーザーのリダイレクト）
- 現在のユーザー情報へのアクセス（`current_user`）

**次回**: サブタスク機能とスケジュール管理を実装します。

## リポジトリ

完成版のコードはGitHubで公開しています：
https://github.com/soratakeuchi-227/todo_app

---

最後まで読んでいただきありがとうございました。
