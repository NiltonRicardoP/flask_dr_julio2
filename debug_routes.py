from flask import Blueprint, jsonify, request

debug_bp = Blueprint("debug_bp", __name__)

@debug_bp.route("/api/debug/echo", methods=["POST", "GET"])
def echo():
    try:
        json_data = request.get_json(silent=True)
    except Exception:
        json_data = None

    resp = {
        "method": request.method,
        "path": request.path,
        "content_type": request.content_type,
        "mimetype": request.mimetype,
        "args": request.args.to_dict(flat=True),
        "form": request.form.to_dict(flat=True),
        "data_raw": request.data.decode("utf-8", errors="replace"),
        "json": json_data,
        "headers_subset": {
            "Content-Type": request.headers.get("Content-Type"),
            "Accept": request.headers.get("Accept"),
            "User-Agent": request.headers.get("User-Agent"),
        }
    }
    return jsonify(resp), 200
