from flask import current_app
from flask_login import UserMixin
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='student')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def __repr__(self):
        return f'<User {self.username}>'

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(255))
    image = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def is_past(self):
        return datetime.utcnow() > self.end_date
    
    @classmethod
    def get_upcoming_events(cls):
        return cls.query.filter(
            cls.start_date >= datetime.utcnow(),
            cls.is_active == True
        ).order_by(cls.start_date).all()
    
    @classmethod
    def get_past_events(cls):
        return cls.query.filter(
            cls.end_date < datetime.utcnow(),
            cls.is_active == True
        ).order_by(cls.start_date.desc()).all()

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Appointment {self.name} - {self.date} {self.time}>'


class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ContactMessage {self.name}>'

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_title = db.Column(db.String(100), default='Dr. Julio Vasconcelos')
    contact_email = db.Column(db.String(100))
    contact_phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    about_text = db.Column(db.Text)
    academic_background = db.Column(db.Text)
    professional_experience = db.Column(db.Text)
    social_facebook = db.Column(db.String(255))
    social_instagram = db.Column(db.String(255))
    social_youtube = db.Column(db.String(255))
    about_image = db.Column(db.String(255))

    
    def __repr__(self):
        return f'<Settings {self.site_title}>'


class GalleryItem(db.Model):
    __tablename__ = 'gallery_item'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=True)
    description = db.Column(db.Text, nullable=True)
    media_type = db.Column(db.String(10), nullable=False)  # "image" ou "video"
    filename = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(255), nullable=True)
    categoria = db.Column(db.String(50), nullable=False, default='eventos')  # campo de categoria adicionado corretamente
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class BillingRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<BillingRecord {self.patient_name} - {self.amount}>'


class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(50), unique=True, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Invoice {self.number}>'


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    image = db.Column(db.String(255))
    price = db.Column(db.Float, default=0.0)
    access_url = db.Column(db.String(255))
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Course {self.title}>'

    @classmethod
    def get_upcoming_courses(cls):
        """Return active courses starting today or later."""
        return (
            cls.query.filter(
                cls.is_active == True,
                cls.start_date >= datetime.utcnow(),
            )
            .order_by(cls.start_date)
            .all()
        )

    @classmethod
    def get_past_courses(cls):
        """Return active courses that have ended."""
        return (
            cls.query.filter(
                cls.is_active == True,
                cls.end_date < datetime.utcnow(),
            )
            .order_by(cls.start_date.desc())
            .all()
        )


class CourseEnrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    payment_status = db.Column(db.String(20), default='pending')
    transaction_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    access_start = db.Column(db.DateTime)
    access_end = db.Column(db.DateTime)

    course = db.relationship('Course', backref=db.backref('enrollments', lazy=True))
    user = db.relationship('User', backref=db.backref('course_enrollments', lazy=True))

    def activate_access(self, days=None):
        """Start access period for this enrollment."""
        now = datetime.utcnow()
        duration = days or current_app.config.get('COURSE_ACCESS_DAYS', 365)
        self.access_start = now
        self.access_end = now + timedelta(days=duration)


class PaymentTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey('course_enrollment.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    provider_id = db.Column(db.String(100))
    status = db.Column(db.String(20), default='paid')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    enrollment = db.relationship('CourseEnrollment', backref=db.backref('transactions', lazy=True))

    def __repr__(self):
        return f'<PaymentTransaction {self.id}>'


class CoursePurchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    stripe_session_id = db.Column(db.String(255))
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    course = db.relationship('Course', backref=db.backref('purchases', lazy=True))

    def __repr__(self):
        return f'<CoursePurchase {self.id}>'


class CourseRegistration(db.Model):
    """Registro público de interesse em cursos."""
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    participant_name = db.Column(db.String(100), nullable=False)
    participant_email = db.Column(db.String(100), nullable=False)
    payment_status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    course = db.relationship('Course', backref=db.backref('registrations', lazy=True))

    def __repr__(self):
        return f'<CourseRegistration {self.id}>'


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.Integer, db.ForeignKey('course_registration.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    provider = db.Column(db.String(50))
    status = db.Column(db.String(20), default='pending')
    transaction_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    registration = db.relationship('CourseRegistration', backref=db.backref('payments', lazy=True))

    def __repr__(self):
        return f'<Payment {self.id}>'


class Convenio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    details = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Convenio {self.name}>'
