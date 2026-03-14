import hmac

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import inspect, text

from extensions import db


health_bp = Blueprint("health_bp", __name__)


def _details_authorized() -> bool:
    configured_token = (current_app.config.get("HEALTHCHECK_TOKEN") or "").strip()
    if not configured_token:
        return bool(
            current_app.config.get("TESTING")
            or current_app.config.get("DEBUG")
            or current_app.config.get("HEALTHCHECK_ALLOW_DETAILS")
        )

    provided_token = (request.headers.get("X-Health-Token") or "").strip()
    return bool(provided_token) and hmac.compare_digest(configured_token, provided_token)


def _engine_url() -> str:
    return db.engine.url.render_as_string(hide_password=True)


@health_bp.route("/api/health/db", methods=["GET"])
def health_db():
    tables_flag = request.args.get("tables", "0") == "1"
    write_flag = request.args.get("write", "0") == "1"
    details_allowed = _details_authorized()

    if (tables_flag or write_flag) and not details_allowed:
        return jsonify({"ok": False, "error": "forbidden"}), 403

    if write_flag and not current_app.config.get("HEALTHCHECK_ALLOW_WRITE", False):
        return jsonify({"ok": False, "error": "write checks disabled"}), 403

    try:
        db.session.execute(text("SELECT 1"))

        result = {"ok": True}
        if details_allowed:
            result.update(
                {
                    "database": db.engine.url.database,
                    "dialect": db.engine.dialect.name,
                    "engine_url": _engine_url(),
                }
            )

        if write_flag:
            db.session.execute(text("CREATE TABLE IF NOT EXISTS __ping (id INTEGER PRIMARY KEY)"))
            exists = db.session.execute(text("SELECT 1 FROM __ping WHERE id = 1")).scalar()
            if not exists:
                db.session.execute(text("INSERT INTO __ping (id) VALUES (1)"))
            db.session.commit()
            result["write_test"] = "ok"

        if tables_flag:
            tables = inspect(db.engine).get_table_names()
            result["tables"] = tables
            result["tables_count"] = len(tables)

        return jsonify(result), 200
    except Exception as exc:
        db.session.rollback()
        if details_allowed:
            return jsonify({"ok": False, "error": str(exc), "engine_url": _engine_url()}), 503
        return jsonify({"ok": False, "error": "database unavailable"}), 503
