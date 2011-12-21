from django.shortcuts import render

from django_easyfilters.tests.models import Book, Author
from django_easyfilters import FilterSet
from django_easyfilters.filters import NumericRangeFilter

class BookFilterSet(FilterSet):
    fields = [
        'binding',
        'authors',
        'genre',
        'price',
        'date_published',
        'rating',
        ]

def books(request):
    books = Book.objects.all()
    booksfilter = BookFilterSet(books, request.GET)
    return render(request, "books.html", {'books': booksfilter.qs,
                                          'booksfilter': booksfilter})

class AuthorFilterSet(FilterSet):
    fields = [
        ('likes', {}, NumericRangeFilter)
        ]

def authors(request):
    authors = Author.objects.all()
    authorsfilter = AuthorFilterSet(authors, request.GET)
    return render(request, "authors.html", {'authors': authorsfilter.qs,
                                            'authorsfilter': authorsfilter})
