from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    
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
    categoria = db.Column(db.String(50), nullable=False, default='eventos')  # ✅ campo de categoria adicionado corretamente
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
