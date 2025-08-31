from datetime import datetime, timedelta

from models import Course, User, CourseEnrollment
from extensions import db


def test_course_access_denied_after_expiration(client):
    with client.application.app_context():
        course = Course(title='Temporal', description='desc', access_url='http://example.com')
        user = User(username='temp', email='temp@example.com', role='student')
        user.set_password('pass')
        enrollment = CourseEnrollment(
            course=course,
            user=user,
            name='Temp',
            email=user.email,
            payment_status='paid',
            access_start=datetime.utcnow() - timedelta(days=10),
            access_end=datetime.utcnow() - timedelta(days=1),
        )
        db.session.add_all([course, user, enrollment])
        db.session.commit()
        enrollment_id = enrollment.id

    client.post('/aluno/login', data={'username': 'temp', 'password': 'pass'})
    resp = client.get(f'/curso/acesso/{enrollment_id}')
    assert resp.status_code == 302
    assert '/aluno/' in resp.headers['Location']
