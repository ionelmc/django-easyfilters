# URLs to make it easy to add more data for the test suite.

from django.conf.urls.defaults import *
from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
    (r'^books/', 'test_app.views.books'),
    (r'^book-search/', 'test_app.views.book_search'),
    (r'^authors/', 'test_app.views.authors'),
    (r'^admin/', include(admin.site.urls)),
)
