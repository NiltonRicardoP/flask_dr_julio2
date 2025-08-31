from models import Course, User, CourseEnrollment
from extensions import db


def test_pay_course_rejects_other_users(client):
    with client.application.app_context():
        course = Course(title='Secure', description='desc', price=100)
        owner = User(username='owner', email='owner@example.com', role='student')
        owner.set_password('pass1')
        intruder = User(username='intruder', email='intruder@example.com', role='student')
        intruder.set_password('pass2')
        enrollment = CourseEnrollment(
            course=course,
            user=owner,
            name='Owner',
            email=owner.email,
            payment_status='pending',
        )
        db.session.add_all([course, owner, intruder, enrollment])
        db.session.commit()
        enrollment_id = enrollment.id

    client.post('/aluno/login', data={'username': 'intruder', 'password': 'pass2'})
    resp = client.get(f'/pagamento/{enrollment_id}')
    assert resp.status_code == 403
