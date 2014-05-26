try:
    from django.db.models.constants import LOOKUP_SEP
except ImportError:  # Django < 1.5 fallback
    from django.db.models.sql.constants import LOOKUP_SEP
from django.db.models.related import RelatedObject
from six import PY3


def python_2_unicode_compatible(klass):  # Copied from Django 1.5
    """
    A decorator that defines __unicode__ and __str__ methods under Python 2.
    Under Python 3 it does nothing.

    To support Python 2 and 3 with a single code base, define a __str__ method
    returning text and apply this decorator to the class.
    """
    if not PY3:
        klass.__unicode__ = klass.__str__
        klass.__str__ = lambda self: self.__unicode__().encode('utf-8')
    return klass


def get_model_field(model, f):
    parts = f.split(LOOKUP_SEP)
    opts = model._meta
    for name in parts[:-1]:
        rel = opts.get_field_by_name(name)[0]
        if isinstance(rel, RelatedObject):
            model = rel.model
            opts = rel.opts
        else:
            model = rel.rel.to
            opts = model._meta
    rel, model, direct, m2m = opts.get_field_by_name(parts[-1])
    return rel, m2m
