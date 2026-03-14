import os
import re
import unicodedata
from datetime import datetime, date, time as dtime, timedelta

from flask import Blueprint, jsonify, request, current_app
from flask_mail import Message

from extensions import db
from appointments_api import create_pending_appointment
from models import Appointment, Settings, Convenio, Course, Event, ContactMessage

chatbot_bp = Blueprint("chatbot_bp", __name__)

_DATE_YMD = re.compile(r"\b(20\d{2})[-/\.](\d{1,2})[-/\.](\d{1,2})\b")
_DATE_DMY = re.compile(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](20\d{2}))?\b")

_TIME_HHMM_COLON = re.compile(r"\b([01]?\d|2[0-3])[:hH]([0-5]\d)\b")
_TIME_H_ONLY = re.compile(r"\b([01]?\d|2[0-3])\s*h\b")
_TIME_4DIGITS = re.compile(r"\b([01]\d|2[0-3])([0-5]\d)\b")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _normalize(text: str) -> str:
    s = (text or "").strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(k in text for k in keywords)


def _safe_int(x, default=None):
    try:
        return int(x)
    except Exception:
        return default


def parse_day_from_text(text: str) -> date | None:
    s = (text or "").strip().lower()
    today = date.today()

    if "hoje" in s:
        return today
    if "amanh" in s:
        return today + timedelta(days=1)

    m = _DATE_YMD.search(s)
    if m:
        yy = _safe_int(m.group(1))
        mm = _safe_int(m.group(2))
        dd = _safe_int(m.group(3))
        try:
            return date(yy, mm, dd)
        except Exception:
            return None

    m = _DATE_DMY.search(s)
    if m:
        dd = _safe_int(m.group(1))
        mm = _safe_int(m.group(2))
        yy = _safe_int(m.group(3)) or today.year
        try:
            return date(yy, mm, dd)
        except Exception:
            return None

    return None


def parse_time_from_text(text: str) -> dtime | None:
    s = (text or "").strip().lower()

    m = _TIME_HHMM_COLON.search(s)
    if m:
        hh = _safe_int(m.group(1))
        mm = _safe_int(m.group(2))
        try:
            return dtime(hh, mm)
        except Exception:
            return None

    m = _TIME_4DIGITS.search(s)
    if m:
        hh = _safe_int(m.group(1))
        mm = _safe_int(m.group(2))
        try:
            return dtime(hh, mm)
        except Exception:
            return None

    m = _TIME_H_ONLY.search(s)
    if m:
        hh = _safe_int(m.group(1))
        try:
            return dtime(hh, 0)
        except Exception:
            return None

    return None


def extract_phone(text: str) -> str | None:
    if not text:
        return None

    candidates = re.findall(r"\d[\d\-\(\)\s]{8,}\d", text)
    scored = []

    for c in candidates:
        d = re.sub(r"\D+", "", c)
        if not (10 <= len(d) <= 13):
            continue

        score = 0
        if len(d) == 11:
            score += 100
            if len(d) >= 3 and d[2] == "9":
                score += 20
        elif len(d) == 10:
            score += 80
        else:
            score += 10

        scored.append((score, d))

    if scored:
        scored.sort(reverse=True, key=lambda x: x[0])
        return scored[0][1]

    return None


def extract_email(text: str) -> str | None:
    if not text:
        return None
    m = _EMAIL_RE.search(text)
    if not m:
        return None
    return m.group(0)[:120]


def extract_name(text: str) -> str | None:
    if not text:
        return None

    s = " " + text.strip() + " "

    m = re.search(
        r"(?:meu\s+nome\s+e|me\s+chamo|sou)\s+(.+?)(?=(?:,|\.|;|\s*$))",
        s,
        flags=re.IGNORECASE
    )
    if not m:
        return None

    raw = m.group(1).strip()
    raw = re.split(
        r"\b(?:e\s+meu|meu\s+whats|meu\s+whatsapp|whats(?:app)?|telefone|celular|contato)\b",
        raw,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0].strip()

    raw = re.sub(r"\s+", " ", raw)
    raw = re.sub(r"[^A-Za-z\s']", "", raw).strip()

    if not raw:
        return None

    if len(raw) > 60:
        raw = raw[:60].strip()

    return " ".join([p.capitalize() for p in raw.split()])


def extract_reason_from_text(text: str) -> str | None:
    if not text:
        return None
    m = re.search(r"(?:motivo|queixa|assunto)\s*(?::|-|e)?\s+(.+)", text, flags=re.IGNORECASE)
    if not m:
        return None
    reason = m.group(1).strip()
    return reason[:500] if reason else None


def looks_like_name(text: str) -> bool:
    if not text:
        return False
    if extract_email(text) or extract_phone(text) or parse_day_from_text(text) or parse_time_from_text(text):
        return False
    if re.search(r"\d", text):
        return False
    words = re.findall(r"[A-Za-z']+", text)
    if not words or len(words) > 6:
        return False
    stop = {
        "oi", "ola", "ola", "bom", "boa", "dia", "tarde", "noite",
        "agendamento", "agendar", "consulta", "horario", "horario", "data",
        "motivo", "email", "e-mail", "telefone", "whatsapp", "contato",
        "retorno", "ajuda", "duvida", "duvida", "obrigado", "obrigada",
        "sim", "nao", "nao", "ok", "certo",
    }
    filtered = [w for w in words if _normalize(w) not in stop]
    return bool(filtered)


def extract_name_from_history(user_messages: list[str]) -> str | None:
    for txt in reversed(user_messages):
        if not looks_like_name(txt):
            continue
        words = re.findall(r"[A-Za-z']+", txt)
        if not words:
            continue
        return " ".join([p.capitalize() for p in words])[:60]
    return None


def extract_question_from_history(user_messages: list[str]) -> str | None:
    for txt in reversed(user_messages):
        normalized = (txt or "").strip()
        if not normalized or len(normalized) < 6:
            continue
        if parse_day_from_text(normalized) or parse_time_from_text(normalized) or extract_phone(normalized) or extract_email(normalized):
            continue
        if looks_like_schedule_intent(normalized):
            continue
        return normalized[:800]
    return None


def looks_like_schedule_intent(text: str) -> bool:
    s = _normalize(text)
    keywords = ["marcar", "agendar", "agendamento", "consulta", "horario", "vaga", "disponibilidade"]
    return _contains_any(s, keywords)


def _history_has_schedule_prompt(history: list[dict]) -> bool:
    prompt_words = ["data", "horario", "whatsapp", "nome", "motivo", "e-mail", "email"]
    for item in history:
        if item.get("role") != "assistant":
            continue
        content = _normalize(item.get("content", ""))
        if _contains_any(content, prompt_words):
            return True
    return False


def _prompted_for(last_assistant: str | None, keyword: str) -> bool:
    if not last_assistant:
        return False
    content = _normalize(last_assistant)
    return keyword in content


def _is_reset_command(message: str) -> str | None:
    norm = _normalize(message)
    reset_keys = [
        "reiniciar", "recomecar", "recomecar", "limpar", "novo assunto",
        "outro assunto", "nova pergunta", "nova duvida", "nova duvida",
    ]
    end_keys = ["encerrar", "finalizar", "sair", "tchau", "ate mais", "ate mais"]
    if _contains_any(norm, reset_keys):
        return "reset"
    if _contains_any(norm, end_keys):
        return "end"
    return None


def _truncate(text: str, limit: int = 600) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _apply_mail_settings(settings: Settings | None) -> None:
    if not settings:
        return
    cfg = current_app.config
    if settings.mail_server:
        cfg["MAIL_SERVER"] = settings.mail_server
    if settings.mail_port:
        cfg["MAIL_PORT"] = settings.mail_port
    if settings.mail_use_tls is not None:
        cfg["MAIL_USE_TLS"] = bool(settings.mail_use_tls)
    if settings.mail_username:
        cfg["MAIL_USERNAME"] = settings.mail_username
    if settings.mail_password:
        cfg["MAIL_PASSWORD"] = settings.mail_password
    if settings.mail_default_sender:
        cfg["MAIL_DEFAULT_SENDER"] = settings.mail_default_sender

    mail = current_app.extensions.get("mail") if current_app else None
    if not mail:
        return
    if hasattr(mail, "init_app"):
        mail.init_app(current_app)
        return
    for attr, key in (
        ("server", "MAIL_SERVER"),
        ("port", "MAIL_PORT"),
        ("use_tls", "MAIL_USE_TLS"),
        ("username", "MAIL_USERNAME"),
        ("password", "MAIL_PASSWORD"),
        ("default_sender", "MAIL_DEFAULT_SENDER"),
    ):
        if hasattr(mail, attr) and key in cfg:
            setattr(mail, attr, cfg[key])


def _resolve_notify_email(settings: Settings | None) -> str | None:
    settings = settings or Settings.query.first()
    if settings and settings.admin_notify_email:
        return settings.admin_notify_email.strip()
    env_email = (os.getenv("ADMIN_NOTIFY_EMAIL") or "").strip()
    if env_email:
        return env_email
    if settings and settings.contact_email:
        return settings.contact_email.strip()
    return None


def _send_notification_email(subject: str, body: str, settings: Settings | None) -> bool:
    mail = current_app.extensions.get("mail") if current_app else None
    if not mail:
        return False

    _apply_mail_settings(settings)
    to_email = _resolve_notify_email(settings)
    if not to_email:
        return False

    try:
        msg = Message(subject=subject, recipients=[to_email], body=body)
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.exception("Falha ao enviar e-mail: %s", e)
        return False


def _faq_reply(message: str, settings: Settings | None) -> str | None:
    if not message:
        return None

    norm = _normalize(message)

    if _contains_any(norm, ["oi", "ola", "ola", "bom dia", "boa tarde", "boa noite"]):
        return "Ola! Posso ajudar com duvidas do consultorio e agendamentos. Como posso te atender?"

    if _contains_any(norm, ["endereco", "endereco", "local", "onde fica", "como chegar"]):
        if settings and settings.address:
            return f"Endereco: {settings.address}"
        return "No momento nao tenho o endereco aqui."

    if _contains_any(norm, ["telefone", "whatsapp", "contato", "ligar", "fone"]):
        if settings and (settings.contact_phone or settings.contact_email):
            lines = []
            if settings.contact_phone:
                lines.append(f"Telefone/WhatsApp: {settings.contact_phone}")
            if settings.contact_email:
                lines.append(f"E-mail: {settings.contact_email}")
            return "\n".join(lines)
        return "No momento nao tenho contato disponivel aqui."

    if _contains_any(norm, ["email", "e-mail"]):
        if settings and settings.contact_email:
            return f"E-mail: {settings.contact_email}"
        return "No momento nao tenho o e-mail de contato aqui."

    if _contains_any(norm, ["sobre", "biografia", "quem e", "formacao", "formacao", "experiencia", "experiencia"]):
        if settings and settings.about_text:
            return _truncate(settings.about_text)
        return "No momento nao tenho essa informacao aqui."

    if _contains_any(norm, ["convenio", "convenio", "planos", "plano"]):
        items = Convenio.query.filter_by(status="active").all()
        if items:
            names = ", ".join([c.name for c in items])
            return f"Convenios: {names}."
        return "No momento nao tenho convenios cadastrados."

    if _contains_any(norm, ["curso", "cursos"]):
        courses = Course.query.filter_by(is_active=True).order_by(Course.created_at.desc()).limit(5).all()
        if courses:
            names = ", ".join([c.title for c in courses])
            return f"Cursos disponiveis: {names}."
        return "No momento nao tenho cursos ativos."

    if _contains_any(norm, ["evento", "eventos", "palestra"]):
        upcoming = Event.get_upcoming_events()
        if upcoming:
            names = ", ".join([e.title for e in upcoming[:5]])
            return f"Proximos eventos: {names}."
        return "No momento nao ha eventos programados."

    return None


@chatbot_bp.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    max_message_length = max(100, int(current_app.config.get("CHATBOT_MAX_MESSAGE_LENGTH", 500)))
    max_history_items = max(1, int(current_app.config.get("CHATBOT_MAX_HISTORY_ITEMS", 30)))
    max_session_id_length = max(16, int(current_app.config.get("CHATBOT_MAX_SESSION_ID_LENGTH", 120)))

    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"ok": False, "error": "message e obrigatorio"}), 400
    if len(message) > max_message_length:
        return jsonify({"ok": False, "error": f"message excede {max_message_length} caracteres"}), 400

    session_id = (data.get("session_id") or "").strip()[:max_session_id_length]
    history = data.get("history") or []
    if not isinstance(history, list):
        history = []

    sanitized_history = []
    for item in history:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            sanitized_history.append({"role": role, "content": content[:max_message_length]})
    sanitized_history = sanitized_history[-max_history_items:]

    user_messages = [h["content"] for h in sanitized_history if h["role"] == "user"]
    if not user_messages or user_messages[-1] != message:
        user_messages.append(message)

    last_assistant = None
    for item in reversed(sanitized_history):
        if item["role"] == "assistant":
            last_assistant = item["content"]
            break

    aggregated_user_text = "\n".join(user_messages)
    name = extract_name(aggregated_user_text) or extract_name_from_history(user_messages)
    phone = extract_phone(aggregated_user_text)
    email = extract_email(aggregated_user_text)
    parsed_day = parse_day_from_text(aggregated_user_text)
    parsed_time = parse_time_from_text(aggregated_user_text)

    prompted_name = _prompted_for(last_assistant, "nome")
    prompted_phone = _prompted_for(last_assistant, "whatsapp") or _prompted_for(last_assistant, "telefone")
    prompted_email = _prompted_for(last_assistant, "e-mail") or _prompted_for(last_assistant, "email")
    prompted_date = _prompted_for(last_assistant, "data")
    prompted_time = _prompted_for(last_assistant, "horario") or _prompted_for(last_assistant, "horario")
    prompted_reason = _prompted_for(last_assistant, "motivo")

    if prompted_name and not name and looks_like_name(message):
        name = extract_name(message) or " ".join([p.capitalize() for p in re.findall(r"[A-Za-z']+", message)]).strip()
    if prompted_phone and not phone:
        phone = extract_phone(message)
    if prompted_email and not email:
        email = extract_email(message)
    if prompted_date and not parsed_day:
        parsed_day = parse_day_from_text(message)
    if prompted_time and not parsed_time:
        parsed_time = parse_time_from_text(message)

    if prompted_reason:
        reason = message.strip()
    else:
        reason = extract_reason_from_text(message)

    reset_cmd = _is_reset_command(message)
    if reset_cmd == "reset":
        reply = "Perfeito! Vamos comecar de novo. Como posso te ajudar agora?"
        return jsonify({"ok": True, "session_id": session_id, "reply": reply, "reset_history": True}), 200
    if reset_cmd == "end":
        reply = "Atendimento encerrado. Se precisar de algo, e so chamar!"
        return jsonify({"ok": True, "session_id": session_id, "reply": reply, "reset_history": True}), 200

    settings = Settings.query.first()

    schedule_mode = looks_like_schedule_intent(aggregated_user_text) or _history_has_schedule_prompt(sanitized_history)

    if schedule_mode:
        if not parsed_day:
            reply = "Claro! Para qual data voce gostaria de agendar? (ex: 07/12 ou 2025-12-07)"
        elif not parsed_time:
            reply = "Qual horario voce prefere? (ex: 14:30)"
        elif not name:
            reply = "Perfeito. Qual e o seu nome?"
        elif not phone:
            reply = "Qual e o seu WhatsApp com DDD? (ex: 21999999999)"
        elif not email:
            reply = "Qual e o seu email para confirmacao?"
        elif not reason:
            reply = "Qual e o motivo da consulta? (ex: retorno, dor de cabeca, avaliacao)"
        else:
            try:
                appt = create_pending_appointment(
                    name=name.strip(),
                    phone=phone.strip(),
                    email=(email or "").strip() or None,
                    date_s=parsed_day.strftime("%Y-%m-%d"),
                    time_s=parsed_time.strftime("%H:%M"),
                    reason=reason,
                )
            except ValueError as e:
                reply = f"Ops! {str(e)} Pode me informar outra data ou horario?"
            else:
                body = "\n".join([
                    "Novo pedido de agendamento (Chatbot)",
                    "",
                    f"Nome: {name}",
                    f"Email: {email or 'n/d'}",
                    f"Telefone: {phone}",
                    f"Data: {parsed_day.strftime('%Y-%m-%d')}",
                    f"Horario: {parsed_time.strftime('%H:%M')}",
                    f"Motivo: {reason or 'n/d'}",
                    f"Protocolo: {appt.id}",
                ])
                email_sent = _send_notification_email("Novo pedido de agendamento (Chatbot)", body, settings)
                notice = "" if email_sent else "\n(Aviso: nao consegui enviar o email automatico.)"
                reply = (
                    "Perfeito! Registrei seu pedido de agendamento.\n\n"
                    f"Protocolo: {appt.id}\n"
                    "Nossa equipe vai checar a disponibilidade e confirmar com voce.\n\n"
                    "Se quiser tirar outra duvida, e so escrever aqui."
                    f"{notice}"
                )

        return jsonify({"ok": True, "session_id": session_id, "reply": reply}), 200
    faq_reply = _faq_reply(message, settings)
    if faq_reply:
        reply = f"{faq_reply}\n\nSe precisar de mais alguma coisa, e so me chamar."
        return jsonify({"ok": True, "session_id": session_id, "reply": reply}), 200

    pending_question = extract_question_from_history(user_messages) or message

    if not name:
        reply = "Posso encaminhar sua pergunta para a equipe. Qual e o seu nome?"
    elif not email:
        reply = "Qual e o seu e-mail para que possamos responder?"
    else:
        phone_info = f"Telefone: {phone}" if phone else "Telefone: n/d"
        contact = ContactMessage(
            name=name.strip(),
            email=email.strip(),
            subject="Pergunta via Chatbot",
            message=f"Pergunta: {pending_question}\n{phone_info}",
        )
        db.session.add(contact)
        db.session.commit()

        body = "\n".join([
            "Nova pergunta recebida via Chatbot",
            "",
            f"Nome: {name}",
            f"Email: {email}",
            phone_info,
            f"Pergunta: {pending_question}",
        ])
        email_sent = _send_notification_email("Pergunta via Chatbot", body, settings)
        notice = "" if email_sent else "\n(Aviso: nao consegui enviar o e-mail automatico.)"
        reply = (
            "Obrigado! Ja encaminhei sua pergunta para a equipe. "
            "Assim que possivel, vamos responder.\n\n"
            "Se quiser tirar outra duvida, e so escrever aqui."
            f"{notice}"
        )

    return jsonify({"ok": True, "session_id": session_id, "reply": reply}), 200
