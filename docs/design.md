# 設計書

## 1. システム構成

### 1.1 アーキテクチャ
```
┌─────────────────────────────────────────────────┐
│                   クライアント                    │
│                  (Webブラウザ)                   │
└─────────────────────┬───────────────────────────┘
                      │ HTTP/HTTPS
┌─────────────────────▼───────────────────────────┐
│                  Flask Application              │
│  ┌───────────┐ ┌───────────┐ ┌───────────────┐ │
│  │   Routes  │ │   Forms   │ │   Templates   │ │
│  │  (app.py) │ │(forms.py) │ │  (templates/) │ │
│  └─────┬─────┘ └───────────┘ └───────────────┘ │
│        │                                        │
│  ┌─────▼─────────────────────────────────────┐ │
│  │              Models (models.py)            │ │
│  │    Flask-SQLAlchemy / Flask-Login          │ │
│  └─────────────────────┬─────────────────────┘ │
└────────────────────────┼────────────────────────┘
                         │
┌────────────────────────▼────────────────────────┐
│                    SQLite                       │
│                   (todo.db)                     │
└─────────────────────────────────────────────────┘
```

### 1.2 技術スタック

| レイヤー | 技術 | バージョン |
|----------|------|------------|
| バックエンド | Python | 3.x |
| Webフレームワーク | Flask | 3.0.0 |
| ORM | Flask-SQLAlchemy | 3.1.1 |
| 認証 | Flask-Login | 0.6.3 |
| フォーム | Flask-WTF | 1.2.1 |
| データベース | SQLite | - |
| フロントエンド | HTML/CSS (Jinja2テンプレート) | - |

### 1.3 ディレクトリ構成
```
todo_app/
├── app.py              # メインアプリケーション（ルーティング）
├── config.py           # 設定ファイル
├── models.py           # データベースモデル
├── forms.py            # フォーム定義
├── requirements.txt    # 依存パッケージ
├── todo.db             # SQLiteデータベース
├── static/
│   └── style.css       # スタイルシート
├── templates/
│   ├── base.html               # ベーステンプレート
│   ├── login.html              # ログイン画面
│   ├── register.html           # ユーザー登録画面
│   ├── tasks.html              # タスク一覧画面
│   ├── task_form.html          # タスク作成/編集画面
│   ├── task_detail.html        # タスク詳細画面
│   ├── subtask_form.html       # サブタスク作成/編集画面
│   ├── categories.html         # カテゴリ一覧画面
│   ├── category_form.html      # カテゴリ作成/編集画面
│   ├── daily_schedule.html     # 日別スケジュール画面
│   ├── weekly_schedule.html    # 週間スケジュール画面
│   └── schedule_form.html      # スケジュール設定画面
└── docs/
    ├── requirements.md         # 要件定義書
    └── design.md               # 設計書（本書）
```

---

## 2. データベース設計

### 2.1 ER図
```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│     User     │       │   Category   │       │     Task     │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id (PK)      │───┐   │ id (PK)      │───┐   │ id (PK)      │
│ username     │   │   │ name         │   │   │ title        │
│ email        │   │   │ color        │   │   │ description  │
│ password_hash│   └──▶│ user_id (FK) │   └──▶│ completed    │
│ created_at   │       └──────────────┘       │ priority     │
└──────────────┘                              │ due_date     │
       │                                      │ order        │
       │                                      │ scheduled_date│
       │                                      │ start_time   │
       │                                      │ end_time     │
       │                                      │ created_at   │
       │                                      │ updated_at   │
       └─────────────────────────────────────▶│ user_id (FK) │
                                              │ category_id (FK)│
                                         ┌───▶│ parent_id (FK)│◀──┐
                                         │    └──────────────┘   │
                                         │         │             │
                                         └─────────┴─────────────┘
                                           (自己参照: サブタスク)
```

### 2.2 テーブル定義

#### User テーブル
| カラム名 | データ型 | 制約 | 説明 |
|----------|----------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | ユーザーID |
| username | VARCHAR(80) | NOT NULL, UNIQUE | ユーザー名 |
| email | VARCHAR(120) | NOT NULL, UNIQUE | メールアドレス |
| password_hash | VARCHAR(256) | NOT NULL | パスワードハッシュ |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 作成日時 |

#### Category テーブル
| カラム名 | データ型 | 制約 | 説明 |
|----------|----------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | カテゴリID |
| name | VARCHAR(50) | NOT NULL | カテゴリ名 |
| color | VARCHAR(7) | DEFAULT '#6c757d' | 表示色（HEX） |
| user_id | INTEGER | FK → User.id, NOT NULL | 所有ユーザー |

#### Task テーブル
| カラム名 | データ型 | 制約 | 説明 |
|----------|----------|------|------|
| id | INTEGER | PK, AUTO INCREMENT | タスクID |
| title | VARCHAR(200) | NOT NULL | タイトル |
| description | TEXT | NULL | 説明 |
| completed | BOOLEAN | DEFAULT FALSE | 完了フラグ |
| priority | INTEGER | DEFAULT 2 | 優先度（1:高, 2:中, 3:低） |
| due_date | DATE | NULL | 期限日 |
| order | INTEGER | DEFAULT 0 | サブタスク順序 |
| scheduled_date | DATE | NULL | スケジュール予定日 |
| start_time | TIME | NULL | 開始時刻 |
| end_time | TIME | NULL | 終了時刻 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 作成日時 |
| updated_at | DATETIME | ON UPDATE CURRENT_TIMESTAMP | 更新日時 |
| user_id | INTEGER | FK → User.id, NOT NULL | 所有ユーザー |
| category_id | INTEGER | FK → Category.id, NULL | カテゴリ |
| parent_id | INTEGER | FK → Task.id, NULL | 親タスク（サブタスク用） |

### 2.3 リレーション

| 関係 | 説明 |
|------|------|
| User : Task | 1 : N（ユーザーは複数タスクを所有） |
| User : Category | 1 : N（ユーザーは複数カテゴリを所有） |
| Category : Task | 1 : N（カテゴリには複数タスクが属する） |
| Task : Task | 1 : N（親タスクは複数サブタスクを持つ） |

---

## 3. API設計（ルーティング）

### 3.1 認証

| メソッド | エンドポイント | 機能 | 認証 |
|----------|----------------|------|------|
| GET | / | リダイレクト（ログイン済み→/tasks, 未ログイン→/login） | 不要 |
| GET/POST | /login | ログイン画面表示・処理 | 不要 |
| GET/POST | /register | ユーザー登録画面表示・処理 | 不要 |
| GET | /logout | ログアウト処理 | 必要 |

### 3.2 タスク管理

| メソッド | エンドポイント | 機能 | 認証 |
|----------|----------------|------|------|
| GET | /tasks | タスク一覧表示 | 必要 |
| GET/POST | /tasks/new | タスク作成 | 必要 |
| GET/POST | /tasks/{id}/edit | タスク編集 | 必要 |
| POST | /tasks/{id}/toggle | 完了状態切替 | 必要 |
| POST | /tasks/{id}/delete | タスク削除 | 必要 |
| GET | /tasks/{id} | タスク詳細表示 | 必要 |

### 3.3 サブタスク管理

| メソッド | エンドポイント | 機能 | 認証 |
|----------|----------------|------|------|
| GET/POST | /tasks/{id}/subtasks/new | サブタスク作成 | 必要 |
| GET/POST | /tasks/{id}/subtasks/{sid}/edit | サブタスク編集 | 必要 |
| POST | /tasks/{id}/subtasks/{sid}/toggle | サブタスク完了状態切替 | 必要 |

### 3.4 カテゴリ管理

| メソッド | エンドポイント | 機能 | 認証 |
|----------|----------------|------|------|
| GET | /categories | カテゴリ一覧表示 | 必要 |
| GET/POST | /categories/new | カテゴリ作成 | 必要 |
| GET/POST | /categories/{id}/edit | カテゴリ編集 | 必要 |
| POST | /categories/{id}/delete | カテゴリ削除 | 必要 |

### 3.5 スケジュール管理

| メソッド | エンドポイント | 機能 | 認証 |
|----------|----------------|------|------|
| GET | /schedule/today | 今日のスケジュール表示 | 必要 |
| GET | /schedule/day/{date} | 指定日のスケジュール表示 | 必要 |
| GET | /schedule/week | 今週のスケジュール表示 | 必要 |
| GET | /schedule/week/{date} | 指定週のスケジュール表示 | 必要 |
| GET/POST | /tasks/{id}/schedule | スケジュール設定 | 必要 |
| POST | /tasks/{id}/unschedule | スケジュール解除 | 必要 |

---

## 4. クラス設計

### 4.1 モデルクラス

#### User
```python
class User(UserMixin, db.Model):
    # 属性
    id: int              # ユーザーID
    username: str        # ユーザー名
    email: str           # メールアドレス
    password_hash: str   # パスワードハッシュ
    created_at: datetime # 作成日時

    # リレーション
    tasks: List[Task]       # 所有タスク
    categories: List[Category]  # 所有カテゴリ

    # メソッド
    set_password(password: str) -> None  # パスワード設定
    check_password(password: str) -> bool  # パスワード検証
```

#### Category
```python
class Category(db.Model):
    # 属性
    id: int          # カテゴリID
    name: str        # カテゴリ名
    color: str       # 表示色
    user_id: int     # 所有ユーザーID

    # リレーション
    tasks: List[Task]  # 所属タスク
```

#### Task
```python
class Task(db.Model):
    # 属性
    id: int              # タスクID
    title: str           # タイトル
    description: str     # 説明
    completed: bool      # 完了フラグ
    priority: int        # 優先度
    due_date: date       # 期限日
    order: int           # 順序
    scheduled_date: date # スケジュール日
    start_time: time     # 開始時刻
    end_time: time       # 終了時刻
    created_at: datetime # 作成日時
    updated_at: datetime # 更新日時
    user_id: int         # 所有ユーザーID
    category_id: int     # カテゴリID
    parent_id: int       # 親タスクID

    # リレーション
    subtasks: List[Task]  # サブタスク
    parent: Task          # 親タスク

    # プロパティ
    is_overdue: bool           # 期限切れ判定
    priority_label: str        # 優先度ラベル
    priority_class: str        # 優先度CSSクラス
    is_parent: bool            # 親タスク判定
    subtask_count: int         # サブタスク数
    completed_subtask_count: int  # 完了サブタスク数
    progress: int              # 進捗率
    ordered_subtasks: List[Task]  # 順序付きサブタスク
    is_scheduled: bool         # スケジュール設定済み判定
    time_range: str            # 時間帯文字列
    duration_hours: float      # タスク時間（時間単位）
```

### 4.2 フォームクラス

| クラス名 | 用途 | フィールド |
|----------|------|------------|
| LoginForm | ログイン | username, password, remember_me |
| RegisterForm | ユーザー登録 | username, email, password, password2 |
| TaskForm | タスク作成/編集 | title, description, priority, due_date, category_id |
| CategoryForm | カテゴリ作成/編集 | name, color |
| ScheduleForm | スケジュール設定 | scheduled_date, start_time, end_time |

---

## 5. セキュリティ設計

### 5.1 認証・認可

| 項目 | 実装 |
|------|------|
| パスワード保存 | Werkzeug による PBKDF2-SHA256 ハッシュ化 |
| セッション管理 | Flask-Login によるセッション管理 |
| アクセス制御 | @login_required デコレータによる認証チェック |
| データ分離 | クエリに user_id フィルタを適用 |

### 5.2 入力検証

| 項目 | 実装 |
|------|------|
| CSRF対策 | Flask-WTF による CSRFトークン |
| バリデーション | WTForms バリデータ |
| SQLインジェクション対策 | SQLAlchemy ORM によるパラメータ化クエリ |

---

## 6. 画面遷移図

```
                    ┌─────────────┐
                    │   /login    │
                    │  ログイン画面 │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ /register   │    │   /tasks    │    │/schedule/   │
│ユーザー登録  │    │ タスク一覧  │◀───│today 日別   │
└─────────────┘    └──────┬──────┘    └──────┬──────┘
                          │                  │
         ┌────────────────┼────────┐         │
         │                │        │         │
         ▼                ▼        ▼         ▼
┌─────────────┐  ┌─────────────┐ ┌─────────────┐
│/tasks/new   │  │/tasks/{id}  │ │/categories  │
│タスク作成   │  │タスク詳細   │ │カテゴリ一覧 │
└─────────────┘  └──────┬──────┘ └─────────────┘
                        │
                        ▼
               ┌─────────────────┐
               │/tasks/{id}/     │
               │subtasks/new     │
               │サブタスク作成   │
               └─────────────────┘
```
