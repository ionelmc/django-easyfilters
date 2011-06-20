import decimal

from django.test import TestCase
from django_easyfilters import FilterSet

from models import Book, Genre


class TestFilterSet(TestCase):

    fixtures = ['django_easyfilters_tests']

    def test_queryset_no_filters(self):
        class BookFilterSet(FilterSet):
            fields = []
            model = Book

        qs = Book.objects.all()
        data = {}
        f = BookFilterSet(qs, data)
        self.assertEqual(qs.count(), f.qs.count())

    def test_foreignkey_filters_produced(self):
        """
        A ForeignKey should produce a list of the possible related objects,
        with counts.
        """
        class BookFilterSet(FilterSet):
            fields = [
                'genre',
                ]
            model = Book

        # Make another Genre that isn't used
        new_g, created = Genre.objects.get_or_create(name='Nonsense')
        assert created

        qs = Book.objects.all()
        data = {}
        fs = BookFilterSet(qs, data)

        choices = [(c.label, c.count) for c in fs.filters[0].get_choices(qs, data)]

        reached = [False, False]
        for g in Genre.objects.all():
            count = g.book_set.count()
            if count == 0:
                reached[0] = True
                self.assertTrue((g.name, count) not in choices)
            else:
                reached[1] = True
                self.assertTrue((g.name, count) in choices)

        self.assertTrue(reached[0])
        self.assertTrue(reached[1])

