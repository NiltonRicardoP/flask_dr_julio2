import os
from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError

from availability_service import is_slot_available, is_valid_slot
from extensions import db
from models import Appointment
from google_calendar import upsert_appointment_event, cancel_appointment_event

appointments_bp = Blueprint("appointments_bp", __name__)


# ---------------------------
# Helpers
# ---------------------------
def _require_admin():
    expected = (os.getenv("ADMIN_API_KEY") or "").strip()
    provided = (request.headers.get("X-Admin-Key") or "").strip()

    if not expected:
        return False, ("ADMIN_API_KEY nao esta configurado no servidor.", 500)

    if provided != expected:
        return False, ("Acesso negado (X-Admin-Key invalido).", 403)

    return True, None


def _parse_date(s: str):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def _parse_time(s: str):
    try:
        return datetime.strptime(s, "%H:%M").time()
    except Exception:
        return None


def _appt_to_dict(a: Appointment):
    return {
        "id": a.id,
        "name": a.name,
        "email": a.email,
        "phone": a.phone,
        "date": a.date.strftime("%Y-%m-%d") if a.date else None,
        "time": a.time.strftime("%H:%M") if a.time else None,
        "reason": getattr(a, "reason", None),
        "status": a.status,
        "created_at": a.created_at.isoformat() if getattr(a, "created_at", None) else None,
    }


def create_pending_appointment(
    *,
    name: str,
    phone: str,
    date_s: str,
    time_s: str,
    email: str | None = None,
    reason: str | None = None
):
    """
    Reusable helper (endpoint and chatbot).
    - Idempotent by (date, time, phone) when pending exists.
    - Avoids overbooking using availability rules.
    - Email saved as "" when missing (avoid NOT NULL).
    """
    day = _parse_date(date_s)
    slot_time = _parse_time(time_s)

    if not day or not slot_time:
        raise ValueError("Formato invalido. Use date=YYYY-MM-DD e time=HH:MM.")

    if not is_valid_slot(day, slot_time):
        raise ValueError("Horario fora da agenda. Escolha outro.")

    if datetime.combine(day, slot_time) < datetime.now():
        raise ValueError("Data e horario nao podem ser no passado.")

    # Idempotency: same phone in same slot returns existing pending record.
    same_pending = Appointment.query.filter(
        and_(
            Appointment.date == day,
            Appointment.time == slot_time,
            Appointment.phone == phone,
            Appointment.status == "pending",
        )
    ).first()
    if same_pending:
        if not same_pending.manage_token:
            same_pending.ensure_manage_token()
            db.session.commit()
        if not same_pending.google_event_id:
            upsert_appointment_event(same_pending)
        return same_pending

    if not is_slot_available(day, slot_time):
        raise ValueError("Este horario acabou de ser ocupado. Escolha outro.")

    safe_email = (email or "").strip()

    appt = Appointment(
        name=name.strip(),
        email=safe_email,
        phone=phone.strip(),
        date=day,
        time=slot_time,
        reason=reason,
        status="pending",
    )
    appt.ensure_manage_token()

    db.session.add(appt)
    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        msg = str(e.orig) if getattr(e, "orig", None) else str(e)
        if "Column 'email' cannot be null" in msg:
            raise ValueError("No momento o sistema exige email. Informe um email para continuar.")
        raise ValueError("Erro ao salvar agendamento.")

    upsert_appointment_event(appt)
    return appt


# ---------------------------
# Endpoints
# ---------------------------
@appointments_bp.route("/api/appointments", methods=["GET"])
def list_appointments():
    ok, err = _require_admin()
    if not ok:
        msg, code = err
        return jsonify({"ok": False, "error": msg}), code

    date_s = (request.args.get("date") or "").strip()
    if not date_s:
        return jsonify({"ok": False, "error": "Parametro date e obrigatorio (YYYY-MM-DD)."}), 400

    day = _parse_date(date_s)
    if not day:
        return jsonify({"ok": False, "error": "Formato invalido. Use YYYY-MM-DD."}), 400

    items = (
        Appointment.query
        .filter(Appointment.date == day)
        .order_by(Appointment.time.asc())
        .all()
    )

    return jsonify({
        "ok": True,
        "date": date_s,
        "count": len(items),
        "appointments": [_appt_to_dict(a) for a in items],
    }), 200


@appointments_bp.route("/api/appointments/request", methods=["POST"])
def request_appointment():
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    email = (data.get("email") or "").strip() or None
    date_s = (data.get("date") or "").strip()
    time_s = (data.get("time") or "").strip()
    reason = (data.get("reason") or "").strip() or None

    if not name or not phone or not date_s or not time_s:
        return jsonify({"ok": False, "error": "name, phone, date e time sao obrigatorios"}), 400

    try:
        appt = create_pending_appointment(
            name=name,
            phone=phone,
            email=email,
            date_s=date_s,
            time_s=time_s,
            reason=reason,
        )
    except ValueError as e:
        msg = str(e)
        if "ocupado" in msg.lower():
            return jsonify({"ok": False, "error": msg}), 409
        return jsonify({"ok": False, "error": msg}), 400

    return jsonify({
        "ok": True,
        "appointment_id": appt.id,
        "status": appt.status,
        "date": appt.date.strftime("%Y-%m-%d"),
        "time": appt.time.strftime("%H:%M"),
        "message": "Solicitacao registrada. Nossa equipe confirmara em breve.",
    }), 201


@appointments_bp.route("/api/appointments/<int:appt_id>/confirm", methods=["POST"])
def confirm_appointment(appt_id: int):
    ok, err = _require_admin()
    if not ok:
        msg, code = err
        return jsonify({"ok": False, "error": msg}), code

    appt = Appointment.query.get(appt_id)
    if not appt:
        return jsonify({"ok": False, "error": "Agendamento nao encontrado."}), 404

    if appt.status in ("canceled", "cancelled"):
        return jsonify({"ok": False, "error": "Nao e possivel confirmar um agendamento cancelado."}), 409

    appt.status = "confirmed"
    db.session.commit()
    upsert_appointment_event(appt)

    return jsonify({"ok": True, "appointment": _appt_to_dict(appt)}), 200


@appointments_bp.route("/api/appointments/<int:appt_id>/cancel", methods=["POST"])
def cancel_appointment(appt_id: int):
    ok, err = _require_admin()
    if not ok:
        msg, code = err
        return jsonify({"ok": False, "error": msg}), code

    appt = Appointment.query.get(appt_id)
    if not appt:
        return jsonify({"ok": False, "error": "Agendamento nao encontrado."}), 404

    appt.status = "cancelled"
    appt.cancelled_at = datetime.utcnow()
    db.session.commit()
    cancel_appointment_event(appt)

    return jsonify({"ok": True, "appointment": _appt_to_dict(appt)}), 200
