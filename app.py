import os
from datetime import datetime

from flask import Flask

from admin_routes import admin_bp
from appointments_api import appointments_bp
from availability_routes import availability_bp
from chatbot_routes import chatbot_bp
from config import get_config_for_env
from debug_routes import debug_bp
from deploy import register_deploy_commands
from extensions import db, login_manager, mail, migrate
from health_routes import health_bp
from models import Settings, User
from reminders import register_reminder_commands
from routes import main_bp
from seed import register_seed_commands
from student_routes import student_bp


login_manager.login_view = "admin_bp.login"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def _ensure_upload_dirs(app: Flask) -> None:
    uploads_path = app.config["UPLOAD_FOLDER"]
    os.makedirs(uploads_path, exist_ok=True)
    os.makedirs(os.path.join(uploads_path, "courses"), exist_ok=True)
    os.makedirs(os.path.join(uploads_path, "gallery"), exist_ok=True)


def create_app(config_object=None) -> Flask:
    app = Flask(__name__)

    if config_object is None:
        config_class = get_config_for_env()
        app.config.from_object(config_class)
    elif isinstance(config_object, str):
        config_class = get_config_for_env(config_object)
        app.config.from_object(config_class)
    elif isinstance(config_object, dict):
        config_class = None
        app.config.from_object(get_config_for_env("development"))
        app.config.update(config_object)
    else:
        config_class = config_object
        app.config.from_object(config_object)

    if config_class and hasattr(config_class, "init_app"):
        config_class.init_app(app)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)

    app.register_blueprint(health_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(student_bp)
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(availability_bp)
    app.register_blueprint(appointments_bp)

    if app.config.get("ENABLE_DEBUG_ROUTES"):
        app.register_blueprint(debug_bp)

    register_seed_commands(app)
    register_reminder_commands(app)
    register_deploy_commands(app)
    _ensure_upload_dirs(app)

    @app.context_processor
    def inject_settings():
        settings = Settings.query.first()
        return {"settings": settings or {}, "current_year": datetime.now().year}

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=app.config.get("DEBUG", False))
