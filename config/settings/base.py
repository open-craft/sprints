"""
Base settings to build other settings files upon.
"""
import datetime
import json

import environ
from celery.schedules import crontab

SECONDS_IN_HOUR = 3600
SECONDS_IN_MINUTE = 60
HOURS_IN_DAY = 24

ROOT_DIR = (
    environ.Path(__file__) - 3
)  # (sprints/config/settings/base.py - 3 = sprints/)
APPS_DIR = ROOT_DIR.path("sprints")

env = environ.Env()

READ_DOT_ENV_FILE = env.bool("DJANGO_READ_DOT_ENV_FILE", default=False)
if READ_DOT_ENV_FILE:
    # OS environment variables take precedence over variables from .env
    env.read_env(str(ROOT_DIR.path(".env")))

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool("DJANGO_DEBUG", False)
# Local time zone. Choices are
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# though not all of them may be available with every OS.
# In Windows, this must be set to your system time zone.
TIME_ZONE = "UTC"
# https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = "en-us"
# https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1
# https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
# https://docs.djangoproject.com/en/dev/ref/settings/#locale-paths
LOCALE_PATHS = [ROOT_DIR.path("locale")]

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ATOMIC_REQUESTS"] = True

# URLS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = "config.urls"
# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "config.wsgi.application"

# APPS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # "django.contrib.humanize", # Handy template tags
    "django.contrib.admin",
]
THIRD_PARTY_APPS = [
    "crispy_forms",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    'allauth.socialaccount.providers.google',
    "rest_framework",
    "rest_framework.authtoken",
    "rest_auth",
    "rest_auth.registration",
    "drf_yasg",
    "corsheaders",
    'rest_framework_simplejwt.token_blacklist',
]
LOCAL_APPS = [
    "sprints.users.apps.UsersConfig",
    "sprints.dashboard.apps.DashboardConfig",
    "sprints.sustainability.apps.SustainabilityConfig",
    # Your stuff: custom apps go here
]
# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # Mimicing memcache behavior.
            # http://niwinz.github.io/django-redis/latest/#_memcached_exceptions_behavior
            "IGNORE_EXCEPTIONS": True,
        },
    }
}

# MIGRATIONS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#migration-modules
MIGRATION_MODULES = {"sites": "sprints.contrib.sites.migrations"}

# AUTHENTICATION
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-user-model
AUTH_USER_MODEL = "users.User"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
LOGIN_REDIRECT_URL = "users:redirect"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-url
LOGIN_URL = "account_login"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = [
    # https://docs.djangoproject.com/en/dev/topics/auth/passwords/#using-argon2-with-django
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# MIDDLEWARE
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#middleware
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# STATIC
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(ROOT_DIR("staticfiles"))
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = "/static/"
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [str(APPS_DIR.path("static"))]
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = str(APPS_DIR("media"))
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "/media/"

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        # https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
        "DIRS": [str(APPS_DIR.path("templates"))],
        "OPTIONS": {
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
            "debug": DEBUG,
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-loaders
            # https://docs.djangoproject.com/en/dev/ref/templates/api/#loader-types
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]
# http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
CRISPY_TEMPLATE_PACK = "bootstrap4"

# FIXTURES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#fixture-dirs
FIXTURE_DIRS = (str(APPS_DIR.path("fixtures")),)

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-httponly
SESSION_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-httponly
CSRF_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-browser-xss-filter
SECURE_BROWSER_XSS_FILTER = True
# https://docs.djangoproject.com/en/dev/ref/settings/#x-frame-options
X_FRAME_OPTIONS = "DENY"

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
)
# https://docs.djangoproject.com/en/dev/ref/settings/#default-from-email
DEFAULT_FROM_EMAIL = env(
    "DJANGO_DEFAULT_FROM_EMAIL", default="Sprints <noreply@sprints.opencraft.com>"
)

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL.
ADMIN_URL = "admin/"
# https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = [("""OpenCraft""", "ops@opencraft.com")]
# https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS

# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s "
                      "%(process)d %(thread)d %(message)s"
        }
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}

# Celery
# ------------------------------------------------------------------------------
if USE_TZ:
    # http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-timezone
    CELERY_TIMEZONE = TIME_ZONE
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-broker_url
CELERY_BROKER_URL = env("CELERY_BROKER_URL")
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-result_backend
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-accept_content
CELERY_ACCEPT_CONTENT = ["json"]
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-task_serializer
CELERY_TASK_SERIALIZER = "json"
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-result_serializer
CELERY_RESULT_SERIALIZER = "json"
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-time-limit
# TODO: set to whatever value is adequate in your circumstances
CELERYD_TASK_TIME_LIMIT = SECONDS_IN_MINUTE * 30
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-soft-time-limit
# TODO: set to whatever value is adequate in your circumstances
CELERYD_TASK_SOFT_TIME_LIMIT = CELERYD_TASK_TIME_LIMIT

CELERY_BEAT_SCHEDULE = {
    "Validate long-term cache integrity every 15 minutes.": {
        "task": "sprints.sustainability.tasks.validate_worklog_cache",
        "schedule": crontab(minute='*/15'),
        "kwargs": {
            "long_term": True,
            "force_regenerate": False,
        },
    },
    "Recreate long-term cache once per week.": {
        "task": "sprints.sustainability.tasks.validate_worklog_cache",
        "schedule": crontab(
            minute=0,
            hour=0,
            day_of_week='sun',
        ),
        "kwargs": {
            "long_term": True,
            "force_regenerate": True,
        },
    },
    "Send budget email alerts once per week.": {
        "task": "sprints.sustainability.tasks.send_email_alerts",
        "schedule": crontab(
            minute=0,
            hour=16,
            day_of_week='sun',
        ),
    },
}

# django-allauth
# ------------------------------------------------------------------------------
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_ADAPTER = "sprints.users.adapters.AccountAdapter"
SOCIALACCOUNT_ADAPTER = "sprints.users.adapters.SocialAccountAdapter"
SOCIALACCOUNT_EMAIL_VERIFICATION = False
# Custom options for disabling login/registration.
ACCOUNT_ALLOW_LOGIN = env.bool("DJANGO_ACCOUNT_ALLOW_LOGIN", True)
ACCOUNT_ALLOW_REGISTRATION = env.bool("DJANGO_ACCOUNT_ALLOW_REGISTRATION", True)
SOCIALACCOUNT_ALLOW_REGISTRATION = env.bool("DJANGO_SOCIALACCOUNT_ALLOW_REGISTRATION", True)
ACCOUNT_ALLOWED_EMAIL_DOMAINS = env.list("DJANGO_ACCOUNT_ALLOWED_EMAIL_DOMAINS", default=["opencraft.com"])

# DRF
# ------------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ),
}
REST_USE_JWT = True
REST_AUTH_SERIALIZERS = {
    'USER_DETAILS_SERIALIZER': 'sprints.users.serializers.UserDetailsSerializer',
}
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': datetime.timedelta(hours=env.float("JWT_ACCESS_TOKEN_LIFETIME_HOURS", 3)),
    'REFRESH_TOKEN_LIFETIME': datetime.timedelta(days=env.float("JWT_REFRESH_TOKEN_LIFETIME_DAYS", 30)),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}


# REACT FRONTEND
# ------------------------------------------------------------------------------
# URL to the react frontend.
FRONTEND_URL = env.str("FRONTEND_URL", "http://localhost:3000")
CORS_ORIGIN_WHITELIST = (
    FRONTEND_URL,
)

# JIRA
# ------------------------------------------------------------------------------
# URL of the Jira server.
JIRA_SERVER = env.str("JIRA_SERVER")
# Username of the user used for accessing Jira API.
JIRA_USERNAME = env.str("JIRA_USERNAME")
# Password of the user used for accessing Jira API.
JIRA_PASSWORD = env.str("JIRA_PASSWORD")
# THe prefix used for distinguishing sprint boards from other ones.
JIRA_SPRINT_BOARD_PREFIX = env.str("SPRINT_BOARD_PREFIX", "Sprint - ")
# Username of a helper Jira bot used for indicating custom review time requirements.
JIRA_BOT_USERNAME = env.str("JIRA_BOT_USERNAME", "crafty")
# Date format used by the Jira API.
JIRA_API_DATE_FORMAT = env.str("JIRA_API_DATE_FORMAT", "%Y-%m-%d")
JIRA_REQUIRED_FIELDS = (
    "Assignee",
    "Summary",
    "Description",
    "Issue Type",
    "Status",
    "Time Spent",
    "Remaining Estimate",
    "Sprint",
    "Story Points",
    "Reviewer 1",
    "Account",
    "Epic Link",
    "Flagged",
)
# Fields required for documenting spillovers.
SPILLOVER_REQUIRED_FIELDS = (
    "Status",
    "Sprint",
    "Assignee",
    "Reviewer 1",
    "Reviewer 2",
    "Reporter",
    "Story Points",
    "Original Estimate",
    "Remaining Estimate",
    "Comment",
)
# Issue fields that contain time in seconds.
JIRA_TIME_FIELDS = {
    "Time Spent",
    "Original Estimate",
    "Remaining Estimate",
}
# Issue fields with numeric values.
JIRA_INTEGER_FIELDS = {
    "Story Points",
} | JIRA_TIME_FIELDS
# A pattern for getting board's quickfilters to retrieve the cell's members without admin permissions.
JIRA_BOARD_QUICKFILTER_PATTERN = env.str("JIRA_BOARD_QUICKFILTER_PATTERN", r"assignee = ([\w-]+).* or .*\1.*\1")
# Jira default account for assigning cell-role-related tickets.
JIRA_CELL_ROLE_ACCOUNT = env.str("JIRA_CELL_ROLE_ACCOUNT")
# Jira epic name for cell-role tickets.
JIRA_CELL_ROLE_EPIC_NAME = env.str("JIRA_CELL_ROLE_EPIC_NAME", "Firefighting")
# Jira cell roles in the following format:
# {
#   ROLE1: [
#       {
#           name: subrole1,
#           hours: 1,
#           story_points: 0.5
#       }
#   ]
# }
JIRA_CELL_ROLES = json.loads(env.str("JIRA_CELL_ROLES", "{}"))
# SPRINT
# ------------------------------------------------------------------------------
# How many hours per sprint to reserve for meetings.
SPRINT_HOURS_RESERVED_FOR_MEETINGS = env.int("SPRINT_HOURS_RESERVED_FOR_MEETINGS", 2)
# How many hours per sprint to reserve for epic management by default.
SPRINT_HOURS_RESERVED_FOR_EPIC_MANAGEMENT = env.int("SPRINT_HOURS_RESERVED_FOR_EPIC_MANAGEMENT", 2)
SPRINT_STATUS_BACKLOG = "Backlog"
SPRINT_STATUS_IN_PROGRESS = "In progress"
SPRINT_STATUS_REVIEW = "Need Review"
SPRINT_STATUS_EXTERNAL_REVIEW = "External Review / Blocker"
SPRINT_STATUS_MERGED = "Merged"
SPRINT_STATUS_RECURRING = "Recurring"
SPRINT_STATUS_ACCEPTED = "Accepted"
SPRINT_STATUS_IN_DEVELOPMENT = "In development"
SPRINT_STATUS_DEPLOYED_AND_DELIVERED = "Deployed & Delivered"
SPRINT_STATUS_DONE = "Done"
SPRINT_STATUS_ARCHIVED = "Archived"
# Which tickets statuses will be counted as a spillover.
SPRINT_STATUS_SPILLOVER = {
    SPRINT_STATUS_BACKLOG,
    SPRINT_STATUS_IN_PROGRESS,
    SPRINT_STATUS_REVIEW,
    SPRINT_STATUS_MERGED,
}
# Which tickets will be moved the the next sprint.
SPRINT_STATUS_ACTIVE = {
    SPRINT_STATUS_EXTERNAL_REVIEW,
    SPRINT_STATUS_RECURRING,
} | SPRINT_STATUS_SPILLOVER
# Which epic statuses indicate ongoing epic.
SPRINT_STATUS_EPIC_IN_PROGRESS = {
    SPRINT_STATUS_RECURRING,
    SPRINT_STATUS_ACCEPTED,
    SPRINT_STATUS_IN_DEVELOPMENT,
}
# Which statuses indicate that the ticket doesn't need a review (unless specified with a bot's directive).
SPRINT_STATUS_NO_MORE_REVIEW = {
    SPRINT_STATUS_EXTERNAL_REVIEW,
    SPRINT_STATUS_MERGED,
    SPRINT_STATUS_RECURRING,
}
# Regex for retrieving time from sprint directives. It captures data into `hours` and `minutes` groups.
SPRINT_TIME_REGEX = r"(?:(?P<hours>\d+)\s?h.*?)?\s?(?:(?P<minutes>\d+)\s?m.*?)?"
# Base of the sprint directive for planning time.
SPRINT_PLANNING_DIRECTIVE_BASE = fr"\[~{JIRA_BOT_USERNAME}\]: plan {SPRINT_TIME_REGEX}"
# String for overriding how much time will be needed for an epic management per sprint.
SPRINT_EPIC_DIRECTIVE = f"{SPRINT_PLANNING_DIRECTIVE_BASE} per sprint for epic management"
# String for overriding how much time will be needed for a recurring task per sprint.
SPRINT_RECURRING_DIRECTIVE = f"{SPRINT_PLANNING_DIRECTIVE_BASE} per sprint for this task"
# String for overriding how much time will be needed for the task's review.
SPRINT_REVIEW_DIRECTIVE = f"{SPRINT_PLANNING_DIRECTIVE_BASE} for reviewing this task"
# Regexp for retrieving spillover reason from the issue's comment.
SPILLOVER_REASON_DIRECTIVE = fr"\[~{JIRA_BOT_USERNAME}\]: <spillover>(.*)<\/spillover>"
# Adds ability to ignore users that are not members of the specific cells, but are assigned to their boards.
SPILLOVER_CLEAN_SPRINT_IGNORED_USERS = set(env.list("SPILLOVER_CLEAN_SPRINT_IGNORED_USERS", default=[]))
# Regex for extracting sprint data from the name of the sprint.
# It is also used for distinguishing standard sprints from special ones (e.g. Stretch Goals).
# The following data is gathered:
# Group 1. cell's key
# Group 2. sprint number
# Group 3. sprint starting date
SPRINT_REGEX = env.str("SPRINT_REGEX", r"(\w+).*?(\d+).*\((.*)\)")
# Number of days that a sprint lasts
SPRINT_DURATION_DAYS = env.int("SPRINT_DURATION_DAYS", 14)
# Regex for extracting issue data from the key of the issue.
# The following data is gathered:
# Group 1. cell's key
# Group 2. issue number
SPRINT_ISSUE_REGEX = env.str("SPRINT_ISSUE_REGEX", r"(\w+)-(\d+)")
# UTC time at which a new sprint starts (format: `%H:%M`).
SPRINT_START_TIME_UTC = env.int("SPRINT_START_TIME_UTC", "00:00")
# Exact name of the tickets for logging the clean sprint hints.
SPRINT_MEETINGS_TICKET = env.str("SPRINT_MEETINGS_TICKET", "Meetings")

# GOOGLE CALENDAR
# ------------------------------------------------------------------------------
# Google API credentials for retrieving data from Calendar API.
# To get these credentials, you need to:
# 1. Go to https://console.developers.google.com/projectselector2/iam-admin/serviceaccounts.
# 2. Create service account for the selected project.
# 3. Create key for the user and download JSON file.
# 4. Extract `private_key` and `token_uri` from the downloaded key and set these values in envs.
GOOGLE_API_CREDENTIALS = {
  "private_key": env.str("GOOGLE_API_PRIVATE_KEY", multiline=True),
  "client_email": env.str("GOOGLE_API_CLIENT_EMAIL"),
  "token_uri": env.str("GOOGLE_API_TOKEN_URI", "https://oauth2.googleapis.com/token"),
}
# Regex for retrieving users' vacations from Google Calendar. This one is case-insensitive.
# It supports two basic cases:
# - `{name} off`, `{name} away`, etc. for full vacation.
# - `{name} available 4 hours/day`, `{name} 3h`, etc. for reduced availability.
# FIXME: It doesn't currently support people with the same name, so, if needed, we'll need to change it.
GOOGLE_CALENDAR_VACATION_REGEX = env.str("GOOGLE_CALENDAR_VACATION_REGEX", r"^(?P<user>\w+)\s(?P<action>.*?)(?:(?P<hours>\d+)\s?h.*?)?$")
GOOGLE_SPILLOVER_SPREADSHEET = env.str("GOOGLE_SPILLOVER_SPREADSHEET")
GOOGLE_CONTACT_SPREADSHEET = env.str("GOOGLE_CONTACT_SPREADSHEET")
GOOGLE_AVAILABILITY_RANGE = env.str("GOOGLE_AVAILABILITY_RANGE")
# Regex for retrieving users' availability from the "Contact" sheet.
GOOGLE_AVAILABILITY_REGEX = env.str("GOOGLE_AVAILABILITY_REGEX", r"\d+(?::\d+)?.*?(?:pm|am)")
GOOGLE_AVAILABILITY_TIME_FORMAT = env.str("GOOGLE_AVAILABILITY_TIME_FORMAT", "%I%p")
GOOGLE_SPILLOVER_SPREADSHEET_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SPILLOVER_SPREADSHEET}"
# Spreadsheet with the cell rotations.
GOOGLE_ROTATIONS_SPREADSHEET = env.str("GOOGLE_ROTATIONS_SPREADSHEET")
# Range (sheet) of the spreadsheet with the cell rotations.
GOOGLE_ROTATIONS_RANGE = env.str("GOOGLE_ROTATIONS_RANGE")
# Message to put in the comment as a reminder to the user who forgot to post the spillover reason.
SPILLOVER_REMINDER_MESSAGE = fr"please fill the spillover reason in the " \
                             fr"[Spillover spreadsheet|{GOOGLE_SPILLOVER_SPREADSHEET_URL}] " \
                             fr"and the next time add the spillover reason as a Jira comment " \
                             fr"matching the following regexp: {{code:python}} {SPILLOVER_REASON_DIRECTIVE}{{code}}"
# Message to put in the comment as a reminder to the user who forgot to post the spillover avoidance hints.
SPILLOVER_CLEAN_HINTS_MESSAGE = fr"congratulations for achieving a clean sprint! " \
                                fr"If you have any hints about how you did this, please add them to the " \
                                fr"[Spillover spreadsheet|{GOOGLE_SPILLOVER_SPREADSHEET_URL}]. " \
                                fr"You can also add them upfront as a Jira comment " \
                                fr"matching the following regexp: {{code:python}} {SPILLOVER_REASON_DIRECTIVE}{{code}}"

# Specify names of the Tempo account categories.
TEMPO_BILLABLE_ACCOUNT = env.str("TEMPO_BILLABLE_ACCOUNT", "BILLABLE")
TEMPO_BILLABLE_ACCOUNT_NAME = env.str("TEMPO_BILLABLE_ACCOUNT_NAME", "Billable account")
TEMPO_NON_BILLABLE_ACCOUNT = env.str("TEMPO_NON_BILLABLE_ACCOUNT", "NON-BILLABLE")
TEMPO_NON_BILLABLE_ACCOUNT_NAME = env.str("TEMPO_NON_BILLABLE_ACCOUNT_NAME", "Non-billable account")
TEMPO_NON_BILLABLE_RESPONSIBLE_ACCOUNT = env.str("TEMPO_NON_BILLABLE_RESPONSIBLE_ACCOUNT", "NON-BILLABLE-CELL")
TEMPO_NON_BILLABLE_RESPONSIBLE_ACCOUNT_NAME = env.str("TEMPO_NON_BILLABLE_RESPONSIBLE_ACCOUNT_NAME", "Non-billable cell responsibility account")
TEMPO_START_YEAR = env.int("TEMPO_START_YEAR", 2015)

CACHE_WORKLOG_MUTABLE_MONTHS = env.int("CACHE_TEMPO_MUTABLE_MONTHS", 2)
CACHE_WORKLOG_TIMEOUT_LONG_TERM = SECONDS_IN_HOUR * HOURS_IN_DAY * 31
CACHE_WORKLOG_TIMEOUT_SHORT_TERM = SECONDS_IN_MINUTE * 2
CACHE_WORKLOG_TIMEOUT_ONE_TIME = SECONDS_IN_MINUTE * 2
CACHE_SPRINT_TIMEOUT_ONE_TIME = SECONDS_IN_MINUTE * 2
CACHE_WORKLOG_REGENERATE_LOCK = "cache-worklog-regenerate"
CACHE_WORKLOG_REGENERATE_LOCK_TIMEOUT_SECONDS = env.int("CACHE_WORKLOG_REGENERATE_LOCK_TIMEOUT_SECONDS", SECONDS_IN_MINUTE * 30)
CACHE_SPRINT_END_DATE_PREFIX = "sprint_end_date-"
CACHE_SPRINT_END_DATE_TIMEOUT_SECONDS = SECONDS_IN_HOUR * HOURS_IN_DAY * SPRINT_DURATION_DAYS
CACHE_SPRINT_END_LOCK = "sprint_end_lock-"
CACHE_SPRINT_END_LOCK_TIMEOUT_SECONDS = SECONDS_IN_HOUR * HOURS_IN_DAY
CACHE_SUSTAINABILITY_PREFIX = "sustainability-"
CACHE_SUSTAINABILITY_DATE_FORMAT = "%Y-%m"
CACHE_WORKLOGS_KEY = "worklogs"
CACHE_WORKLOGS_KEY_LONG_TERM = "worklogs_lt"
CACHE_ISSUES_KEY = "issues"
CACHE_ISSUES_KEY_LONG_TERM = "issues_lt"
CACHE_ISSUES_TIMEOUT_SHOT_TERM = SECONDS_IN_HOUR * HOURS_IN_DAY * 2
CACHE_ISSUES_LOCK = "issues_lock"

# Dict for local account naming.
TEMPO_ACCOUNT_TRANSLATE = {
    TEMPO_BILLABLE_ACCOUNT_NAME: 'billable_accounts',
    TEMPO_NON_BILLABLE_ACCOUNT_NAME: 'non_billable_accounts',
    TEMPO_NON_BILLABLE_RESPONSIBLE_ACCOUNT_NAME: 'non_billable_responsible_accounts',
}

# Base TEMPO Team ID
TEMPO_TEAM_ID = env.int("TEMPO_TEAM_ID", 1)

# Email addresses that will receive all notifications about budget overheads and cell sustainability problems.
NOTIFICATIONS_SUSTAINABILITY_EMAILS = env.list("NOTIFICATIONS_SUSTAINABILITY_EMAILS", default=[])
SUSTAINABILITY_MAX_NON_BILLABLE_TO_BILLABLE_CELL_RATIO = env.float("SUSTAINABILITY_MAX_NON_BILLABLE_TO_BILLABLE_CELL_RATIO", .3)

# Pool size for making parallel API requests
MULTIPROCESSING_POOL_SIZE = env.int("MULTIPROCESSING_POOL_SIZE", 32)
MULTIPROCESSING_TIMEOUT = env.int("MULTIPROCESSING_TIMEOUT", 128)

# MATTERMOST
# ------------------------------------------------------------------------------
# URL of the Mattermost server.
MATTERMOST_SERVER = env.str("MATTERMOST_SERVER")
# Default is the https port but it can be configured
MATTERMOST_PORT = env.int("MATTERMOST_PORT", 443)
# Channel to ping
# Name of the channel should always be in lowercase and if incase the channel name
# has a space in between then it is replaced by a hyphen. For eg: "Sprint Planning"
# changes to "sprint-planning"
MATTERMOST_CHANNEL = env.str("MATTERMOST_CHANNEL")
# Login Id
MATTERMOST_LOGIN_ID = env.str("MATTERMOST_LOGIN_ID")
# Access Token
MATTERMOST_ACCESS_TOKEN = env.str("MATTERMOST_ACCESS_TOKEN")
# Team Name
MATTERMOST_TEAM_NAME = env.str("MATTERMOST_TEAM_NAME")

# WEBHOOKS
# ------------------------------------------------------------------------------
# Webhook username (Used with basic auth)
WEBHOOK_USERNAME = env.str("WEBHOOK_USERNAME")
# Webhook password (Used with basic auth)
WEBHOOK_PASSWORD = env.str("WEBHOOK_PASSWORD")
# Handbook roles page URL
HANDBOOK_ROLES_PAGE = env.str("HANDBOOK_ROLES_PAGE")
