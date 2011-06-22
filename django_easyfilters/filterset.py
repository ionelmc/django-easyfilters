from collections import namedtuple
import operator

from django.db import models
from django.utils.datastructures import SortedDict
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.utils.http import urlencode
from django.utils.text import capfirst

FILTER_ADD = 'add'
FILTER_REMOVE = 'remove'

FilterChoice = namedtuple('FilterChoice', 'label count params link_type')


class FilterOptions(object):
    """
    Defines some common options for all Filters.

    A FilterOption instance can be used when defining the 'fields' attribute of
    a FilterSet. The actual choice of Filter subclass will be done by the
    FilterSet in this case.
    """
    def __init__(self, query_param=None, order_by_count=False):
        self.query_param = query_param
        self.order_by_count = order_by_count

class Filter(FilterOptions):
    """
    A Filter creates links/URLs that correspond to some DB filtering,
    and can apply the information from a URL to filter a QuerySet.
    """
    def __init__(self, field, model, **kwargs):
        # State: Filter objects are created as class attributes of FilterSets,
        # and so cannot carry any request specific state. They only have
        # configuration information.
        self.field = field
        self.model = model
        if kwargs.get('query_param', None) is None:
            kwargs['query_param'] = field
        super(Filter, self).__init__(**kwargs)

    def apply_filter(self, qs, params):
        p_val = params.get(self.query_param, None)
        if p_val is None:
            return qs
        else:
            return qs.filter(**{self.field: p_val})

    def build_params(self, qs, params, add=None, remove=False):
        params = params.copy()
        if remove:
            del params[self.query_param]
        else:
            params[self.query_param] = add
        params.pop('page', None) # links should reset paging
        return params

    def get_values_counts(self, qs, params):
        """
        Returns a SortedDict dictionary of {value: count}
        """
        values_counts = qs.values_list(self.field).order_by(self.field).annotate(models.Count(self.field))

        count_dict = SortedDict()
        for val, count in values_counts:
            count_dict[val] = count
        return count_dict

    def sort_choices(self, qs, params, choices):
        """
        Sorts the choices by applying order_by_count if applicable.

        See also sort_choices_custom.
        """
        if self.order_by_count:
            choices.sort(key=operator.attrgetter('count'), reverse=True)
        else:
            choices = self.sort_choices_custom(qs, params, choices)
        return choices

    def sort_choices_custom(self, qs, params, choices):
        """
        Override this to provide a custom sorting method for a field. If sorting
        can be better done in the DB, it should be done in the get_choices_add
        method.
        """
        return choices

    def display_choice(self, qs, params, choice):
        retval = unicode(choice)
        if retval == u'':
            return u'(empty)'
        else:
            return retval

    def get_choices_add(self, qs, params):
        """
        Called by 'get_choices', this is usually the one to override.
        """
        count_dict = self.get_values_counts(qs, params)
        return [FilterChoice(self.display_choice(qs, params, val),
                             count,
                             self.build_params(qs, params, add=val),
                             FILTER_ADD)
                for val, count in count_dict.items()]

    def get_choices(self, qs, params):
        raise NotImplementedError()

    def choice_from_params(self, qs, params):
        return params[self.query_param]

    def get_choice_remove(self, qs, params):
        choice = self.choice_from_params(qs, params)
        return FilterChoice(self.display_choice(qs, params, choice),
                            None, # Don't need count for removing
                            self.build_params(qs, params, remove=True),
                            FILTER_REMOVE)


class SingleValueFilterMixin(object):

    def get_choices(self, qs, params):
        """
        Returns a list of namedtuples containing
        (label (as a string), count, url)
        """
        if self.query_param in params:
            # Already filtered on this, we just display a remove link.
            return [self.get_choice_remove(qs, params)]
        else:
            choices = self.get_choices_add(qs, params)

        return self.sort_choices(qs, params, choices)


class ValuesFilter(SingleValueFilterMixin, Filter):
    pass


class RelatedFilter(SingleValueFilterMixin, Filter):
    def __init__(self, *args, **kwargs):
        super(RelatedFilter, self).__init__(*args, **kwargs)
        self.field_obj = self.model._meta.get_field(self.field)
        self.rel_model = self.field_obj.rel.to
        self.rel_field = self.field_obj.rel.get_related_field()

    def choice_from_params(self, qs, params):
        lookup = {self.rel_field.attname: params[self.query_param]}
        return self.rel_model.objects.get(**lookup)

    def get_choices_add(self, qs, params):
        count_dict = self.get_values_counts(qs, params)
        lookup = {self.rel_field.attname + '__in': count_dict.keys()}
        objs = self.rel_model.objects.filter(**lookup)
        choices = []

        for o in objs:
            pk = getattr(o, self.rel_field.attname)
            choices.append(FilterChoice(unicode(o),
                                        count_dict[pk],
                                        self.build_params(qs, params, add=pk),
                                        FILTER_ADD))
        return choices


def non_breaking_spaces(val):
    return u'&nbsp;'.join(escape(part) for part in val.split(u' '))


class FilterSet(object):

    def __init__(self, queryset, params, request=None):
        self.params = params
        self.initial_queryset = queryset
        self.model = queryset.model
        self.filters = self.setup_filters()
        self.qs = self.apply_filters(queryset, params)

    def apply_filters(self, queryset, params):
        for f in self.filters:
            queryset = f.apply_filter(queryset, params)
        return queryset

    def render_filter(self, filter_, qs, params):
        out = []
        field_obj = self.model._meta.get_field(filter_.field)
        label = capfirst(field_obj.verbose_name)
        for c in filter_.get_choices(qs, params):
            if c.link_type == FILTER_REMOVE:
                out.append(u'<span class="removefilter"><span class="filterchoice">%s</span> <a href="%s" title="Remove filter">[&laquo;]</a></span> '
                           % (escape(c.label), escape(u'?' + urlencode(c.params))))
            else:
                out.append(u'<span class="addfilter"><a href="%s" class="addfilter">%s</a>&nbsp;(%d)</span>&nbsp;&nbsp; '
                           % (escape(u'?' + urlencode(c.params)), non_breaking_spaces(c.label), c.count))
        return (u'<div class="filterline"><span class="filterlabel">%s:</span> %s</div>'
                % (escape(label), u''.join(out)))

    def render(self):
        return mark_safe(u'\n'.join(self.render_filter(f, self.qs, self.params) for f in self.filters))

    def get_fields(self):
        return self.fields

    def get_filter_for_field(self, field, **kwargs):
        f = self.model._meta.get_field(field)
        if f.rel is not None:
            return RelatedFilter(field, self.model, **kwargs)
        else:
            return ValuesFilter(field, self.model, **kwargs)

    def setup_filters(self):
        filters = []
        for i, f in enumerate(self.get_fields()):
            if isinstance(f, basestring):
                f = self.get_filter_for_field(f)
            else:
                # (field name, FilterOptions)
                field = f[0]
                opts = f[1].__dict__.copy()
                f = self.get_filter_for_field(field, **opts)
            filters.append(f)
        return filters

    def __unicode__(self):
        return self.render()
