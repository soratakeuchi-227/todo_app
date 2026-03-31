from datetime import date, timedelta
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, User, Task, Category
from forms import LoginForm, RegisterForm, TaskForm, CategoryForm, ScheduleForm

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'このページにアクセスするにはログインが必要です'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ==================== 認証 ====================

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('tasks'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('tasks'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            flash('ログインしました', 'success')
            return redirect(next_page or url_for('tasks'))
        flash('ユーザー名またはパスワードが正しくありません', 'danger')

    return render_template('login.html', form=form)


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


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('ログアウトしました', 'info')
    return redirect(url_for('login'))


# ==================== タスク ====================

@app.route('/tasks')
@login_required
def tasks():
    filter_type = request.args.get('filter', 'all')
    category_id = request.args.get('category', type=int)

    # 親タスクのみ表示（サブタスクは親の中で表示）
    query = Task.query.filter_by(user_id=current_user.id, parent_id=None)

    if filter_type == 'active':
        query = query.filter_by(completed=False)
    elif filter_type == 'completed':
        query = query.filter_by(completed=True)

    if category_id:
        query = query.filter_by(category_id=category_id)

    tasks = query.order_by(Task.priority.asc(), Task.due_date.asc().nullslast(), Task.created_at.desc()).all()
    categories = Category.query.filter_by(user_id=current_user.id).all()

    return render_template('tasks.html', tasks=tasks, categories=categories,
                          filter_type=filter_type, selected_category=category_id)


@app.route('/tasks/new', methods=['GET', 'POST'])
@login_required
def new_task():
    form = TaskForm()
    categories = Category.query.filter_by(user_id=current_user.id).all()
    form.category_id.choices = [(0, '-- なし --')] + [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        task = Task(
            title=form.title.data,
            description=form.description.data,
            priority=int(form.priority.data),
            due_date=form.due_date.data,
            category_id=form.category_id.data if form.category_id.data != 0 else None,
            user_id=current_user.id
        )
        db.session.add(task)
        db.session.commit()
        flash('タスクを作成しました', 'success')
        return redirect(url_for('tasks'))

    return render_template('task_form.html', form=form, title='新規タスク')


@app.route('/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    form = TaskForm(obj=task)
    categories = Category.query.filter_by(user_id=current_user.id).all()
    form.category_id.choices = [(0, '-- なし --')] + [(c.id, c.name) for c in categories]

    if request.method == 'GET':
        form.priority.data = str(task.priority)
        form.category_id.data = task.category_id or 0

    if form.validate_on_submit():
        task.title = form.title.data
        task.description = form.description.data
        task.priority = int(form.priority.data)
        task.due_date = form.due_date.data
        task.category_id = form.category_id.data if form.category_id.data != 0 else None
        db.session.commit()
        flash('タスクを更新しました', 'success')
        return redirect(url_for('tasks'))

    return render_template('task_form.html', form=form, title='タスク編集')


@app.route('/tasks/<int:task_id>/toggle', methods=['POST'])
@login_required
def toggle_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    task.completed = not task.completed
    db.session.commit()
    return redirect(url_for('tasks'))


@app.route('/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    parent_id = task.parent_id
    db.session.delete(task)
    db.session.commit()
    flash('タスクを削除しました', 'info')
    if parent_id:
        return redirect(url_for('task_detail', task_id=parent_id))
    return redirect(url_for('tasks'))


# ==================== タスク詳細・サブタスク ====================

@app.route('/tasks/<int:task_id>')
@login_required
def task_detail(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    return render_template('task_detail.html', task=task)


@app.route('/tasks/<int:task_id>/subtasks/new', methods=['GET', 'POST'])
@login_required
def new_subtask(task_id):
    parent = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    form = TaskForm()
    # サブタスクではカテゴリは親から継承するので非表示
    del form.category_id

    if form.validate_on_submit():
        # 次の順序番号を取得
        max_order = db.session.query(db.func.max(Task.order)).filter_by(parent_id=task_id).scalar() or 0
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

    return render_template('subtask_form.html', form=form, parent=parent, title='サブタスク追加')


@app.route('/tasks/<int:task_id>/subtasks/<int:subtask_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_subtask(task_id, subtask_id):
    parent = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    subtask = Task.query.filter_by(id=subtask_id, parent_id=task_id, user_id=current_user.id).first_or_404()
    form = TaskForm(obj=subtask)
    del form.category_id

    if request.method == 'GET':
        form.priority.data = str(subtask.priority)

    if form.validate_on_submit():
        subtask.title = form.title.data
        subtask.description = form.description.data
        subtask.priority = int(form.priority.data)
        subtask.due_date = form.due_date.data
        db.session.commit()
        flash('サブタスクを更新しました', 'success')
        return redirect(url_for('task_detail', task_id=task_id))

    return render_template('subtask_form.html', form=form, parent=parent, title='サブタスク編集')


@app.route('/tasks/<int:task_id>/subtasks/<int:subtask_id>/toggle', methods=['POST'])
@login_required
def toggle_subtask(task_id, subtask_id):
    subtask = Task.query.filter_by(id=subtask_id, parent_id=task_id, user_id=current_user.id).first_or_404()
    subtask.completed = not subtask.completed
    db.session.commit()
    return redirect(url_for('task_detail', task_id=task_id))


# ==================== スケジュール ====================

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

    # スケジュール済みタスク（その日の予定）
    scheduled_tasks = Task.query.filter_by(
        user_id=current_user.id,
        scheduled_date=target_date
    ).filter(Task.start_time.isnot(None)).order_by(Task.start_time.asc()).all()

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

    # タイムスロット生成（8時〜21時）
    time_slots = list(range(8, 22))

    return render_template('weekly_schedule.html',
                          target_date=target_date,
                          start_of_week=start_of_week,
                          end_of_week=end_of_week,
                          prev_week=prev_week,
                          next_week=next_week,
                          week_dates=week_dates,
                          tasks_by_date=tasks_by_date,
                          time_slots=time_slots)


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
        return redirect(url_for('daily_schedule', date_str=task.scheduled_date.isoformat()))

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


# ==================== カテゴリ ====================

@app.route('/categories')
@login_required
def categories():
    categories = Category.query.filter_by(user_id=current_user.id).all()
    return render_template('categories.html', categories=categories)


@app.route('/categories/new', methods=['GET', 'POST'])
@login_required
def new_category():
    form = CategoryForm()
    if form.validate_on_submit():
        category = Category(
            name=form.name.data,
            color=form.color.data,
            user_id=current_user.id
        )
        db.session.add(category)
        db.session.commit()
        flash('カテゴリを作成しました', 'success')
        return redirect(url_for('categories'))

    return render_template('category_form.html', form=form, title='新規カテゴリ')


@app.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    category = Category.query.filter_by(id=category_id, user_id=current_user.id).first_or_404()
    form = CategoryForm(obj=category)

    if form.validate_on_submit():
        category.name = form.name.data
        category.color = form.color.data
        db.session.commit()
        flash('カテゴリを更新しました', 'success')
        return redirect(url_for('categories'))

    return render_template('category_form.html', form=form, title='カテゴリ編集')


@app.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_category(category_id):
    category = Category.query.filter_by(id=category_id, user_id=current_user.id).first_or_404()
    db.session.delete(category)
    db.session.commit()
    flash('カテゴリを削除しました', 'info')
    return redirect(url_for('categories'))


# ==================== 初期化 ====================

with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(debug=True)
