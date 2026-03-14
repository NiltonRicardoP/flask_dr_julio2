from __future__ import annotations

import os
from datetime import datetime, timedelta

import click
from flask import current_app
from flask_mail import Message

from extensions import db
from models import Appointment, Settings


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


def _resolve_public_base_url() -> str:
    base_url = (os.getenv("PUBLIC_BASE_URL") or current_app.config.get("PUBLIC_BASE_URL") or "").strip()
    return base_url.rstrip("/")


def register_reminder_commands(app):
    @app.cli.command("send-reminders")
    @click.option("--hours", default=24, show_default=True, help="Janela de horas para enviar lembretes.")
    @click.option("--dry-run", is_flag=True, help="Somente listar, sem enviar.")
    def send_reminders(hours: int, dry_run: bool):
        settings = Settings.query.first()
        _apply_mail_settings(settings)

        mail = current_app.extensions.get("mail") if current_app else None
        if not mail:
            click.echo("Flask-Mail nao esta inicializado.")
            return

        base_url = _resolve_public_base_url()
        now = datetime.now()
        end = now + timedelta(hours=hours)

        appointments = Appointment.query.filter(
            Appointment.status.in_(["pending", "confirmed"])
        ).all()

        sent = 0
        for appt in appointments:
            if appt.reminder_sent_at:
                continue
            if not appt.email or not appt.email.strip():
                continue

            appt_dt = datetime.combine(appt.date, appt.time)
            if not (now <= appt_dt <= end):
                continue

            if not appt.manage_token:
                appt.ensure_manage_token()

            manage_url = (
                f"{base_url}/appointment/manage/{appt.manage_token}"
                if base_url and appt.manage_token
                else None
            )

            body_lines = [
                "Lembrete de consulta",
                "",
                f"Nome: {appt.name}",
                f"Data: {appt.date.strftime('%d/%m/%Y')}",
                f"Horario: {appt.time.strftime('%H:%M')}",
            ]
            if manage_url:
                body_lines.append("")
                body_lines.append(f"Gerenciar agendamento: {manage_url}")

            body = "\n".join(body_lines)

            if dry_run:
                click.echo(f"[DRY] {appt.email} - {appt.date} {appt.time}")
                continue

            try:
                msg = Message(subject="Lembrete de consulta", recipients=[appt.email], body=body)
                mail.send(msg)
                appt.reminder_sent_at = datetime.utcnow()
                sent += 1
            except Exception as exc:
                current_app.logger.exception("Falha ao enviar lembrete: %s", exc)

        if not dry_run:
            db.session.commit()

        click.echo(f"Lembretes enviados: {sent}")
