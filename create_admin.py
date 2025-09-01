from app import app
from models import db, User
from flask_migrate import upgrade

with app.app_context():
    # Ensure the database schema is up to date using migrations
    upgrade()

    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(username="admin", email="admin@drjulio.com")
        db.session.add(admin)
        print("✅ Usuário admin criado com sucesso.")
    else:
        print("🔄 Usuário admin atualizado.")

    admin.role = 'admin'
    admin.set_password("12345678")  # ou senha via env
    db.session.commit()
