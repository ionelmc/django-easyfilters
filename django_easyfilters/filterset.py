from collections import namedtuple

from django.db import models
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.utils.http import urlencode
from django.utils.text import capfirst

FilterChoice = namedtuple('FilterChoice', 'label count params')


class FilterOptions(object):
    """
    Defines some common options for all Filters.

    A FilterOption instance can be used when defining the 'fields' attribute of
    a FilterSet. The actual choice of Filter subclass will be done by the
    FilterSet in this case.
    """
    def __init__(self, field, query_param=None):
        # State: Filter objects are created as class attributes of FilterSets,
        # and so cannot carry any request specific state. They only have
        # configuration information.
        self.field = field
        if query_param is None:
            query_param = field
        self.query_param = query_param


class Filter(FilterOptions):
    """
    A Filter creates links/URLs that correspond to some DB filtering,
    and can apply the information from a URL to filter a QuerySet.
    """
    def apply_filter(self, qs, params):
        p_val = params.get(self.query_param, None)
        if p_val is None:
            return qs
        else:
            return qs.filter(**{self.field: p_val})

    def build_params(self, params, filter_val):
        params = params.copy()
        params[self.query_param] = filter_val
        params.pop('page', None) # links should reset paging
        return params

    def get_choices(self, qs, params):
        """
        Returns a list of namedtuples containing
        (label (as a string), count, url)
        """
        field_obj = qs.model._meta.get_field(self.field)

        # First get the IDs and counts in one query.
        ids_counts = qs.values_list(self.field).order_by(self.field).annotate(models.Count(self.field))

        # Then get the instances, so that we can get the unicode() of them,
        # using their normal manager to get them in normal order.
        rel_model = field_obj.rel.to
        rel_field = field_obj.rel.get_related_field()
        count_dict = {}
        for id, count in ids_counts:
            count_dict[id] = count

        # Filter to the ones relevant to our queryset:
        lookup = {rel_field.attname + '__in': [x[0] for x in ids_counts]}
        objs = rel_model.objects.filter(**lookup)
        choices = []

        for o in objs:
            id = getattr(o, rel_field.attname)
            choices.append(FilterChoice(unicode(o),
                                        count_dict[id],
                                        self.build_params(params, id)))
        return choices

    def get_remove_url(self, params, request=None):
        """
        Returns a URL for removing the filter, or None
        if the filter is not currently in use.
        """
        pass

    # TODO - move all this HTML specific stuff to FilterSet
    def render(self, qs, params):
        out = []
        field_obj = qs.model._meta.get_field(self.field)
        label = capfirst(field_obj.verbose_name)
        for c in self.get_choices(qs, params):
            out.append(u'<a href="%s">%s</a> (%d) &nbsp;&nbsp;' % (escape('?%s' % urlencode(c.params)), escape(c.label), c.count))
        return u'<div>%s: %s</div>' % (escape(label), u''.join(out))


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

    def render(self):
        return mark_safe(u'\n'.join(f.render(self.qs, self.params) for f in self.filters))

    def get_fields(self):
        return self.fields

    def get_filter_for_field(self, field, **kwargs):
        return Filter(field, **kwargs)

    def setup_filters(self):
        # This could run once, as soon as FilterSet is created
        filters = []
        for i, f in enumerate(self.get_fields()):
            if isinstance(f, basestring):
                f = self.get_filter_for_field(f)
            elif isinstance(f, FilterOptions):
                opts = f.__dict__.copy()
                field = opts.pop('field')
                f = self.get_filter_for_field(field, **opts)
            filters.append(f)
        return filters

    def __unicode__(self):
        return self.render()
