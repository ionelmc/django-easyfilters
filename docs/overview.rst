========
Overview
========

Suppose your models.py looks something like this:

.. code-block:: python

    class Book(models.Model):
        name = models.CharField(max_length=100)
        binding = models.CharField(max_length=2, choices=BINDING_CHOICES)
        authors = models.ManyToManyField(Author)
        genre = models.ForeignKey(Genre)
        price = models.DecimalField(max_digits=6, decimal_places=2)
        date_published = models.DateField()

(with BINDING_CHOICES, Author and Genre omitted for brevity).

You might want to present a list of Book objects, allowing the user to filter on
the various fields. Your views.py would be something like this:

.. code-block:: python

    from django.shortcuts import render

    from myapp.models import Book

    def booklist(request):
        books = Book.objects.all()
        return render(request, "booklist.html", {'books': books})

and the template is like this:

.. code-block:: django

    {% for book in books %}
       {# etc #}
    {% endfor %}

To add the filters, in views.py add a FilterSet subclass and change the view
code as follow:

.. code-block:: python

    from django.shortcuts import render
    from django_easyfilters import FilterSet

    from myapp.models import Book

    class BookFilterSet(FilterSet):
        fields = [
            'binding',
            'authors',
            'genre',
            'price',
            ]

    def booklist(request):
        books = Book.objects.all()
        booksfilter = BookFilterSet(books, request.GET)
        return render(request, "booklist.html", {'books': booksfilter.qs,
                                                 'booksfilter': booksfilter})

Notice that the ``books`` item put in the context has been replaced by
``bookfilter.qs``, so that the QuerySet passed to the template has filtering
applied to it, as defined by BookFilterSet and the information from the query
string (request.GET).

The ``booksfilter`` item has been added to the context in order for the filters
to be displayed on the template.

Then, in the template, just add ``{{ booksfilter }}`` to the template.
You can also use pagination e.g. using django-pagination:

.. code-block:: django

    {% autopaginate books 20 %}

    <h2>Filters:</h2>
    {{ booksfilter }}

    {% paginate %}

    <h2>Books found</h2>
    {% for book in books %}
       {# etc #}
    {% endfor %}

The ``FilterSet`` also provides a 'title' attribute that can be used to provide
a simple summary of what has been selected so far. It is made up of a comma
separated list of chosen fields. For example, if the user has selected genre
'Classics' and binding 'Hardback' in the example above, you would get the following::

    >>> books = Book.objects.all()
    >>> booksfilter = BookFilterSet(books, request.GET)
    >>> booksfilter.title
    u"Hardback, Classics"

The fields used for the ``title`` attribute, and the order they are used, can be
customised by adding a ``title_fields`` attribute to your ``FilterSet``:

.. code-block:: python

    class BookFilterSet(FilterSet):
        fields = [
            'binding',
            'authors',
            'genre',
            'price',
            ]

        title_fields = ['genre', 'binding']

Customisation of the filters can be done in various ways - see :doc:`the
FilterSet documentation <filterset>` for how to do this, and :doc:`the Filters
documentation <filters>` for options that can be specified.
