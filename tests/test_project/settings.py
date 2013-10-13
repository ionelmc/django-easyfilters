DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'tests.db',
    },
}

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'django_easyfilters',
    'test_app',
    #'debug_toolbar',
    #'django_extensions',
]
try:
    import debug_toolbar
    INSTALLED_APPS.append('debug_toolbar')
    from django.conf.global_settings import MIDDLEWARE_CLASSES
    MIDDLEWARE_CLASSES = MIDDLEWARE_CLASSES + (
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    )
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda req: True,
    }
except ImportError:
    pass

try:
    import django_extensions
    INSTALLED_APPS.append('django_extensions')
except ImportError:
    pass

TEMPLATE_CONTEXT_PROCESSORS = [
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.contrib.messages.context_processors.messages",
    "django.core.context_processors.request",
]

ROOT_URLCONF = 'test_app.urls'

DEBUG = True

SITE_ID = 1

STATIC_URL = '/static/'

SECRET_KEY = 'x'

#TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
