from app import app
from models import db, User

with app.app_context():
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
