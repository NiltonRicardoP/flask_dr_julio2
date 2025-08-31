from flask import Flask
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
import os

from config import Config
from extensions import db  # Correto: db importado do extensions.py
from models import User
from routes import main_bp
from admin_routes import admin_bp
from student_routes import student_bp

# Create Flask application
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'student_bp.login'
mail = Mail(app)

# Register blueprints
app.register_blueprint(main_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(student_bp, url_prefix='/aluno')

# Flask-Login: Carregador de usuário
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Criação de pasta de uploads caso não exista
if __name__ == '__main__':
    uploads_path = os.path.join(app.root_path, 'static', 'uploads')
    os.makedirs(uploads_path, exist_ok=True)
    courses_path = os.path.join(uploads_path, 'courses')
    os.makedirs(courses_path, exist_ok=True)
    content_path = os.path.join(app.root_path, 'course_content')
    os.makedirs(content_path, exist_ok=True)

    app.run(debug=True)

