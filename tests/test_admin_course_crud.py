import pytest
from models import db, User, Course


def create_admin_user():
    admin = User(username='admin', email='admin@example.com')
    admin.set_password('admin123')
    db.session.add(admin)
    db.session.commit()
    return admin


def login(client, username='admin', password='admin123'):
    return client.post(
        '/admin/login',
        data={'username': username, 'password': password},
        follow_redirects=True,
    )


def test_admin_add_course(client):
    with client.application.app_context():
        create_admin_user()
    login(client)
    data = {
        'title': 'New Course',
        'description': 'desc',
        'price': '9.99',
        'access_url': 'http://example.com',
        'is_active': 'y',
    }
    resp = client.post('/admin/courses/add', data=data, follow_redirects=True)
    assert resp.status_code == 200
    with client.application.app_context():
        course = Course.query.filter_by(title='New Course').first()
        assert course is not None
        assert course.price == 9.99


def test_admin_edit_course(client):
    with client.application.app_context():
        create_admin_user()
        course = Course(title='Edit Me', description='d', price=1)
        db.session.add(course)
        db.session.commit()
        cid = course.id
    login(client)
    data = {
        'title': 'Edited',
        'description': 'new',
        'price': '2.5',
        'access_url': '',
        'is_active': 'y',
    }
    resp = client.post(f'/admin/courses/edit/{cid}', data=data, follow_redirects=True)
    assert resp.status_code == 200
    with client.application.app_context():
        course = Course.query.get(cid)
        assert course.title == 'Edited'
        assert course.price == 2.5


def test_admin_delete_course(client):
    with client.application.app_context():
        create_admin_user()
        course = Course(title='Delete Me', description='d', price=1)
        db.session.add(course)
        db.session.commit()
        cid = course.id
    login(client)
    resp = client.post(f'/admin/courses/delete/{cid}', follow_redirects=True)
    assert resp.status_code == 200
    with client.application.app_context():
        assert Course.query.get(cid) is None