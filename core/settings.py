import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

# Load environment variables
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,.onrender.com').split(',')

# ===== GLITCHTIP CONFIGURATION =====
# Configure GlitchTip for error monitoring using Sentry SDK
GLITCHTIP_DSN = os.getenv('GLITCHTIP_DSN', 'https://1455826932ce426c8f44b6a0df2637f4@app.glitchtip.com/12017')

if GLITCHTIP_DSN:
    sentry_sdk.init(
        dsn="https://1455826932ce426c8f44b6a0df2637f4@app.glitchtip.com/12017",
        integrations=[DjangoIntegration()],
        auto_session_tracking=False,
        traces_sample_rate=0.01,
        release=os.getenv('APP_VERSION', '1.0.0'),
        environment='development' if DEBUG else 'production',
    )
# Configure SSL for production
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',  # For sitemap generation
    'django.contrib.sites',     # Required for sitemaps
    'django.contrib.humanize',  # For human-friendly data formatting
    
    # Third-party
    'django_htmx',
    'crispy_forms',
    'crispy_tailwind',
    'robots',                   # For robots.txt management
    'meta',                     # For meta tags management
    
    # Django REST Framework
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    
    # Production Security Apps
    'axes',
    'defender',
    'encrypted_model_fields',
    # 'django_ratelimit',  # Temporarily disabled due to cache backend incompatibility
    
    # Local
    'accounts.apps.AccountsConfig',
    'banking.apps.BankingConfig',
    'dashboard.apps.DashboardConfig',
    'pages.apps.PagesConfig',
    'api.apps.ApiConfig',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Added for static files in production
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    
    # Security Middleware
    'axes.middleware.AxesMiddleware',
    'defender.middleware.FailedLoginMiddleware',
    'accounts.audit_logging.AuditMiddleware',
    
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]

# GlitchTip uses Sentry SDK which automatically handles middleware through DjangoIntegration
# No need to manually add middleware

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 20,  # in seconds
            'isolation_level': None,  # autocommit mode
        },
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # Increased minimum length
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Use WhiteNoise for static files in production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Database Configuration
if DEBUG:
    # Development: Use PostgreSQL (hardcoded for now)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'primetrust_db',
            'USER': 'postgres',
            'PASSWORD': 'derry221',
            'HOST': 'localhost',
            'PORT': '5433',
            'OPTIONS': {
                'options': '-c default_transaction_isolation=serializable'
            },
        }
    }
else:
    # Production: Use DATABASE_URL from environment
    try:
        import dj_database_url
        DATABASES = {
            'default': dj_database_url.config(
                conn_max_age=600,
                conn_health_checks=True,
            )
        }
        if not DATABASES['default']:
            raise ValueError("DATABASE_URL environment variable is required in production")
    except ImportError:
        raise ImportError("dj_database_url is required for production deployment")

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'accounts.CustomUser'

# Login/Logout
LOGIN_REDIRECT_URL = 'dashboard:home'
LOGOUT_REDIRECT_URL = 'accounts:login'
LOGIN_URL = 'accounts:login'

# Security settings for production
if not DEBUG:
    # HTTPS settings
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Content security policy
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'

# CSRF trusted origins: split only non-empty values and require scheme
origins = os.getenv('CSRF_TRUSTED_ORIGINS', '')
CSRF_TRUSTED_ORIGINS = [o for o in origins.split(',') if o.startswith('http')]

# Email Configuration - Gmail API for Both Development and Production
EMAIL_BACKEND = 'core.gmail_backend.GmailBackend'  # Always use Gmail API
DEFAULT_FROM_EMAIL = os.getenv('GMAIL_SENDER_EMAIL', 'primetrustbank02@gmail.com')

# Gmail API Configuration
GMAIL_OAUTH_CREDENTIALS_FILE = os.getenv('GMAIL_OAUTH_CREDENTIALS_FILE', 'credentials/gmail-oauth-credentials.json')
GMAIL_TOKEN_FILE = os.getenv('GMAIL_TOKEN_FILE', 'credentials/gmail-token.json')
GMAIL_SENDER_EMAIL = os.getenv('GMAIL_SENDER_EMAIL', 'primetrustbank02@gmail.com')
GMAIL_SUBJECT_PREFIX = os.getenv('GMAIL_SUBJECT_PREFIX', 'PrimeTrust - ')

# Email timeout settings
EMAIL_TIMEOUT = 30

# Verification settings
EMAIL_VERIFICATION_TIMEOUT = 3600  # 1 hour in seconds
LOGIN_VERIFICATION_TIMEOUT = 300   # 5 minutes in seconds

# News API key for real-time news
NEWS_API_KEY = os.getenv('NEWS_API_KEY', '')

# Site ID for django.contrib.sites
SITE_ID = 1

# SEO Settings
META_SITE_PROTOCOL = 'https' if not DEBUG else 'http'
META_SITE_DOMAIN = os.getenv('META_SITE_DOMAIN', 'primetrust.yourdomain.com')
META_SITE_NAME = 'PrimeTrust'
META_SITE_TYPE = 'website'
META_INCLUDE_KEYWORDS = ['banking', 'online banking', 'secure banking', 'digital banking', 'financial services']
META_DEFAULT_KEYWORDS = ['PrimeTrust', 'banking', 'secure banking', 'online banking']
META_DESCRIPTION_LENGTH = 300
META_USE_OG_PROPERTIES = True
META_USE_TWITTER_PROPERTIES = True
META_USE_SCHEMAORG_PROPERTIES = True
META_USE_TITLE_TAG = True
META_DEFAULT_IMAGE = 'img/primetrust-logo.png'

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'security': {
            'format': '{asctime} {levelname} SECURITY: {message}',
            'style': '{',
        },
        'production': {
            'format': '{asctime} [{levelname}] {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/django.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'production' if not DEBUG else 'verbose',
        },
        'security_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/security.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'security',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/errors.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'production',
        },
        'console': {
            'level': 'DEBUG' if DEBUG else 'WARNING',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose' if DEBUG else 'production',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'] if DEBUG else ['file', 'error_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'security': {
            'handlers': ['security_file', 'console'] if DEBUG else ['security_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'accounts.security': {
            'handlers': ['security_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'banking': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'api': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'sentry_sdk': {
            'handlers': ['error_file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwindcss"
CRISPY_TEMPLATE_PACK = "tailwindcss"

# Session settings
SESSION_COOKIE_AGE = int(os.getenv('SESSION_COOKIE_AGE', '3600'))  # 1 hour default
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = os.getenv('SESSION_EXPIRE_AT_BROWSER_CLOSE', 'True') == 'True'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Security settings (only in production)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
    SECURE_REFERRER_POLICY = 'same-origin'
    
    # Additional production security headers
    SECURE_CONTENT_SECURITY_POLICY = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"

# Bank SWIFT code for wire transfers (Fictional for PrimeTrust)
BANK_SWIFT_CODE = 'PTRTUS33XXX'

# ===== DJANGO REST FRAMEWORK CONFIGURATION =====

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# JWT settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,
    
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',
    
    'JTI_CLAIM': 'jti',
    
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Add environment-specific CORS origins
if not DEBUG:
    cors_origins = os.getenv('CORS_ALLOWED_ORIGINS', '')
    if cors_origins:
        CORS_ALLOWED_ORIGINS.extend(cors_origins.split(','))

CORS_ALLOW_CREDENTIALS = True

# API Documentation settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'PrimeTrust Banking API',
    'DESCRIPTION': 'RESTful API for PrimeTrust Banking Platform',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': '/api/v1/',
    'COMPONENT_SPLIT_REQUEST': True,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
    },
    'AUTHENTICATION_WHITELIST': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}

# API Rate Limiting
API_RATE_LIMIT_ENABLED = True
API_RATE_LIMIT_PER_MINUTE = 60
API_RATE_LIMIT_BURST = 10

# API Version
API_VERSION = 'v1'

# Security settings for API
if not DEBUG:
    SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
    SECURE_REFERRER_POLICY = 'same-origin'

# Production Security Configuration
FIELD_ENCRYPTION_KEY = os.environ.get('FIELD_ENCRYPTION_KEY', 'UzWtJN5K4jU9Wz-rGx8vQ2nM7yB3kR1pE6fX0dL4aP8=')

# Authentication Backends
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',  # AxesStandaloneBackend should be first
    'django.contrib.auth.backends.ModelBackend',
]

# Django Axes Configuration (Brute Force Protection)
AXES_ENABLED = True
AXES_FAILURE_LIMIT = 5  # Number of failed attempts before lockout
AXES_COOLOFF_TIME = 1  # Hours to lockout
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = 'accounts/lockout.html'

# Django Defender Configuration
DEFENDER_LOGIN_FAILURE_LIMIT = 3
DEFENDER_COOLOFF_TIME = 300  # 5 minutes
DEFENDER_LOCKOUT_TEMPLATE = 'accounts/lockout.html'

# Rate Limiting Configuration (using custom implementation instead of django_ratelimit)
# RATELIMIT_ENABLE = True
# RATELIMIT_USE_CACHE = 'default'

# Cache Configuration for Security (Using database backend for atomic operations)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache_table',
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    },
    'security': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_security_cache_table',
        'TIMEOUT': 600,
        'OPTIONS': {
            'MAX_ENTRIES': 500,
        }
    }
}

# GeoIP Configuration (for geographic security)
GEOIP_PATH = os.path.join(BASE_DIR, 'geoip')

# API Rate Limiting per user
API_RATE_LIMITS = {
    'default': '100/hour',
    'login': '10/hour',
    'password_reset': '5/hour',
    'transaction': '50/hour',
    'high_value_transaction': '10/hour',
}