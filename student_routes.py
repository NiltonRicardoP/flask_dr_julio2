from datetime import datetime
from functools import wraps

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import current_user

from models import Settings


student_bp = Blueprint("student_bp", __name__, url_prefix="/student")


@student_bp.context_processor
def inject_settings():
    """Provide settings and current year to student templates."""
    settings = Settings.query.first()
    return {"settings": settings, "current_year": datetime.now().year}


def student_required(f):
    """Allow access only to authenticated users with the student role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "student":
            flash("Acesso restrito aos alunos", "danger")
            return redirect(url_for("main_bp.index"))
        return f(*args, **kwargs)

    return decorated_function


@student_bp.route("/dashboard")
@student_required
def dashboard():
    """Simple student dashboard."""
    return render_template("student/dashboard.html")

