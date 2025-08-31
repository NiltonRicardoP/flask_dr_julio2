import json
import hmac
import hashlib
from unittest.mock import patch

import pytest

from models import Course, User, CourseEnrollment, PaymentTransaction
from extensions import db


def create_course(**kwargs):
    course = Course(**kwargs)
    db.session.add(course)
    db.session.commit()
    return course


@pytest.mark.parametrize(
    'webhook_status,expected_status',
    [
        ('approved', 'paid'),
        ('refunded', 'refunded'),
        ('canceled', 'canceled'),
    ],
)
def test_hotmart_webhook_creates_enrollment(client, webhook_status, expected_status):
    with client.application.app_context():
        course = create_course(title='Webhook Course', description='desc', price=100, is_active=True)
        course_id = course.id
        login_path = '/aluno/login'

    secret = 'whsec'
    client.application.config['HOTMART_WEBHOOK_SECRET'] = secret
    email = f'hook-{webhook_status}@example.com'
    payload = {
        'status': webhook_status,
        'id': course_id,
        'email': email,
        'name': 'Hook User',
        'amount': 100,
        'transaction_id': 'tx123',
    }
    body = json.dumps(payload).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    sent_messages = []

    with client.application.app_context():
        mail_ext = client.application.extensions['mail']

    def fake_send(message):
        sent_messages.append(message)

    with patch('routes.secrets.token_urlsafe', return_value='temp-pass'):
        with patch.object(mail_ext, 'send', side_effect=fake_send):
            resp = client.post(
                '/webhook/hotmart',
                data=body,
                headers={
                    'Content-Type': 'application/json',
                    'X-HOTMART-HMAC-SHA256': signature,
                },
            )

    assert resp.status_code == 200
    assert len(sent_messages) == 1
    msg_body = sent_messages[0].body
    assert login_path in msg_body
    assert 'temp-pass' in msg_body
    assert 'Altere sua senha' in msg_body

    with client.application.app_context():
        user = User.query.filter_by(email=email).first()
        assert user is not None
        assert user.check_password('temp-pass')
        enrollment = CourseEnrollment.query.filter_by(course_id=course_id, email=email).first()
        assert enrollment is not None
        assert enrollment.payment_status == expected_status
        txn = PaymentTransaction.query.filter_by(enrollment_id=enrollment.id).first()
        assert txn is not None
        assert txn.amount == 100
        assert txn.provider_id == 'tx123'
        assert txn.status == expected_status
