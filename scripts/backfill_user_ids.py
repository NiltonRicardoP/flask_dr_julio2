"""Backfill user_id for course enrollments based on matching email addresses."""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app import app
from extensions import db
from models import CourseEnrollment, User


def backfill_user_ids():
    with app.app_context():
        enrollments = CourseEnrollment.query.filter_by(user_id=None).all()
        for enrollment in enrollments:
            user = User.query.filter_by(email=enrollment.email).first()
            if user:
                enrollment.user_id = user.id
        if enrollments:
            db.session.commit()


if __name__ == "__main__":
    backfill_user_ids()
