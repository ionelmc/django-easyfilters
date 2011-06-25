from django.shortcuts import render

from django_easyfilters.tests.models import Book
from django_easyfilters import FilterSet

class BookFilterSet(FilterSet):
    fields = [
        'binding',
        'authors',
        'genre',
        'price',
        'date_published',
        ]

def books(request):
    books = Book.objects.all()
    booksfilter = BookFilterSet(books, request.GET)
    return render(request, "books.html", {'books': booksfilter.qs,
                                          'booksfilter': booksfilter})
