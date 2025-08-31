from app import app
from models import db, User

with app.app_context():
    db.create_all()
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(username="admin", email="admin@drjulio.com", role='admin')
        admin.set_password("12345678")
        db.session.add(admin)
        db.session.commit()
        print("✅ Usuário admin criado com sucesso.")
    else:
        print("ℹ️ Usuário admin já existe.")
