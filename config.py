import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-should-be-changed-in-production')
    
    # SQLAlchemy configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///dr_julio.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload folder for images
    UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static/uploads'))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload size
    
    # Email configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'Dr. Julio Vasconcelos <noreply@drjulio.com>')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
