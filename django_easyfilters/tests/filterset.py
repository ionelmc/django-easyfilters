# -*- coding: utf-8; -*-

import decimal
import operator

from django.http import QueryDict
from django.test import TestCase
from django.utils.datastructures import MultiValueDict

from django_easyfilters.filterset import FilterSet
from django_easyfilters.filters import FilterOptions, \
    FILTER_ADD, FILTER_REMOVE, FILTER_ONLY_CHOICE, \
    ForeignKeyFilter, ValuesFilter, ChoicesFilter, ManyToManyFilter

from models import Book, Genre, Author, BINDING_CHOICES


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
        data = QueryDict('')
        f = BookFilterSet(qs, data)
        self.assertEqual(qs.count(), f.qs.count())

    def test_filterset_render(self):
        """
        Smoke test to ensure that filtersets can be rendered
        """
        class BookFilterSet(FilterSet):
            fields = [
                'genre',
                ]

        qs = Book.objects.all()
        fs = BookFilterSet(qs, QueryDict(''))
        rendered = fs.render()
        self.assertTrue('Genre' in rendered)
        self.assertEqual(rendered, unicode(fs))

        # And when in 'already filtered' mode:
        choice = fs.filters[0].get_choices(qs, QueryDict(''))[0]
        fs_filtered = BookFilterSet(qs, choice.params)
        rendered_2 = fs_filtered.render()
        self.assertTrue('Genre' in rendered_2)

    def test_get_filter_for_field(self):
        """
        Ensures that the get_filter_for_field method chooses appropriately.
        """
        class BookFilterSet(FilterSet):
            fields = [
                'genre',
                'edition',
                'binding',
                'authors',
                ]

        fs = BookFilterSet(Book.objects.all(), QueryDict(''))
        self.assertEqual(ForeignKeyFilter, type(fs.filters[0]))
        self.assertEqual(ValuesFilter, type(fs.filters[1]))
        self.assertEqual(ChoicesFilter, type(fs.filters[2]))
        self.assertEqual(ManyToManyFilter, type(fs.filters[3]))


class TestFilters(TestCase):
    fixtures = ['django_easyfilters_tests']

    def test_foreignkey_filters_produced(self):
        """
        A ForeignKey should produce a list of the possible related objects,
        with counts.
        """
        # Make another Genre that isn't used
        new_g, created = Genre.objects.get_or_create(name='Nonsense')
        assert created

        filter_ = ForeignKeyFilter('genre', Book)
        qs = Book.objects.all()
        data = MultiValueDict()

        choices = [(c.label, c.count) for c in filter_.get_choices(qs, data)]

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
        qs = Book.objects.all()
        data = MultiValueDict()
        filter_ = ForeignKeyFilter('genre', Book)
        choices = filter_.get_choices(qs, data)

        # If we use the params from e.g. the first choice, that should produce a
        # filtered qs when fed back in (i.e. when we 'click' on that option we
        # should get a filter on it).
        reached = False
        for choice in choices:
            reached = True
            qs_filtered = filter_.apply_filter(qs, choice.params)
            self.assertEqual(len(qs_filtered), choice.count)
            for book in qs_filtered:
                self.assertEqual(unicode(book.genre), choice.label)
        self.assertTrue(reached)

    def test_foreignkey_remove_link(self):
        """
        Ensure that a ForeignKey Filter will turn into a 'remove' link when an
        item has been selected.
        """
        filter_ = ForeignKeyFilter('genre', Book)
        qs = Book.objects.all()
        data = MultiValueDict()
        choices = filter_.get_choices(qs, data)
        choice = choices[0]

        qs_filtered = filter_.apply_filter(qs, choice.params)
        choices2 = filter_.get_choices(qs_filtered, choice.params)

        # Should have one item
        self.assertEqual(1, len(choices2))
        self.assertEqual(choices2[0].link_type, FILTER_REMOVE)

        # 'Clicking' should remove filtering
        qs_reverted = filter_.apply_filter(qs, choices2[0].params)
        self.assertEqual(qs, qs_reverted)

    def test_values_filter(self):
        """
        Tests for ValuesFilter
        """
        # We combine the tests for brevity
        filter_ = ValuesFilter('edition', Book)
        qs = Book.objects.all()
        choices = filter_.get_choices(qs, MultiValueDict())

        for choice in choices:
            count = Book.objects.filter(edition=choice.params.values()[0]).count()
            self.assertEqual(choice.count, count)

            # Check the filtering
            qs_filtered = filter_.apply_filter(qs, choice.params)
            self.assertEqual(len(qs_filtered), choice.count)
            for book in qs_filtered:
                self.assertEqual(unicode(book.edition), choice.label)

            # Check we've got a 'remove link' on filtered.
            choices_filtered = filter_.get_choices(qs, choice.params)
            self.assertEqual(1, len(choices_filtered))
            self.assertEqual(choices_filtered[0].link_type, FILTER_REMOVE)


        # Check list is full, and in right order
        self.assertEqual([unicode(v) for v in Book.objects.values_list('edition', flat=True).order_by('edition').distinct()],
                         [choice.label for choice in choices])

    def test_choices_filter(self):
        """
        Tests for ChoicesFilter
        """
        filter_ = ChoicesFilter('binding', Book)
        qs = Book.objects.all()
        choices = filter_.get_choices(qs, MultiValueDict())
        # Check:
        # - order is correct.
        # - all values present (guaranteed by fixture data)
        # - choice display value is used.

        binding_choices_db = [b[0] for b in BINDING_CHOICES]
        binding_choices_display = [b[1] for b in BINDING_CHOICES]
        self.assertEqual([c.label for c in choices], binding_choices_display)

        # Check choice db value in params
        for c in choices:
            self.assertTrue(c.params.values()[0] in binding_choices_db)

    def test_manytomany_filter(self):
        """
        Tests for ManyToManyFilter
        """
        filter_ = ManyToManyFilter('authors', Book)
        qs = Book.objects.all()

        # ManyToMany can have 'drill down', i.e. multiple levels of filtering,
        # which can be removed individually.

        # First level:
        choices = filter_.get_choices(qs, MultiValueDict())

        # Check list is full, and in right order
        self.assertEqual([unicode(v) for v in Author.objects.all()],
                         [choice.label for choice in choices])

        for choice in choices:
            # For single choice, param will be single integer:
            param = int(choice.params[filter_.query_param])

            # Check the count
            count = Book.objects.filter(authors=int(param)).count()
            self.assertEqual(choice.count, count)

            author = Author.objects.get(id=param)

            # Check the label
            self.assertEqual(unicode(author),
                             choice.label)

            # Check the filtering
            qs_filtered = filter_.apply_filter(qs, choice.params)
            self.assertEqual(len(qs_filtered), choice.count)

            for book in qs_filtered:
                self.assertTrue(author in book.authors.all())

            # Check we've got a 'remove link' on filtered.
            choices_filtered = filter_.get_choices(qs, choice.params)
            self.assertEqual(choices_filtered[0].link_type, FILTER_REMOVE)


    def test_manytomany_filter_multiple(self):
        filter_ = ManyToManyFilter('authors', Book)
        qs = Book.objects.all()

        # Specific example - multiple filtering
        emily = Author.objects.get(name='Emily Brontë')
        charlotte = Author.objects.get(name='Charlotte Brontë')
        anne = Author.objects.get(name='Anne Brontë')

        # If we select 'emily' as an author:

        data =  MultiValueDict({'authors':[str(emily.pk)]})
        qs_emily = filter_.apply_filter(qs, data)

        # ...we should get a qs that includes Poems and Wuthering Heights.
        self.assertTrue(qs_emily.filter(name='Poems').exists())
        self.assertTrue(qs_emily.filter(name='Wuthering Heights').exists())
        # ...and excludes Jane Eyre
        self.assertFalse(qs_emily.filter(name='Jane Eyre').exists())

        # We should get a 'choices' that includes charlotte and anne
        choices = filter_.get_choices(qs_emily, data)
        self.assertTrue(unicode(anne) in [c.label for c in choices if c.link_type is FILTER_ADD])
        self.assertTrue(unicode(charlotte) in [c.label for c in choices if c.link_type is FILTER_ADD])

        # ... but not emily, because that is obvious and boring
        self.assertTrue(unicode(emily) not in [c.label for c in choices if c.link_type is FILTER_ADD])
        # emily should be in 'remove' links, however.
        self.assertTrue(unicode(emily) in [c.label for c in choices if c.link_type is FILTER_REMOVE])

        # If we select again:
        data =  MultiValueDict({'authors': [str(emily.pk), str(anne.pk)]})

        qs_emily_anne = filter_.apply_filter(qs, data)

        # ...we should get a qs that includes Poems
        self.assertTrue(qs_emily_anne.filter(name='Poems').exists())
        # ... but not Wuthering Heights
        self.assertFalse(qs_emily_anne.filter(name='Wuthering Heights').exists())

        # The choices should contain just emily and anne to remove, and
        # charlotte should have 'link_type' set to FILTER_ONLY_CHOICE, and
        # params set to None, because there is no point adding a filter when it
        # is the only choice.
        choices = filter_.get_choices(qs_emily_anne, data)
        self.assertEqual([(c.label, c.link_type) for c in choices],
                         [(unicode(emily), FILTER_REMOVE),
                          (unicode(anne), FILTER_REMOVE),
                          (unicode(charlotte), FILTER_ONLY_CHOICE)])
        self.assertEqual(choices[2].params, None)

    def test_order_by_count(self):
        """
        Tests the 'order_by_count' option.
        """
        filter1 = ForeignKeyFilter('genre', Book, order_by_count=True)
        qs = Book.objects.all()
        choices1 = filter1.get_choices(qs, MultiValueDict())

        # Should be same after sorting by 'count'
        self.assertEqual(choices1, sorted(choices1, key=operator.attrgetter('count'), reverse=True))

        filter2 = ForeignKeyFilter('genre', Book, order_by_count=False)
        choices2 = filter2.get_choices(qs, MultiValueDict())

        # Should be same after sorting by 'label' (that is equal to Genre.name,
        # and Genre ordering is by that field)
        self.assertEqual(choices2, sorted(choices2, key=operator.attrgetter('label')))
