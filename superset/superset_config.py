import os

# Security
SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "change_me_in_production")

# Metadata Database (PostgreSQL)
SQLALCHEMY_DATABASE_URI = os.environ.get("SUPERSET_DB_URI", "postgresql://postgres:postgres@postgres:5432/superset_metadata")

# Security & CSRF
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = None  # Forever for local dev dashboards
SESSION_COOKIE_SAMESITE = "Lax"

# Talisman security (disable for local dev, but keep config)
TALISMAN_ENABLED = False

# Allow embedding and CORS
ENABLE_CORS = True

# Performance - Row limits
ROW_LIMIT = 50000

# Language
BABEL_DEFAULT_LOCALE = "en"
BABEL_DEFAULT_FOLDER = "superset/translations"
LANGUAGES = {
    "en": {"flag": "us", "name": "English"},
    "ar": {"flag": "eg", "name": "Arabic"},
}
