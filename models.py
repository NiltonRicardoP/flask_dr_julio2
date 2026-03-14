from flask_login import UserMixin
from datetime import datetime
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='student', nullable=False)
    
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
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    manage_token = db.Column(db.String(64), unique=True, index=True)
    google_event_id = db.Column(db.String(128), index=True)
    cancelled_at = db.Column(db.DateTime)
    rescheduled_at = db.Column(db.DateTime)
    reminder_sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def ensure_manage_token(self):
        if not self.manage_token:
            self.manage_token = secrets.token_urlsafe(16)
    
    def __repr__(self):
        return f'<Appointment {self.name} - {self.date} {self.time}>'


class CalendarEvent(db.Model):
    __tablename__ = "calendar_event"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    start_at = db.Column(db.DateTime, nullable=False)
    end_at = db.Column(db.DateTime, nullable=False)
    all_day = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default="active")
    source = db.Column(db.String(20), default="system")
    google_event_id = db.Column(db.String(128), unique=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CalendarEvent {self.title} - {self.start_at}>"


class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ContactMessage {self.name}>'


class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(30))
    birth_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    notes_items = db.relationship(
        'PatientNote',
        backref='patient',
        cascade='all, delete-orphan',
        order_by='PatientNote.created_at.desc()',
    )

    def __repr__(self):
        return f'<Patient {self.name}>'


class PatientNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    title = db.Column(db.String(150))
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<PatientNote {self.id}>'

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_title = db.Column(db.String(100), default='Dr. Julio Vasconcelos')
    contact_email = db.Column(db.String(100))
    contact_phone = db.Column(db.String(20))
    admin_notify_email = db.Column(db.String(120))
    mail_server = db.Column(db.String(120))
    mail_port = db.Column(db.Integer)
    mail_use_tls = db.Column(db.Boolean, default=True)
    mail_username = db.Column(db.String(120))
    mail_password = db.Column(db.String(255))
    mail_default_sender = db.Column(db.String(255))
    address = db.Column(db.Text)
    about_text = db.Column(db.Text)
    academic_background = db.Column(db.Text)
    professional_experience = db.Column(db.Text)
    social_facebook = db.Column(db.String(255))
    social_instagram = db.Column(db.String(255))
    social_youtube = db.Column(db.String(255))
    about_image = db.Column(db.String(255))
    google_calendar_id = db.Column(db.String(255))
    google_attendee_emails = db.Column(db.Text)
    google_sync_enabled = db.Column(db.Boolean, default=False)
    google_sync_token = db.Column(db.Text)
    google_sync_last_at = db.Column(db.DateTime)

    
    def __repr__(self):
        return f'<Settings {self.site_title}>'


class SiteSection(db.Model):
    __tablename__ = 'site_section'

    id = db.Column(db.Integer, primary_key=True)
    page = db.Column(db.String(50), nullable=False)
    slug = db.Column(db.String(60), unique=True, nullable=False)
    title = db.Column(db.String(150))
    subtitle = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)

    items = db.relationship(
        'SiteSectionItem',
        backref='section',
        cascade='all, delete-orphan',
        order_by='SiteSectionItem.sort_order',
    )

    def __repr__(self):
        return f'<SiteSection {self.slug}>'


class SiteSectionItem(db.Model):
    __tablename__ = 'site_section_item'

    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('site_section.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    body = db.Column(db.Text)
    icon = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<SiteSectionItem {self.title}>'


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
    purchase_link = db.Column(db.String(255))
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


class CourseEnrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transaction_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    course = db.relationship('Course', backref=db.backref('enrollments', lazy=True))
    user = db.relationship('User', backref=db.backref('enrollments', lazy=True))

    def __repr__(self):
        return f'<CourseEnrollment {self.id}>'

class Convenio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    details = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Convenio {self.name}>'
