from models import Course
from extensions import db
from datetime import datetime, timedelta


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



def test_course_page_shows_course_info(client):
    with client.application.app_context():
        course = create_course(
            title='Course',
            description='desc',
            price=10,
            is_active=True,
            purchase_link='http://example.com/buy'
        )
        url = f'/courses/{course.id}'
    resp = client.get(url)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'Course' in html
    assert 'http://example.com/buy' in html


def test_course_register_redirects_to_purchase_link(client):
    with client.application.app_context():
        course = create_course(
            title='Link Course',
            description='desc',
            price=10,
            is_active=True,
            purchase_link='http://example.com/register'
        )
        url = f'/courses/{course.id}/register'
    resp = client.get(url, follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers['Location'] == 'http://example.com/register'


def test_active_courses_order_by_start_date(client):
    """Upcoming courses should be ordered by start_date."""
    with client.application.app_context():
        now = datetime.utcnow()
        create_course(
            title='Sooner',
            description='desc',
            price=10,
            is_active=True,
            start_date=now + timedelta(days=1),
            end_date=now + timedelta(days=2),
        )
        create_course(
            title='Later',
            description='desc',
            price=10,
            is_active=True,
            start_date=now + timedelta(days=3),
            end_date=now + timedelta(days=4),
        )
    resp = client.get('/active-courses')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert html.index('Sooner') < html.index('Later')
