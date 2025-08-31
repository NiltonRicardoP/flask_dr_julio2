from models import Course
from extensions import db
from datetime import datetime


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
        course = create_course(title='Course', description='desc', price=10, is_active=True)
        url = f'/courses/{course.id}'
    resp = client.get(url)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'Course' in html


def test_courses_order_by_created_at_without_start_date(client):
    """Courses should be ordered by created_at when no start_date attribute exists."""
    with client.application.app_context():
        create_course(
            title='First',
            description='desc',
            price=10,
            is_active=True,
            created_at=datetime(2023, 1, 1),
        )
        create_course(
            title='Second',
            description='desc',
            price=10,
            is_active=True,
            created_at=datetime(2023, 1, 2),
        )
    resp = client.get('/courses')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert html.index('First') < html.index('Second')


def test_courses_order_by_created_at_with_start_date_attr(client, monkeypatch):
    """Even if Course.start_date exists, ordering should use created_at."""
    monkeypatch.setattr(Course, 'start_date', None, raising=False)
    with client.application.app_context():
        create_course(
            title='Early',
            description='desc',
            price=10,
            is_active=True,
            created_at=datetime(2023, 1, 1),
        )
        create_course(
            title='Late',
            description='desc',
            price=10,
            is_active=True,
            created_at=datetime(2023, 1, 2),
        )
    resp = client.get('/courses')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert html.index('Early') < html.index('Late')
