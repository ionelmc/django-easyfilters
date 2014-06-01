from __future__ import unicode_literals

import math
import operator
import re
from datetime import date
from logging import getLogger

import six
from dateutil.relativedelta import relativedelta
from django import VERSION
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.dates import MONTHS

from .queries import date_aggregation
from .queries import numeric_range_counts
from .queries import value_counts
from .ranges import auto_ranges
from .utils import get_model_field
from .utils import python_2_unicode_compatible

logger = getLogger(__name__)


if six.PY3:
    # Support for __cmp__ implementation below
    def cmp(a, b):
        return (a > b) - (a < b)
    from functools import total_ordering
else:
    total_ordering = lambda c: c


try:
    from collections import namedtuple
    FilterChoice = namedtuple('FilterChoice', 'label count params link_type')
except ImportError:
    # We don't use it as a tuple, so this will do:
    class FilterChoice(object):
        def __init__(self, label, count, params, link_type):
            self.label, self.count, self.params, self.link_type = \
                label, count, params, link_type


FILTER_ADD = 'add'
FILTER_REMOVE = 'remove'
FILTER_DISPLAY = 'display'


class Filter(object):
    """
    A Filter creates links/URLs that correspond to some DB filtering,
    and can apply the information from a URL to filter a QuerySet.
    """

    # Public interface

    def __init__(self,
                 field,
                 model,
                 params,
                 query_param=None,
                 order_by_count=False,
                 sticky=False,
                 show_counts=True):
        self.field = field
        self.model = model
        self.params = params
        if query_param is None:
            query_param = field
        self.query_param = query_param
        self.order_by_count = order_by_count
        self.field_obj, m2m = get_model_field(self.model, self.field)

        if self.field_obj.rel is not None:
            self.rel_model = self.field_obj.rel.to
            self.rel_field = self.field_obj.rel.get_related_field()
        # Make chosen an immutable sequence, to stop accidental mutation.
        self.chosen = tuple(self.choices_from_params())
        self.sticky = sticky
        self.show_counts = show_counts

    def apply_filter(self, qs):
        """
        Apply the filtering defined in params (request.GET) to the queryset qs,
        returning the new QuerySet.
        """
        chosen = list(self.chosen)
        while len(chosen) > 0:
            lookup = self.lookup_from_choice(chosen.pop())
            if self.sticky:
                qs._next_is_sticky()
            qs = qs.filter(**lookup)
        return qs

    def get_choices(self, qs):
        """
        Returns a list of namedtuples containing (label (as a string), count,
        params, link type)
        """
        raise NotImplementedError()

    # Methods that are used by base implementation above

    def choices_from_params(self):
        out = []
        for p in self.params.getlist(self.query_param):
            try:
                choice = self.choice_from_param(p)
                out.append(choice)
            except ValueError:
                pass
        for p in self.params.getlist(self.query_param + '--isnull'):
            out.append(self.choice_from_param(None))
        return out

    def choice_from_param(self, param):
        """
        Returns a native Python object representing something that has been
        chosen for a filter, converted from the string value in param.
        """
        try:
            return self.field_obj.to_python(param)
        except ValidationError:
            raise ValueError()

    def lookup_from_choice(self, choice):
        """
        Converts a choice value to a lookup dictionary that can be passed to
        QuerySet.filter() to do the filtering for that choice.
        """
        return {self.field: choice}

    # Utility methods needed by most/all subclasses

    def param_from_choice(self, choice):
        return six.text_type(choice)

    def paramlist_from_choices(self, choices):
        """
        For a list of choices, return the parameter list that should be created.
        """
        return list(map(self.param_from_choice, choices))

    def build_params(self, add=Ellipsis, remove=()):
        """
        Builds a new parameter MultiDict.
        add is an optional item to add,
        remove is an option list of items to remove.
        """
        params = self.params.copy()
        chosen = list(self.chosen)
        for r in remove:
            chosen.remove(r)
        if add is not Ellipsis and add not in chosen:
            chosen.append(add)
        if NullChoice in chosen:
            params[self.query_param + "--isnull"] = ''
        else:
            params.pop(self.query_param + "--isnull", None)
        chosen = list(i for i in chosen if i is not NullChoice)
        if chosen:
            params.setlist(self.query_param,
                           self.paramlist_from_choices(chosen))
        else:
            params.pop(self.query_param, None)
        params.pop('page', None)  # links should reset paging
        return params

    def sort_choices(self, qs, choices):
        """
        Sorts the choices by applying order_by_count if applicable.

        See also sort_choices_custom.
        """
        if self.order_by_count:
            choices.sort(key=operator.attrgetter('count'), reverse=True)
        return choices

    def normalize_add_choices(self, choices):
        return choices

    def get_choices_remove(self, qs):
        chosen = self.chosen
        choices = []
        for choice in chosen:
            choices.append(FilterChoice(self.render_choice_object(choice),
                                        None,  # Don't need count for removing
                                        self.build_params(remove=[choice]),
                                        FILTER_REMOVE))
        return choices

    def render_choice_object(self, choice_obj):
        """
        Converts an object that is available for choosing (that usually is the
        result of a database lookup) or has been chosen already into a unicode
        object for display.

        The choice object could be the 'raw' query string or database value,
        or transformed into something more convenient (e.g. a model instance)
        """
        return six.text_type(choice_obj)


class SingleValueMixin(object):
    """
    A mixin for filters where the field conceptually has just one value.
    """
    def normalize_add_choices(self, choices):
        addchoices = [(i, choice) for i, choice in enumerate(choices)
                      if choice.link_type == FILTER_ADD]
        if len(addchoices) == 1:
            # No point giving people a choice of one, since all the results will
            # already have the selected value (apart from nullable fields, which
            # might have null)
            for i, c in addchoices:
                choices[i] = FilterChoice(label=choices[i].label,
                                          count=choices[i].count,
                                          link_type=FILTER_DISPLAY,
                                          params=None)
        return choices


class ChooseOnceMixin(SingleValueMixin):
    """
    A mixin for filters where you can only choose the filter once, and then
    remove the filter.
    """
    def get_choices(self, qs):
        choices_remove = self.get_choices_remove(qs)
        if len(choices_remove) > 0:
            return choices_remove
        else:
            choices_add = self.normalize_add_choices(self.get_choices_add(qs))
            return self.sort_choices(qs, choices_add)

    def get_choices_add(self, qs):
        raise NotImplementedError()


class ChooseAgainMixin(SingleValueMixin):
    """
    A mixin for filters where it is possible to choose the filter more than
    once.
    """
    # This includes drill down, as well as many-valued fields.
    def get_choices(self, qs):
        # In general, can filter multiple times, so we can have multiple remove
        # links, and multiple add links, at the same time.
        choices_remove = self.get_choices_remove(qs)
        choices_add = self.normalize_add_choices(self.get_choices_add(qs))
        choices_add = self.sort_choices(qs, choices_add)
        return choices_remove + choices_add


class RelatedObjectMixin(object):
    """
    Mixin for fields that need to validate params against related field.
    """
    def choice_from_param(self, param):
        try:
            return self.rel_field.to_python(param)
        except ValidationError:
            raise ValueError()


class SimpleQueryMixin(object):
    """
    Mixin for filters that do a simple DB query on main table to get counts.
    """
    def get_values_counts(self, qs):
        """
        Returns a SortedDict dictionary of {value: count}.

        The order is the underlying order produced by sorting ascending on the
        DB field.
        """
        if self.show_counts or self.order_by_count:
            return value_counts(qs, self.field)
        else:
            return dict((val, None)
                        for val, in qs.values_list(self.field)
                        .order_by(self.field).distinct())


class RangeFilterMixin(ChooseAgainMixin):

    # choice_type must be set to a class that provides the static method
    # 'from_param' and instance methods 'make_lookup' and 'display', and the
    # __cmp__ and __eq__ methods for sorting.
    choice_type = None

    def choice_from_param(self, param):
        return self.choice_type.from_param(param)

    def choices_from_params(self):
        choices = super(RangeFilterMixin, self).choices_from_params()
        choices.sort()
        return choices

    def lookup_from_choice(self, choice):
        return choice.make_lookup(self.field)

    def get_choices_remove(self, qs):
        # Due to drill down, if a broader param is removed, the more specific
        # params must be removed too. We assume we can do an ordering on
        # whatever 'choice' objects are in chosen, and 'greater' means 'more
        # specific'.
        chosen = list(self.chosen)
        out = []
        for i, choice in enumerate(chosen):
            to_remove = [c for c in chosen if c >= choice]
            out.append(FilterChoice(self.render_choice_object(choice),
                                    None,
                                    self.build_params(remove=to_remove),
                                    FILTER_REMOVE))
        return out


# Concrete filter classes that are used by FilterSet

class ValuesFilter(ChooseOnceMixin, SimpleQueryMixin, Filter):
    """
    Fallback Filter for various kinds of simple values.
    """
    def render_choice_object(self, choice):
        retval = super(ValuesFilter, self).render_choice_object(choice)
        if retval == u'':
            return u'(empty)'
        else:
            return retval

    def get_choices_add(self, qs):
        """
        Called by 'get_choices', this is usually the one to override.
        """
        count_dict = self.get_values_counts(qs)
        return [FilterChoice(self.render_choice_object(val),
                             count,
                             self.build_params(add=val),
                             FILTER_ADD)
                for val, count in count_dict.items()
                for val in (NullChoice if val is None else val,)]


class ChoicesFilter(ValuesFilter):
    """
    Filter for fields that have 'choices' defined.
    """
    # Need to do the following:
    # 1) ensure we only display options that are in 'choices'
    # 2) ensure the order is the same as in choices
    # 3) make display value = the second element in choices' tuples.
    def __init__(self, *args, **kwargs):
        super(ChoicesFilter, self).__init__(*args, **kwargs)
        self.choices_dict = dict(self.field_obj.flatchoices)

    def render_choice_object(self, choice):
        # 3) above
        return self.choices_dict.get(choice, choice)

    def get_choices_add(self, qs):
        count_dict = self.get_values_counts(qs)
        choices = []
        for val, display in self.field_obj.choices:
            # 1), 2) above
            if val in count_dict:
                choice = NullChoice if val is None else val
                choices.append(FilterChoice(self.render_choice_object(val),
                                            count_dict[val],
                                            self.build_params(add=choice),
                                            FILTER_ADD))
        return choices


class ForeignKeyFilter(ChooseOnceMixin,
                       SimpleQueryMixin,
                       RelatedObjectMixin,
                       Filter):
    """
    Filter for ForeignKey fields.
    """
    def choice_from_param(self, param):
        if param is None:
            return self.field_obj.to_python(param)
        else:
            choice_pk = super(ForeignKeyFilter, self).choice_from_param(param)
            lookup = {self.rel_field.name: choice_pk}
            try:
                obj = self.rel_model.objects.get(**lookup)
            except self.rel_model.DoesNotExist:
                raise ValueError("object does not exist in DB")
            return obj

    def param_from_choice(self, choice):
        if hasattr(choice, 'pk'):
            return six.text_type(choice.pk)
        else:
            return super(ForeignKeyFilter, self).param_from_choice(choice)

    def get_choices_add(self, qs):
        count_dict = self.get_values_counts(qs)
        lookup = {self.rel_field.name + '__in': count_dict.keys()}
        objs = self.rel_model.objects.filter(**lookup)
        choices = []

        null_count = (not self.chosen
                      and self.field_obj.null
                      and qs.filter(**{self.field + '__isnull': True}).count())
        if null_count:
            choices.append(FilterChoice(self.render_choice_object(NullChoice),
                                        null_count,
                                        self.build_params(add=NullChoice),
                                        FILTER_ADD))

        for o in objs:
            pk = getattr(o, self.rel_field.attname)
            choices.append(FilterChoice(self.render_choice_object(o),
                                        count_dict[pk],
                                        self.build_params(add=o),
                                        FILTER_ADD))

        return choices


class ManyToManyFilter(ChooseAgainMixin, RelatedObjectMixin, Filter):

    def get_values_counts(self, qs):
        # It is easiest to base queries around the intermediate table, in order
        # to get counts.
        through = self.field_obj.rel.through
        rel_model = self.rel_model

        assert rel_model != self.model, "Can't cope with this yet..."
        fkey_this = [f for f in through._meta.fields
                     if f.rel is not None and f.rel.to is self.model][0]
        fkey_other = [f for f in through._meta.fields
                      if f.rel is not None and f.rel.to is rel_model][0]

        # We need to limit items by what is in the main QuerySet (which might
        # already be filtered).
        m2m_objs = through.objects.filter(**{fkey_this.name + '__in': qs})

        # We need to exclude items in other table that we have already filtered
        # on, because they are not interesting.
        m2m_objs = m2m_objs.exclude(**{fkey_other.name + '__in': self.chosen})

        # Now get counts:
        field_name = fkey_other.name
        return value_counts(m2m_objs, field_name)

    def get_choices_add(self, qs):
        count_dict = self.get_values_counts(qs)
        # Now, need to lookup objects on related table, to display them.
        objs = self.rel_model.objects.filter(pk__in=count_dict.keys())

        return [FilterChoice(self.render_choice_object(o),
                             count_dict[o.pk],
                             self.build_params(add=o),
                             FILTER_ADD)
                for o in objs]

    def param_from_choice(self, choice):
        return six.text_type(choice.pk)

    def choices_from_params(self):
        # To create the model instances, we override this method rather than
        # choice_from_param in order to do a single bulk query rather than
        # multiple queries. So 'choice_from_param' technically returns the
        # wrong type of thing, since it returns PKs not instances.
        chosen_pks = super(ManyToManyFilter, self).choices_from_params()
        objs = self.rel_model.objects.filter(pk__in=chosen_pks)
        # Now need to get original order back. But also need to be aware
        # that some things may not exist in DB
        obj_dict = dict([(obj.pk, obj) for obj in objs])
        retval = []
        for c in chosen_pks:
            if c in obj_dict:
                retval.append(obj_dict[c])
        return retval


@total_ordering
class DateRangeType(object):

    all = {}  # Keep a cache, so that we have unique instances

    def __init__(self, level, single, label, regex):
        self.level, self.single, self.label = level, single, label
        self.regex = re.compile((r'^(%s)$' % regex) if single else
                                (r'^(%s)..(%s)$' % (regex, regex)))
        DateRangeType.all[(level, single)] = self

    def __repr__(self):
        return '<DateRange %d %s %s>' % (self.level,
                                         "single" if self.single else "multi",
                                         self.label)

    def __eq__(self, other):
        return self.__cmp__(other) == 0

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    def __cmp__(self, other):
        if other is None:
            return 1
        else:
            return cmp((self.level, self.single),
                       (other.level, other.single))

    @classmethod
    def get(cls, level, single):
        return cls.all[(level, single)]

    @property
    def dateattr(self):
        #  The attribute of a date object that we truncate
        #  to when collapsing results.
        return self.label

    @property
    def relativedeltaattr(self):
        # The attribute to use for calculations using relativedelta
        return self.label + 's'

    def drilldown(self):
        if self is DAY:
            return None
        if not self.single:
            return DateRangeType.get(self.level, True)
        else:
            # We always drill down to 'single', and then generate
            # ranges (i.e. multi) if appropriate.
            return DateRangeType.get(self.level + 1, True)


_y, _ym, _ymd = r'\d{4}', r'\d{4}-\d{2}', r'\d{4}-\d{2}-\d{2}'
YEARGROUP = DateRangeType(1,    False, 'year',  _y)
YEAR = DateRangeType(1,         True,  'year',  _y)
MONTHGROUP = DateRangeType(2,   False, 'month', _ym)
MONTH = DateRangeType(2,        True,  'month', _ym)
DAYGROUP = DateRangeType(3,     False, 'day',   _ymd)
DAY = DateRangeType(3,          True,  'day',   _ymd)


class NullChoice(object):
    def make_lookup(self, field_name):
        return {field_name+"__isnull": True}

    def display(self):
        return "(null)"
    __str__ = __repr__ = display

    def __cmp__(self, other):
        return 0 if other is NullChoice else 1

    def __eq__(self, other):
        return other is NullChoice

    range_type = values = None
NullChoice = NullChoice()


class AnyChoice(object):
    def make_lookup(self, field_name):
        return {}

    def display(self):
        return "(any)"
    __str__ = __repr__ = display

    def __cmp__(self, other):
        return 0 if other is AnyChoice else 1

    def __eq__(self, other):
        return other is AnyChoice

    range_type = values = None
AnyChoice = AnyChoice()


@python_2_unicode_compatible
@total_ordering
class DateChoice(object):
    """
    Represents a choice of date. Params are converted to this, and this is used
    to build new params and format links.

    It can represent a year, month or day choice, or a range (start, end, both
    inclusive) of any of these choice.
    """

    def __init__(self, range_type, values):
        self.range_type = range_type
        self.values = values

    def __str__(self):
        # This is called when converting to URL
        return '..'.join(self.values)

    def __repr__(self):
        return '<DateChoice %s %s>' % (self.range_type, self)

    def __eq__(self, other):
        return self.__cmp__(other) == 0

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    def __cmp__(self, other):
        # 'greater' means more specific.
        if other is None:
            return 1
        else:
            return cmp((self.range_type, self.values),
                       (other.range_type, other.values))

    def display(self):
        # Called for user presentable string
        if self.range_type.single:
            value = self.values[0]
            parts = value.split('-')
            if self.range_type is YEAR:
                return parts[0]
            elif self.range_type is MONTH:
                return six.text_type(MONTHS[int(parts[1])])
            elif self.range_type is DAY:
                return str(int(parts[-1]))
        else:
            return u'-'.join([DateChoice(
                             DateRangeType.get(self.range_type.level,
                                               True), [val]).display()
                for val in self.values])

    @staticmethod
    def datetime_to_value(range_type, dt):
        if range_type is YEAR:
            return '%04d' % dt.year
        elif range_type is MONTH:
            return '%04d-%02d' % (dt.year, dt.month)
        else:
            return '%04d-%02d-%02d' % (dt.year, dt.month, dt.day)

    @staticmethod
    def from_datetime(range_type, dt):
        return DateChoice(range_type,
                          [DateChoice.datetime_to_value(range_type, dt)])

    @staticmethod
    def from_datetime_range(range_type, dt1, dt2):
        return DateChoice(DateRangeType.get(range_type.level, False),
                          [DateChoice.datetime_to_value(range_type, dt1),
                           DateChoice.datetime_to_value(range_type, dt2)])

    @staticmethod
    def from_param(param):
        if param is None:
            return NullChoice
        for drt in DateRangeType.all.values():
            m = drt.regex.match(param)
            if m is not None:
                return DateChoice(drt, list(m.groups()))
        raise ValueError()

    def make_lookup(self, field_name):
        # It's easier to do this all using datetime comparisons than have a
        # separate path for the single year/month/day case.
        if self.range_type.single:
            start, end = self.values[0], self.values[0]
        else:
            start, end = self.values

        start_parts = list(map(int, start.split('-')))
        end_parts = list(map(int, end.split('-')))

        # Fill the parts we don't have with '1' so that e.g. 2000 becomes
        # 2000-1-1
        start_parts = start_parts + [1] * (3 - len(start_parts))
        end_parts = end_parts + [1] * (3 - len(end_parts))
        start_date = date(start_parts[0], start_parts[1], start_parts[2])
        end_date = date(end_parts[0], end_parts[1], end_parts[2])

        # Now add one year/month/day:
        end_date = end_date + \
            relativedelta(**{self.range_type.relativedeltaattr: 1})

        return {field_name + '__gte': start_date,
                field_name + '__lt':  end_date}


class DateTimeFilter(RangeFilterMixin, Filter):

    choice_type = DateChoice

    max_depth_levels = {'year': YEAR.level,
                        'month': MONTH.level,
                        None: DAY.level + 1}

    def __init__(self, *args, **kwargs):
        self.max_links = kwargs.pop('max_links', 12)
        self.max_depth = kwargs.pop('max_depth', None)
        assert self.max_depth in ['year', 'month', None]
        self.max_depth_level = self.max_depth_levels[self.max_depth]
        super(DateTimeFilter, self).__init__(*args, **kwargs)

    def render_choice_object(self, choice):
        return choice.display()

    def get_choices_remove(self, qs):
        chosen = list(self.chosen)
        out = []

        for i, choice in enumerate(chosen):
            # As for RangeFilterMixin, if a broader param is removed, the more
            # specific params must be removed too.
            to_remove = [c for c in chosen if c >= choice]
            out.append(FilterChoice(self.render_choice_object(choice),
                                    None,
                                    self.build_params(remove=to_remove),
                                    FILTER_REMOVE))
            # There can be cases where there are gaps, so we need to bridge
            # using FILTER_DISPLAY
            out.extend(self.bridge_choices(chosen[0:i+1], chosen[i+1:]))
        return out

    def get_choices_add(self, qs):
        chosen = list(self.chosen)
        if NullChoice in chosen:
            return []

        # For the case of needing to drill down past a single option
        # to get to some real choices, we define a recursive
        # function.

        def get_choices_add_recursive(chosen):
            range_type = None

            if len(chosen) > 0:
                range_type = chosen[-1].range_type.drilldown()
                if range_type is None:
                    return []

            if range_type is None:
                # Get some initial idea of range
                date_range = qs.aggregate(first=models.Min(self.field),
                                          last=models.Max(self.field))
                first = date_range['first']
                last = date_range['last']
                if first is None or last is None:
                    # No values, can't drill down:
                    return []
                if first.year == last.year:
                    if first.month == last.month:
                        range_type = DAY
                    else:
                        range_type = MONTH
                else:
                    range_type = YEAR

            if (VERSION >= (1, 6) and isinstance(self.field_obj,
                                                 models.fields.DateTimeField)):
                date_qs = qs.datetimes(self.field, range_type.label)
            else:
                date_qs = qs.dates(self.field, range_type.label)

            results = date_aggregation(date_qs)

            date_choice_counts = self.collapse_results(results, range_type)
            if len(date_choice_counts) == 1 and range_type is not None:
                # Single choice - recurse.
                single_choice, count = date_choice_counts[0]
                date_choice_counts_deeper = \
                    get_choices_add_recursive([single_choice])
                if len(date_choice_counts_deeper) == 0:
                    # Nothing there, so ignore
                    return date_choice_counts
                else:
                    # We discard date_choice_counts, because bridge_choices will
                    # make it up again.
                    return date_choice_counts_deeper
            else:
                return date_choice_counts

        date_choice_counts = get_choices_add_recursive(chosen)

        choices = []
        # Additional display links, to give context for choices if necessary.
        if len(date_choice_counts) > 0:
            choices.extend(self.bridge_choices(
                chosen, [choice for choice, count in date_choice_counts]))

        null_count = (not chosen
                      and qs.filter(**{self.field + '__isnull': True}).count())

        if null_count:
            choices.append(
                FilterChoice(self.render_choice_object(NullChoice),
                             null_count if self.show_counts else None,
                             self.build_params(add=NullChoice),
                             FILTER_ADD))

        for date_choice, count in date_choice_counts:
            if date_choice in chosen:
                continue

            # To ensure we get the bridge choices, which are useful, we check
            # self.max_depth_level late on and bailout here.
            if date_choice.range_type.level > self.max_depth_level:
                continue

            if (len(date_choice_counts) == 1 and
                (date_choice.range_type.level == self.max_depth_level or
                 count == 1)):
                link_type = FILTER_DISPLAY
            else:
                link_type = FILTER_ADD

            choices.append(FilterChoice(self.render_choice_object(date_choice),
                                        count if self.show_counts else None,
                                        self.build_params(add=date_choice),
                                        link_type))
        return choices

    def collapse_results(self, results, range_type):
        if len(results) > self.max_links:
            # If range_type is month/day, we don't want any possibility of the
            # buckets wrapping over to the next year/month, so we set first and
            # last accordingly
            if range_type is MONTH:
                first, last = 1, 12
            elif range_type is DAY:
                first, last = 1, ((results[0][0] + relativedelta(day=1))
                                  + relativedelta(months=1, days=-1)).day
            else:
                first = results[0][0].year
                last = results[-1][0].year

            # We need to split into even sized buckets, so it looks nice.
            span = last - first + 1
            bucketsize = int(math.ceil(float(span) / self.max_links))
            numbuckets = int(math.ceil(float(span) / bucketsize))

            buckets = [[] for i in range(numbuckets)]
            for row in results:
                val = getattr(row[0], range_type.dateattr)
                bucketnum = int(math.floor(float(val - first)/bucketsize))
                buckets[bucketnum].append(row)

            dt_template = results[0][0]
            date_choice_counts = []
            for i, bucket in enumerate(buckets):
                count = sum(row[1] for row in bucket)
                if count:
                    start_val = first + bucketsize * i
                    end_val = min(start_val + bucketsize, last)
                    start_date = dt_template.replace(
                        **dict({range_type.dateattr: start_val}))
                    end_date = dt_template.replace(
                        **dict({range_type.dateattr: end_val}))

                    choice = DateChoice.from_datetime_range(range_type,
                                                            start_date,
                                                            end_date)
                    date_choice_counts.append((choice, count))
        else:
            date_choice_counts = \
                [(DateChoice.from_datetime(range_type, dt), count)
                 for dt, count in results]
        return date_choice_counts

    def bridge_choices(self, chosen, choices):
        # Returns FILTER_DISPLAY type choices to bridge from what is chosen
        # (which might be nothing) to what can be chosen, to give context to the
        # link.

        # Note this is used in bridging to the 'add' choices, and in bridging
        # between 'remove' choices

        if len(choices) == 0:
            return []
        if len(chosen) == 0:
            chosen_level = 0
            bridge_to_single = False
        else:
            chosen_level = chosen[-1].range_type.level
            bridge_to_single = not chosen[-1].range_type.single

        # first choice in list can act as template, as it will have all the
        # values we need.
        new_choice = choices[0]
        new_level = new_choice.range_type.level

        retval = []
        while ((chosen_level < new_level - 1)
               or (chosen_level < new_level and bridge_to_single)):
            # If the first chosen was multi, first bridge just bridges to single
            if bridge_to_single:
                bridge_to_single = False
            else:
                chosen_level += 1
            if chosen_level > self.max_depth_level:
                continue
            date_choice = DateChoice(DateRangeType.get(chosen_level, True),
                                     new_choice.values)
            retval.append(FilterChoice(self.render_choice_object(date_choice),
                                       None, None,
                                       FILTER_DISPLAY))

        return retval


class RangeEnd(object):
    """
    Simple structure to store part of a range
    """
    def __init__(self, value, inclusive):
        # value is some generic value, inclusive is a bool specifying where this
        # value is included as part of the range.
        self.value, self.inclusive = value, inclusive


def make_numeric_range_choice(to_python, to_str):
    """
    Returns a Choice class that represents a numeric choice range,
    using the passed in 'to_python' and 'to_str' callables to do
    conversion to/from native data types.
    """
    @python_2_unicode_compatible
    @total_ordering
    class NumericRangeChoice(object):

        def __init__(self, values):
            # Values are instances of RangeEnd
            self.values = tuple(values)

        def display(self):
            return '-'.join([str(v.value) for v in self.values])

        @classmethod
        def from_param(cls, param):
            if param is None:
                return NullChoice

            vals = []
            for p in param.split('..', 1):
                inclusive = False
                if p.endswith('i'):
                    inclusive = True
                    p = p[:-1]

                try:
                    val = to_python(p)
                    vals.append(RangeEnd(val, inclusive))
                except ValidationError:
                    raise ValueError()
            return cls(vals)

        def make_lookup(self, field_name):
            if self.values is None:
                return {field_name: None}
            elif len(self.values) == 1:
                return {field_name: self.values[0].value}
            else:
                start, end = self.values[0], self.values[1]
                return {field_name + '__gt' +
                        ('e' if start.inclusive else ''): start.value,
                        field_name + '__lt' +
                        ('e' if end.inclusive else ''): end.value}

        def __str__(self):
            return '..'.join([to_str(v.value) + ('i' if v.inclusive else '')
                              for v in self.values])

        def __repr__(self):
            return '<NumericRangeChoice %s>' % self

        def __eq__(self, other):
            return self.__cmp__(other) == 0

        def __lt__(self, other):
            return self.__cmp__(other) < 0

        def __cmp__(self, other):
            # 'greater' means more specific.
            if other is None:
                return cmp(self.values, ())
            else:
                if other is NullChoice:
                    return -1
                if len(self.values) != len(other.values):
                    # one value is more specific than two
                    return -cmp(len(self.values), len(other.values))
                elif len(self.values) == 1:
                    return 0
                else:
                    # Larger difference means less specific
                    return -cmp(self.values[1].value - self.values[0].value,
                                other.values[1].value - other.values[0].value)

    return NumericRangeChoice


class NumericRangeFilter(RangeFilterMixin, SingleValueMixin, Filter):

    def __init__(self, field, model, params, **kwargs):
        self.max_links = kwargs.pop('max_links', 5)
        self.drilldown = kwargs.pop('drilldown', True)
        self.ranges = kwargs.pop('ranges', None)
        field_obj, _ = get_model_field(model, field)
        self.choice_type = make_numeric_range_choice(field_obj.to_python, str)
        super(NumericRangeFilter, self).__init__(field, model, params, **kwargs)

    def render_choice_object(self, c):
        if c is None:
            return str(None)
        if self.ranges is None:
            return c.display()
        if len(c.values) == 1:
            return c.display()
        for r in self.ranges:
            if r[0] == c.values[0].value and r[1] == c.values[1].value:
                # found a match in ranges
                if len(r) > 2:
                    # found a label, so use it
                    return r[2]
                else:
                    return c.display()
        return c.display()

    def get_choices_add(self, qs):
        chosen = list(self.chosen)
        if NullChoice in chosen or (not self.drilldown and len(chosen) > 0):
            return []

        all_vals = qs.values_list(self.field).distinct()

        num = all_vals.count()

        choices = []
        if num <= self.max_links:
            val_counts = value_counts(qs, self.field)
            for v, count in val_counts.items():
                choice = (NullChoice if v is None
                          else self.choice_type([RangeEnd(v, True)]))
                choices.append(FilterChoice(self.render_choice_object(choice),
                                            count if self.show_counts else None,
                                            self.build_params(add=choice),
                                            FILTER_ADD))
        else:
            null_count = (not chosen
                          and qs.filter(**{self.field +
                                           '__isnull': True}).count())
            if null_count:
                choice = NullChoice
                choices.append(FilterChoice(self.render_choice_object(choice),
                                            null_count if self.show_counts
                                            else None,
                                            self.build_params(add=choice),
                                            FILTER_ADD))
            if self.ranges is None:
                val_range = qs.aggregate(
                    lower=models.Min(self.field),
                    upper=models.Max(self.field)
                )
                ranges = auto_ranges(val_range['lower'],
                                     val_range['upper'],
                                     self.max_links)
            else:
                ranges = self.ranges

            if self.show_counts or self.order_by_count:
                val_counts = numeric_range_counts(qs, self.field, ranges)
            else:
                val_counts = dict((val, None) for val in ranges)
            for i, (vals, count) in enumerate(val_counts.items()):
                # For the lower bound, we make it inclusive only if it the first
                # choice. The upper bound is always inclusive. This gives
                # filters that behave sensibly e.g. with 10-20, 20-30, 30-40,
                # the first will include 10 and 20, the second will exlude 20.
                choice = self.choice_type([RangeEnd(vals[0], i == 0),
                                           RangeEnd(vals[1], True)])
                choices.append(FilterChoice(self.render_choice_object(choice),
                                            count,
                                            self.build_params(add=choice),
                                            FILTER_ADD))
        return choices
