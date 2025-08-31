from app import app
from models import db, User

with app.app_context():
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(username="admin", email="admin@drjulio.com", role='admin')
        admin.set_password("12345678")
        db.session.add(admin)
        print("✅ Usuário admin criado com sucesso.")
    else:
        admin.role = 'admin'
        admin.set_password("12345678")
        print("🔄 Usuário admin atualizado.")
    db.session.commit()
