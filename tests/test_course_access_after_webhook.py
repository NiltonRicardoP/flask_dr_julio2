import json
import hmac
import hashlib

from models import Course, User, CourseEnrollment
from extensions import db


def test_webhook_payment_allows_course_access(client):
    with client.application.app_context():
        course = Course(
            title='AccessCourse',
            description='desc',
            price=50,
            is_active=True,
            access_url='http://example.com'
        )
        user = User(username='student', email='student@example.com', role='student')
        user.set_password('pass')
        db.session.add_all([course, user])
        db.session.commit()
        course_id = course.id
        user_id = user.id

    secret = 'whsec'
    client.application.config['HOTMART_WEBHOOK_SECRET'] = secret
    payload = {
        'status': 'paid',
        'id': course_id,
        'email': 'student@example.com',
        'name': 'Student',
        'amount': 50,
        'transaction_id': 'tx999'
    }
    body = json.dumps(payload).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    resp = client.post(
        '/webhook/hotmart',
        data=body,
        headers={
            'Content-Type': 'application/json',
            'X-HOTMART-HMAC-SHA256': signature,
        },
    )
    assert resp.status_code == 200

    with client.application.app_context():
        enrollment = CourseEnrollment.query.filter_by(course_id=course_id, user_id=user_id).first()
        assert enrollment is not None
        assert enrollment.access_end is not None
        enrollment_id = enrollment.id

    resp_no_login = client.get(f'/curso/acesso/{enrollment_id}')
    assert resp_no_login.status_code == 302
    assert '/aluno/login' in resp_no_login.headers['Location']

    login_resp = client.post(
        '/aluno/login',
        data={'username': 'student', 'password': 'pass'},
        follow_redirects=False,
    )
    assert login_resp.status_code == 302
    assert '/aluno/' in login_resp.headers['Location']

    access_resp = client.get(f'/curso/acesso/{enrollment_id}')
    assert access_resp.status_code == 200
    html = access_resp.get_data(as_text=True)
    assert 'AccessCourse' in html
