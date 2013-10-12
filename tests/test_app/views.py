from django.shortcuts import render

from .models import Book, Author
from django_easyfilters import FilterSet
from django_easyfilters.filters import NumericRangeFilter

class BookFilterSet(FilterSet):
    fields = [
        'binding',
        'authors',
        ('authors__likes', {}, NumericRangeFilter),
        'genre',
        ('genre__likes', {}, NumericRangeFilter),
        'price',
        'date_published',
        'rating',
        'edition',
        'other',
    ]

def books(request):
    books = Book.objects.all()
    booksfilter = BookFilterSet(books, request.GET)
    return render(request, "books.html", {'books': booksfilter.qs,
                                          'booksfilter': booksfilter,
                                          'title': "Books",
                                          })

class AuthorFilterSet(FilterSet):
    fields = [
        ('likes', {}, NumericRangeFilter)
        ]

def authors(request):
    authors = Author.objects.all()
    authorsfilter = AuthorFilterSet(authors, request.GET)
    return render(request, "authors.html", {'authors': authorsfilter.qs,
                                            'authorsfilter': authorsfilter,
                                            'title': "Authors",
                                            })


def book_search(request):
    books = Book.objects.all()
    if 'search_q' in request.GET:
        books = books.filter(name__icontains=request.GET['search_q'])

    booksfilter = BookFilterSet(books, request.GET)
    return render(request, "book_search.html", {'books': booksfilter.qs,
                                                'booksfilter': booksfilter,
                                                'title': "Books",
                                                })
