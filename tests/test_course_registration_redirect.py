from urllib.parse import quote
from models import Course, CourseRegistration, Settings
from extensions import db


def create_course(**kwargs):
    course = Course(**kwargs)
    db.session.add(course)
    db.session.commit()
    return course


def create_settings(**kwargs):
    settings = Settings(**kwargs)
    db.session.add(settings)
    db.session.commit()
    return settings


def test_register_course_redirects_to_whatsapp(client):
    with client.application.app_context():
        course = create_course(title='WhatsApp Course', description='d', price=1, is_active=True)
        create_settings(site_title='Test', contact_email='c@example.com', contact_phone='(11) 99999-8888')
        url = f'/courses/{course.id}/register'

    data = {'name': 'John', 'email': 'john@example.com', 'phone': '12345'}
    resp = client.post(url, data=data, follow_redirects=False)
    assert resp.status_code == 302

    whatsapp_number = '11999998888'
    msg = (
        f"Nova inscrição no curso {course.title}!\n"
        f"Nome: {data['name']}\n"
        f"Email: {data['email']}\n"
        f"Telefone: {data['phone']}"
    )
    expected_url = f"https://wa.me/{whatsapp_number}?text={quote(msg)}"
    assert resp.headers['Location'] == expected_url
