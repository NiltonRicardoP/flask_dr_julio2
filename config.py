import os

from dotenv import load_dotenv


load_dotenv(override=False)


DEFAULT_SECRET_KEY = "dev-key-should-be-changed-in-production"
TRUTHY_VALUES = {"1", "true", "on", "yes"}


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in TRUTHY_VALUES


class Config:
    APP_ENV = (os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or "development").strip().lower()
    DEBUG = False
    TESTING = False

    SECRET_KEY = os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY)

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///dr_julio.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    WTF_CSRF_ENABLED = True
    UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), "static/uploads"))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = _env_flag("MAIL_USE_TLS", True)
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv(
        "MAIL_DEFAULT_SENDER",
        "Dr. Julio Vasconcelos <noreply@drjulio.com>",
    )

    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    HOTMART_WEBHOOK_SECRET = os.getenv("HOTMART_WEBHOOK_SECRET", "")
    HOTMART_CLIENT_ID = os.getenv("HOTMART_CLIENT_ID", "")
    HOTMART_CLIENT_SECRET = os.getenv("HOTMART_CLIENT_SECRET", "")
    HOTMART_USE_SANDBOX = _env_flag("HOTMART_USE_SANDBOX", False)

    COURSE_ACCESS_DAYS = int(os.getenv("COURSE_ACCESS_DAYS", 365))
    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")

    GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "")
    GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "")
    GOOGLE_CALENDAR_TZ = os.getenv("GOOGLE_CALENDAR_TZ", "America/Sao_Paulo")
    GOOGLE_APPT_DURATION_MINUTES = int(os.getenv("GOOGLE_APPT_DURATION_MINUTES", 50))
    GOOGLE_SYNC_MIN_INTERVAL_MIN = int(os.getenv("GOOGLE_SYNC_MIN_INTERVAL_MIN", 2))

    CHATBOT_MAX_MESSAGE_LENGTH = int(os.getenv("CHATBOT_MAX_MESSAGE_LENGTH", 500))
    CHATBOT_MAX_HISTORY_ITEMS = int(os.getenv("CHATBOT_MAX_HISTORY_ITEMS", 30))
    CHATBOT_MAX_SESSION_ID_LENGTH = int(os.getenv("CHATBOT_MAX_SESSION_ID_LENGTH", 120))

    ENABLE_DEBUG_ROUTES = _env_flag("ENABLE_DEBUG_ROUTES", False)
    HEALTHCHECK_TOKEN = os.getenv("HEALTHCHECK_TOKEN", "").strip()
    HEALTHCHECK_ALLOW_DETAILS = _env_flag("HEALTHCHECK_ALLOW_DETAILS", False)
    HEALTHCHECK_ALLOW_WRITE = _env_flag("HEALTHCHECK_ALLOW_WRITE", False)
    ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "").strip()

    @classmethod
    def init_app(cls, app):
        if not app.config.get("SECRET_KEY"):
            raise RuntimeError("SECRET_KEY is required.")


class DevelopmentConfig(Config):
    APP_ENV = "development"
    DEBUG = True
    ENABLE_DEBUG_ROUTES = _env_flag("ENABLE_DEBUG_ROUTES", True)
    HEALTHCHECK_ALLOW_DETAILS = _env_flag("HEALTHCHECK_ALLOW_DETAILS", True)


class TestingConfig(Config):
    APP_ENV = "testing"
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False
    ENABLE_DEBUG_ROUTES = True
    HEALTHCHECK_ALLOW_DETAILS = True
    HEALTHCHECK_ALLOW_WRITE = False
    MAIL_SUPPRESS_SEND = True


class ProductionConfig(Config):
    APP_ENV = "production"

    @classmethod
    def init_app(cls, app):
        super().init_app(app)
        if app.config.get("SECRET_KEY") == DEFAULT_SECRET_KEY:
            raise RuntimeError("SECRET_KEY must be configured for production.")
        if app.config.get("ENABLE_DEBUG_ROUTES"):
            raise RuntimeError("ENABLE_DEBUG_ROUTES must stay disabled in production.")


CONFIG_BY_ENV = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config_for_env(env_name: str | None = None):
    resolved_env = (env_name or os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or "development").strip().lower()
    return CONFIG_BY_ENV.get(resolved_env, DevelopmentConfig)
