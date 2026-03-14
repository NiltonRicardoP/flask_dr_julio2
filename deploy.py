from __future__ import annotations

import os

import click
from flask_migrate import upgrade
from sqlalchemy import inspect, or_

from extensions import db
from models import Settings, User


def _list_app_tables() -> list[str]:
    tables = inspect(db.engine).get_table_names()
    return [name for name in tables if name != "alembic_version" and not name.startswith("sqlite_")]


def apply_database_migrations() -> list[str]:
    upgrade()
    tables = _list_app_tables()
    if not tables:
        raise click.ClickException(
            "As migracoes nao criaram nenhuma tabela. Verifique a configuracao do Alembic antes do deploy."
        )
    return tables


def ensure_settings_record() -> tuple[Settings, bool]:
    settings = Settings.query.first()
    if settings:
        return settings, False
    settings = Settings()
    db.session.add(settings)
    db.session.commit()
    return settings, True


def ensure_admin_user(*, require_password: bool) -> dict:
    username = (os.getenv("ADMIN_USERNAME") or "admin").strip() or "admin"
    email = (os.getenv("ADMIN_EMAIL") or "admin@drjulio.com").strip() or "admin@drjulio.com"
    password = (os.getenv("ADMIN_PASSWORD") or "").strip()

    admin = (
        User.query
        .filter(or_(User.username == username, User.email == email))
        .order_by(User.id.asc())
        .first()
    )

    created = False
    password_updated = False
    default_password_used = False

    if not admin:
        if not password and require_password:
            raise click.ClickException(
                "ADMIN_PASSWORD deve ser definido para criar o admin em producao."
            )
        admin = User(username=username, email=email, role="admin")
        db.session.add(admin)
        created = True

    admin.username = username
    admin.email = email
    admin.role = "admin"

    if password:
        admin.set_password(password)
        password_updated = True
    elif created:
        admin.set_password("12345678")
        password_updated = True
        default_password_used = True

    db.session.commit()
    return {
        "username": username,
        "email": email,
        "created": created,
        "password_updated": password_updated,
        "default_password_used": default_password_used,
    }


def register_deploy_commands(app):
    @app.cli.command("deploy")
    def deploy_cmd():
        """Aplica migracoes e garante registros basicos para producao."""
        tables = apply_database_migrations()
        _, settings_created = ensure_settings_record()
        admin_info = ensure_admin_user(require_password=app.config.get("APP_ENV") == "production")

        click.echo(f"Migracoes aplicadas. Tabelas detectadas: {len(tables)}")
        click.echo("Settings criado." if settings_created else "Settings ja existia.")

        if admin_info["created"]:
            click.echo(f"Admin criado: {admin_info['username']} ({admin_info['email']})")
        else:
            click.echo(f"Admin validado: {admin_info['username']} ({admin_info['email']})")

        if admin_info["default_password_used"]:
            click.echo("Aviso: senha padrao de desenvolvimento aplicada ao admin.")
        elif admin_info["password_updated"]:
            click.echo("Senha do admin atualizada a partir do ambiente.")
        else:
            click.echo("Senha do admin preservada.")
