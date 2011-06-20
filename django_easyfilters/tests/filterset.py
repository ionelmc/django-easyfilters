import decimal
import operator

from django.test import TestCase
from django_easyfilters import FilterSet, FilterOptions, FILTER_ADD, FILTER_REMOVE

from models import Book, Genre


class TestFilterSet(TestCase):

    # Tests are written so that adding new data to fixtures won't break the
    # tests, so numbers/values are compared using DB queries. Extra care is
    # taken to ensure that there is some data that matches what we are assuming
    # is there.
    fixtures = ['django_easyfilters_tests']

    def test_queryset_no_filters(self):
        class BookFilterSet(FilterSet):
            fields = []

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

    def test_foreignkey_params_produced(self):
        """
        A ForeignKey filter shoud produce params that cause the query to be
        limited by that filter.
        """
        class BookFilterSet(FilterSet):
            fields = [
                'genre',
                ]

        qs = Book.objects.all()
        data = {}
        fs = BookFilterSet(qs, data)
        choices = fs.filters[0].get_choices(qs, data)

        # If we use the params from e.g. the first choice, that should produce a
        # filtered qs when fed back in (i.e. when we 'click' on that option we
        # should get a filter on it).
        reached = False
        for choice in choices:
            reached = True
            fs_filtered = BookFilterSet(qs, choice.params)
            qs_filtered = fs_filtered.qs
            self.assertEqual(len(qs_filtered), choice.count)
            for book in qs_filtered:
                self.assertEqual(unicode(book.genre), choice.label)
        self.assertTrue(reached)

    def test_foreignkey_remove_link(self):
        """
        Ensure that a ForeignKey Filter will turn into a 'remove' link when an
        item has been selected.
        """
        class BookFilterSet(FilterSet):
            fields = [
                'genre',
                ]

        qs = Book.objects.all()
        data = {}
        fs = BookFilterSet(qs, data)
        choices = fs.filters[0].get_choices(qs, data)
        choice = choices[0]
        fs_filtered = BookFilterSet(qs, choice.params)
        qs_filtered = fs_filtered.qs
        choices2 = fs_filtered.filters[0].get_choices(qs_filtered, choice.params)

        # Should have one item
        self.assertEqual(1, len(choices2))
        self.assertEqual(choices2[0].link_type, FILTER_REMOVE)

        # 'Clicking' should remove filtering
        fs_reverted = BookFilterSet(qs, choices2[0].params)
        self.assertEqual(qs, fs_reverted.qs)

    def test_filterset_render(self):
        """
        Smoke test to ensure that filtersets can be rendered
        """
        class BookFilterSet(FilterSet):
            fields = [
                'genre',
                ]
        qs = Book.objects.all()
        fs = BookFilterSet(qs, {})
        rendered = fs.render()
        self.assertTrue('Genre' in rendered)
        self.assertEqual(rendered, unicode(fs))

        # And when in 'already filtered' mode:
        choice = fs.filters[0].get_choices(qs, {})[0]
        fs_filtered = BookFilterSet(qs, choice.params)
        rendered_2 = fs_filtered.render()
        self.assertTrue('Genre' in rendered_2)

    def test_order_by_count(self):
        """
        Tests the 'order_by_count' option.
        """
        class BookFilterSet1(FilterSet):
            fields = [
                FilterOptions('genre', order_by_count=True)
                ]
        qs = Book.objects.all()
        fs1 = BookFilterSet1(qs, {})
        choices1 = fs1.filters[0].get_choices(qs, {})

        # Should be same after sorting by 'count'
        self.assertEqual(choices1, sorted(choices1, key=operator.attrgetter('count'), reverse=True))
        class BookFilterSet2(FilterSet):
            fields = [
                FilterOptions('genre', order_by_count=False)
                ]
        fs2 = BookFilterSet2(qs, {})
        choices2 = fs2.filters[0].get_choices(qs, {})

        # Should be same after sorting by 'label' (that is equal to Genre.name,
        # and Genre ordering is by that field)
        self.assertEqual(choices2, sorted(choices2, key=operator.attrgetter('label')))
