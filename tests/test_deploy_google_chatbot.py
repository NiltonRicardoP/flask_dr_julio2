import io
import json

from app import create_app
from deploy import apply_database_migrations, ensure_admin_user, ensure_settings_record
from extensions import db
from google_calendar import get_google_credentials_details
from models import Appointment, Settings, User


def _create_admin():
    admin = User.query.filter_by(username="admin").first()
    if admin is None:
        admin = User(username="admin", email="admin@example.com", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
    return admin


def _login_admin(client):
    with client.application.app_context():
        _create_admin()
    return client.post(
        "/admin/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )


def test_google_calendar_credentials_can_be_saved_from_admin(client):
    _login_admin(client)
    payload = {
        "type": "service_account",
        "project_id": "drjulio-test",
        "private_key_id": "abc123",
        "private_key": "-----BEGIN PRIVATE KEY-----\\nabc\\n-----END PRIVATE KEY-----\\n",
        "client_email": "calendar-bot@drjulio-test.iam.gserviceaccount.com",
        "client_id": "1234567890",
        "token_uri": "https://oauth2.googleapis.com/token",
    }

    response = client.post(
        "/admin/settings/google-calendar",
        data={
            "google_calendar_id": "agenda@drjulio.com",
            "google_attendee_emails": "contato@drjulio.com",
            "google_sync_enabled": "y",
            "google_credentials_file": (
                io.BytesIO(json.dumps(payload).encode("utf-8")),
                "service-account.json",
            ),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200

    with client.application.app_context():
        settings = Settings.query.first()
        assert settings is not None
        assert settings.google_calendar_id == "agenda@drjulio.com"
        assert settings.google_credentials_filename == "service-account.json"
        assert settings.google_credentials_json is not None
        details = get_google_credentials_details(settings)
        assert details["exists"] is True
        assert details["source"] == "db"
        assert details["client_email"] == payload["client_email"]


def test_apply_database_migrations_creates_schema_for_empty_database(tmp_path, monkeypatch):
    db_path = tmp_path / "deploy-test.db"
    monkeypatch.setenv("ADMIN_PASSWORD", "Admin123!")

    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "WTF_CSRF_ENABLED": False,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SQLALCHEMY_ENGINE_OPTIONS": {},
        }
    )

    with app.app_context():
        tables = apply_database_migrations()
        settings, created_settings = ensure_settings_record()
        admin_info = ensure_admin_user(require_password=False)

        assert "appointment" in tables
        assert "settings" in tables
        assert settings is not None
        assert created_settings is True
        assert admin_info["username"] == "admin"
        assert User.query.filter_by(username="admin").first() is not None


def test_chatbot_creates_pending_appointment(client):
    response = client.post(
        "/api/chat",
        json={
            "message": (
                "Quero agendar uma consulta em 2035-12-07 10:00. "
                "Meu nome e Maria Silva, whatsapp 21999999999, "
                "email maria@example.com, motivo retorno."
            )
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert "Perfeito! Registrei seu pedido de agendamento." in data["reply"]

    with client.application.app_context():
        appt = Appointment.query.first()
        assert appt is not None
        assert appt.name == "Maria Silva"
        assert appt.phone == "21999999999"
        assert appt.email == "maria@example.com"
        assert appt.status == "pending"


def test_chatbot_rejects_oversized_message(client):
    response = client.post("/api/chat", json={"message": "a" * 501})
    assert response.status_code == 400
    data = response.get_json()
    assert data["ok"] is False
    assert "excede 500 caracteres" in data["error"]
