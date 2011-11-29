=======
Filters
=======
.. currentmodule:: django_easyfilters.filters

When you specify the ``fields`` attribute on a
:class:`~django_easyfilters.FilterSet` subclass, various different ``Filter``
classes will be chosen depending on the type of field. They are listed below,
with the keyword argument options that they take.

.. class:: Filter

   This is the base class for all filters, and provides some options:

   * ``query_param``:

     The parameter in the query string that will be used for this field.
     This can be useful for shortening the query strings that are generated.

   * ``order_by_count``:

     Default: False

     If ``True``, this will cause the choices to be sorted so that the choices
     with the largest 'count' appear first.

.. class:: ForeignKeyFilter

   This is used for ForeignKey fields

.. class:: ManyToManyFilter

   This is used for ManyToMany fields

.. class:: ChoicesFilter

   This is used for fields that have 'choices' defined (normally passed in to
   the field constructor). The choices presented will be in the order specified
   in 'choices'.

.. class:: DateTimeFilter

   This is the most complex of the filters, as it allows drill-down from year to
   month to day. It takes the following options:

   * ``max_links``

     Default: 12

     The maximum number of links to display. If the number of choices at any
     level does not fit into this value, ranges will be used to shrink the
     number of choices.

   * ``max_depth``

     Default: None

     If ``'year'`` or ``'month'`` is specified, the drill-down will be limited
     to that level.

.. class:: NumericRangeFilter

   This filter produces ranges of values for a numeric field. It is the default
   filter for decimal fields, but can also be used with integer fields. It
   attempts to make the ranges 'look nice' using rounded numbers in an automatic
   way. It uses 'drill-down' like DateTimeFilter.

   It takes the following options:

   * ``max_links``

     Default: 5

     The maximum number of links to display. If there are fewer distinct values
     than this in the data, single values will be shown, and ranges otherwise.

   * ``ranges``

     Default: None

     If this is specified, it will override the (initial) automatic range. The
     value should be a list of ranges, where each item in the list is either:

     * a two-tuple containing the beginning and end range values

     * a three-tuple containing the beginning and end range values
       and a custom label.

   * ``drilldown``

     Default: True

     If ``False``, only one level of choices will be displayed.

   The 'end points' of ranges are handled in the following way: the lower bound
   is exclusive, and the upper bound is inclusive, apart from for the first
   range, where both are inclusive. This is designed for a fairly intuitive
   behaviour.

.. class:: ValuesFilter

   This is the fallback that is used when nothing else matches.

.. _custom-filter-classes:

Custom Filter classes
=====================

As described in the :class:`~django_easyfilters.FilterSet` documentation, you
can provide your own Filter class for a field. If you do so, it is expected to
have the following API:

* ``__init__(field, model, params, **kwargs)``

  Constructor. ``field`` is the string identifying the field, ``model`` is the
  model class, ``params`` is a QueryDict (i.e. normally request.GET). ``kwargs``
  contains any custom options specified for the filter.

* ``apply_filter(qs)``

  This method takes the QuerySet ``qs`` and returns a QuerySet that has filters
  applied to it, where the filter parameters are defined in the ``params`` that
  were passed to the constructor. The method must be able to extract the
  relevant parameter, if it exists, and filter the QuerySet accordingly.

* ``get_choices(qs)``

  This method is passed a fully filtered QuerySet, and must return a list of
  choices to present to the user. The choices should be instances of
  ``django_easyfilters.filters.FilterChoice``, which has the attributes:

  * label: User presentable text string for the choice
  * link_type: choice of FILTER_ADD, FILTER_REMOVE, FILTER_DISPLAY
  * count: the number of items for this choice (only for FILTER_ADD)
  * params: parameters used to create a link for this option, as a QueryDict

If you want to use a provided Filter and subclass from it, at the moment only
the following additional methods are considered public:

* ``render_choice_object(choice)``

  This method is responsible for generating the label for a choice (whether it
  is an 'add' or 'remove' choice). It is passed a choice object that is derived
  either from the query string (for 'remove' choices) or from the database (for
  'add' choices).

  Different subclasses of Filter pass different types of object in. Currently
  the following can be relied on:

  * :class:`ForeignKeyFilter` and :class:`ManyToManyFilter` pass in the related
    database model instances as 'choice'.

  * :class:`ValuesFilter` and :class:`ChoicesFilter` pass in the underlying raw
    database value as 'choice'.

All other methods of Filter and subclasses are considered private implementation
details and may change without warning.


