from datetime import datetime, date, time
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tasks = db.relationship('Task', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    categories = db.relationship('Category', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(7), default='#6c757d')  # Hex color
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    tasks = db.relationship('Task', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    completed = db.Column(db.Boolean, default=False)
    priority = db.Column(db.Integer, default=2)  # 1=High, 2=Medium, 3=Low
    due_date = db.Column(db.Date)
    order = db.Column(db.Integer, default=0)  # サブタスクの順序

    # スケジュール関連
    scheduled_date = db.Column(db.Date)  # 予定日
    start_time = db.Column(db.Time)      # 開始時刻
    end_time = db.Column(db.Time)        # 終了時刻
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    parent_id = db.Column(db.Integer, db.ForeignKey('task.id'))  # 親タスク

    # 子タスク（サブタスク）
    subtasks = db.relationship('Task', backref=db.backref('parent', remote_side=[id]),
                               lazy='dynamic', cascade='all, delete-orphan')

    @property
    def is_overdue(self):
        if self.due_date and not self.completed:
            return self.due_date < datetime.utcnow().date()
        return False

    @property
    def priority_label(self):
        labels = {1: '高', 2: '中', 3: '低'}
        return labels.get(self.priority, '中')

    @property
    def priority_class(self):
        classes = {1: 'danger', 2: 'warning', 3: 'secondary'}
        return classes.get(self.priority, 'warning')

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

    def __repr__(self):
        return f'<Task {self.title}>'
