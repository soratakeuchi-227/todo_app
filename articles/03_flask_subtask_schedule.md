# 【Flask応用】サブタスクとスケジュール管理機能を実装する

## はじめに

前回までの記事で、Flask-Loginを使ったユーザー認証機能を実装しました。今回は、より実用的なTodoアプリにするために、以下の機能を追加します：

- サブタスク（親タスクを細分化）
- 進捗率の表示
- 日別・週間スケジュール表示

## 完成イメージ

| 機能 | 説明 |
|------|------|
| サブタスク | タスクを細かいステップに分割 |
| 進捗率 | サブタスクの完了率をプログレスバーで表示 |
| 日別スケジュール | タイムライン形式で1日の予定を表示 |
| 週間スケジュール | 1週間の予定を一覧表示 |

## Step 1: モデルの拡張

### 自己参照リレーション

サブタスクを実現するために、Taskモデルに自己参照（self-referential）のリレーションを追加します。

```python
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    completed = db.Column(db.Boolean, default=False)
    priority = db.Column(db.Integer, default=2)
    due_date = db.Column(db.Date)
    order = db.Column(db.Integer, default=0)  # サブタスクの順序

    # スケジュール関連
    scheduled_date = db.Column(db.Date)   # 予定日
    start_time = db.Column(db.Time)       # 開始時刻
    end_time = db.Column(db.Time)         # 終了時刻

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                          onupdate=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    parent_id = db.Column(db.Integer, db.ForeignKey('task.id'))  # 親タスク

    # 自己参照リレーション
    subtasks = db.relationship(
        'Task',
        backref=db.backref('parent', remote_side=[id]),
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
```

### 自己参照の仕組み

```
┌─────────────────────┐
│      Task           │
├─────────────────────┤
│ id = 1              │ ◀──┐
│ title = "買い物"     │    │
│ parent_id = None    │    │
└─────────────────────┘    │
                           │ parent_id
┌─────────────────────┐    │
│      Task           │    │
├─────────────────────┤    │
│ id = 2              │    │
│ title = "牛乳を買う" │    │
│ parent_id = 1       │ ───┘
└─────────────────────┘

Task(id=1).subtasks → [Task(id=2), ...]
Task(id=2).parent   → Task(id=1)
```

### プロパティの追加

```python
@property
def is_parent(self):
    """サブタスクを持つ親タスクかどうか"""
    return self.subtasks.count() > 0

@property
def subtask_count(self):
    """サブタスクの数"""
    return self.subtasks.count()

@property
def completed_subtask_count(self):
    """完了したサブタスクの数"""
    return self.subtasks.filter_by(completed=True).count()

@property
def progress(self):
    """進捗率（%）"""
    total = self.subtask_count
    if total == 0:
        return 100 if self.completed else 0
    return int((self.completed_subtask_count / total) * 100)

@property
def ordered_subtasks(self):
    """順序付きサブタスクを取得"""
    return self.subtasks.order_by(Task.order.asc(), Task.created_at.asc()).all()

@property
def is_scheduled(self):
    """スケジュールが設定されているか"""
    return self.scheduled_date is not None and self.start_time is not None

@property
def time_range(self):
    """時間帯の文字列表現"""
    if self.start_time and self.end_time:
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"
    elif self.start_time:
        return self.start_time.strftime('%H:%M')
    return ""

@property
def duration_hours(self):
    """タスクの長さ（時間単位）"""
    if self.start_time and self.end_time:
        start = datetime.combine(date.today(), self.start_time)
        end = datetime.combine(date.today(), self.end_time)
        return (end - start).seconds / 3600
    return 1  # デフォルト1時間
```

## Step 2: サブタスク機能の実装

### フォームの準備

```python
# forms.py
class ScheduleForm(FlaskForm):
    """スケジュール設定フォーム"""
    scheduled_date = DateField('予定日', validators=[DataRequired()])
    start_time = TimeField('開始時刻', validators=[DataRequired()])
    end_time = TimeField('終了時刻', validators=[Optional()])
```

### ルーティング

```python
# タスク詳細・サブタスク一覧
@app.route('/tasks/<int:task_id>')
@login_required
def task_detail(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    return render_template('task_detail.html', task=task)


# サブタスク作成
@app.route('/tasks/<int:task_id>/subtasks/new', methods=['GET', 'POST'])
@login_required
def new_subtask(task_id):
    parent = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    form = TaskForm()
    del form.category_id  # サブタスクはカテゴリ不要

    if form.validate_on_submit():
        # 次の順序番号を取得
        max_order = db.session.query(db.func.max(Task.order))\
            .filter_by(parent_id=task_id).scalar() or 0

        subtask = Task(
            title=form.title.data,
            description=form.description.data,
            priority=int(form.priority.data),
            due_date=form.due_date.data,
            parent_id=task_id,
            order=max_order + 1,
            user_id=current_user.id
        )
        db.session.add(subtask)
        db.session.commit()
        flash('サブタスクを追加しました', 'success')
        return redirect(url_for('task_detail', task_id=task_id))

    return render_template('subtask_form.html', form=form, parent=parent)


# サブタスクの完了切替
@app.route('/tasks/<int:task_id>/subtasks/<int:subtask_id>/toggle', methods=['POST'])
@login_required
def toggle_subtask(task_id, subtask_id):
    subtask = Task.query.filter_by(
        id=subtask_id,
        parent_id=task_id,
        user_id=current_user.id
    ).first_or_404()
    subtask.completed = not subtask.completed
    db.session.commit()
    return redirect(url_for('task_detail', task_id=task_id))
```

### タスク詳細テンプレート

```html
<!-- templates/task_detail.html -->
{% extends "base.html" %}

{% block content %}
<div class="mb-4">
    <a href="{{ url_for('tasks') }}" class="text-decoration-none">← タスク一覧に戻る</a>
</div>

<div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
        <h4 class="mb-0">{{ task.title }}</h4>
        <span class="badge bg-{{ task.priority_class }}">{{ task.priority_label }}</span>
    </div>
    <div class="card-body">
        {% if task.description %}
        <p>{{ task.description }}</p>
        {% endif %}

        {% if task.due_date %}
        <p class="text-muted">
            期限: {{ task.due_date.strftime('%Y/%m/%d') }}
            {% if task.is_overdue %}
            <span class="badge bg-danger">期限切れ</span>
            {% endif %}
        </p>
        {% endif %}

        <!-- 進捗バー -->
        {% if task.is_parent %}
        <div class="mb-3">
            <div class="d-flex justify-content-between mb-1">
                <span>進捗</span>
                <span>{{ task.completed_subtask_count }}/{{ task.subtask_count }}</span>
            </div>
            <div class="progress">
                <div class="progress-bar" style="width: {{ task.progress }}%">
                    {{ task.progress }}%
                </div>
            </div>
        </div>
        {% endif %}
    </div>
</div>

<!-- サブタスク一覧 -->
<div class="mt-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h5>サブタスク</h5>
        <a href="{{ url_for('new_subtask', task_id=task.id) }}" class="btn btn-sm btn-primary">
            + 追加
        </a>
    </div>

    <div class="list-group">
        {% for subtask in task.ordered_subtasks %}
        <div class="list-group-item d-flex justify-content-between align-items-center
                    {% if subtask.completed %}bg-light{% endif %}">
            <div class="d-flex align-items-center">
                <form action="{{ url_for('toggle_subtask', task_id=task.id, subtask_id=subtask.id) }}"
                      method="post" class="me-3">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                    <button type="submit" class="btn btn-sm
                        {% if subtask.completed %}btn-success{% else %}btn-outline-secondary{% endif %}">
                        {% if subtask.completed %}✓{% else %}○{% endif %}
                    </button>
                </form>
                <span class="{% if subtask.completed %}text-decoration-line-through text-muted{% endif %}">
                    {{ subtask.title }}
                </span>
            </div>
        </div>
        {% else %}
        <p class="text-muted">サブタスクはありません</p>
        {% endfor %}
    </div>
</div>
{% endblock %}
```

## Step 3: スケジュール機能の実装

### 日別スケジュール

```python
from datetime import date, timedelta

@app.route('/schedule/today')
@app.route('/schedule/day/<date_str>')
@login_required
def daily_schedule(date_str=None):
    """日別スケジュール表示"""
    if date_str:
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            target_date = date.today()
    else:
        target_date = date.today()

    prev_date = target_date - timedelta(days=1)
    next_date = target_date + timedelta(days=1)

    # スケジュール済みタスク
    scheduled_tasks = Task.query.filter_by(
        user_id=current_user.id,
        scheduled_date=target_date
    ).filter(Task.start_time.isnot(None))\
     .order_by(Task.start_time.asc()).all()

    # 未スケジュールタスク（親タスクのみ、未完了）
    unscheduled_tasks = Task.query.filter_by(
        user_id=current_user.id,
        parent_id=None,
        completed=False,
        scheduled_date=None
    ).order_by(Task.priority.asc()).all()

    # タイムスロット生成（8時〜21時）
    time_slots = list(range(8, 22))

    return render_template('daily_schedule.html',
                          target_date=target_date,
                          prev_date=prev_date,
                          next_date=next_date,
                          scheduled_tasks=scheduled_tasks,
                          unscheduled_tasks=unscheduled_tasks,
                          time_slots=time_slots)
```

### 週間スケジュール

```python
@app.route('/schedule/week')
@app.route('/schedule/week/<date_str>')
@login_required
def weekly_schedule(date_str=None):
    """週間スケジュール表示"""
    if date_str:
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            target_date = date.today()
    else:
        target_date = date.today()

    # 週の開始日（月曜日）を計算
    start_of_week = target_date - timedelta(days=target_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    prev_week = start_of_week - timedelta(days=7)
    next_week = start_of_week + timedelta(days=7)

    # 週の日付リスト
    week_dates = [start_of_week + timedelta(days=i) for i in range(7)]

    # その週のスケジュール済みタスクを取得
    scheduled_tasks = Task.query.filter(
        Task.user_id == current_user.id,
        Task.scheduled_date >= start_of_week,
        Task.scheduled_date <= end_of_week,
        Task.start_time.isnot(None)
    ).order_by(Task.scheduled_date.asc(), Task.start_time.asc()).all()

    # 日付ごとにタスクをグループ化
    tasks_by_date = {d: [] for d in week_dates}
    for task in scheduled_tasks:
        if task.scheduled_date in tasks_by_date:
            tasks_by_date[task.scheduled_date].append(task)

    return render_template('weekly_schedule.html',
                          start_of_week=start_of_week,
                          end_of_week=end_of_week,
                          prev_week=prev_week,
                          next_week=next_week,
                          week_dates=week_dates,
                          tasks_by_date=tasks_by_date)
```

### タスクのスケジュール設定

```python
@app.route('/tasks/<int:task_id>/schedule', methods=['GET', 'POST'])
@login_required
def schedule_task(task_id):
    """タスクをスケジュールに追加"""
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    form = ScheduleForm()

    if request.method == 'GET':
        form.scheduled_date.data = task.scheduled_date or date.today()
        form.start_time.data = task.start_time
        form.end_time.data = task.end_time

    if form.validate_on_submit():
        task.scheduled_date = form.scheduled_date.data
        task.start_time = form.start_time.data
        task.end_time = form.end_time.data
        db.session.commit()
        flash('スケジュールを設定しました', 'success')
        return redirect(url_for('daily_schedule',
                                date_str=task.scheduled_date.isoformat()))

    return render_template('schedule_form.html', form=form, task=task)


@app.route('/tasks/<int:task_id>/unschedule', methods=['POST'])
@login_required
def unschedule_task(task_id):
    """タスクのスケジュールを解除"""
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    task.scheduled_date = None
    task.start_time = None
    task.end_time = None
    db.session.commit()
    flash('スケジュールを解除しました', 'info')
    return redirect(url_for('daily_schedule'))
```

### 日別スケジュールテンプレート

```html
<!-- templates/daily_schedule.html -->
{% extends "base.html" %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <a href="{{ url_for('daily_schedule', date_str=prev_date.isoformat()) }}"
       class="btn btn-outline-secondary">← 前日</a>
    <h4>{{ target_date.strftime('%Y年%m月%d日') }}</h4>
    <a href="{{ url_for('daily_schedule', date_str=next_date.isoformat()) }}"
       class="btn btn-outline-secondary">翌日 →</a>
</div>

<div class="row">
    <!-- タイムライン -->
    <div class="col-md-8">
        <div class="card">
            <div class="card-header">スケジュール</div>
            <div class="card-body p-0">
                <div class="timeline">
                    {% for hour in time_slots %}
                    <div class="timeline-slot d-flex border-bottom">
                        <div class="time-label p-2 bg-light" style="width: 60px;">
                            {{ '%02d:00'|format(hour) }}
                        </div>
                        <div class="slot-content flex-grow-1 p-2" style="min-height: 60px;">
                            {% for task in scheduled_tasks %}
                                {% if task.start_time.hour == hour %}
                                <div class="task-block bg-primary text-white p-2 rounded mb-1">
                                    <strong>{{ task.title }}</strong>
                                    <small class="d-block">{{ task.time_range }}</small>
                                </div>
                                {% endif %}
                            {% endfor %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>

    <!-- 未スケジュールタスク -->
    <div class="col-md-4">
        <div class="card">
            <div class="card-header">未スケジュール</div>
            <div class="list-group list-group-flush">
                {% for task in unscheduled_tasks %}
                <div class="list-group-item d-flex justify-content-between align-items-center">
                    <span>{{ task.title }}</span>
                    <a href="{{ url_for('schedule_task', task_id=task.id) }}"
                       class="btn btn-sm btn-outline-primary">予定に追加</a>
                </div>
                {% else %}
                <div class="list-group-item text-muted">
                    すべてのタスクがスケジュール済みです
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

## Step 4: 親タスクの一覧表示を更新

タスク一覧では、サブタスクは親の中に含めて表示します。

```python
@app.route('/tasks')
@login_required
def tasks():
    filter_type = request.args.get('filter', 'all')

    # 親タスクのみ表示（サブタスクは親の中で表示）
    query = Task.query.filter_by(user_id=current_user.id, parent_id=None)

    if filter_type == 'active':
        query = query.filter_by(completed=False)
    elif filter_type == 'completed':
        query = query.filter_by(completed=True)

    tasks = query.order_by(
        Task.priority.asc(),
        Task.due_date.asc().nullslast(),
        Task.created_at.desc()
    ).all()

    return render_template('tasks.html', tasks=tasks, filter_type=filter_type)
```

### タスク一覧での進捗表示

```html
<!-- templates/tasks.html（一部） -->
{% for task in tasks %}
<div class="list-group-item">
    <div class="d-flex justify-content-between align-items-center">
        <div>
            <a href="{{ url_for('task_detail', task_id=task.id) }}">
                {{ task.title }}
            </a>
            {% if task.is_parent %}
            <small class="text-muted ms-2">
                ({{ task.completed_subtask_count }}/{{ task.subtask_count }})
            </small>
            {% endif %}
        </div>
    </div>

    {% if task.is_parent %}
    <div class="progress mt-2" style="height: 5px;">
        <div class="progress-bar" style="width: {{ task.progress }}%"></div>
    </div>
    {% endif %}
</div>
{% endfor %}
```

## デザインパターン: 自己参照リレーション

サブタスク機能で使った自己参照は、以下のような階層構造を持つデータに応用できます：

| ユースケース | 例 |
|-------------|-----|
| コメントのスレッド | 返信コメント |
| 組織図 | 上司-部下関係 |
| カテゴリ | 親子カテゴリ |
| フォルダ構造 | ネストしたフォルダ |

```python
# 汎用的なパターン
class TreeNode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    parent_id = db.Column(db.Integer, db.ForeignKey('tree_node.id'))

    children = db.relationship(
        'TreeNode',
        backref=db.backref('parent', remote_side=[id]),
        lazy='dynamic'
    )
```

## まとめ

この記事では、以下の機能を実装しました：

- **サブタスク**: 自己参照リレーションによる親子関係
- **進捗率**: サブタスクの完了率を動的に計算
- **日別スケジュール**: タイムライン形式での予定表示
- **週間スケジュール**: 週単位での予定一覧

これで、基本的なTodoアプリから、実用的なタスク・スケジュール管理アプリに進化しました。

## 全体のまとめ（3部作）

| 記事 | 内容 |
|------|------|
| 第1回 | Flask基礎、CRUD、テンプレート |
| 第2回 | Flask-Login、ユーザー認証 |
| 第3回 | サブタスク、スケジュール管理 |

## リポジトリ

完成版のコードはGitHubで公開しています：
https://github.com/soratakeuchi-227/todo_app

---

3部作を最後まで読んでいただきありがとうございました。
