from app import create_app
from deploy import apply_database_migrations, ensure_admin_user


app = create_app()


with app.app_context():
    apply_database_migrations()
    info = ensure_admin_user(require_password=app.config.get("APP_ENV") == "production")
    if info["created"]:
        print("Usuario admin criado com sucesso.")
    else:
        print("Usuario admin atualizado.")
    if info["default_password_used"]:
        print("Aviso: usando senha padrao de desenvolvimento para o admin.")
