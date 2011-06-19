# URLs to make it easy to add more data for the test suite.

from django.conf.urls.defaults import *
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Normal views
    (r'^admin/', include(admin.site.urls)),

)

