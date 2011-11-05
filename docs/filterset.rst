=========
FilterSet
=========

.. currentmodule:: django_easyfilters.filterset

.. class:: FilterSet

   This is meant to be used by subclassing. The only required
   attribute is ``fields``, which must be a list of fields to produce filters
   for. For example, given the following model definition:

   .. code-block:: python

      class Book(models.Model):
          name = models.CharField(max_length=100)
          authors = models.ManyToManyField(Author)
          genre = models.ForeignKey(Genre)
          date_published = models.DateField()

   ...you could create a BookFilterSet like this:

   .. code-block:: python

       class BookFilterSet(FilterSet):
           fields = [
               'genre',
               'authors',
               'date_published',
           ]

   Each item in the fields attribute can also be a two-tuple containing first
   the field name and second a dictionary of options to be passed to the
   :doc:`filters <filters>` as keyword arguments, or a three-tuple containing
   the field name, a dictionary of options, and a Filter class. In this way you
   can override default options and the default filter type used e.g.:

   .. code-block:: python

       from django_easyfilters.filters import ValuesFilter

       class BookFilterSet(FilterSet):
           fields = [
               ('genre', dict(order_by_count=True)),
               ('date_published', {}, ValuesFilter),
           ]

   This also allows :ref:`custom Filter classes <custom-filter-classes>` to be used.

   To use the BookFilterSet, please see :doc:`the overview instructions
   <overview>`. The public API of ``FilterSet`` for use consists of:

   .. method:: __init__(queryset, params)

      queryset must be a QuerySet, which can already be filtered.

      params must be a QueryDict, normally request.GET.

   .. attribute:: qs

      This attribute contains the input QuerySet filtered according to the data
      in ``params``.

   .. attribute:: title

      This attribute contains a title summarising the filters that have
      been selected.

   In addition, there are methods/attributes that can be overridden to customise
   the FilterSet:

   .. method:: get_template(field_name)

      This method is called for each field in the filterset, with the field name
      being passed in.

      It is expected to return a Django Template instance. This template will
      then be rendered with the following Context data:

      * ``filterlabel`` - the label for the filter (derived from verbose_name of
        the field)
      * ``choices`` - a list of `choices` for the filter. Each one has the
        following attributes:

        * ``link_type``: either ``remove``, ``add`` or ``display``, depending
          on the type of the choice.

        * ``label``: the text to be displayed for this choice.

        * ``url`` for those that are ``remove`` or ``add``, a URL for selecting
          that filter.

        * ``count``: for those that are ``add`` links, the number of items in
          the QuerySet that match that choice.

   .. attribute:: template

      A string containing a Django template, used to render all the filters.  It
      is used by the default ``get_template`` method, see above.

   .. attribute:: title_fields

      By default, the fields used to create the ``title`` attribute are all
      fields specified in the ``fields`` attribute, in that order. Specify
      ``title_fields`` to override this.
