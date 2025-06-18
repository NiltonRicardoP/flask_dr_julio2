from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail
from flask_migrate import Migrate
from datetime import datetime
import os

from config import Config
from extensions import db  # Correto: db importado do extensions.py
from models import User, Event, Appointment, Settings
from forms import LoginForm, AppointmentForm, ContactForm, EventForm, SettingsForm
from routes import main_bp
from admin_routes import admin_bp

# Create Flask application
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'admin_bp.login'
mail = Mail(app)

# Register blueprints
app.register_blueprint(main_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')

# Flask-Login: Carregador de usuário
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Inicialização customizada (sem create_all)
def create_initial_data():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            user = User(username='admin', email='admin@example.com')
            user.set_password('admin123')
            db.session.add(user)

            if not Settings.query.first():
                settings = Settings(
                    site_title="Dr. Julio Vasconcelos",
                    contact_email="contato@drjulio.com",
                    contact_phone="(11) 99999-9999",
                    address="Av. Paulista, 1000, São Paulo - SP",
                    about_text="Médico experiente com anos de prática clínica."
                )
                db.session.add(settings)

            db.session.commit()

# Criação de pasta de uploads caso não exista
if __name__ == '__main__':
    uploads_path = os.path.join(app.root_path, 'static', 'uploads')
    os.makedirs(uploads_path, exist_ok=True)

    create_initial_data()  # ✅ Só executa quando rodar diretamente (não em flask db ...)
    app.run(debug=True)

