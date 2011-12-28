# -*- coding: utf-8; -*-

from datetime import datetime, date
from decimal import Decimal
import operator
import re

from django.http import QueryDict
from django.test import TestCase
from django.utils.datastructures import MultiValueDict

from django_easyfilters.filterset import FilterSet
from django_easyfilters.filters import \
    FILTER_ADD, FILTER_REMOVE, FILTER_DISPLAY, \
    ForeignKeyFilter, ValuesFilter, ChoicesFilter, ManyToManyFilter, DateTimeFilter, NumericRangeFilter

from models import Book, Genre, Author, BINDING_CHOICES, Person


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
        choice = fs.filters[0].get_choices(qs)[0]
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
                'date_published',
                'price',
                'rating',
                ]

        fs = BookFilterSet(Book.objects.all(), QueryDict(''))
        self.assertEqual(ForeignKeyFilter, type(fs.filters[0]))
        self.assertEqual(ValuesFilter, type(fs.filters[1]))
        self.assertEqual(ChoicesFilter, type(fs.filters[2]))
        self.assertEqual(ManyToManyFilter, type(fs.filters[3]))
        self.assertEqual(DateTimeFilter, type(fs.filters[4]))
        self.assertEqual(NumericRangeFilter, type(fs.filters[5]))
        self.assertEqual(NumericRangeFilter, type(fs.filters[6]))

    def test_specify_custom_filter(self):
        class AuthorFilterSet(FilterSet):
            fields = [
                ('likes', {}, NumericRangeFilter)
                ]

        fs = AuthorFilterSet(Author.objects.all(), QueryDict(''))
        self.assertEqual(NumericRangeFilter, type(fs.filters[0]))

    def test_default_title(self):
        class BookFilterSet(FilterSet):
            fields = [
                'genre',
                'binding',
                'authors',
                ]

        qs = Book.objects.all()
        data = QueryDict('binding=H&genre=6')
        f = BookFilterSet(qs, data)
        self.assertEqual(f.title, "Classics, Hardback")

    def test_custom_title(self):
        class BookFilterSet(FilterSet):
            fields = [
                'genre',
                'binding',
                'authors',
                ]
            title_fields = [
                'genre',
                ]

        qs = Book.objects.all()
        data = QueryDict('binding=H&genre=6')
        f = BookFilterSet(qs, data)
        self.assertEqual(f.title, "Classics")


class TestFilters(TestCase):
    fixtures = ['django_easyfilters_tests']

    def do_invalid_query_param_test(self, make_filter, params):
        """
        Utility to test filters with invalid query parameters.

        make_filter should a callable that accepts MultiValueDict
        and returns a filter.
        """
        f = make_filter(params)
        f_empty = make_filter(MultiValueDict())
        qs = f.model.objects.all()

        # invalid param should be ignored
        qs_filtered = f.apply_filter(qs)
        self.assertEqual(list(qs_filtered),
                         list(qs))

        self.assertEqual(list(f.get_choices(qs)),
                         list(f_empty.get_choices(qs)))

    def do_missing_related_object_test(self, make_filter, params):
        """
        Utility to test filters with query strings representing objects
        not in the database.

        make_filter should a callable that accepts MultiValueDict
        and returns a filter.
        """
        f = make_filter(params)
        qs = f.model.objects.all()

        # choices should render without error, and with no
        # 'remove' links.
        qs_filtered = f.apply_filter(qs)
        choices = list(f.get_choices(qs))
        self.assertFalse(any(c.link_type == FILTER_REMOVE
                             for c in choices))

    def test_foreignkey_filters_produced(self):
        """
        A ForeignKey should produce a list of the possible related objects,
        with counts.
        """
        # Make another Genre that isn't used
        new_g, created = Genre.objects.get_or_create(name='Nonsense')
        assert created

        data = MultiValueDict()
        filter_ = ForeignKeyFilter('genre', Book, data)
        qs = Book.objects.all()

        choices = [(c.label, c.count) for c in filter_.get_choices(qs)]

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
        filter1 = ForeignKeyFilter('genre', Book, data)
        choices = filter1.get_choices(qs)

        # If we use the params from e.g. the first choice, that should produce a
        # filtered qs when fed back in (i.e. when we 'click' on that option we
        # should get a filter on it).
        reached = False
        for choice in choices:
            reached = True
            filter2 = ForeignKeyFilter('genre', Book, choice.params)
            qs_filtered = filter2.apply_filter(qs)
            self.assertEqual(len(qs_filtered), choice.count)
            for book in qs_filtered:
                self.assertEqual(unicode(book.genre), choice.label)
        self.assertTrue(reached)

    def test_foreignkey_remove_link(self):
        """
        Ensure that a ForeignKey Filter will turn into a 'remove' link when an
        item has been selected.
        """
        qs = Book.objects.all()
        data = MultiValueDict()
        filter1 = ForeignKeyFilter('genre', Book, data)
        choices = filter1.get_choices(qs)
        choice = choices[0]

        filter2 = ForeignKeyFilter('genre', Book, choice.params)
        qs_filtered = filter2.apply_filter(qs)
        choices2 = filter2.get_choices(qs_filtered)

        # Should have one item
        self.assertEqual(1, len(choices2))
        self.assertEqual(choices2[0].link_type, FILTER_REMOVE)
        self.assertEqual(choices2[0].label, choice.label)

        # 'Clicking' should remove filtering
        filter3 = ForeignKeyFilter('genre', Book, choices2[0].params)
        qs_reverted = filter3.apply_filter(qs)
        self.assertEqual(qs, qs_reverted)

    def test_foreignkey_invalid_query(self):
        self.do_invalid_query_param_test(lambda params:
                                             ForeignKeyFilter('genre', Book, params),
                                         MultiValueDict({'genre':['xxx']}))
        self.do_missing_related_object_test(lambda params:
                                                ForeignKeyFilter('genre', Book, params),
                                            MultiValueDict({'genre':['1000']}))

    def test_values_filter(self):
        """
        Tests for ValuesFilter
        """
        # We combine the tests for brevity
        filter1 = ValuesFilter('edition', Book, MultiValueDict())
        qs = Book.objects.all()
        choices = filter1.get_choices(qs)

        for choice in choices:
            count = Book.objects.filter(edition=choice.params.values()[0]).count()
            self.assertEqual(choice.count, count)

            # Check the filtering
            filter2 = ValuesFilter('edition', Book, choice.params)
            qs_filtered = filter2.apply_filter(qs)
            self.assertEqual(len(qs_filtered), choice.count)
            for book in qs_filtered:
                self.assertEqual(unicode(book.edition), choice.label)

            # Check we've got a 'remove link' on filtered.
            choices_filtered = filter2.get_choices(qs)
            self.assertEqual(1, len(choices_filtered))
            self.assertEqual(choices_filtered[0].link_type, FILTER_REMOVE)


        # Check list is full, and in right order
        self.assertEqual([unicode(v) for v in Book.objects.values_list('edition', flat=True).order_by('edition').distinct()],
                         [choice.label for choice in choices])

    def test_choices_filter(self):
        """
        Tests for ChoicesFilter
        """
        filter1 = ChoicesFilter('binding', Book, MultiValueDict())
        qs = Book.objects.all()
        choices = filter1.get_choices(qs)
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

    def test_normalize_choices(self):
        # We shouldn't get links for non-nullable fields when there is only one choice.

        # Make sure there are no other books in 1975
        clark = Author.objects.get(name='Arthur C. Clarke')
        Book.objects.filter(date_published__year=1975).exclude(authors=clark.id).delete()
        qs = Book.objects.filter(date_published__year=1975)
        self.assertEqual(len(qs), 1)

        filter1 = ChoicesFilter('binding', Book, MultiValueDict())
        choices1 = filter1.get_choices(qs)
        self.assertEqual(len(choices1), 1)
        self.assertEqual(choices1[0].link_type, FILTER_DISPLAY)

        filter2 = ForeignKeyFilter('genre', Book, MultiValueDict())
        choices2 = filter2.get_choices(qs)
        self.assertEqual(len(choices2), 1)
        self.assertEqual(choices2[0].link_type, FILTER_DISPLAY)

    def test_manytomany_filter(self):
        """
        Tests for ManyToManyFilter
        """
        filter1 = ManyToManyFilter('authors', Book, MultiValueDict())
        qs = Book.objects.all()

        # ManyToMany can have 'drill down', i.e. multiple levels of filtering,
        # which can be removed individually.

        # First level:
        choices = filter1.get_choices(qs)

        # Check list is full, and in right order
        self.assertEqual([unicode(v) for v in Author.objects.all()],
                         [choice.label for choice in choices])

        for choice in choices:
            # For single choice, param will be single integer:
            param = int(choice.params[filter1.query_param])

            # Check the count
            count = Book.objects.filter(authors=int(param)).count()
            self.assertEqual(choice.count, count)

            author = Author.objects.get(id=param)

            # Check the label
            self.assertEqual(unicode(author),
                             choice.label)

            # Check the filtering
            filter2 = ManyToManyFilter('authors', Book, choice.params)
            qs_filtered = filter2.apply_filter(qs)
            self.assertEqual(len(qs_filtered), choice.count)

            for book in qs_filtered:
                self.assertTrue(author in book.authors.all())

            # Check we've got a 'remove link' on filtered.
            choices_filtered = filter2.get_choices(qs)
            self.assertEqual(choices_filtered[0].link_type, FILTER_REMOVE)

    def test_manytomany_filter_multiple(self):
        qs = Book.objects.all()

        # Specific example - multiple filtering
        emily = Author.objects.get(name='Emily Brontë')
        charlotte = Author.objects.get(name='Charlotte Brontë')
        anne = Author.objects.get(name='Anne Brontë')

        # If we select 'emily' as an author:

        data =  MultiValueDict({'authors':[str(emily.pk)]})
        with self.assertNumQueries(1):
            # 1 query for all chosen objects
            filter1 = ManyToManyFilter('authors', Book, data)

        with self.assertNumQueries(0):
            # This shouldn't need to do any more queries
            qs_emily = filter1.apply_filter(qs)

        # ...we should get a qs that includes Poems and Wuthering Heights.
        self.assertTrue(qs_emily.filter(name='Poems').exists())
        self.assertTrue(qs_emily.filter(name='Wuthering Heights').exists())
        # ...and excludes Jane Eyre
        self.assertFalse(qs_emily.filter(name='Jane Eyre').exists())

        with self.assertNumQueries(2):
            # 0 query for all chosen objects (already done)
            # 1 query for available objects
            # 1 query for counts
            choices = filter1.get_choices(qs_emily)

        # We should have a 'choices' that includes charlotte and anne
        self.assertTrue(unicode(anne) in [c.label for c in choices if c.link_type is FILTER_ADD])
        self.assertTrue(unicode(charlotte) in [c.label for c in choices if c.link_type is FILTER_ADD])

        # ... but not emily, because that is obvious and boring
        self.assertTrue(unicode(emily) not in [c.label for c in choices if c.link_type is FILTER_ADD])
        # emily should be in 'remove' links, however.
        self.assertTrue(unicode(emily) in [c.label for c in choices if c.link_type is FILTER_REMOVE])

        # Select again - should have sensible params
        anne_choice = [c for c in choices if c.label.startswith('Anne')][0]
        self.assertTrue(unicode(emily.pk) in anne_choice.params.getlist('authors'))
        self.assertTrue(unicode(anne.pk) in anne_choice.params.getlist('authors'))

        # Now do the second select:
        filter2 = ManyToManyFilter('authors', Book, anne_choice.params)

        qs_emily_anne = filter2.apply_filter(qs)

        # ...we should get a qs that includes Poems
        self.assertTrue(qs_emily_anne.filter(name='Poems').exists())
        # ... but not Wuthering Heights
        self.assertFalse(qs_emily_anne.filter(name='Wuthering Heights').exists())

        # The choices should contain just Emily and Anne to remove, and
        # Charlotte should have 'link_type' FILTER_ADD. Even though it
        # is the only choice, adding the choice is not necessarily the same as
        # not adding it (could have books by Emily and Anne, but not Charlotte)
        choices = filter2.get_choices(qs_emily_anne)
        self.assertEqual([(c.label, c.link_type) for c in choices],
                         [(unicode(emily), FILTER_REMOVE),
                          (unicode(anne), FILTER_REMOVE),
                          (unicode(charlotte), FILTER_ADD)])

    def test_manytomany_filter_invalid_query(self):
        self.do_invalid_query_param_test(lambda params:
                                             ManyToManyFilter('authors', Book, params),
                                         MultiValueDict({'authors':['xxx']}))
        self.do_missing_related_object_test(lambda params:
                                                ManyToManyFilter('authors', Book, params),
                                            MultiValueDict({'authors':['10000']}))

    def test_datetime_filter_multiple_year_choices(self):
        """
        Tests that DateTimeFilter can produce choices spanning a set of years
        (and limit to max_links)
        """
        # This does drill down, and has multiple values.
        f = DateTimeFilter('date_published', Book, MultiValueDict(), max_links=10)
        qs = Book.objects.all()

        # We have enough data that it will not show a simple list of years.
        choices = f.get_choices(qs)
        self.assertTrue(len(choices) <= 10)
        self.assertTrue('-' in choices[0].label)

    def test_datetime_filter_single_year_selected(self):
        params = MultiValueDict({'date_published':['1818']})
        f = DateTimeFilter('date_published', Book, params, max_links=10)
        qs = Book.objects.all()

        # Should get a number of books in queryset.
        qs_filtered = f.apply_filter(qs)

        self.assertEqual(list(qs_filtered),
                         list(qs.filter(date_published__year=1818)))
        # We only need 1 query if we've already told it what year to look at.
        with self.assertNumQueries(1):
            choices = f.get_choices(qs_filtered)

        # There are at least 2 books in 1818, in different months.
        self.assertTrue(len([c for c in choices if c.link_type == FILTER_ADD]) >= 2)
        self.assertEqual(len([c for c in choices if c.link_type == FILTER_REMOVE]), 1)

    def test_datetime_filter_year_range_selected(self):
        params = MultiValueDict({'date_published':['1813..1814']})
        f = DateTimeFilter('date_published', Book, params, max_links=10)
        qs = Book.objects.all()

        # Should get a number of books in queryset.
        qs_filtered = f.apply_filter(qs)

        start = date(1813, 1, 1)
        end = date(1815, 1, 1)
        self.assertEqual(list(qs_filtered),
                         list(qs.filter(date_published__gte=start,
                                        date_published__lt=end)))

        # We only need 1 query if we've already told it what years to look at,
        # and there is data for both years.
        with self.assertNumQueries(1):
            choices = f.get_choices(qs_filtered)

        # There are at least 2 books in 1813..1814, on different years
        self.assertEqual(len([c for c in choices if c.link_type == FILTER_REMOVE]), 1)
        self.assertEqual(len([c for c in choices if c.link_type == FILTER_ADD]), 2)
        self.assertEqual([c.label for c in choices if c.link_type == FILTER_ADD],
                         ['1813', '1814'])

    def test_datetime_filter_single_month_selected(self):
        params = MultiValueDict({'date_published':['1847-10']})
        f = DateTimeFilter('date_published', Book, params, max_links=10)
        qs = Book.objects.all()

        # Should get a number of books in queryset.
        qs_filtered = f.apply_filter(qs)

        self.assertEqual(list(qs_filtered),
                         list(qs.filter(date_published__year=1847,
                                        date_published__month=10)))

        # We only need 1 query if we've already told it what month to look at.
        with self.assertNumQueries(1):
            choices = f.get_choices(qs_filtered)

        # There are at least 2 books for Oct 1847, on different days
        self.assertTrue(len([c for c in choices if c.link_type == FILTER_ADD]) >= 2)
        self.assertEqual(len([c for c in choices if c.link_type == FILTER_REMOVE]), 1)

    def test_datetime_filter_month_range_selected(self):
        params = MultiValueDict({'date_published':['1818-08..1818-09']})
        f = DateTimeFilter('date_published', Book, params, max_links=10)
        qs = Book.objects.all()

        # Should get a number of books in queryset.
        qs_filtered = f.apply_filter(qs)

        start = date(1818, 8, 1)
        end = date(1818, 10, 1)
        self.assertEqual(list(qs_filtered),
                         list(qs.filter(date_published__gte=start,
                                        date_published__lt=end)))

        # We only need 1 query if we've already told it what months to look at,
        # and there is data for both months.
        with self.assertNumQueries(1):
            choices = f.get_choices(qs_filtered)

        self.assertEqual(len([c for c in choices if c.link_type == FILTER_REMOVE]), 1)
        # There are at least 2 books in this range, in different months
        self.assertEqual(len([c for c in choices if c.link_type == FILTER_ADD]), 2)
        self.assertEqual([c.label for c in choices if c.link_type == FILTER_ADD],
                         ['August', 'September'])

    def test_datetime_filter_single_day_selected(self):
        params = MultiValueDict({'date_published':['1847-10-16']})
        f = DateTimeFilter('date_published', Book, params, max_links=10)
        qs = Book.objects.all()

        # Should get a number of books in queryset.
        qs_filtered = f.apply_filter(qs)

        self.assertEqual(list(qs_filtered),
                         list(qs.filter(date_published__year=1847,
                                        date_published__month=10,
                                        date_published__day=16)))

        # We need 0 queries if we've already told it what day to look at.
        with self.assertNumQueries(0):
            choices = f.get_choices(qs_filtered)

        # There can be no add links.
        self.assertEqual(len([c for c in choices if c.link_type == FILTER_ADD]), 0)
        self.assertEqual(len([c for c in choices if c.link_type == FILTER_REMOVE]), 1)

    def test_datetime_filter_day_range_selected(self):
        params = MultiValueDict({'date_published':['1847-10-10..1847-10-23']})
        f = DateTimeFilter('date_published', Book, params, max_links=10)
        qs = Book.objects.all()

        # Should get a number of books in queryset.
        qs_filtered = f.apply_filter(qs)

        start = date(1847, 10, 10)
        end = date(1847, 10, 24)
        self.assertEqual(list(qs_filtered),
                         list(qs.filter(date_published__gte=start,
                                        date_published__lt=end)))

        # We only need 1 query if we've already told it what days to look at,
        # and there is data for more than one day.
        with self.assertNumQueries(1):
            choices = f.get_choices(qs_filtered)

        self.assertEqual(len([c for c in choices if c.link_type == FILTER_REMOVE]), 1)
        # There are at least 2 books in this range, on different days.
        add_choices = [c for c in choices if c.link_type == FILTER_ADD]
        self.assertTrue(len(add_choices) >= 2)

        self.assertTrue("16" in [c.label for c in add_choices])

    def test_datetime_filter_start_at_year(self):
        # Tests that the first filter shown is a year, not a day,
        # even if initial query gets you down to a day.
        params = MultiValueDict()
        qs = Book.objects.filter(id=1)
        f = DateTimeFilter('date_published', Book, params, max_links=10)

        choices = f.get_choices(qs)
        self.assertEqual(len(choices), 3)

        self.assertEqual(choices[0].link_type, FILTER_DISPLAY)
        self.assertEqual(choices[0].label, str(qs[0].date_published.year))

        self.assertEqual(choices[1].link_type, FILTER_DISPLAY)

        self.assertEqual(choices[2].link_type, FILTER_DISPLAY)
        self.assertEqual(choices[2].label, str(qs[0].date_published.day))

    def test_datetime_filter_select_year_display_month(self):
        # Tests that if a year is selected, and only one thing matches,
        # the month should be displayed in 'display' mode.
        qs = Book.objects.filter(id=1)
        params = MultiValueDict(dict(date_published=[str(qs[0].date_published.year)]))
        f = DateTimeFilter('date_published', Book, params, max_links=10, max_depth='month')

        choices = f.get_choices(qs)
        self.assertEqual(len(choices), 2)

        self.assertEqual(choices[0].link_type, FILTER_REMOVE)
        self.assertEqual(choices[0].label, str(qs[0].date_published.year))

        self.assertEqual(choices[1].link_type, FILTER_DISPLAY)

    def test_datetime_filter_max_depth(self):
        qs = Book.objects.all()
        params = MultiValueDict({'date_published':['1813']})
        f = DateTimeFilter('date_published', Book, params, max_depth='year')
        choices = f.get_choices(f.apply_filter(qs))
        self.assertEqual(len(choices), 1)
        self.assertEqual(choices[0].link_type, FILTER_REMOVE)

    def test_datetime_filter_invalid_query(self):
        self.do_invalid_query_param_test(lambda params: DateTimeFilter('date_published', Book, params, max_links=10),
                                         MultiValueDict({'date_published':['1818xx']}))

    def test_datetime_filter_empty_qs(self):
        """
        Tests that DateTimeFilter works when it is passed in an empty QuerySet.
        """
        f = DateTimeFilter('date_published', Book, MultiValueDict(), max_links=10)
        qs = Book.objects.filter(id=1000)

        qs_filtered = f.apply_filter(qs)
        choices = f.get_choices(qs_filtered)
        self.assertEqual(len(choices), 0)
        self.assertEqual(len(qs_filtered), 0)

    def test_datetime_filter_remove_broad(self):
        """
        If we remove a broader choice (e.g. year), the more specific choices
        (e.g. day) should be removed too.
        """
        # This should hold whichever order the params are defined:
        params1 = MultiValueDict({'date_published': ['1818-08-24',
                                                     '1818-08-24..1818-08-30',
                                                     '1818-08',
                                                     '1818-08..1818-10',
                                                     '1818..1819',
                                                     '1818']})
        params2 = MultiValueDict({'date_published': ['1818..1819',
                                                     '1818',
                                                     '1818-08..1818-10',
                                                     '1818-08',
                                                     '1818-08-24..1818-08-30',
                                                     '1818-08-24',
                                                     ]})

        for p in [params1, params2]:
            f = DateTimeFilter('date_published', Book, p)
            qs = Book.objects.all()
            qs_filtered = f.apply_filter(qs)
            choices = f.get_choices(qs_filtered)

            # First choice should be for '1818-1819' and remove all 'date_published'
            self.assertEqual(choices[0].label, '1818-1819')
            self.assertEqual(choices[0].link_type, FILTER_REMOVE)
            self.assertEqual(choices[0].params.getlist('date_published'),
                             [])

            self.assertEqual(choices[1].link_type, FILTER_REMOVE)
            self.assertEqual(choices[1].params.getlist('date_published'),
                             ['1818..1819'])

            self.assertEqual(choices[2].link_type, FILTER_REMOVE)
            self.assertEqual(choices[2].params.getlist('date_published'),
                             ['1818..1819',
                              '1818',
                              ])

            self.assertEqual(choices[3].link_type, FILTER_REMOVE)
            self.assertEqual(choices[3].params.getlist('date_published'),
                             ['1818..1819',
                              '1818',
                              '1818-08..1818-10',
                              ])

            self.assertEqual(choices[4].link_type, FILTER_REMOVE)
            self.assertEqual(choices[4].params.getlist('date_published'),
                             ['1818..1819',
                              '1818',
                              '1818-08..1818-10',
                              '1818-08',
                              ])

            self.assertEqual(choices[5].link_type, FILTER_REMOVE)
            self.assertEqual(choices[5].params.getlist('date_published'),
                             ['1818..1819',
                              '1818',
                              '1818-08..1818-10',
                              '1818-08',
                              '1818-08-24..1818-08-30',
                              ])


    def test_datetime_filter_drill_down_to_choice(self):
        """
        Tests that if there is a choice that can be displayed, it will drill
        down to reach it.
        """
        # Two birthdays in Jan 2011
        Person.objects.create(name="Joe", date_of_birth=date(2011, 1, 10))
        Person.objects.create(name="Peter", date_of_birth=date(2011, 1, 20))

        # Chosen year = 2011
        params = MultiValueDict({'date_of_birth':['2011']})

        f = DateTimeFilter('date_of_birth', Person, params)
        qs = Person.objects.all()
        qs_filtered = f.apply_filter(qs)
        choices = f.get_choices(qs_filtered)

        # Expect 2011 as remove link
        self.assertEqual(['2011'], [c.label for c in choices if c.link_type == FILTER_REMOVE])
        # Expect January as display
        self.assertEqual(['January'], [c.label for c in choices if c.link_type == FILTER_DISPLAY])
        # Expect '10' and '20' as choices
        self.assertEqual(['10', '20'], [c.label for c in choices if c.link_type == FILTER_ADD])

    def test_datetime_filter_remove_choices_complete(self):
        """
        Tests that in the case produced in test_datetime_filter_drill_down_to_choice,
        the remove links display correctly.
        """
        # Two birthdays in Jan 2011
        Person.objects.create(name="Joe", date_of_birth=date(2011, 1, 10))
        Person.objects.create(name="Peter", date_of_birth=date(2011, 1, 20))

        # Chosen year = 2011, and date = 2011-01-10
        params = MultiValueDict({'date_of_birth':['2011', '2011-01-10']})

        f = DateTimeFilter('date_of_birth', Person, params)
        qs = Person.objects.all()
        qs_filtered = f.apply_filter(qs)
        choices = f.get_choices(qs_filtered)

        self.assertEqual([('2011', FILTER_REMOVE),
                          ('January', FILTER_DISPLAY),
                          ('10', FILTER_REMOVE),
                          ],
                         [(c.label, c.link_type) for c in choices])

    def test_datetime_filter_bridge_from_multi_to_single(self):
        """
        Tests that bridge_choices will bridge from range (multi) choices to
        single choices.
        """
        # Two birthdays in Jan 2011
        Person.objects.create(name="Joe", date_of_birth=date(2011, 1, 10))
        Person.objects.create(name="Peter", date_of_birth=date(2011, 1, 20))

        # Chosen year = 2010 - 2011
        params = MultiValueDict({'date_of_birth':['2010..2011']})

        f = DateTimeFilter('date_of_birth', Person, params)
        qs = Person.objects.all()
        qs_filtered = f.apply_filter(qs)
        choices = f.get_choices(qs_filtered)

        # Expect 2010 - 2011 as remove link
        self.assertEqual(['2010-2011'], [c.label for c in choices if c.link_type == FILTER_REMOVE])
        # Expect 2011 and January as display
        self.assertEqual(['2011', 'January'], [c.label for c in choices if c.link_type == FILTER_DISPLAY])
        # Expect '10' and '20' as choices
        self.assertEqual(['10', '20'], [c.label for c in choices if c.link_type == FILTER_ADD])

    def test_datetime_filter_day_ranges_end(self):
        """
        Test that the ranges for day selection end at the right point (e.g. 31)
        """
        # September
        for i in range(1, 30):
            Person.objects.create(name="Joe", date_of_birth=date(2011, 9, i))

        params = MultiValueDict({'date_of_birth':['2011-09']})

        f = DateTimeFilter('date_of_birth', Person, params)
        qs = Person.objects.all()
        qs_filtered = f.apply_filter(qs)
        choices = f.get_choices(qs_filtered)
        self.assertEqual(choices[-1].label[-3:], "-30")

        # October
        for i in range(2, 31):
            Person.objects.create(name="Joe", date_of_birth=date(2011, 10, i))

        params = MultiValueDict({'date_of_birth':['2011-10']})

        f = DateTimeFilter('date_of_birth', Person, params)
        qs = Person.objects.all()
        qs_filtered = f.apply_filter(qs)
        choices = f.get_choices(qs_filtered)
        self.assertEqual(choices[-1].label[-3:], "-31")

    def test_numericrange_filter_simple_vals(self):
        # If data is less than max_links, we should get a simple list of values.
        filter1 = NumericRangeFilter('price', Book, MultiValueDict(), max_links=20)

        # Limit to single value to force the case
        qs = Book.objects.filter(price=Decimal('3.50'))

        # Should only take 2 queries - one to find out how many distinct values,
        # one to get the counts.
        with self.assertNumQueries(2):
            choices = filter1.get_choices(qs)

        self.assertEqual(len(choices), 1)
        self.assertTrue('3.5' in choices[0].label)

    def test_numericrange_filter_range_choices(self):
        # If data is more than max_links, we should get a range
        filter1 = NumericRangeFilter('price', Book, MultiValueDict(), max_links=8)

        qs = Book.objects.all()
        # Should take 3 queries - one to find out how many distinct values,
        # one to find a range, one to get the counts.
        with self.assertNumQueries(3):
            choices = filter1.get_choices(qs)

        self.assertTrue(len(choices) <= 8)
        total_count = sum(c.count for c in choices)
        self.assertEqual(total_count, qs.count())

        # First choice should be inclusive on first and last
        p0 = choices[0].params.getlist('price')[0]
        self.assertTrue('..' in p0)
        self.assertTrue('i' in p0.split('..')[0])
        self.assertTrue('i' in p0.split('..')[1])

        # Second choice should be exlusive on first,
        # inclusive on second.
        p1 = choices[1].params.getlist('price')[0]
        self.assertTrue('..' in p1)
        self.assertTrue('i' not in p1.split('..')[0])
        self.assertTrue('i' in p1.split('..')[1])

    def test_numericrange_filter_apply_filter(self):
        qs = Book.objects.all()

        # exclusive
        params1 = MultiValueDict({'price': ['3.50..4.00']})
        filter1 = NumericRangeFilter('price', Book, params1)
        qs_filtered1 = filter1.apply_filter(qs)
        self.assertEqual(list(qs_filtered1),
                         list(qs.filter(price__gt=Decimal('3.50'),
                                        price__lt=Decimal('4.00'))))

        # inclusive
        params2 = MultiValueDict({'price': ['3.50i..4.00i']})
        filter2 = NumericRangeFilter('price', Book, params2)
        qs_filtered2 = filter2.apply_filter(qs)
        self.assertEqual(list(qs_filtered2),
                         list(qs.filter(price__gte=Decimal('3.50'),
                                        price__lte=Decimal('4.00'))))

    def test_numericrange_filter_manual_ranges(self):
        """
        Test we can specify 'ranges' and it works as expected.
        """
        # Also tests that aggregation works as expected with regards to
        # lower/upper limits.
        qs = Book.objects.all()

        ranges = [(Decimal('3.50'), Decimal('5.00')),
                  (Decimal('5.00'), Decimal('6.00'))]
        # There are books with prices exactly equal to 3.50/5.00/6.00 which
        # makes this test real.

        self.assertTrue(qs.filter(price=Decimal('3.50')).exists())
        self.assertTrue(qs.filter(price=Decimal('5.00')).exists())
        self.assertTrue(qs.filter(price=Decimal('6.00')).exists())

        filter1 = NumericRangeFilter('price', Book, MultiValueDict(), ranges=ranges)
        choices = filter1.get_choices(qs)
        self.assertEqual(choices[0].count, qs.filter(price__gte=Decimal('3.50'), price__lte=Decimal('5.00')).count())
        self.assertEqual(choices[1].count, qs.filter(price__gt=Decimal('5.00'), price__lte=Decimal('6.00')).count())

    def test_numericrange_filter_manual_ranges_labels(self):
        """
        Test we can specify 'ranges' with manual labels
        """
        qs = Book.objects.all()

        ranges = [(Decimal('1.00'), Decimal('4.00'), "$4 or less"),
                  (Decimal('4.00'), Decimal('6.00'), "$4.00 - $6.00"),
                  (Decimal('6.00'), Decimal('100.00'), "More than $6")]

        filter1 = NumericRangeFilter('price', Book, MultiValueDict(), ranges=ranges)
        choices = filter1.get_choices(qs)
        self.assertEqual(choices[0].label, "$4 or less")
        self.assertEqual(choices[1].label, "$4.00 - $6.00")

    def test_numericrange_filter_drilldown(self):
        # Can specify to turn off drilldown
        # We shouldn't get drilldown if ranges is specified manually.

        params1 = MultiValueDict({'price': ['3.50i..5.00i']})
        filter1 = NumericRangeFilter('price', Book, params1, drilldown=False)

        qs = Book.objects.all()
        qs_filtered1 = filter1.apply_filter(qs)
        choices = filter1.get_choices(qs_filtered1)
        self.assertEqual(len(choices), 1)
        self.assertEqual(choices[0].link_type, FILTER_REMOVE)

    def test_order_by_count(self):
        """
        Tests the 'order_by_count' option.
        """
        filter1 = ForeignKeyFilter('genre', Book, MultiValueDict(), order_by_count=True)
        qs = Book.objects.all()
        choices1 = filter1.get_choices(qs)

        # Should be same after sorting by 'count'
        self.assertEqual(choices1, sorted(choices1, key=operator.attrgetter('count'), reverse=True))

        filter2 = ForeignKeyFilter('genre', Book, MultiValueDict(), order_by_count=False)
        choices2 = filter2.get_choices(qs)

        # Should be same after sorting by 'label' (that is equal to Genre.name,
        # and Genre ordering is by that field)
        self.assertEqual(choices2, sorted(choices2, key=operator.attrgetter('label')))


class TestCustomFilters(TestCase):

    fixtures = ['django_easyfilters_tests']

    def test_render_choice_object(self):
        for field, filter_class, test_str in [
            ('genre', ForeignKeyFilter, u"~~Fantasy"),
            ('authors', ManyToManyFilter, u"~~Charles"),
            ('binding', ValuesFilter, u"~~H~~"),
            ('binding', ChoicesFilter, u"~~Hardback~~"),
            ('price', NumericRangeFilter, re.compile(u"\~\~\d+")),
            ('date_published', DateTimeFilter, re.compile('\~\~\d{4}')),
            ]:

            class CustomFilter(filter_class):
                def render_choice_object(self, obj):
                    return u"~~%s~~" % super(CustomFilter, self).render_choice_object(obj)

            class BookFilterSet(FilterSet):
                fields = [
                    (field, {}, CustomFilter)
                    ]

            fs = BookFilterSet(Book.objects.all(), QueryDict(''))
            if hasattr(test_str, 'search'):
                self.assertTrue(test_str.search(fs.render()), "%s does not allow customization via render_choice_object" % filter_class)
            else:
                self.assertTrue(test_str in fs.render(), "%s does not allow customization via render_choice_object" % filter_class)
