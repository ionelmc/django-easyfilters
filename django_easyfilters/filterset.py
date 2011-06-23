from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.utils.text import capfirst

from django_easyfilters.filters import FILTER_ADD, FILTER_REMOVE, FILTER_ONLY_CHOICE, \
    ValuesFilter, ChoicesFilter, ForeignKeyFilter, ManyToManyFilter


def non_breaking_spaces(val):
    # This helps a lot with presentation, by stopping the links+count from being
    # split over a line end.
    return mark_safe(u'&nbsp;'.join(escape(part) for part in val.split(u' ')))


class FilterSet(object):

    template = """
<div class="filterline"><span class="filterlabel">{{ filterlabel }}:</span>
{% for choice in remove_choices %}
  <span class="removefilter"><a href="{{ choice.url }}" title="Remove filter">{{ choice.label }}&nbsp;&laquo;&nbsp;</a></span>
{% endfor %}
{% for choice in add_choices %}
  <span class="addfilter"><a href="{{ choice.url }}" class="addfilter" title="Add filter">{{ choice.label }}</a>&nbsp;({{ choice.count }})</span>&nbsp;&nbsp;
{% endfor %}
{% for choice in only_choices %}
  <span class="onlychoice">{{ choice.label }}</span>
{% endfor %}
</div>
"""

    def __init__(self, queryset, params):
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
        field_obj = self.model._meta.get_field(filter_.field)
        choices = filter_.get_choices(qs, params)
        ctx = {'filterlabel': capfirst(field_obj.verbose_name)}
        ctx['remove_choices'] = [dict(label=non_breaking_spaces(c.label),
                                      url=u'?' + c.params.urlencode())
                                 for c in choices if c.link_type == FILTER_REMOVE]
        ctx['add_choices'] = [dict(label=non_breaking_spaces(c.label),
                                   url=u'?' + c.params.urlencode(),
                                   count=c.count)
                              for c in choices if c.link_type == FILTER_ADD]
        ctx['only_choices'] = [dict(label=non_breaking_spaces(c.label),
                                    count=c.count)
                               for c in choices if c.link_type == FILTER_ONLY_CHOICE]

        return self.get_template().render(template.Context(ctx))

    def get_template(self):
        return template.Template(self.template)

    def render(self):
        return mark_safe(u'\n'.join(self.render_filter(f, self.qs, self.params) for f in self.filters))

    def get_fields(self):
        return self.fields

    def get_filter_for_field(self, field, **kwargs):
        f, model, direct, m2m = self.model._meta.get_field_by_name(field)
        if f.rel is not None:
            if m2m:
                klass = ManyToManyFilter
            else:
                klass = ForeignKeyFilter
        elif f.choices:
            klass = ChoicesFilter
        else:
            klass = ValuesFilter
        return klass(field, self.model, **kwargs)

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
