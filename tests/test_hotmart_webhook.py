import json
import hmac
import hashlib

from models import Course, User, CourseEnrollment, PaymentTransaction
from extensions import db


def create_course(**kwargs):
    course = Course(**kwargs)
    db.session.add(course)
    db.session.commit()
    return course


def test_hotmart_webhook_creates_enrollment(client):
    with client.application.app_context():
        course = create_course(title='Webhook Course', description='desc', price=100, is_active=True)
        course_id = course.id

    secret = 'whsec'
    client.application.config['HOTMART_WEBHOOK_SECRET'] = secret
    payload = {
        'status': 'approved',
        'id': course_id,
        'email': 'hook@example.com',
        'name': 'Hook User',
        'amount': 100,
        'transaction_id': 'tx123'
    }
    body = json.dumps(payload).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    resp = client.post('/webhook/hotmart', data=body, headers={
        'Content-Type': 'application/json',
        'X-HOTMART-HMAC-SHA256': signature,
    })
    assert resp.status_code == 200

    with client.application.app_context():
        user = User.query.filter_by(email='hook@example.com').first()
        assert user is not None
        enrollment = CourseEnrollment.query.filter_by(course_id=course_id, email='hook@example.com').first()
        assert enrollment is not None
        assert enrollment.payment_status == 'approved'
        txn = PaymentTransaction.query.filter_by(enrollment_id=enrollment.id).first()
        assert txn is not None
        assert txn.amount == 100
        assert txn.provider_id == 'tx123'
