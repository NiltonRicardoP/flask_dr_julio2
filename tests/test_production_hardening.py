from app import create_app
from extensions import db


def _build_app(**overrides):
    config = {
        "TESTING": False,
        "DEBUG": False,
        "SECRET_KEY": "test-secret",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_ENGINE_OPTIONS": {},
        "WTF_CSRF_ENABLED": False,
        "ENABLE_DEBUG_ROUTES": False,
        "HEALTHCHECK_ALLOW_DETAILS": False,
        "HEALTHCHECK_ALLOW_WRITE": False,
    }
    config.update(overrides)
    app = create_app(config)
    with app.app_context():
        db.create_all()
    return app


def test_debug_route_disabled_by_default():
    app = _build_app()
    client = app.test_client()

    resp = client.get("/api/debug/echo")

    assert resp.status_code == 404


def test_healthcheck_hides_details_and_blocks_table_listing_without_token():
    app = _build_app()
    client = app.test_client()

    resp = client.get("/api/health/db")
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}

    resp = client.get("/api/health/db?tables=1")
    assert resp.status_code == 403


def test_healthcheck_allows_details_with_token():
    app = _build_app(HEALTHCHECK_TOKEN="health-secret")
    client = app.test_client()

    resp = client.get("/api/health/db?tables=1", headers={"X-Health-Token": "health-secret"})

    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["ok"] is True
    assert payload["dialect"] == "sqlite"
    assert "tables_count" in payload


def test_healthcheck_blocks_write_checks_unless_explicitly_enabled():
    app = _build_app(HEALTHCHECK_TOKEN="health-secret")
    client = app.test_client()

    resp = client.get("/api/health/db?write=1", headers={"X-Health-Token": "health-secret"})

    assert resp.status_code == 403
