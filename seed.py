# seed.py
from __future__ import annotations

from datetime import datetime, timedelta
import click

def register_seed_commands(app):
    @app.cli.command("seed")
    @click.option("--reset", is_flag=True, help="Apaga e recria dados básicos (Settings/Convenios/Courses).")
    def seed_cmd(reset: bool):
        """
        Popula dados mínimos para testar o sistema (admin + chat).
        Não mexe em Users nem em Appointments.
        """
        from extensions import db
        from models import Settings, Convenio, Course

        if reset:
            # Atenção: apagar apenas tabelas “conteúdo”, não dados sensíveis
            Convenio.query.delete()
            Course.query.delete()
            Settings.query.delete()
            db.session.commit()

        # -----------------------
        # Settings (1 registro)
        # -----------------------
        if Settings.query.count() == 0:
            s = Settings(
                site_title="Dr. Julio Vasconcelos",
                contact_email="contato@exemplo.com",
                contact_phone="(21) 99999-9999",
                address="Rua Exemplo, 123 - Centro, Rio de Janeiro/RJ",
                about_text="Atendimento especializado. Agende sua consulta.",
            )
            db.session.add(s)

        # -----------------------
        # Convenios
        # -----------------------
        if Convenio.query.count() == 0:
            convenios = [
                Convenio(name="Particular", details="Atendimento particular.", status="active"),
                Convenio(name="Unimed", details="Consulte cobertura e reembolso.", status="active"),
                Convenio(name="Bradesco Saúde", details="Consulte cobertura e reembolso.", status="active"),
            ]
            db.session.add_all(convenios)

        # -----------------------
        # Courses (cursos futuros)
        # -----------------------
        if Course.query.count() == 0:
            now = datetime.utcnow()
            courses = [
                Course(
                    title="Curso Introdutório - Tema X",
                    description="Conteúdo programático básico para iniciantes.",
                    price=97.0,
                    purchase_link="https://pagamento.exemplo.com/curso-x",
                    access_url="https://plataforma.exemplo.com/curso-x",
                    start_date=now + timedelta(days=7),
                    end_date=now + timedelta(days=37),
                    is_active=True,
                ),
                Course(
                    title="Curso Avançado - Tema Y",
                    description="Aprofundamento com materiais e aulas gravadas.",
                    price=197.0,
                    purchase_link="https://pagamento.exemplo.com/curso-y",
                    access_url="https://plataforma.exemplo.com/curso-y",
                    start_date=now + timedelta(days=14),
                    end_date=now + timedelta(days=60),
                    is_active=True,
                ),
            ]
            db.session.add_all(courses)

        db.session.commit()
        click.echo("Seed concluído com sucesso.")
