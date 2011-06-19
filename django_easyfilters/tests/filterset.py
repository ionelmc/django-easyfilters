import decimal

from django.test import TestCase
from django_easyfilters import FilterSet

from models import Book, Genre


class BookFilterSet(FilterSet):
    fields = [
        'binding',
        ]
    model = Book


class TestFilterSet(TestCase):

    fixtures = ['django_easyfilters_tests']

    def test_no_filters(self):
        qs = Book.objects.all()
        data = {}
        f = BookFilterSet(data, qs)
        self.assertEqual(qs.count(), f.qs.count())
