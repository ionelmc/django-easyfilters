=======
Filters
=======
.. currentmodule:: django_easyfilters.filters

When you specify the ``fields`` attribute on a
:class:`~django_easyfilters.FilterSet` subclass, various different ``Filter``
classes will be chosen depending on the type of field. They are listed below,
with the keyword argument options that they take.

At the moment, all other methods of Filter and subclasses are considered private
implementation details, until all the Filters are implemented and the API firms
up.

.. class:: Filter

   This is the base class for all filters, and has provides some options:

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

   This is used for fields that have 'choices' defined. The choices presented
   will be in the order specified in 'choices'.

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

.. class:: ValuesFilter

   This is the fallback that is used when nothing else matches.
