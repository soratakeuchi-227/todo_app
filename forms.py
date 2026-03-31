from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, BooleanField, SelectField, DateField, TimeField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional
from models import User


class LoginForm(FlaskForm):
    username = StringField('ユーザー名', validators=[DataRequired()])
    password = PasswordField('パスワード', validators=[DataRequired()])
    remember_me = BooleanField('ログイン状態を保持')


class RegisterForm(FlaskForm):
    username = StringField('ユーザー名', validators=[
        DataRequired(),
        Length(min=3, max=80, message='ユーザー名は3〜80文字で入力してください')
    ])
    email = StringField('メールアドレス', validators=[DataRequired(), Email()])
    password = PasswordField('パスワード', validators=[
        DataRequired(),
        Length(min=6, message='パスワードは6文字以上で入力してください')
    ])
    password2 = PasswordField('パスワード（確認）', validators=[
        DataRequired(),
        EqualTo('password', message='パスワードが一致しません')
    ])

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('このユーザー名は既に使用されています')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('このメールアドレスは既に登録されています')


class TaskForm(FlaskForm):
    title = StringField('タイトル', validators=[
        DataRequired(),
        Length(max=200, message='タイトルは200文字以内で入力してください')
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
        Length(max=50, message='カテゴリ名は50文字以内で入力してください')
    ])
    color = StringField('色', default='#6c757d')


class ScheduleForm(FlaskForm):
    """タスクをスケジュールに追加するフォーム"""
    scheduled_date = DateField('予定日', validators=[DataRequired()])
    start_time = TimeField('開始時刻', validators=[DataRequired()])
    end_time = TimeField('終了時刻', validators=[Optional()])
