from datetime import datetime, timedelta

from extensions import db
from models import Course, Event, Settings, SiteSection, SiteSectionItem


def test_public_text_blocks_strip_markup_and_preserve_line_breaks(client):
    with client.application.app_context():
        db.session.add(Settings(site_title="Teste"))

        hero = SiteSection(page="index", slug="index-hero", title="Titulo<script>alert(1)</script>\nLinha 2")
        about = SiteSection(page="index", slug="index-about", title="Sobre")
        about.items.append(
            SiteSectionItem(
                title="Resumo",
                body="Primeira linha\n<img src=x onerror=alert(2)>Segunda linha",
            )
        )

        db.session.add_all([hero, about])
        db.session.commit()

    resp = client.get("/")
    html = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert "alert(1)" not in html
    assert "onerror=alert(2)" not in html
    assert "Titulo<br" in html
    assert "Primeira linha<br" in html
    assert "Segunda linha" in html


def test_about_page_sanitizes_rich_text_but_keeps_safe_markup(client):
    with client.application.app_context():
        db.session.add(
            Settings(
                site_title="Teste",
                academic_background="<ul><li>Formacao segura</li></ul><script>alert(1)</script>",
                professional_experience="<p><strong>Experiencia valida</strong></p>",
            )
        )
        db.session.commit()

    resp = client.get("/about")
    html = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert "<li>Formacao segura</li>" in html
    assert "<strong>Experiencia valida</strong>" in html
    assert "alert(1)" not in html


def test_course_detail_removes_script_urls_and_script_blocks(client):
    with client.application.app_context():
        course = Course(
            title="Curso Seguro",
            description="<p><strong>Conteudo seguro</strong></p><script>alert(1)</script><a href=\"javascript:alert(2)\">Clique</a>",
            price=10,
            is_active=True,
        )
        db.session.add(course)
        db.session.commit()
        course_id = course.id

    resp = client.get(f"/courses/{course_id}")
    html = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert "<strong>Conteudo seguro</strong>" in html
    assert "javascript:alert(2)" not in html
    assert "alert(1)" not in html


def test_events_page_sanitizes_public_description_and_sets_security_headers(client):
    with client.application.app_context():
        now = datetime.utcnow()
        event = Event(
            title="Evento Seguro",
            description="<p>Descricao</p><iframe src=\"https://evil.example\"></iframe><script>alert(3)</script>",
            start_date=now + timedelta(days=1),
            end_date=now + timedelta(days=1, hours=2),
            location="Online",
            is_active=True,
        )
        db.session.add(event)
        db.session.commit()

    resp = client.get("/events")
    html = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert "<p>Descricao</p>" in html
    assert "alert(3)" not in html
    assert "evil.example" not in html
    assert "default-src 'self'" in resp.headers["Content-Security-Policy"]
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
