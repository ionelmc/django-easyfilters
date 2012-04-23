
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
    'django_easyfilters',
    'django_easyfilters.tests',
]

ROOT_URLCONF = 'django_easyfilters.tests.urls'

DEBUG = True

SITE_ID = 1

STATIC_URL = '/static/'

SECRET_KEY = 'x'
