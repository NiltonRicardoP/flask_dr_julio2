from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Iterable

from flask import current_app, has_app_context

from extensions import db
from models import Appointment, Settings, CalendarEvent

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except Exception:  # pragma: no cover - optional dependency in some environments
    service_account = None
    build = None

    class HttpError(Exception):
        pass

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - fallback for older Python
    ZoneInfo = None


SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _config_value(key: str, default: str | None = None) -> str | None:
    value = (os.getenv(key) or "").strip()
    if value:
        return value
    if has_app_context():
        app_value = current_app.config.get(key)
        if app_value is not None and str(app_value).strip():
            return str(app_value).strip()
    return default


def _get_settings(settings: Settings | None) -> Settings | None:
    return settings or Settings.query.first()


def _get_calendar_id(settings: Settings | None) -> str | None:
    settings = _get_settings(settings)
    if settings and settings.google_calendar_id:
        value = settings.google_calendar_id.strip()
        if value:
            return value
    return _config_value("GOOGLE_CALENDAR_ID")


def _get_credentials_path() -> str | None:
    return _config_value("GOOGLE_CREDENTIALS_FILE")


def _parse_service_account_info(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def get_google_credentials_details(settings: Settings | None = None) -> dict:
    settings = _get_settings(settings)
    payload = None
    source = "none"
    display = ""
    path = ""

    if settings and settings.google_credentials_json:
        payload = _parse_service_account_info(settings.google_credentials_json)
        if payload:
            source = "db"
            display = (settings.google_credentials_filename or "service-account.json").strip() or "service-account.json"

    if payload is None:
        path = _get_credentials_path() or ""
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)
            except (OSError, ValueError, json.JSONDecodeError):
                payload = None
            else:
                if not isinstance(payload, dict):
                    payload = None
                else:
                    source = "env"
                    display = os.path.basename(path)

    client_email = ""
    if isinstance(payload, dict):
        client_email = (payload.get("client_email") or "").strip()

    return {
        "exists": payload is not None,
        "source": source,
        "display": display,
        "path": path,
        "info": payload,
        "client_email": client_email,
    }


def _get_timezone() -> str:
    return _config_value("GOOGLE_CALENDAR_TZ", "America/Sao_Paulo") or "America/Sao_Paulo"


def _get_duration_minutes() -> int:
    raw = _config_value("GOOGLE_APPT_DURATION_MINUTES", "50") or "50"
    try:
        value = int(raw)
    except ValueError:
        value = 50
    return max(10, min(value, 180))


def _get_sync_min_interval_minutes() -> int:
    raw = _config_value("GOOGLE_SYNC_MIN_INTERVAL_MIN", "2") or "2"
    try:
        value = int(raw)
    except ValueError:
        value = 2
    return max(1, min(value, 60))


def _load_credentials(settings: Settings | None = None):
    if service_account is None:
        return None
    details = get_google_credentials_details(settings)
    if not details["exists"]:
        return None
    if details["source"] == "db":
        return service_account.Credentials.from_service_account_info(details["info"], scopes=SCOPES)
    path = details["path"]
    if not path:
        return None
    if not os.path.exists(path):
        if has_app_context():
            current_app.logger.warning("Google credentials file not found: %s", path)
        return None
    return service_account.Credentials.from_service_account_file(path, scopes=SCOPES)


def _get_service(settings: Settings | None = None):
    if build is None:
        return None
    creds = _load_credentials(settings)
    if not creds:
        return None
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _parse_attendee_emails(raw: str | None) -> list[str]:
    if not raw:
        return []
    emails = []
    for part in raw.replace("\n", ",").split(","):
        candidate = part.strip()
        if candidate:
            emails.append(candidate)
    # Preserve order but remove duplicates.
    seen = set()
    unique = []
    for email in emails:
        if email.lower() in seen:
            continue
        seen.add(email.lower())
        unique.append(email)
    return unique


def _strip_attendees(body: dict) -> dict:
    if "attendees" not in body:
        return body
    sanitized = dict(body)
    sanitized.pop("attendees", None)
    return sanitized


def _is_forbidden_attendees_error(exc: Exception) -> bool:
    if not isinstance(exc, HttpError):
        return False
    status = getattr(getattr(exc, "resp", None), "status", None)
    if status != 403:
        return False
    content = getattr(exc, "content", None)
    if not content:
        return False
    try:
        data = json.loads(content.decode("utf-8"))
    except Exception:
        return False
    error = data.get("error", {}) if isinstance(data, dict) else {}
    reasons = []
    for item in error.get("errors", []) if isinstance(error, dict) else []:
        reason = item.get("reason")
        if reason:
            reasons.append(reason)
    if "forbiddenForServiceAccounts" in reasons:
        return True
    message = str(error.get("message") or "")
    return "service accounts cannot invite attendees" in message.lower()


def _to_timezone(dt: datetime, tz: str) -> datetime:
    if ZoneInfo is None:
        return dt
    try:
        tzinfo = ZoneInfo(tz)
    except Exception:
        return dt
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tzinfo)
    return dt.astimezone(tzinfo)


def _event_description(appointment: Appointment) -> str:
    lines = [
        f"Paciente: {appointment.name}",
        f"Telefone: {appointment.phone}",
    ]
    if appointment.email:
        lines.append(f"Email: {appointment.email}")
    if appointment.reason:
        lines.append("")
        lines.append("Motivo:")
        lines.append(appointment.reason)

    base_url = (_config_value("PUBLIC_BASE_URL") or "").rstrip("/")
    if base_url and appointment.manage_token:
        lines.append("")
        lines.append(f"Gerenciar: {base_url}/appointment/manage/{appointment.manage_token}")
    return "\n".join(lines)


def _build_event_body(appointment: Appointment, settings: Settings | None) -> dict:
    tz = _get_timezone()
    duration = _get_duration_minutes()
    start_dt = datetime.combine(appointment.date, appointment.time)
    end_dt = start_dt + timedelta(minutes=duration)
    start_dt = _to_timezone(start_dt, tz)
    end_dt = _to_timezone(end_dt, tz)

    private_props = {
        "appointment_id": str(appointment.id),
        "manage_token": appointment.manage_token or "",
        "source": "dr_julio",
    }

    body = {
        "summary": f"Consulta - {appointment.name}",
        "description": _event_description(appointment),
        "start": {"dateTime": start_dt.isoformat(), "timeZone": tz},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": tz},
        "extendedProperties": {"private": private_props},
    }

    settings = _get_settings(settings)
    attendee_raw = settings.google_attendee_emails if settings else None
    attendees = _parse_attendee_emails(attendee_raw)
    if attendees:
        body["attendees"] = [{"email": email} for email in attendees]
    return body


def _parse_google_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _extract_event_times(event: dict):
    tz = _get_timezone()
    start = event.get("start", {})
    end = event.get("end", {})

    start_dt = _parse_google_datetime(start.get("dateTime"))
    end_dt = _parse_google_datetime(end.get("dateTime"))
    if start_dt:
        all_day = False
        start_dt = _to_timezone(start_dt, tz)
        if end_dt:
            end_dt = _to_timezone(end_dt, tz)
        else:
            end_dt = start_dt + timedelta(minutes=_get_duration_minutes())
    else:
        start_date = _parse_google_date(start.get("date"))
        end_date = _parse_google_date(end.get("date"))
        if not start_date:
            return None, None, False
        all_day = True
        start_dt = datetime.combine(start_date, datetime.min.time())
        if not end_date:
            end_date = start_date + timedelta(days=1)
        end_dt = datetime.combine(end_date, datetime.min.time())

    if start_dt.tzinfo is not None:
        start_dt = start_dt.replace(tzinfo=None)
    if end_dt.tzinfo is not None:
        end_dt = end_dt.replace(tzinfo=None)
    return start_dt, end_dt, all_day


def _calendar_event_private_props(event: CalendarEvent) -> dict:
    return {
        "calendar_event_id": str(event.id),
        "source": "dr_julio_calendar",
    }


def _build_calendar_event_body(event: CalendarEvent, settings: Settings | None) -> dict:
    tz = _get_timezone()
    start_dt = event.start_at
    end_dt = event.end_at
    if start_dt.tzinfo is not None:
        start_dt = start_dt.replace(tzinfo=None)
    if end_dt.tzinfo is not None:
        end_dt = end_dt.replace(tzinfo=None)

    if event.all_day:
        body = {
            "summary": event.title,
            "description": event.description or "",
            "start": {"date": start_dt.date().isoformat()},
            "end": {"date": end_dt.date().isoformat()},
            "extendedProperties": {"private": _calendar_event_private_props(event)},
        }
    else:
        start_dt = _to_timezone(start_dt, tz)
        end_dt = _to_timezone(end_dt, tz)
        body = {
            "summary": event.title,
            "description": event.description or "",
            "start": {"dateTime": start_dt.isoformat(), "timeZone": tz},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": tz},
            "extendedProperties": {"private": _calendar_event_private_props(event)},
        }

    settings = _get_settings(settings)
    attendee_raw = settings.google_attendee_emails if settings else None
    attendees = _parse_attendee_emails(attendee_raw)
    if attendees:
        body["attendees"] = [{"email": email} for email in attendees]
    return body


def _should_sync(settings: Settings | None) -> bool:
    settings = _get_settings(settings)
    if not settings or not settings.google_sync_enabled:
        return False
    if not _get_calendar_id(settings):
        return False
    if not get_google_credentials_details(settings)["exists"]:
        return False
    return True


def _send_updates_param(attendees: Iterable[str]) -> str:
    return "all" if attendees else "none"


def upsert_appointment_event(appointment: Appointment, settings: Settings | None = None) -> bool:
    settings = _get_settings(settings)
    if not _should_sync(settings):
        return False
    service = _get_service(settings)
    if not service:
        return False

    calendar_id = _get_calendar_id(settings)
    if not calendar_id:
        return False

    body = _build_event_body(appointment, settings)
    attendees = [a["email"] for a in body.get("attendees", [])]
    send_updates = _send_updates_param(attendees)

    def _perform_upsert(payload: dict, updates: str):
        if appointment.google_event_id:
            try:
                return (
                    service.events()
                    .update(calendarId=calendar_id, eventId=appointment.google_event_id, body=payload, sendUpdates=updates)
                    .execute()
                )
            except HttpError as exc:
                if getattr(getattr(exc, "resp", None), "status", None) == 404:
                    return (
                        service.events()
                        .insert(calendarId=calendar_id, body=payload, sendUpdates=updates)
                        .execute()
                    )
                raise
        return (
            service.events()
            .insert(calendarId=calendar_id, body=payload, sendUpdates=updates)
            .execute()
        )

    try:
        event = _perform_upsert(body, send_updates)
    except Exception as exc:
        if _is_forbidden_attendees_error(exc) and body.get("attendees"):
            fallback_body = _strip_attendees(body)
            try:
                if has_app_context():
                    current_app.logger.warning(
                        "Service account nao pode convidar participantes. Criando evento sem convites."
                    )
                event = _perform_upsert(fallback_body, "none")
            except Exception as retry_exc:
                if has_app_context():
                    current_app.logger.exception("Falha ao sincronizar com Google Agenda: %s", retry_exc)
                return False
        else:
            if has_app_context():
                current_app.logger.exception("Falha ao sincronizar com Google Agenda: %s", exc)
            return False

    event_id = event.get("id") if isinstance(event, dict) else None
    if event_id and appointment.google_event_id != event_id:
        appointment.google_event_id = event_id
        db.session.commit()
    return True


def upsert_calendar_event(event: CalendarEvent, settings: Settings | None = None) -> bool:
    settings = _get_settings(settings)
    if not _should_sync(settings):
        return False
    service = _get_service(settings)
    if not service:
        return False

    calendar_id = _get_calendar_id(settings)
    if not calendar_id:
        return False

    body = _build_calendar_event_body(event, settings)
    attendees = [a["email"] for a in body.get("attendees", [])]
    send_updates = _send_updates_param(attendees)

    def _perform_upsert(payload: dict, updates: str):
        if event.google_event_id:
            try:
                return (
                    service.events()
                    .update(calendarId=calendar_id, eventId=event.google_event_id, body=payload, sendUpdates=updates)
                    .execute()
                )
            except HttpError as exc:
                if getattr(getattr(exc, "resp", None), "status", None) == 404:
                    return (
                        service.events()
                        .insert(calendarId=calendar_id, body=payload, sendUpdates=updates)
                        .execute()
                    )
                raise
        return (
            service.events()
            .insert(calendarId=calendar_id, body=payload, sendUpdates=updates)
            .execute()
        )

    try:
        event_data = _perform_upsert(body, send_updates)
    except Exception as exc:
        if _is_forbidden_attendees_error(exc) and body.get("attendees"):
            fallback_body = _strip_attendees(body)
            try:
                if has_app_context():
                    current_app.logger.warning(
                        "Service account nao pode convidar participantes. Criando evento sem convites."
                    )
                event_data = _perform_upsert(fallback_body, "none")
            except Exception as retry_exc:
                if has_app_context():
                    current_app.logger.exception("Falha ao sincronizar com Google Agenda: %s", retry_exc)
                return False
        else:
            if has_app_context():
                current_app.logger.exception("Falha ao sincronizar com Google Agenda: %s", exc)
            return False

    event_id = event_data.get("id") if isinstance(event_data, dict) else None
    if event_id and event.google_event_id != event_id:
        event.google_event_id = event_id
        db.session.commit()
    return True


def cancel_calendar_event(event: CalendarEvent, settings: Settings | None = None) -> bool:
    settings = _get_settings(settings)
    if not _should_sync(settings):
        return False
    service = _get_service(settings)
    if not service:
        return False

    calendar_id = _get_calendar_id(settings)
    if not calendar_id:
        return False

    if not event.google_event_id:
        return False

    try:
        service.events().delete(calendarId=calendar_id, eventId=event.google_event_id, sendUpdates="none").execute()
    except Exception as exc:
        if has_app_context():
            current_app.logger.exception("Falha ao cancelar evento no Google Agenda: %s", exc)
        return False
    return True


def cancel_appointment_event(appointment: Appointment, settings: Settings | None = None) -> bool:
    settings = _get_settings(settings)
    if not _should_sync(settings):
        return False
    service = _get_service(settings)
    if not service:
        return False

    calendar_id = _get_calendar_id(settings)
    if not calendar_id:
        return False

    if not appointment.google_event_id:
        return False

    try:
        service.events().delete(calendarId=calendar_id, eventId=appointment.google_event_id, sendUpdates="all").execute()
    except Exception as exc:
        if has_app_context():
            current_app.logger.exception("Falha ao cancelar evento no Google Agenda: %s", exc)
        return False
    return True


def _parse_google_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _find_appointment_for_event(event: dict) -> Appointment | None:
    event_id = event.get("id")
    private_props = event.get("extendedProperties", {}).get("private", {})
    appointment_id = private_props.get("appointment_id")

    appointment = None
    if appointment_id:
        try:
            appointment = Appointment.query.get(int(appointment_id))
        except (TypeError, ValueError):
            appointment = None
    if not appointment and event_id:
        appointment = Appointment.query.filter_by(google_event_id=event_id).first()
    return appointment


def _find_calendar_event_for_event(event: dict) -> CalendarEvent | None:
    event_id = event.get("id")
    if not event_id:
        return None
    return CalendarEvent.query.filter_by(google_event_id=event_id).first()


def _apply_event_to_appointment(event: dict, appointment: Appointment) -> bool:
    status = (event.get("status") or "").lower()
    if status == "cancelled":
        if appointment.status not in ("cancelled", "canceled"):
            appointment.status = "cancelled"
            appointment.cancelled_at = datetime.utcnow()
            return True
        return False

    if appointment.status in ("cancelled", "canceled"):
        return False

    start = event.get("start", {})
    start_dt = _parse_google_datetime(start.get("dateTime"))
    if not start_dt:
        return False

    tz = _get_timezone()
    start_dt = _to_timezone(start_dt, tz)
    new_date = start_dt.date()
    new_time = start_dt.time().replace(second=0, microsecond=0)

    if appointment.date != new_date or appointment.time != new_time:
        appointment.date = new_date
        appointment.time = new_time
        appointment.status = appointment.status or "pending"
        appointment.rescheduled_at = datetime.utcnow()
        appointment.reminder_sent_at = None
        return True
    return False


def _apply_event_to_calendar_event(event: dict, item: CalendarEvent) -> bool:
    status = (event.get("status") or "").lower()
    if status == "cancelled":
        if item.status != "cancelled":
            item.status = "cancelled"
            return True
        return False

    start_dt, end_dt, all_day = _extract_event_times(event)
    if not start_dt or not end_dt:
        return False

    title = (event.get("summary") or "Evento sem titulo").strip()
    description = event.get("description") or None

    changed = False
    if item.title != title:
        item.title = title
        changed = True
    if item.description != description:
        item.description = description
        changed = True
    if item.start_at != start_dt:
        item.start_at = start_dt
        changed = True
    if item.end_at != end_dt:
        item.end_at = end_dt
        changed = True
    if item.all_day != all_day:
        item.all_day = all_day
        changed = True
    if item.status != "active":
        item.status = "active"
        changed = True
    return changed


def sync_google_calendar(settings: Settings | None = None, force: bool = False) -> bool:
    settings = _get_settings(settings)
    if not _should_sync(settings):
        return False

    now = datetime.utcnow()
    if not force and settings.google_sync_last_at:
        delta = now - settings.google_sync_last_at
        if delta.total_seconds() < _get_sync_min_interval_minutes() * 60:
            return False

    service = _get_service(settings)
    if not service:
        return False

    calendar_id = _get_calendar_id(settings)
    if not calendar_id:
        return False

    events = []
    next_sync_token = None

    params = {
        "calendarId": calendar_id,
        "singleEvents": True,
        "showDeleted": True,
        "maxResults": 250,
    }

    if settings.google_sync_token:
        params["syncToken"] = settings.google_sync_token
    else:
        time_min = (datetime.utcnow() - timedelta(days=90)).isoformat() + "Z"
        params["timeMin"] = time_min

    page_token = None
    try:
        while True:
            if page_token:
                params["pageToken"] = page_token
            response = service.events().list(**params).execute()
            events.extend(response.get("items", []))
            page_token = response.get("nextPageToken")
            next_sync_token = response.get("nextSyncToken") or next_sync_token
            if not page_token:
                break
    except HttpError as exc:
        if getattr(getattr(exc, "resp", None), "status", None) == 410:
            settings.google_sync_token = None
            db.session.commit()
            return sync_google_calendar(settings=settings, force=True)
        if has_app_context():
            current_app.logger.exception("Falha ao listar eventos do Google Agenda: %s", exc)
        return False
    except Exception as exc:
        if has_app_context():
            current_app.logger.exception("Falha ao listar eventos do Google Agenda: %s", exc)
        return False

    changed = False
    for event in events:
        appointment = _find_appointment_for_event(event)
        if appointment:
            if not appointment.google_event_id and event.get("id"):
                appointment.google_event_id = event.get("id")
                changed = True
            if _apply_event_to_appointment(event, appointment):
                changed = True
            continue

        cal_event = _find_calendar_event_for_event(event)
        if not cal_event:
            status = (event.get("status") or "").lower()
            if status == "cancelled":
                continue
            start_dt, end_dt, all_day = _extract_event_times(event)
            if not start_dt or not end_dt:
                continue
            private_props = event.get("extendedProperties", {}).get("private", {})
            source = "google"
            if private_props.get("source") == "dr_julio_calendar":
                source = "system"
            cal_event = CalendarEvent(
                title=(event.get("summary") or "Evento sem titulo").strip(),
                description=event.get("description") or None,
                start_at=start_dt,
                end_at=end_dt,
                all_day=all_day,
                status="active",
                source=source,
                google_event_id=event.get("id"),
            )
            db.session.add(cal_event)
            changed = True

        if cal_event and not cal_event.google_event_id and event.get("id"):
            cal_event.google_event_id = event.get("id")
            changed = True
        if cal_event and _apply_event_to_calendar_event(event, cal_event):
            changed = True

    if next_sync_token and next_sync_token != settings.google_sync_token:
        settings.google_sync_token = next_sync_token
        changed = True

    settings.google_sync_last_at = datetime.utcnow()
    changed = True

    if changed:
        db.session.commit()
    return True
