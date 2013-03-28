# admin registration to make it easy to add more data for the test suite.
from __future__ import unicode_literals

from .models import *
from django.contrib import admin

from six import text_type

class BookAdmin(admin.ModelAdmin):
    def authors(obj):
        return ", ".join(text_type(a) for a in obj.authors.all())
    list_display = ["name", authors, "binding", "genre", "price", "date_published", "edition", "rating"]
    list_editable = ["binding", "genre", "price", "date_published", "edition", "rating"]
    list_filter = ["genre", "authors", "binding", "price"]


class AuthorAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "likes"]
    list_editable = ["name", "likes"]

admin.site.register(Book, BookAdmin)
admin.site.register(Author, AuthorAdmin)
admin.site.register(Genre)
