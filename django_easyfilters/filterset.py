from collections import namedtuple

from django.db import models
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

    def build_params(self, params, add=None, remove=False):
        params = params.copy()
        if remove:
            del params[self.query_param]
        else:
            params[self.query_param] = add
        params.pop('page', None) # links should reset paging
        return params

    def get_choices(self, qs, params):
        """
        Returns a list of namedtuples containing
        (label (as a string), count, url)
        """
        field_obj = qs.model._meta.get_field(self.field)
        rel_model = field_obj.rel.to
        rel_field = field_obj.rel.get_related_field()

        if self.query_param in params:
            # Already filtered on this, there is just one object.
            lookup = {rel_field.attname: params[self.query_param]}
            obj = rel_model.objects.get(**lookup)
            return [FilterChoice(unicode(obj),
                                 None, # Don't need count for removing
                                 self.build_params(params, remove=True),
                                 FILTER_REMOVE)]

        # Not filtered on this yet, need counts

        # First get the IDs and counts in one query.
        ids_counts = qs.values_list(self.field).order_by(self.field).annotate(models.Count(self.field))

        # Then get the instances, so that we can get the unicode() of them,
        # using their normal manager to get them in normal order.
        count_dict = {}
        for id, count in ids_counts:
            count_dict[id] = count

        # Filter to the ones relevant to our queryset:
        lookup = {rel_field.attname + '__in': [x[0] for x in ids_counts]}
        objs = rel_model.objects.filter(**lookup)
        choices = []

        for o in objs:
            pk = getattr(o, rel_field.attname)
            choices.append(FilterChoice(unicode(o),
                                        count_dict[pk],
                                        self.build_params(params, add=pk),
                                        FILTER_ADD))
        return choices


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
        field_obj = qs.model._meta.get_field(filter_.field)
        label = capfirst(field_obj.verbose_name)
        for c in filter_.get_choices(qs, params):
            if c.link_type == FILTER_REMOVE:
                out.append(u'%s <a href="%s" title="Remove filter" class="removefilter">[x]</a> ' % (escape(c.label), escape('?%s' % urlencode(c.params))))
            else:
                out.append(u'<a href="%s" class="addfilter">%s</a> (%d) &nbsp;&nbsp;' % (escape('?%s' % urlencode(c.params)), escape(c.label), c.count))
        return u'<div>%s: %s</div>' % (escape(label), u''.join(out))

    def render(self):
        return mark_safe(u'\n'.join(self.render_filter(f, self.qs, self.params) for f in self.filters))

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
