from flask import url_for
from models import Course, CourseEnrollment
from extensions import db


def create_course(**kwargs):
    course = Course(**kwargs)
    db.session.add(course)
    db.session.commit()
    return course


def test_courses_shows_active_courses(client):
    with client.application.app_context():
        active = create_course(title='Active', description='desc', price=10, is_active=True)
        inactive = create_course(title='Inactive', description='desc', price=10, is_active=False)
    resp = client.get('/cursos')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'Active' in html
    assert 'Inactive' not in html


def test_courses_route_english_alias(client):
    """Ensure /courses returns the course list."""
    with client.application.app_context():
        create_course(title='Active EN', description='desc', price=10, is_active=True)
    resp = client.get('/courses')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'Active EN' in html


def test_course_detail_post_creates_enrollment(client):
    with client.application.app_context():
        course = create_course(title='Course', description='desc', price=10, is_active=True)
        url = f'/cursos/{course.id}'
    data = {'name': 'Test User', 'email': 'test@example.com', 'phone': '12345678'}
    resp = client.post(url, data=data, follow_redirects=False)
    assert resp.status_code == 302
    with client.application.app_context():
        enrollment = CourseEnrollment.query.first()
        assert enrollment is not None
        assert enrollment.name == 'Test User'
        assert enrollment.email == 'test@example.com'
        assert enrollment.course_id == course.id
        assert resp.headers['Location'].endswith(f'/pagamento/{enrollment.id}')
