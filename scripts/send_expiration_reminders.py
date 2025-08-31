from datetime import datetime, timedelta
from flask_mail import Message

from app import app, mail
from models import CourseEnrollment


def send_expiration_reminders():
    with app.app_context():
        now = datetime.utcnow()
        start = now + timedelta(days=7)
        end = start + timedelta(days=1)
        enrollments = CourseEnrollment.query.filter(
            CourseEnrollment.payment_status == 'paid',
            CourseEnrollment.access_end != None,  # noqa: E711
            CourseEnrollment.access_end >= start,
            CourseEnrollment.access_end < end,
        ).all()
        for e in enrollments:
            msg = Message(
                subject='Seu acesso ao curso expirará em breve',
                recipients=[e.email],
                body=(
                    f"Olá {e.name}, seu acesso ao curso {e.course.title} expira em "
                    f"{e.access_end.strftime('%d/%m/%Y')}."
                ),
            )
            mail.send(msg)


if __name__ == '__main__':
    send_expiration_reminders()
