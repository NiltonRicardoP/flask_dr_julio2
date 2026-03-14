import os

from flask_migrate import upgrade

from app import create_app
from models import User, db


app = create_app()


with app.app_context():
    upgrade()

    username = os.getenv("ADMIN_USERNAME", "admin").strip() or "admin"
    email = os.getenv("ADMIN_EMAIL", "admin@drjulio.com").strip() or "admin@drjulio.com"
    password = os.getenv("ADMIN_PASSWORD", "").strip()

    if not password and app.config.get("APP_ENV") == "production":
        raise SystemExit("ADMIN_PASSWORD deve ser definido para criar o admin em producao.")

    if not password:
        password = "12345678"
        print("Aviso: usando senha padrao de desenvolvimento para o admin.")

    admin = User.query.filter_by(username=username).first()
    if not admin:
        admin = User(username=username, email=email)
        db.session.add(admin)
        print("Usuario admin criado com sucesso.")
    else:
        print("Usuario admin atualizado.")

    admin.email = email
    admin.role = "admin"
    admin.set_password(password)
    db.session.commit()
