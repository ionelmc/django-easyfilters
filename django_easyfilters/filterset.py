from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.utils.text import capfirst

from django_easyfilters.filters import FILTER_ADD, FILTER_REMOVE, FILTER_DISPLAY, \
    ValuesFilter, ChoicesFilter, ForeignKeyFilter, ManyToManyFilter, DateTimeFilter


def non_breaking_spaces(val):
    # This helps a lot with presentation, by stopping the links+count from being
    # split over a line end.
    return mark_safe(u'&nbsp;'.join(escape(part) for part in val.split(u' ')))


class FilterSet(object):

    template = """
<div class="filterline"><span class="filterlabel">{{ filterlabel }}:</span>
{% for choice in choices %}
  {% if choice.link_type == 'add' %}
    <span class="addfilter"><a href="{{ choice.url }}" title="Add filter">{{ choice.label }}&nbsp;({{ choice.count }})</a></span>&nbsp;&nbsp;
  {% else %}
    {% if choice.link_type == 'remove' %}
    <span class="removefilter"><a href="{{ choice.url }}" title="Remove filter">{{ choice.label }}&nbsp;&laquo;&nbsp;</a></span>
    {% else %}
      <span class="displayfilter">{{ choice.label }}</span>
    {% endif %}
  {% endif %}
{% endfor %}
</div>
"""

    def __init__(self, queryset, params):
        self.params = params
        self.model = queryset.model
        self.filters = self.setup_filters()
        self.qs = self.apply_filters(queryset)

    def apply_filters(self, queryset):
        for f in self.filters:
            queryset = f.apply_filter(queryset)
        return queryset

    def render_filter(self, filter_, qs):
        field_obj = self.model._meta.get_field(filter_.field)
        choices = filter_.get_choices(qs)
        ctx = {'filterlabel': capfirst(field_obj.verbose_name)}
        ctx['choices'] = [dict(label=non_breaking_spaces(c.label),
                               url=u'?' + c.params.urlencode() \
                                   if c.link_type != FILTER_DISPLAY else None,
                               link_type=c.link_type,
                               count=c.count)
                          for c in choices]
        return self.get_template(filter_.field).render(template.Context(ctx))

    def get_template(self, field_name):
        return template.Template(self.template)

    def render(self):
        return mark_safe(u'\n'.join(self.render_filter(f, self.qs) for f in self.filters))

    def get_fields(self):
        return self.fields

    def get_filter_for_field(self, field):
        f, model, direct, m2m = self.model._meta.get_field_by_name(field)
        if f.rel is not None:
            if m2m:
                return ManyToManyFilter
            else:
                return ForeignKeyFilter
        elif f.choices:
            return ChoicesFilter
        else:
            type_ = f.get_internal_type()
            if type_ == 'DateField' or type_ == 'DateTimeField':
                return DateTimeFilter
            else:
                return ValuesFilter

    def setup_filters(self):
        filters = []
        for i, f in enumerate(self.get_fields()):
            if isinstance(f, basestring):
                opts = {}
                field_name = f
            else:
                opts = f[1]
                field_name = f[0]
            klass = self.get_filter_for_field(field_name)
            filters.append(klass(field_name, self.model, self.params, **opts))
        return filters

    def __unicode__(self):
        return self.render()
