
standard_filter_mapping = {

}

class Filter(object):

    def get_choices(self, qs, params, request=None):
        pass

    def get_remove_link(self, params, request=None):
        pass

class FilterSet(object):

    filter_mapping = standard_filter_mapping
    include_count = True


    def __init__(self, params, queryset, request=None):
        self.params = params
        self.initial_queryset = queryset
        self.qs = self.apply_filters(params, queryset)

    def apply_filters(self, params, queryset):
        return queryset

    def render(self):
        pass

    def get_fields(self):
        return self.fields

    def get_filters(self):
        filters = []
        for f in fields:
            if isinstance(basestring, f):
                filters.append(get_filter_for_field(f))
            else:
                filters.append(f)
        return filters
