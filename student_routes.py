from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from forms import LoginForm, UserRegistrationForm
from models import User, CourseEnrollment, Settings
from extensions import db
from datetime import datetime

student_bp = Blueprint('student_bp', __name__)


@student_bp.context_processor
def inject_settings():
    settings = Settings.query.first()
    return dict(settings=settings or {}, current_year=datetime.now().year)


@student_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_bp.dashboard'))
        return redirect(url_for('student_bp.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Usuário ou senha inválidos', 'danger')
            return redirect(url_for('student_bp.login'))
        login_user(user, remember=form.remember_me.data)
        if user.role == 'admin':
            return redirect(url_for('admin_bp.dashboard'))
        return redirect(url_for('student_bp.dashboard'))
    return render_template('student/login.html', form=form)


@student_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('student_bp.dashboard'))
    form = UserRegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, role='student')
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registro realizado com sucesso! Faça login.', 'success')
        return redirect(url_for('student_bp.login'))
    return render_template('student/register.html', form=form)


@student_bp.route('/')
@login_required
def dashboard():
    if current_user.role != 'student':
        return redirect(url_for('admin_bp.dashboard'))
    enrollments = CourseEnrollment.query.filter_by(user_id=current_user.id).all()
    return render_template('student/dashboard.html', enrollments=enrollments)


@student_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main_bp.index'))
