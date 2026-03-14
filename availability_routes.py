from datetime import datetime
from flask import Blueprint, jsonify, request

from availability_service import get_availability

availability_bp = Blueprint("availability_bp", __name__)

def _parse_date(s: str):
    s = (s or "").strip()
    if not s:
        return None

    # aceita YYYY-MM-DD
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        pass

    # aceita DD/MM/YYYY
    try:
        return datetime.strptime(s, "%d/%m/%Y").date()
    except Exception:
        return None

@availability_bp.route("/api/availability", methods=["GET"])
def availability():
    day = _parse_date(request.args.get("date"))
    if not day:
        return jsonify({"ok": False, "error": "Parâmetro 'date' obrigatório (YYYY-MM-DD ou DD/MM/YYYY)"}), 400

    data = get_availability(day)
    return jsonify({"ok": True, **data}), 200
